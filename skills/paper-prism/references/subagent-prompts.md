# Subagent prompt templates

paper-prism's pipeline fans work out to subagents. This file holds the self-contained
prompts the main agent injects. Subagents cannot see the main conversation, so
every prompt must carry its own constants (`{method}`, `{arxiv_id}`,
`{pdf_path}`, `{title}`, `{deck_dir}`, `{project}`).

Model tiers (from `cfg.models`): **A = analysis (opus)**, **B = figures
(sonnet)**, **C = tables (sonnet)**. Reasoning depth lives in A; B and C are
mechanical extraction, ~3× cheaper on a smaller model.

---

## Phase 2 · Agent A — deep analysis (model: opus)

> The most important agent: its depth sets the ceiling for both the note and the
> deck.

```
You are running paper-prism's Step 2 deep analysis as an isolated task.

## Input
- PDF: {pdf_path}
- Method name: {method}
- arXiv id (if any): {arxiv_id}

## Read first
- skills/paper-prism/references/twelve-questions.md  (full 12-Q template + self-checks)
- skills/paper-prism/assets/paper-note-template.md   (main-note structure)

## Task A — twelve questions  →  {deck_dir}/.cache/{method}_qa.md
Answer all twelve questions in full. Each answer carries its "how I'd know I
understood it" self-check. Put the TL;DR (Q12) first.
- Q3 (core insight) must be INTUITION — "the regularity the authors exploit" —
  not a list of module names. Litmus test: strip the proper nouns; if nothing
  remains, it's a module list, rewrite it.
- Q6: 2–5 key formulas, each as a triplet (meaning + intuition + symbol table).
- Q9: ≥5 honest limitations; mark anything the paper doesn't state 【inferred】.

## Task B — main-note body  →  {deck_dir}/.cache/{method}_note_body.md
Write the long-form note body following paper-note-template.md (no frontmatter,
no top title — the coordinator assembles those). Sections: Key Contributions /
Background (problem · prior-gap · motivation) / Method (one paragraph PER module:
design motive + how it works + what breaks without it) / Key Formulas (every
formula as a triplet) / Experiments / Critique (strengths · limits · improve ·
reproducibility) / Related Work.
Wrap each technical term in [[wiki links]] at first mention (for the concept
graph). Reuse concepts likely already created by sibling papers rather than
minting near-duplicates.

### 🚨 Figure/table hard rule (violation = bug)
In the "Key Figures/Tables" section, DO NOT re-type any paper table as markdown,
and DO NOT replace a figure with prose. Emit placeholders the coordinator fills:

    ### Figure 1: {short title}
    <!-- FIGURE_1_PLACEHOLDER -->
    **Read-key**: {1–3 sentences}

    ### Table 1: {short title}
    <!-- TABLE_1_PLACEHOLDER -->
    **Read-key**: {1–3 sentences, do NOT restate the numbers}

The only exception is a comparison table YOU author (e.g. a "module role" table) —
that's your synthesis, markdown is fine.

### 🔢 Number & table discipline (hard rules — these prevent the #1 failure mode)
Adversarial validation found the dominant error is **fabricating or mislabeling
numbers from multi-row results tables**. Obey:
1. **Cell-level provenance.** Every number in Q7/Q8 must be traceable to a
   specific table cell. Before citing a value, locate its exact (table, row
   label, column). If you can't, don't cite it.
2. **Never invent a baseline number.** If a comparison needs a baseline value the
   paper doesn't report, write "not reported" — never fill the slot with a
   plausible-looking number.
3. **Confirm baseline rows are baselines.** Results tables interleave the paper's
   OWN method (and its variants) with baselines. Before calling a row "the LSTM
   baseline," re-read its label — it must not be the proposed method or a variant
   of it.
4. **Cross-table superlatives by delta-from-baseline.** When "best X" spans
   separate ablation tables that each vary from a shared baseline, rank by
   delta-from-baseline, not raw value; in any "X vs Y" claim, name Y's row.

### 🪶 Language fidelity (preserve the paper's strength of claim)
- Don't strengthen the paper's verbs: "highly correlated" ≠ "common/identical";
  "not too correlated" ≠ "orthogonal / gains add up". If you paraphrase a hedged
  claim, keep the hedge or mark 【inferred】.
- An illustrative example you invent for Q3/insight (not one the paper
  demonstrates) must be tagged 【illustrative】.
- A body-vs-caption / table-vs-text numeric discrepancy in the source is flagged
  【paper-internal discrepancy】, not silently resolved.
- When a signature formula lives in an appendix (e.g. an additive-attention
  scoring function), surface it in Q6 and cite the appendix.

## Output (DURABLE cache, so a crash can resume):
   {deck_dir}/.cache/{method}_qa.md  and  {deck_dir}/.cache/{method}_note_body.md
## Report: "QA N chars / note M chars."
## Do NOT: extract figures, screenshot tables, render slides, or write to the vault.
```

---

## Phase 2 · Agent B — figures (model: sonnet)

```
You are running paper-prism's figure extraction as an isolated task.

## Input
- arXiv id: {arxiv_id}
- Output dir: {deck_dir}/assets/
- PDF (fallback): {pdf_path}

## Single path — arXiv HTML (do not mix strategies)
1. import sys; sys.path.insert(0, "skills/paper-prism/assets")  # resolve the import from repo root
   from prism_helpers import fetch_arxiv_html, parse_arxiv_figures, download_figures
   html = fetch_arxiv_html("{arxiv_id}")
   figs = parse_arxiv_figures(html)          # [{id, src, caption}, ...]
   got  = download_figures("{arxiv_id}", figs, "{deck_dir}/assets", prefix="{method}_fig")
   Download ONLY what the HTML references — never a blind x1..x30 scan.
2. Read each downloaded image and verify it matches its caption. arXiv x-numbers
   do NOT map 1:1 to printed Figure numbers (see references/image-troubleshooting.md).
   Treat <10 KB files as failures.

## Fallbacks (only if the primary path yields nothing)
- Project page: find a homepage URL in the abstract/HTML, fetch its teaser images.
- pdfimages -png "{pdf_path}" {deck_dir}/assets/{method}_fig   (empty for vector PDFs — then mark missing).

## Output: {deck_dir}/.cache/{method}_figmap.json (durable) — list of
   {file, src_id, figure_num, caption, content_summary, verified}
## Report: "figures: N ok, M failed."
## Do NOT: analyse the paper, handle tables, or write slides.
```

---

## Phase 2 · Agent C — tables (model: sonnet)

```
You are running paper-prism's table screenshotting as an isolated task.

## Input
- PDF: {pdf_path}
- Output dir: {deck_dir}/assets/

## 🚨 Iron rule
Tables are PDF screenshots, NEVER re-typed markdown. Full rationale: SKILL.md.

## Steps
1. pdftotext the PDF; grep "Table [0-9]" to count main + appendix tables.
2. For pages that contain tables, render at 200 DPI WITH a paper-specific prefix
   (parallel papers must not collide on /tmp/page-NN.png):
     import sys; sys.path.insert(0, "skills/paper-prism/assets")  # resolve the import from repo root
     from prism_helpers import render_pdf_pages, crop_region
     render_pdf_pages("{pdf_path}", "/tmp", X, Y, prefix="{method}_page")
3. Read each page PNG, eyeball the table's pixel box (left, top, right, bottom),
   and crop:
     crop_region("/tmp/{method}_page-NN.png",
                 "{deck_dir}/assets/{method}_table_K.png", (L, T, R, B))
   Single-column ≈ 520–800 px wide; cross-column ≈ 1500 px. Include header rows
   + caption. (A4/Letter @200 DPI ≈ 1700×2200.)
4. Read each crop back: header present, all data rows present, caption present,
   no bleed from a neighbouring figure. Re-crop if off.

## Output: {deck_dir}/.cache/{method}_tablemap.json (durable) — list of
   {file, table_num, title, summary, note ("main"|"appendix")}
   (page PNGs may stay in /tmp — they're regenerable scratch.)
## Report: "tables: N main + M appendix."
## Do NOT: re-type tables as markdown, analyse the paper, or extract figures.
```

---

## Phase 4 · Render + bind (parallel Bash + Python, no subagent)

The coordinator issues these in one message:

```bash
marp {method}.slides.md --pdf  --allow-local-files -o {method}.slides.pdf
marp {method}.slides.md --pptx --allow-local-files -o {method}.slides.pptx
```
```python
import sys; sys.path.insert(0, "skills/paper-prism/assets")  # resolve imports from repo root
from prism_config import load_config, slides_moc_path, project_moc_path
from prism_helpers import (copy_paper_pdf, inject_resources_block,
                           append_to_slides_moc, update_project_moc, bootstrap_project)
cfg = load_config()
copy_paper_pdf("{pdf_path}", "{deck_dir}", "{method}")
inject_resources_block("{note_path}", "{method}", arxiv_url="{arxiv_url}",
                       github_url="{github_url}", project="{project}", cfg=cfg)
append_to_slides_moc(str(slides_moc_path(cfg)), "{method}", tag="{tag}",
                     venue="{venue}", year="{year}",
                     slides_pdf_rel="{slides_pdf_rel}", cfg=cfg)
bootstrap_project("{project}", cfg)   # no-op if it already exists
update_project_moc(str(project_moc_path("{project}", cfg)), "{method}",
                   category="{category}", venue="{venue}", year="{year}",
                   status="✅", priority="{priority}", relevance="{relevance}")
```

---

## Batch · per-paper coordinator (model: opus)

One coordinator owns one paper end-to-end and itself fans out A/B/C. The `/loop`
master spawns `cfg.parallel` of these per iteration.

```
You are a paper-prism paper coordinator. Run the full Phase 1–5 pipeline for ONE paper.

## Input
- PDF: {pdf_path}              (or arXiv id {arxiv_id} / Zotero item {zotero_item})
- Method: {method}            (resolve via SKILL.md §1.1 if not given)
- Project: {project}
- notes_strategy: {full | deck-only | analysis-only}

## Run (per SKILL.md Step 4-bis) — resume-aware
Phase 1  load_config; finalize {method}/{arxiv_id}/{title}; mkdir deck dir + .cache/.
         from prism_state import resume_plan, update_paper, is_paper_done, purge_cache
         if is_paper_done(deck_dir, method): return "already done".
         plan = resume_plan(deck_dir, method); update_paper(project, method, cfg, status="in_progress").
Phase 2  fan out A/B/C in ONE message (prompts above), SKIPPING any agent whose
         plan[...] is True. A on opus, B/C on sonnet. Artifacts → {deck_dir}/.cache/.
         After each: update_paper(project, method, cfg, phase_done="analysis"|"figures"|"tables").
Phase 3  if not plan.synth: assemble {method}.slides.md + {method}.md from .cache,
         replacing FIGURE_N/TABLE_N placeholders. update_paper(..., phase_done="synth").
Phase 4  if not plan.render: marp render. Then the binding block above (idempotent;
         skip note/MOC if deck-only; skip render+bind if analysis-only).
         update_paper(..., phase_done="render"); update_paper(..., phase_done="bind").
Phase 5  verify; on success update_paper(..., status="done") + purge_cache(deck_dir)
         + rm /tmp/{method}_page-*.png. On failure KEEP .cache.

## Logging
Append one line to /tmp/prism_progress.log:
  {ISO time} | {method} | {seconds} | OK   (or: FAIL phaseN: reason)
On any failure: update_paper(project, method, cfg, status="failed", error="phaseN: ..."),
append to /tmp/prism_errors.log, and RETURN — never abort the batch. The kept
.cache lets the next run resume from the failed phase.

## Edge cases
- method ambiguous → save under the inbox folder, frontmatter needs_review: true
- arxiv_id unresolved → skip HTML figure path, use pdftoppm/pdfimages fallback
- name collision (different arxiv_id) → {method}-{year}.md

## Return one line: "{method}: OK | note R lines / deck P pages / F figs / T tables"
```

---

## Batch · `/loop` master prompt

Paste this whole block (including `/loop`) to start a batch. It self-paces and
stops when the queue empties.

```
/loop

# paper-prism batch — process {QUEUE SOURCE} into project {PROJECT}

Each iteration:

1. SCAN. Build the queue from the source (each snippet assumes the assets dir on
   sys.path — run from the repo root with
   `PYTHONPATH=skills/paper-prism/assets python3 …`, or prepend
   `import sys; sys.path.insert(0, "skills/paper-prism/assets")`):
   - folder:     from prism_helpers import folder_to_queue; folder_to_queue("{dir}", "{PROJECT}")
   - zotero:     from zotero import zotero_collection_to_queue; zotero_collection_to_queue("{name}", True, "{PROJECT}")
   - zotero-tag: from zotero import zotero_query_to_queue; zotero_query_to_queue("{tag}", "{PROJECT}", by="tag")
   - yaml:       from prism_helpers import parse_paper_queue; parse_paper_queue("{queue.yaml}")
   Resolve {method} per SKILL.md §1.1.

2. DEDUP (resume). from prism_state import is_paper_done
   A paper is DONE if is_paper_done(deck_dir, method) (slides.pdf >50 KB). Drop
   done papers; a partially-done paper keeps its {deck_dir}/.cache and resumes
   from its missing phase. Report "X/N done, Y queued."

3. DISPATCH. Take the next cfg.parallel ({PARALLEL}) queued papers. In ONE message,
   spawn that many per-paper coordinator subagents (prompt above), opus.

4. JOIN. Summarize this iteration; append failures to /tmp/prism_errors.log;
   do NOT block on them.

5. STOP TEST. Queue empty (or all done) → print /tmp/prism_progress.log and
   /tmp/prism_errors.log, then STOP the loop. Otherwise continue.

## Guardrails
- Protect hand-written notes: refresh only the resources block unless told "rewrite".
- Concept budget: ≤ cfg.concept_budget new [[concepts]] per paper; extras → bold.
- Tables are screenshots, never markdown.
- Method names ASCII; collisions → {method}-{year}.
```

Tune cadence with the queue length: a few papers run in one pass; a hundred run
across many `/loop` iterations, each picking up where the last stopped (thanks to
the >50 KB resumability check).
