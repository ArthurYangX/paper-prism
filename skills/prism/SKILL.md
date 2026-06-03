---
name: prism
description: |
  Refract one paper — or a whole library — into a structured Obsidian knowledge
  package: a deep main note, a slide deck (PDF + editable PPTX), and a linked
  concept graph. Batch-first: same flow for one arXiv link or an entire Zotero
  collection.

  Use when the user wants to read, analyze, summarize, or make slides from an
  academic paper, or batch-process a folder / Zotero collection of papers.

  Triggers (EN): "read paper", "analyze paper", "summarize paper", "make a deck",
  "make slides", "make a PPT", "batch these papers", "process my Zotero collection".
  Triggers (ZH): "读一下", "帮我读", "分析这篇", "做成slide", "出PPT", "生成幻灯片",
  "批量处理", "读一下 Zotero 里的 XXX".
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch
---

# prism — paper → notes + slides + concept graph

> **One paper, refracted.** Twelve-question deep read · per-figure/table slide deck ·
> three-piece Obsidian binding · parallel subagents for scale.

prism turns a PDF/arXiv/Zotero reference into:
1. **a main note** — the deepest artifact: twelve-question analysis, formula
   triplets, every figure & table explained, `[[concept]]` links;
2. **a slide deck** — a ~30-page Marp deck (PDF + editable PPTX), one page per
   figure/table, the visual condensation of the note;
3. **graph links** — concept notes, a project reading-queue, and a global slide
   index, all auto-updated.

The single-paper flow and the batch flow are the same pipeline — batch just
feeds it a longer queue.

---

## Step 0 · Load config

Read configuration via the helper (never hard-code paths):

```bash
python3 skills/prism/assets/prism_config.py   # prints resolved config + labels
```

In Python the pipeline uses:

```python
from prism_config import load_config, get_labels, notes_path, project_path, \
    slides_moc_path, project_moc_path
cfg = load_config()        # vault_path, notes_folder, default_project, zotero_*, lang, models, ...
L   = get_labels(cfg)      # output headings (English by default; lang:"zh" for Chinese)
```

Config resolves from `$PRISM_CONFIG` → `assets/config.json` → `~/.config/prism/config.json`
→ built-in defaults. Copy `assets/config.example.json` → `assets/config.json` and edit.
Output headings are **i18n** — set `"lang": "en"` or `"zh"`, or override single
labels under `"labels"`.

---

## Step 0-ter · Input modes (5) — **batch-first**

The pipeline is identical for one paper and a hundred; only the *queue source*
differs.

| Mode | Trigger | Queue source | Scale |
|------|---------|--------------|-------|
| **1 · Single** | `read X.pdf` / `读一下 X` / `make a deck for X` | one item | 1 |
| **2 · Folder** | `batch /path/` / `处理 /path/ 下所有 PDF` | `folder_to_queue()` | 5–100 |
| **3 · Zotero collection** | `process my Zotero "CIL" collection` / `读 Zotero 里 X 分类` | `zotero.zotero_collection_to_queue()` | 10–200 |
| **4 · YAML queue file** | `batch from papers.yaml` | `parse_paper_queue()` | reproducible |
| **5 · Zotero query** | `process Zotero papers tagged X` | SQL → queue | filtered |
| **6 · References / .bib** | `process this paper's references` / `batch from refs.bib` | `prism_refs.parse_bib()` / `parse_references_from_text()` | a citation neighbourhood |
| **7 · Discovery source** | `today's papers → deck the top 5` / `find papers on X → process them` / `batch from digest.json` | `prism_refs.load_discovery()` → `discovery_to_queue()` | a recommender feed |

Modes 1–6 are "you point at papers you have". **Mode 7 is "a discovery source
brings papers to you"** — see below.

**Mode 4 (YAML) is the recommended batch entry** — git-versionable, resumable,
per-paper overrides. Spec: `assets/queue-format.md`.

**Mode 6 (references / .bib)** reads a whole citation list and turns it into a
queue (`assets/prism_refs.py`):
- `.bib` (preferred, high fidelity): `parse_bib(path)` pulls each entry's arXiv
  id (from `eprint`/`archivePrefix`/`journal`/`url`), DOI, and title.
- a paper's PDF bibliography: `references_text_from_pdf(pdf)` →
  `parse_references_from_text(text)` extracts arXiv ids reliably and titles
  best-effort (PDF reference parsing is fuzzy — prefer `.bib`).
- `refs_to_queue(entries, project)` maps arXiv-bearing refs to `arxiv:` items and
  the rest to `zotero:` (title search), producing a runnable queue. CLI:
  `python3 assets/prism_refs.py bib refs.bib` or `... pdf paper.pdf`.

**Mode 7 (discovery sources) — separate by design.** prism does NOT scrape or
score papers; discovery stays in dedicated upstream skills. prism only *ingests*
their output and refracts the keepers. The handoff contract is a JSON list:

```json
[ {"title": "...", "arxiv": "2312.00752", "score": 9.5, "why": "selective SSM"}, ... ]
```

Field names are matched leniently (`arxiv_id`/`id`/`url`, `tldr`/`reason`/`score`/`rating`).
`load_discovery(path)` normalizes it; `discovery_to_queue(items, project, top_k=, min_score=)`
sorts by score, takes the top, maps score→priority and why→relevance, and emits a
runnable queue. CLI: `python3 assets/prism_refs.py discovery digest.json --top 5`.

Selectable discovery front-ends (each is an independent skill / tool — pick one):
- **today's papers** → a daily-digest skill (e.g. `daily-papers` `fetch_and_score.py`
  → `daily_papers_top30.json`) → `discovery digest.json` → process the picks.
- **topic search** → a lit-search skill (e.g. `research-lit "topic" — sources: ...`,
  `semantic-scholar`, `arxiv`) → export its hits as the JSON above (or a `.bib`) →
  feed prism.
- **your own recommender** → emit the JSON contract; prism doesn't care how you got it.

If a discovery skill is present, the main agent may invoke it and pipe its output;
if not, the user runs discovery themselves and hands prism the JSON/`.bib`. Either
way prism stays the deep-processing backend.

**Always surface `_dropped`.** `refs_to_queue` / `discovery_to_queue` return a
`_dropped` count for entries with no usable id or title. When it's > 0, tell the
user (e.g. "40 references → 31 queued, 9 dropped (no arXiv id or title)") — never
let papers vanish silently.

Single-paper reference forms (Mode 1): local `*.pdf`, `arxiv:2312.00752`, an
arXiv URL, `Zotero: Mamba` (title search), or a Zotero item id.

Modes 2–5 all run through `/loop` (see § Batch below).

---

## Step 0-bis · Default-mode decision tree

What the user says → which flow to run:

| User says | Mode | What runs |
|-----------|------|-----------|
| "read X" / "帮我读" / "analyze this" | **Full read** | Twelve-Q + main note + Obsidian save. **No slides.** |
| "quick look" / "速读" / "what's this about" | **Quick** | Condensed 5-Q only, answered in chat, no files |
| "make a deck" / "出 PPT" / "做幻灯" | **Full package** | Twelve-Q + main note + slide deck + Plan-C binding |
| "critique" / "批判性分析" | **Full read (critical)** | Full read, emphasis on Q2/Q9/Q11 |
| "extract the math" / "技术细节" | **Full read (technical)** | Full read, emphasis on Q4/Q5/Q6 |
| follow-up about a paragraph | **Passage-intent** | `references/twelve-questions.md` follow-up mode |

Ambiguous? Ask **once**: "note only, or the full slide package?" — then remember.

---

## Step 1 · Receive the paper

### 1.1 Method-name extraction (critical for batch)

For filenames like `{author}{year}{keyword}.pdf` (e.g. `gu2023mamba.pdf`,
`de2021continual.pdf`), **never** blindly use `keyword` as the method name —
it's often a topic word (`continual`, `multimodal`), not a method.

Resolve by confidence:

1. **High (use directly)**: Zotero title `XXX: ...` → `XXX`; abstract
   "We propose XXX" / "Our model, XXX"; title prefix before the colon
   (`Mamba: Linear-Time...` → `Mamba`).
2. **Medium (use, report)**: GitHub repo name (`state-spaces/mamba` → `Mamba`);
   an all-caps acronym repeated ≥5×.
3. **Low (ask the user)**: filename keyword is a generic topic word; survey /
   benchmark / dataset papers; Greek/formula names (π₀.₅ → `Pi05`).
4. **Fallback**: `{Author}{Year}` + save under the inbox folder
   (`L["untriaged_folder"]`), frontmatter `needs_review: true`.

**Naming rules**: always ASCII; hyphens/internal caps OK (`HyperKD`, `ViT-S`);
no spaces, no CJK, no Greek; no year suffix unless a name collision forces one.

**Collision**: if `{notes}/{project}/{method}.md` exists with a *different*
`arxiv_id`, rename the new one `{method}-{year}.md` and cross-link.

### 1.2 Source resolution

| Reference | Resolution |
|-----------|-----------|
| PDF path | Read directly |
| arXiv id/URL | `prism_helpers.fetch_arxiv_html` / download PDF |
| Zotero title | `zotero.search` → `zotero.pdf_path` |
| Zotero collection | `zotero.zotero_collection_to_queue` |
| no PDF attached | arXiv HTML → arXiv PDF → DOI → web search (in that order) |

Data-source priority (never write "abstract not found" after one failed
source — exhaust them all): Zotero metadata → Zotero PDF fulltext → arXiv HTML →
DOI page → web search.

---

## Step 2 · Twelve-Question understanding (mandatory, never skip)

Before any output mode, answer the twelve questions. Each answer carries a
**"how I'd know I understood it" self-check** — that is what turns a summary into
something the reader can re-explain unaided.

| # | Question | Core requirement |
|---|----------|------------------|
| Q1 | What problem? | one sentence: setting + data/model + pain |
| Q2 | Gap in prior work? | 1–3 concrete, attributed shortcomings |
| Q3 | Core insight ⭐ | 1–2 sentences of *intuition*, not a module list |
| Q4 | Pipeline | input → modules → output |
| Q5 | Module roles | each module: why needed / what breaks without it |
| Q6 | What do the equations do? | 2–5 key formulas, each with intuition |
| Q7 | How validated? | datasets + baselines + metrics + ablations |
| Q8 | Where do gains come from? | structure / training / data / compute, quant+qual |
| Q9 | Limitations | ≥2; mark unstated ones 【inferred】 |
| Q10 | Transferable? | 1–3 coherent extensions |
| Q11 | How to improve? | 2–3 ideas with upside/risk |
| Q12 | Explain in 2–3 sentences | the spoken-intro version |

Full template, output format, self-check wording, and the **passage-intent
follow-up mode** are in `references/twelve-questions.md`.

Rules: read intro + method + experiments + conclusion (don't paraphrase the
abstract); mark unstated things 【inferred】 / 【not stated】; in batch mode do a
condensed 5-question pass (Q1 + Q3 + Q4-brief + Q9 + Q12) per paper, expanding on
request — but never skip it.

---

## Step 3 · Reading modes

| Mode | Trigger | Output | Emphasis |
|------|---------|--------|----------|
| Quick | "quick look" / "速读" | TL;DR + Q1 + Q3 + Q12 | Q1/Q3/Q12 |
| Full | default | all 12 + structured note | all |
| Critical | "critique" / "批判性分析" | all 12, expanded | Q2/Q9/Q11 |
| Technical | "extract math" / "技术细节" | all 12, expanded | Q4/Q5/Q6 |
| Slide package | "make a deck" / "出 PPT" | all 12 + deck (Step 4-bis) | all |

---

## Step 4 · Main note generation

Fill `assets/paper-note-template.md` faithfully (don't simplify it).

Quality rules:
1. **Zero omissions** — every figure, equation, and table appears.
2. **Inline concept links** — wrap each technical term in `[[concept]]` at first
   mention (not only in a trailing list).
3. **No ASCII flowcharts** — structured markdown lists + `$math$`.
4. **Formula triplet** — every equation: name (`[[concept|label]]`), `$$LaTeX$$`
   (blank lines around it), meaning, symbol table.
5. **Tables are screenshots** — see § Iron rule below.

Figure acquisition (multi-source fallback) and formula/figure/table quality
standards: `references/quality-standards.md`, `references/image-troubleshooting.md`.

---

## Step 4-bis · Slide package (the full pipeline)

Triggered by "make a deck / 出 PPT / make slides / deck". Runs five phases;
**parallel by default**.

> Not to be confused with a "write *my own* paper → beamer talk" skill. prism
> reads *other people's* papers and produces a study/share deck via Marp.

```
═══ Phase 1 · Setup + resume check (serial, <10s) ══════════════
[1] load_config → cfg, L
[2] resolve {method} {arxiv_id} {pdf_path} {title} (§1.1)
[3] pick save mode A (vault, default) or B (next to the PDF)
[4] mkdir {deck_dir}=.../{project}/_slides/{method}/assets/  and  {deck_dir}/.cache/
[5] RESUME: from prism_state import resume_plan, update_paper, is_paper_done
    plan = resume_plan(deck_dir, method)   # {analysis,figures,tables,synth,render,bind: skip?}
    update_paper(project, method, cfg, status="in_progress")
    → skip any phase whose artifact already exists. A re-run after a crash only
      does the missing work. (is_paper_done short-circuits the whole paper.)

═══ Phase 2 · ⚡ 3-way subagent fan-out (skips per resume_plan) ═
  One message, up to three Agent calls. Prompts: references/subagent-prompts.md.
  Intermediate artifacts land in the DURABLE cache ({deck_dir}/.cache/), not /tmp,
  so they survive an interruption.
  ┌ Agent A · model cfg.models.analysis (opus): twelve-Q + note body   [skip if plan.analysis]
  │    → .cache/{method}_qa.md  +  .cache/{method}_note_body.md
  ├ Agent B · model cfg.models.figures  (sonnet): arXiv HTML → download → verify  [skip if plan.figures]
  │    → assets/{method}_fig_*.png  +  .cache/{method}_figmap.json
  └ Agent C · model cfg.models.tables   (sonnet): pdftoppm → PIL crop tables       [skip if plan.tables]
       → assets/{method}_table_*.png  +  .cache/{method}_tablemap.json
  After each phase: update_paper(project, method, cfg, phase_done="figures") etc.
  Cost note: 50 papers ≈ Opus×50 + Sonnet×100 (~3× cheaper than all-Opus).

═══ Phase 3 · Synthesize (serial) ══════════════════════════════
[5] read the three artifacts
[6a] fill assets/slide-template.md → {method}.slides.md
     (one page per figure/table with a read-key box; 12-Q section dividers)
[6b] fill assets/paper-note-template.md → {method}.md (main note — the deepest
     artifact; the deck is its visual condensation, not its index)
     Replace <!-- FIGURE_N_PLACEHOLDER --> / <!-- TABLE_N_PLACEHOLDER --> with
     the real image embeds from figmap/tablemap.

═══ Phase 4 · ⚡ Render + bind (parallel Bash + Python) ════════
[7] marp {method}.slides.md --pdf  --allow-local-files -o {method}.slides.pdf
    marp {method}.slides.md --pptx --allow-local-files -o {method}.slides.pptx
    copy_paper_pdf(src_pdf, deck_dir, method)         # original PDF → deck folder
    write main note → {project}/{method}.md
[8] bindings (idempotent; safe to re-run):
    inject_resources_block(note, method, arxiv_url=, github_url=, project=, cfg=)
    append_to_slides_moc(slides_moc_path(cfg), method, tag=, venue=, year=,
                         slides_pdf_rel=, cfg=)
    update_project_moc(project_moc_path(project, cfg), method, category=, venue=,
                       year=, status="✅", priority=, relevance=)
    # if the project MOC doesn't exist yet: bootstrap_project(project, cfg)
    # If the main note is a user's hand-written one, only the resources block is
    # refreshed; their prose is never touched (unless they say "rewrite").

═══ Phase 5 · Report + checkpoint + cleanup ════════════════════
[9]  verify 5 artifacts (note + slides md/pdf/pptx + original pdf) + MOC rows
[10] on SUCCESS:  update_paper(project, method, cfg, status="done")
                  purge_cache(deck_dir)            # drop the durable .cache
                  rm -f /tmp/{method}_page-*.png   # regenerable scratch only
     on FAILURE:  update_paper(project, method, cfg, status="failed", error="phaseN: ...")
                  KEEP .cache so the next run resumes from the missing phase
[11] report output paths
```

### Parallel vs serial

| Trigger | Behaviour |
|---------|-----------|
| default | Phase 2 fan-out + Phase 4 parallel |
| "run serially" / "debug mode" / "串行" | fully serial, for troubleshooting |
| "analysis only" / "no slides" | Agent A only |
| "just the figures/tables" / "preprocess" | Agents B + C only |

Don't parallelize when: arxiv_id is unresolved (Phase 1 can't finalize), or the
paper is <5 pages (serial is ~30s anyway).

### 🚨 Iron rule · tables are screenshots, never re-typed markdown

**Every table from the paper must be embedded as a screenshot of the original**,
never re-drawn as a markdown `| ... |`. Re-typing corrupts numbers, bold,
underlines, arrows, and merged cells; the original layout is the authors'
deliberate visual language; and a screenshot reads as "I read the paper" rather
than "an AI reworded it".

Screenshot SOP:

```bash
python3 skills/prism/assets/prism_helpers.py render paper.pdf /tmp {start} {end} {method}_page
python3 -c "from prism_helpers import crop_region; crop_region('/tmp/{method}_page-NN.png', \
  'assets/{method}_table_K.png', (left, top, right, bottom))"
```

(A4/Letter at 200 DPI ≈ 1700×2200; single-column table ≈ 520–800 px wide,
cross-column ≈ 1500 px; include header rows + caption.) Tiny 2×3 tables may stay
markdown; **main-result and ablation tables must be screenshots.**

### Standard deck layout (~30–40 pages)

Cover/TL;DR · Q1+Q2+lineage · **Core Insight** (highlighted) · architecture
(one page per figure + pipeline + algorithm + module table) · math (formula
triplets) · experimental setup · **results (one page per figure & per table,
each with a read-key box)** · ablation/attribution · limits/transfer/improve ·
Take-away (rating) · related work. Full per-page format + the Marp template:
`assets/slide-template.md`.

### Output paths (Plan C · three-piece binding)

Mode A (vault, default): each paper is a self-contained unit, plus a global index.

```
{vault}/{notes_folder}/{project}/
├── {method}.md                 main note (Obsidian entry point)
└── {slides_subdir}/{method}/
    ├── {method}.pdf            original paper (copied in)
    ├── {method}.slides.md      Marp source
    ├── {method}.slides.pdf     deck (embed/browse)
    ├── {method}.slides.pptx    editable deck
    └── assets/                 {method}_fig_*.png, {method}_table_*.png
{vault}/{moc_folder}/Slide Library.md   ← global deck index
```

Mode B (next to the PDF): `{pdf_dir}/_slides/{method}/...` — no PDF copy, no note
binding, no MOC update. Trigger with "local" / "next to the PDF" / "don't put it
in Obsidian".

### Obsidian behaviour

`.slides.pdf` and `{method}.pdf` embed inline via `![[...]]` (the resources
block puts both at the top of the note). `.slides.md` previews with the Marp /
Advanced-Slides plugin. `.slides.pptx` opens in Keynote/PowerPoint.

### Checklist (run every time)

- [ ] PDF + PPTX both rendered (PDF >500 KB / PPTX >1 MB usually means content)
- [ ] **every main-text figure present** (count matches the paper)
- [ ] **every main-text table present, as a screenshot** (not re-typed markdown)
- [ ] each figure/table has a read-key box, not a bare image
- [ ] Q3 insight page is intuition, not a module list
- [ ] **every cited number traces to a real table cell; every "baseline" is a real
      baseline row (not the method's own variant); no invented numbers** (the #1
      validated failure mode — see `references/quality-standards.md` § Number fidelity)
- [ ] Take-away page has a "worth following up?" rating
- [ ] main note is the **full template** (contributions / background / method
      per-module / formula triplets / per-figure-table sections / critique /
      related / quick-ref / 12-Q cheat-sheet at the end)
- [ ] resources block complete; Slide Library + project MOC rows added (inside
      the tables); concept-library maintenance (Step 6) triggered

---

## Step 5 · Save to Obsidian

Filename: `{method}.md` (no year prefix unless a collision forces it). Path:
`{notes_folder}/{project}/{method}.md`. Frontmatter: title, method_name,
authors, year, venue, tags (3–8, lowercase-hyphen), project, arxiv_id,
arxiv_url, code_url, image_source, created.

Post-save (config-gated): regenerate MOC indexes only if your vault uses an
index generator; `git add/commit` only if `git_commit:true` and `{vault}/.git`
exists; `git push` only if `git_push:true` and a remote is set.

---

## Step 6 · Concept-library maintenance (every paper)

Scan the note's `[[concept]]` links; for each, reuse if a note (or alias) exists,
else create it under the right category. **Budget: ≤ `cfg.concept_budget`
(default 8) new concepts per paper** — beyond that, downgrade extras to bold and
list them under "Concepts not yet created". Alias-dedup avoids
`Mamba`/`Mamba SSM`/`Selective SSM` becoming three files. Categories, templates,
and the budget/dedup rules: `references/concept-categories.md`.

---

## Step 7 · Final self-check

- [ ] twelve questions presented first (each with its self-check)
- [ ] Q3 is intuition, not a module list; Q6 formulas have meaning + symbols;
      Q8 attribution is quantitative + qualitative; unstated points 【inferred】
- [ ] every figure / equation / table present; concept library updated; images load

---

## Batch processing (Modes 2–5 via `/loop`)

A `/loop` master prompt drives batches: scan → dedup against existing artifacts →
each iteration spawns `cfg.parallel` paper-coordinator subagents → stop when the
queue empties. Each coordinator runs the full Phase 1–5 pipeline for one paper
and appends a line to `/tmp/prism_progress.log`; failures go to
`/tmp/prism_errors.log` and **never block** the next iteration. The full master
prompt and the per-paper coordinator prompt are in
`references/subagent-prompts.md` § Batch Coordinator.

### Checkpoint & resume (断点重连)

Batches survive crashes, `/loop` stops, and closed laptops. Two durable layers
(`assets/prism_state.py`):

1. **Per-project state file** `{project}/.prism_state.json` — every paper's
   status (`queued`/`in_progress`/`done`/`failed`) and which phases finished.
   Atomic writes (temp + `os.replace`); a corrupt file degrades to a fresh
   skeleton, never a crash.
2. **Per-paper durable cache** `{deck_dir}/.cache/` — the Phase-2 intermediates
   (`{method}_qa.md`, `{method}_note_body.md`, `{method}_figmap.json`,
   `{method}_tablemap.json`). Survives interruption; purged only on full success.

On any re-run, `resume_plan(deck_dir, method)` inspects the durable artifacts and
returns which phases to **skip**, so a paper that crashed at "render" doesn't
re-run the expensive opus analysis — it resumes from the missing phase.
`is_paper_done(deck_dir, method)` (slides.pdf exists and >50 KB) short-circuits
whole papers in the batch dedup pass. A failed paper keeps its `.cache`, logs to
`/tmp/prism_errors.log`, and never blocks the next paper.

Inspect anytime: `python3 skills/prism/assets/prism_state.py status {project}`.

---

## Reference files

- `references/twelve-questions.md` — full 12-Q template, self-checks, passage-intent mode
- `references/subagent-prompts.md` — Phase-2 A/B/C prompts + batch coordinator + `/loop` master
- `references/concept-categories.md` — concept buckets, budget, alias-dedup, template
- `references/quality-standards.md` — formula/figure/table quality + checks
- `references/image-troubleshooting.md` — arXiv HTML figure pitfalls, PDF fallback
- `assets/slide-template.md` — Marp deck skeleton (~35 pages)
- `assets/paper-note-template.md` — main-note skeleton
- `assets/queue-format.md` — YAML queue spec for Mode 4
- `assets/prism_helpers.py` — render / crop / figures / marp / binding / queue functions
- `assets/prism_state.py` — checkpoint / resume: state file, durable cache, resume_plan
- `assets/prism_refs.py` — reference/.bib import (Mode 6) + discovery-source ingestion (Mode 7): parse_bib, PDF refs, load_discovery → queue
- `assets/zotero.py` — read-only Zotero integration + collection→queue
- `assets/prism_config.py` — config + i18n labels
```
