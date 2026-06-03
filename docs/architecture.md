# paper-prism architecture

This document explains how paper-prism turns a paper into a knowledge package, with
emphasis on the parts that are non-obvious: the five-phase slide pipeline, the
3-way subagent fan-out and *why it is split across model tiers*, and the batch
layer that runs the same pipeline over a hundred papers.

If you only want to *use* paper-prism, read `SKILL.md`. This document is for someone
deciding whether the design is sound, or who needs to extend it.

---

## The two flows are one pipeline

paper-prism has a single-paper flow and a batch flow, and they are deliberately the
same code path. The batch layer does not re-implement reading or rendering; it
just feeds the per-paper pipeline a longer queue and supervises it. Everything
below describes the per-paper pipeline first, then the thin batch wrapper on
top.

The richest output mode — the full slide package, triggered by "make a deck" /
"出 PPT" — runs all five phases. Lighter modes ("read X", "quick look") are
strict subsets: a full read runs Phase 1 setup + the Phase 2 *analysis* agent +
a save, and skips figures, tables, and rendering entirely. So the five-phase
pipeline is the superset worth understanding; the others are it with stages
removed.

---

## The five phases

```
                          paper-prism slide-package pipeline (per paper)

 ┌──────────────────────────────────────────────────────────────────────────┐
 │ PHASE 1 · SETUP                                              serial · <10s │
 │   load_config() → cfg, get_labels() → L                                    │
 │   resolve {method} {arxiv_id} {pdf_path} {title}   (§1.1 method-name)      │
 │   pick save mode A (vault) | B (next to PDF)                               │
 │   mkdir {project}/_slides/{method}/assets/                                 │
 └───────────────────────────────────┬──────────────────────────────────────┘
                                      │  constants are now frozen and inlined
                                      ▼
 ┌──────────────────────────────────────────────────────────────────────────┐
 │ PHASE 2 · 3-WAY SUBAGENT FAN-OUT          ONE message, three Agent calls   │
 │                                                                            │
 │   ┌─ Agent A · analysis ── model = cfg.models.analysis  (opus) ──────────┐ │
 │   │    twelve-question analysis + full note body                         │ │
 │   │    → .cache/{method}_qa.md   .cache/{method}_note_body.md                 │ │
 │   ├─ Agent B · figures ──── model = cfg.models.figures   (sonnet) ───────┤ │
 │   │    fetch_arxiv_html → parse_arxiv_figures → download_figures → verify │ │
 │   │    → assets/{method}_fig_*.png   .cache/{method}_figmap.json            │ │
 │   └─ Agent C · tables ───── model = cfg.models.tables    (sonnet) ───────┘ │
 │        render_pdf_pages → Read → crop_region (PIL)                         │
 │        → assets/{method}_table_*.png  .cache/{method}_tablemap.json          │
 │                                                                            │
 │   wall clock ≈ max(A,B,C) ≈ 70s    (serial would be ≈ 150s)               │
 │   cost: 1×opus + 2×sonnet per paper (~3× cheaper than 3×opus)             │
 └───────────────────────────────────┬──────────────────────────────────────┘
                                      │  three artifacts on disk
                                      ▼
 ┌──────────────────────────────────────────────────────────────────────────┐
 │ PHASE 3 · SYNTHESIZE                                              serial   │
 │   read qa.md + note_body.md + figmap.json + tablemap.json                  │
 │   fill slide-template.md   → {method}.slides.md   (1 page / figure+table)  │
 │   fill paper-note-template → {method}.md          (the DEEPEST artifact)   │
 │   swap <!-- FIGURE_N_PLACEHOLDER --> / <!-- TABLE_N_PLACEHOLDER -->        │
 │        with real embeds from figmap / tablemap                             │
 │                                                                            │
 │   note ⊋ deck:  the note is the full analysis;                            │
 │                 the deck is its visual condensation, not its index.        │
 └───────────────────────────────────┬──────────────────────────────────────┘
                                      ▼
 ┌──────────────────────────────────────────────────────────────────────────┐
 │ PHASE 4 · RENDER + BIND                       ONE message, parallel Bash   │
 │   marp {method}.slides.md --pdf  --allow-local-files -o …slides.pdf        │
 │   marp {method}.slides.md --pptx --allow-local-files -o …slides.pptx       │
 │   copy_paper_pdf(src_pdf, deck_dir, method)        ← original PDF co-located│
 │   inject_resources_block(note, …)        ┐                                 │
 │   append_to_slides_moc(slides_moc, …)    │ three idempotent binders        │
 │   update_project_moc(project_moc, …)     ┘ (+ bootstrap_project if needed) │
 └───────────────────────────────────┬──────────────────────────────────────┘
                                      ▼
 ┌──────────────────────────────────────────────────────────────────────────┐
 │ PHASE 5 · REPORT + CLEANUP                                                 │
 │   verify 5 artifacts (note · slides.md/pdf/pptx · original.pdf) + MOC rows │
 │   on success: purge_cache(.cache/) · rm -f /tmp/{method}_page-*.png (scratch)           │
 │   report output paths                                                      │
 └──────────────────────────────────────────────────────────────────────────┘
```

### Phase 1 · Setup (serial, <10s)

Setup is intentionally cheap and intentionally serial. Its only job is to
*freeze the constants* that every later phase depends on: the resolved method
name, the arXiv id, the PDF path, the title, the save mode, and the working
directory.

This matters because of Phase 2. The three subagents are isolated — they do not
see the main conversation — so every value they need must be inlined into their
prompts as a literal. If `{arxiv_id}` is still ambiguous, the fan-out cannot be
constructed correctly, which is exactly why "arxiv_id unresolved" is one of the
explicit *don't parallelize* conditions. Setup is the gate that guarantees the
fan-out is well-formed.

Config is loaded through `load_config()` and `get_labels()` from
`prism_config.py` — never hard-coded — so the same pipeline writes English or
Chinese headings, into whatever vault the user configured, with no code change.

### Phase 2 · The 3-way subagent fan-out

This is the heart of the design. In a single message the main agent issues three
`Agent` calls that run concurrently, each a self-contained task (their full
prompts live in `references/subagent-prompts.md`):

- **Agent A — analysis**, on `cfg.models.analysis` (**opus**). Produces the
  twelve-question analysis (`.cache/{method}_qa.md`) and the long-form note body
  (`.cache/{method}_note_body.md`). It writes `<!-- FIGURE_N_PLACEHOLDER -->` /
  `<!-- TABLE_N_PLACEHOLDER -->` markers where images will go, but does *not*
  fetch any images itself. This is the agent whose quality determines the depth
  of everything downstream, so it gets the strongest model.
- **Agent B — figures**, on `cfg.models.figures` (**sonnet**). Runs the
  recommended extraction path: `fetch_arxiv_html()` → `parse_arxiv_figures()` →
  `download_figures()`, then Reads each image to confirm it matches its caption
  (arXiv HTML's `xN` ids do not map 1:1 onto printed Figure numbers). Emits
  `.cache/{method}_figmap.json`.
- **Agent C — tables**, on `cfg.models.tables` (**sonnet**). Runs the table
  iron-rule SOP: `render_pdf_pages()` at 200 DPI → Read each page to locate the
  pixel box → `crop_region()` (PIL) to cut the table out of the original.
  Emits `.cache/{method}_tablemap.json`.

**Why split across model tiers.** Agents B and C are mechanical. Figure
download is "parse HTML, fetch the listed `src`s, eyeball that the picture
matches the caption." Table extraction is "render a page, find a bounding box,
crop." Neither needs frontier reasoning; sonnet does them reliably. Only Agent
A — reading the intro/method/experiments, extracting the core insight,
explaining the math, inferring unstated limitations — actually benefits from
opus.

So the natural decomposition (one reasoning task, two extraction tasks) lines up
exactly with a cost decomposition. As `SKILL.md` notes, 50 papers cost roughly
`opus×50 + sonnet×100`. Had all three agents run on opus it would be
`opus×150`. With sonnet at a small fraction of opus's price, the mixed-tier
split lands around **~3× cheaper than all-opus**, with no loss of analysis
quality — the part you would not want to economize on is the only part still on
opus.

**Why fan out at all (wall clock).** The three tasks are genuinely independent:
A reads the PDF text, B hits arXiv's HTML, C rasterizes PDF pages. Run serially
they sum — roughly **~150s**. Run concurrently the wall clock collapses to the
slowest single agent, roughly **~70s**. The analysis agent is usually the long
pole, so you pay close to "just the analysis" latency while figures and tables
come along for free. Over a 50-paper batch that ~80s/paper saving compounds into
hours.

**The contract that makes isolation safe.** The three agents never touch the
same files. A writes only to `.cache/*_qa.md` and `.cache/*_note_body.md`; B writes
images plus `figmap.json`; C writes images plus `tablemap.json`. A leaves
placeholders rather than embedding paths, so it doesn't need to know what B and
C will produce. Phase 3 is the only place the three streams meet. This clean cut
is what lets them run blind to each other without races.

### Phase 3 · Synthesize (serial)

The main agent now reads all three artifacts back and assembles two documents
from templates:

- the **slide deck** (`slide-template.md` → `{method}.slides.md`): one page per
  figure and per table, each with a "read-key" box, organized by twelve-question
  section dividers;
- the **main note** (`paper-note-template.md` → `{method}.md`).

It replaces every `<!-- FIGURE_N_PLACEHOLDER -->` / `<!-- TABLE_N_PLACEHOLDER -->`
left by Agent A with the real `![[...]]` embed, looked up from `figmap.json` /
`tablemap.json`.

**Note vs deck — the relationship to internalize.** The note is the *deepest*
artifact and the canonical one: full contributions, per-module method walk-through,
formula triplets, per-figure and per-table sections, critique, related work, and
a twelve-question cheat-sheet. The deck is the note's **visual condensation** —
the same understanding compressed to ~30–40 slides for studying and sharing. The
deck is explicitly *not* an index of the note; if you want to know what the paper
actually says, you read the note. Keeping this hierarchy straight is why Phase 3
generates the note in full rather than deriving it from the slides.

### Phase 4 · Render + Bind (parallel Bash + Python)

Two kinds of work, all dispatched in one message so they run concurrently.

*Render* — `marp` converts the deck markdown to both PDF and PPTX
(`marp_render()` wraps this for direct calls). PDF is for inline embedding and
browsing; PPTX is the editable deck.

*Bind* — the three-piece Obsidian binding, via three **idempotent** functions
that are safe to re-run on every pass:

- `copy_paper_pdf(src_pdf, deck_dir, method)` — co-locates the original PDF into
  the deck folder as `{method}.pdf`. It compares file sizes and skips the copy
  if the destination already matches, so re-runs are no-ops.
- `inject_resources_block(note, …)` — inserts or refreshes the resources block
  at the top of the note. Critically, it replaces only from the heading up to
  (but not into) the next `#`/`##` heading, and bails out entirely if there is
  no following heading. That guard is what lets paper-prism refresh links on a note a
  human has been hand-editing **without ever swallowing their prose**.
- `append_to_slides_moc(slides_moc_path(cfg), …)` — adds or updates this paper's
  row in the global `Slide Library.md`, matched by `[[method_name]]` and updated
  in place, inserted after the last table row (never appended after trailing
  prose).
- `update_project_moc(project_moc_path(project, cfg), …)` — adds or updates the
  paper's row in the per-project reading queue, maintaining the running index.
  If the project MOC does not exist yet, `bootstrap_project(project, cfg)`
  creates it first.

Every binder matches existing rows/blocks and edits them in place rather than
appending blindly, which is precisely what makes the whole pipeline re-runnable:
process the same paper twice and you get one row, one resources block, one copy
of the PDF — not duplicates.

### Phase 5 · Report + Cleanup

Verify the five expected artifacts exist (note; `slides.md`/`pdf`/`pptx`; the
copied original PDF) and that the MOC rows landed. On success, `purge_cache()`
the per-paper `.cache/` (its qa / note_body / figmap / tablemap exchange files)
and delete the rendered page PNGs from `/tmp`; then report the output paths.
The `.cache/` is **durable until success** — that is exactly what lets a crash
resume from the missing phase (see Checkpoint & resume below); only the page
PNGs and the progress/error logs in `/tmp` are throwaway scratch.

### Parallel vs serial, per phase

| Trigger | Phase 2 | Phase 4 |
|---|---|---|
| default | fan-out A/B/C | parallel render + bind |
| "run serially" / "debug mode" / "串行" | fully serial | fully serial |
| "analysis only" / "no slides" | Agent A only | (no render) |
| "just the figures/tables" / "preprocess" | Agents B + C only | (no render) |

---

## Batch architecture

Batch processing (folder, Zotero collection, YAML queue, Zotero query — Modes
2–5 in `SKILL.md`) is a thin supervisory layer over the per-paper pipeline. It
adds exactly three things: a driver, a coordinator-per-paper pattern, and the
bookkeeping for resumability and error isolation.

```
                         batch layer (Modes 2–5)

   queue source ──────────────────────────────────────────────┐
   folder_to_queue() | zotero_collection_to_queue() |          │
   parse_paper_queue(papers.yaml) | Zotero SQL                 │
                                   │                           │
                                   ▼                           │
   ┌──────────────────── /loop master prompt ────────────────────────────┐
   │  scan queue → dedup vs existing artifacts (>50KB slides.pdf check)    │
   │  each iteration: spawn cfg.parallel paper-coordinator subagents       │
   │  stop when the queue is empty                                         │
   └─────────┬───────────────┬───────────────┬───────────────────────────┘
             ▼               ▼               ▼      (cfg.parallel at a time)
        coordinator      coordinator      coordinator
         (paper 1)        (paper 2)        (paper 3)
             │                │                │
             │  each coordinator runs the FULL Phase 1–5 pipeline,
             │  and itself fans out its own Agent A/B/C in Phase 2
             ▼                ▼                ▼
        append OK → /tmp/prism_progress.log
        on failure → /tmp/prism_errors.log   (never blocks the next iteration)
```

### How `/loop` drives it

A `/loop` master prompt is the driver. Each loop iteration: scan the queue,
dedup against artifacts already on disk, spawn up to `cfg.parallel` (default 4)
paper-coordinator subagents, and stop once the queue empties. The master prompt
and the coordinator prompt are both in `references/subagent-prompts.md` § Batch
Coordinator.

### The per-paper coordinator (fan-out of fan-outs)

The unit of batch work is a **coordinator subagent per paper**, and this is the
key structural point: a coordinator is not a worker — it is a small orchestrator
that runs the entire Phase 1–5 pipeline for its one paper, *including spinning
up its own Agent A/B/C fan-out in Phase 2*. So the concurrency is two levels
deep: `/loop` runs `cfg.parallel` coordinators at once, and each coordinator
runs three subagents at once.

This nesting is what keeps the batch flow honest about being "the same
pipeline." There is no separate batch renderer or batch analyzer; a batch is
literally N independent invocations of the single-paper pipeline, supervised.

### Resumability

A paper counts as **done** if
`{project}/_slides/{method}/{method}.slides.pdf` exists *and is larger than
50 KB*. The size floor is deliberate: an empty or failed render can still leave
a tiny PDF behind, so existence alone would falsely mark it complete; >50 KB
means real content was rendered. The master prompt dedups against this check at
the top of every iteration, so a batch can be interrupted (Ctrl-C, crash, quota
exhaustion) and simply re-run — it skips finished papers and resumes the rest.
Combined with the idempotent binders, re-running a partially-complete batch is
always safe.

### Error isolation

Failures are logged and never block. A coordinator that fails appends to
`/tmp/prism_errors.log`; successes append to `/tmp/prism_progress.log`; the next
`/loop` iteration proceeds regardless. One unparseable PDF or one paper with no
arXiv HTML cannot stall a 100-paper run. The cost of this choice — and paper-prism
accepts it knowingly — is that batches complete with partial coverage by design:
you finish the run, then read the error log and re-drive the stragglers (often
the ones that hit the "ask the user" rung of method-name extraction, or whose
figures were vector-only).

---

## When NOT to parallelize

Parallelism has overhead and failure modes; paper-prism is explicit about when to
turn it off:

- **`arxiv_id` is unresolved.** Phase 1 cannot finalize the constants the
  fan-out needs to inline, so the three agents cannot be constructed correctly.
  Resolve the id (or fall back to PDF-only extraction) first.
- **The paper is very short (<5 pages).** Serial is ~30s anyway; the fan-out's
  setup and coordination overhead is not worth it.
- **Debugging a single stage.** Use the "run serially" / "串行" / "debug mode"
  trigger. Stepping through A → B → C in order makes it obvious which stage
  produced a bad artifact; a three-way concurrent failure is much harder to
  attribute.

The honest tradeoff: the fan-out is a latency-and-cost optimization for the
common case (a normal-length paper with an arXiv id). For the uncommon cases —
ambiguous identity, tiny papers, or active debugging — serial execution is
simpler and the parallel speedup does not pay for itself.

---

## Where the pieces live

- Pipeline phases and triggers — `skills/paper-prism/SKILL.md` (Step 4-bis)
- Subagent A/B/C prompts + `/loop` master + batch coordinator —
  `skills/paper-prism/references/subagent-prompts.md`
- Deterministic building blocks (render / crop / figures / marp / the three
  binders / queue parsing) — `skills/paper-prism/assets/prism_helpers.py`
- Config, model tiers, i18n labels, derived paths —
  `skills/paper-prism/assets/prism_config.py`
