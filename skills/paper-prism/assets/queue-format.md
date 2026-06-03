# Paper Queue YAML Spec

> Input format for Mode 4 (batch processing from a YAML queue file).
> Parser: `prism_helpers.parse_paper_queue(yaml_path)`

> [!important] Quote arXiv IDs
> **arXiv IDs MUST be quoted strings** — e.g. `arxiv: "2312.00752"`, `arxiv_id: "2312.00752"`.
> Unquoted, YAML parses `2312.00752` as a **float**, which loses precision and
> corrupts the ID. paper-prism coerces these fields back to strings defensively, but
> **quoting is the documented contract** — always quote them in your queue files.

## Full field set

```yaml
# === Global metadata (one per queue file) ===
project: Demo                 # required: owning project, decides the vault subdirectory
parallel: 4                          # optional: papers processed concurrently per iter, default 4
notes_strategy: full                 # optional: full | deck-only | analysis-only, default full
default_priority: P2                 # optional: default for papers with no explicit priority
default_status: ⏳                    # optional: initial status, default ⏳ (to-read)

# === Paper list ===
papers:
  - id: icarl                        # required: short ID unique within the queue (logging only)
    path: ~/Desktop/refs/rebuffi2017icarl.pdf  # one of (path / arxiv / zotero) is required
    method_name: iCaRL               # optional override (bypass auto-extraction)
    arxiv_id: "1611.07725"           # optional (auto-extracted from the PDF if omitted) — quote it
    category: "Continual learning · distillation foundation"  # optional: category column in the project MOC
    relevance: "Foundational CIL paradigm"   # optional: "relation to project" column in the project MOC
    priority: P1                     # optional: overrides default_priority
    skip: false                      # optional: set true to skip for now (stays in the queue)

  - id: mamba
    arxiv: "2312.00752"              # arXiv ID/URL only — PDF auto-downloaded from arXiv (quote it)
    method_name: Mamba

  - id: pi05
    zotero: "Pi05"                   # Zotero search: title / item key
    category: "VLA · vision-language-action"
```

## Three path sources

| Field | Meaning | Handling |
|-------|---------|----------|
| `path:` | absolute path to a local PDF | used directly |
| `arxiv:` | arXiv ID or URL | `wget` download to `~/cache/arxiv/{id}.pdf` |
| `zotero:` | Zotero title search / item key | `zotero.py pdf` resolves the PDF path |

Precedence: `path > arxiv > zotero`. Use exactly one per paper.

## notes_strategy (three tiers)

| Tier | What runs | Outputs |
|------|-----------|---------|
| `full` (default) | Phase 1-5, everything | main note + slide PDF/PPTX + copied PDF + MOC |
| `deck-only` | skip writing the main note, render the deck only | slide PDF/PPTX + copied PDF + MOC (no main note) |
| `analysis-only` | only Phase 2 Agent A | `{deck_dir}/.cache/{method}_qa.md` + `_note_body.md` (durable cache, not written to vault) |

## Status emoji legend

- `⏳` to-read / `◐` reading / `✅` done / `❌` dropped / `❄️` shelved

## Example 1 · Curated 10-paper queue across a theme

```yaml
project: Demo
parallel: 4
notes_strategy: full

papers:
  - id: mamba
    path: ~/Desktop/refs/gu2023mamba.pdf
    method_name: Mamba
    arxiv_id: "2312.00752"
    category: "SSM · long sequence · content routing"
    relevance: "Candidate backbone; the selection mechanism maps to CIL retention"
    priority: P1

  - id: icarl
    path: ~/Desktop/refs/rebuffi2017icarl.pdf
    method_name: iCaRL
    arxiv_id: "1611.07725"
    category: "Continual learning · prototype classification · CIL origin"
    relevance: "Foundational CIL paradigm; its three pieces port to an SSM backbone"
    priority: P1

  - id: lwf
    path: ~/Desktop/refs/li2017learning.pdf
    method_name: LwF
    category: "Continual learning · distillation"
    priority: P1

  - id: ewc
    path: ~/Desktop/refs/kirkpatrick2017overcoming.pdf
    method_name: EWC
    category: "Continual learning · weight regularization"
    priority: P1

  - id: foster
    path: ~/Desktop/refs/wang2022foster.pdf
    method_name: FOSTER
    category: "Continual learning · feature boosting"
    priority: P2

  - id: fetril
    path: ~/Desktop/refs/petit2023fetril.pdf
    method_name: FeTrIL
    category: "Continual learning · modern prototypes"
    priority: P2

  - id: dualprompt
    path: ~/Desktop/refs/wang2022dualprompt.pdf
    method_name: DualPrompt
    category: "Continual learning · prompt-based"
    priority: P2

  - id: vmamba
    path: ~/Desktop/refs/liu2024vmamba.pdf
    method_name: VMamba
    category: "SSM · vision backbone"
    relevance: "Mamba ported to vision; a CIL backbone comparison candidate"
    priority: P1

  - id: inflora
    path: ~/Desktop/refs/liang2024inflora.pdf
    method_name: InfLoRA
    category: "Continual learning · LoRA-based"
    priority: P2

  - id: vandeven
    path: ~/Desktop/refs/vandeven2022three.pdf
    method_name: ThreeScenarios
    category: "Continual learning · survey"
    relevance: "Survey of CIL evaluation protocols; required reading before experiments"
    priority: P3
```

## Example 2 · Deck only, no main note (exploration phase)

```yaml
project: Exploration
parallel: 6
notes_strategy: deck-only        # global strategy

papers:
  - id: a
    arxiv: "2403.04652"
  - id: b
    arxiv: "2403.05121"
  - id: c
    arxiv: "2403.07974"
```

## Example 3 · Mixing path / arxiv / zotero

```yaml
project: MyResearch
parallel: 3

papers:
  - id: local-pdf
    path: ~/Desktop/that.pdf

  - id: new-arxiv
    arxiv: "2410.12345"
    method_name: NewModel        # force the method name

  - id: zotero-saved
    zotero: "DINO v3"
```

## Example 4 · Partially completed queue (idempotent re-run)

The skill auto-skips papers already finished in the vault, so this queue is safe to re-run:

```yaml
project: Demo
parallel: 4

papers:
  - id: mamba                    # already done, will be skipped
    path: ...
  - id: icarl                    # already done, will be skipped
    path: ...
  - id: foster                   # not done, will run
    path: ~/Desktop/refs/wang2022foster.pdf
```

Skip logic: check whether `{NOTES_PATH}/{project}/_slides/{method}/{method}.slides.pdf` exists and is larger than 50KB.

## Validation (enforced by `parse_paper_queue`, raises `ValueError`)

These are checked in code at parse time — a bad queue fails fast with the
offending paper index, not deep in the pipeline:

- `project` is ASCII (defaults to `Research` if omitted)
- `parallel` is an int in 1..8
- `notes_strategy` is one of {full, deck-only, analysis-only}
- each paper has exactly one of `path` / `arxiv` / `zotero`
- `path` ends in `.pdf` (existence is checked later, when the paper is processed)
- `method_name`, if provided, is filesystem-safe with no spaces

Applied automatically: `skip: true` papers are dropped from the returned queue;
`default_priority` / `default_status` fill any paper that doesn't set its own
`priority` / `status`. If a reference/discovery source dropped entries (no usable
id or title), the count is reported so "40 in → 31 out" is never silent.
