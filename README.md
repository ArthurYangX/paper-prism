# paper-prism

> **One paper, refracted.** A Claude Code skill that turns an academic paper — or a whole library — into a structured Obsidian knowledge package: a deep main note, a slide deck (PDF + editable PPTX), and a linked concept graph.

![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Claude Code skill](https://img.shields.io/badge/Claude%20Code-skill-8A2BE2)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![tests 153 passing](https://img.shields.io/badge/tests-153%20passing-brightgreen)

**English** · [简体中文](README.zh-CN.md)

---

## What it does

Point paper-prism at a PDF, an arXiv link, or a Zotero collection. It produces three bound artifacts:

- **A main note** — the deepest artifact. A twelve-question deep read, formula triplets (name / `$$LaTeX$$` / meaning / symbol table), every figure and table explained, every technical term wrapped in an inline `[[concept]]` link.
- **A slide deck** — a ~30-page Marp deck as **PDF + editable PPTX**, one page per figure/table with a "read-key" box. The visual condensation of the note, not its index.
- **A concept graph** — concept notes, a per-project reading queue, and a global slide index, all auto-created and idempotently updated so your vault stays navigable.

A single paper in roughly 8 minutes, or your whole Zotero collection overnight — it is the same flow; batch just feeds the pipeline a longer queue.

**At a glance:**

```text
  INPUT · 7 modes
  PDF · arXiv · Zotero · folder · YAML queue · .bib/references · discovery feed
                          │
                          ▼   build & dedup queue
  ┌────────────────── PIPELINE · 5 phases  (parallel by default) ──────────────────┐
  │  1 setup  ▸  2 fan-out ⚡  ▸  3 synthesize  ▸  4 render + bind ⚡  ▸  5 report   │
  │                                                                                │
  │  Phase 2 — three subagents at once:                                            │
  │     A · Opus     twelve questions  +  note body                                │
  │     B · Sonnet   figures   (arXiv HTML → download → verify)                     │
  │     C · Sonnet   tables    (pdftoppm → PIL crop — screenshots, never re-typed)  │
  │                                                                                │
  │  checkpoint / resume (断点重连): a crashed re-run resumes from the missing phase │
  └───────────────────────────────────┬────────────────────────────────────────────┘
                          │   Plan C · three-piece binding
                          ▼
  OUTPUT · one self-contained unit per paper   (+ vault-wide indexes)
  {project}/{method}.md ───────────────── deep main note  (Obsidian entry)
  {project}/_slides/{method}/
       ├─ {method}.pdf ───────────────── original paper
       ├─ {method}.slides.pdf / .pptx ── deck:  PDF + editable PPTX
       └─ assets/ ────────────────────── figures + table screenshots
  _MOC/Slide Library.md  +  project reading-queue MOC ──── auto-indexed
  _concepts/ ──────────────────────────── linked concept graph
```

---

## Install

```bash
git clone https://github.com/ArthurYangX/paper-prism.git
cd paper-prism
./install.sh          # symlinks the skill into ~/.claude/skills/ and runs the dependency doctor
cp skills/paper-prism/assets/config.example.json skills/paper-prism/assets/config.json
# then edit config.json — at minimum set vault_path
```

`install.sh` symlinks `skills/paper-prism/` into `~/.claude/skills/` so Claude Code discovers it (the slash command becomes `/paper-prism`), then runs a dependency doctor that checks for the tools below.

**Dependencies:**

| Tool | Why | Install |
|---|---|---|
| **Python 3.10+** with **Pillow** | table cropping (PIL) | `pip install Pillow` |
| **Node** + **`@marp-team/marp-cli`** | render the deck to PDF + PPTX | `npm i -g @marp-team/marp-cli` |
| **poppler** (`pdftoppm`) | render PDF pages to PNG for table screenshots | `brew install poppler` / `apt install poppler-utils` |
| *optional* **PyYAML** | nicer YAML queue parsing (a zero-dep mini-parser is built in) | `pip install pyyaml` |
| *optional* **Zotero** | the Zotero input modes (read-only) | local Zotero install |

The Python helpers are **stdlib-first**: paper-prism imports and runs its config and binding logic with no third-party packages at all. Pillow, Node/Marp, and poppler are only invoked when you actually render a deck.

---

## Quick start

Once installed, these are things you **say to Claude Code** — not shell commands. paper-prism auto-triggers when your message matches its description (the phrases below); you can also invoke it explicitly with **`/paper-prism`**.

**Single paper → note (default), or the full deck package:**

```text
read paper.pdf and make a deck
```

> Default decision tree: "read X" gives you a full note, no slides. "make a deck / 出 PPT" gives you the full three-piece package. Ambiguous? paper-prism asks once, then remembers.

**A whole Zotero collection:**

```text
process my Zotero "Continual Learning" collection — full package for each
```

**A reproducible YAML queue** (git-versionable, resumable, per-paper overrides — the recommended batch entry). Say:

```text
batch from papers.yaml
```

where `papers.yaml` is:

```yaml
project: Demo
parallel: 4
notes_strategy: full          # full | deck-only | analysis-only

papers:
  - id: transformer
    arxiv: "1706.03762"       # quote arXiv IDs (a bare number becomes a float)
    method_name: Transformer
    category: "attention · sequence modeling"
    priority: P1
  - id: mamba
    arxiv: "2312.00752"
    method_name: Mamba
    category: "SSM · long-sequence"
  - id: my-paper
    path: ~/papers/yourpaper.pdf   # a local PDF
    method_name: MyMethod
```

Each paper needs exactly one of `path` / `arxiv` / `zotero`. Full spec: `skills/paper-prism/assets/queue-format.md`.

### Seven input modes — same pipeline, different queue source

| Mode | What you say | Source |
|------|--------------|--------|
| 1 · Single | `read X.pdf` · `make a deck for X` | one PDF / arXiv id / Zotero title |
| 2 · Folder | `batch ~/papers/` | every `*.pdf` in a folder |
| 3 · Zotero collection | `process my Zotero "X" collection` | a Zotero collection (recursive) |
| 4 · YAML queue | `batch from papers.yaml` | a git-versionable queue file (recommended) |
| 5 · Zotero query | `process Zotero papers tagged X` | a Zotero tag/query |
| 6 · References / `.bib` | `process this paper's references` · `batch from refs.bib` | a paper's bibliography or a LaTeX `.bib` |
| 7 · Discovery source | `today's papers → deck the top 5` · `batch from digest.json` | a recommender feed (daily digest, topic search, …) |

Modes 1–6 are *you point at papers you have*; **Mode 7 is *a discovery source
brings papers to you***. paper-prism doesn't scrape or score — that stays in separate
upstream skills (a daily-digest, a lit-search, Semantic Scholar, arXiv). They just
emit a JSON list of `{title, arxiv?, score?, why?}` (or a `.bib`); paper-prism ingests it
and refracts the keepers, so paper-prism stays a focused deep-processing backend.

```bash
python3 skills/paper-prism/assets/prism_refs.py bib  refs.bib            # .bib       → queue
python3 skills/paper-prism/assets/prism_refs.py pdf  paper.pdf           # PDF refs   → queue
python3 skills/paper-prism/assets/prism_refs.py discovery digest.json --top 5   # a feed → queue
```

---

## See it in action

Two public papers, refracted end-to-end into full paper-prism packages — main note · slide deck · figure/table screenshots · linked MOCs — live in [`examples/showcase/`](examples/showcase/run-attention/):

| Paper | Note | Deck | Produced by |
|-------|------|------|-------------|
| **Transformer** — *Attention Is All You Need* | [Transformer.md](examples/showcase/run-attention/vault/papers/Showcase/Transformer.md) | 35 pages | coordinator-driven (serial) |
| **Mamba** — *Selective State Spaces* | [Mamba.md](examples/showcase/run-attention/vault/papers/Showcase/Mamba.md) | 39 pages | a real parallel A/B/C subagent fan-out, reconciled by the coordinator |

<p align="center">
  <img src="examples/showcase/run-attention/preview/02-architecture.png" width="49%" alt="Transformer deck — architecture page">
  <img src="examples/showcase/run-attention/preview/mamba-03-downstream.png" width="49%" alt="Mamba deck — results page">
</p>

Both share one `Showcase` reading-queue MOC and the global Slide Library — index accumulation across papers, demonstrated. The rendered PDFs/PPTX are git-ignored to keep the repo light; regenerate each with one `marp` command (see the showcase [README](examples/showcase/run-attention/README.md)).

---

> **That's the whole loop — install, say what you want, get a bound note + deck.** Everything below is the *why* and *how*: the pipeline internals, full configuration, and the design rationale. Skim it when you want depth; you don't need it to start.

---

## How it works

The deck pipeline (`make a deck`) runs five phases — **parallel by default**:

```text
Phase 1 · Setup            resolve config, method-name, arxiv_id, paths; mkdir deck folder   (serial, <10s)
Phase 2 · 3-way fan-out ⚡  Agent A (Opus): twelve-Q + note body
                           Agent B (Sonnet): arXiv HTML → download → verify figures
                           Agent C (Sonnet): pdftoppm → PIL-crop tables
Phase 3 · Synthesize       fill the slide template + the note template from the 3 artifacts   (serial)
Phase 4 · Render + bind ⚡  marp → PDF + PPTX · copy source PDF in · resources block ·
                           Slide Library row · project MOC row                                (parallel)
Phase 5 · Report           verify 5 artifacts + MOC rows · clean /tmp · print paths
```

The main agent acts as a coordinator: it fans work out to the three subagents (Phase 2), then reconciles their output and assembles the note + deck (Phase 3) — `main → subagents → main`. Batches (folder / Zotero / YAML) wrap this in a `/loop` master prompt: scan → dedup against existing artifacts → each iteration spawns `parallel` paper-coordinators → stop when the queue empties. Failures go to an error log and **never block** the next paper. See `docs/architecture.md` for the full design.

---

## Configuration

Copy `config.example.json` → `config.json` (gitignored — it holds your private vault path) and edit. Config resolves in this order, first hit wins:

1. `$PRISM_CONFIG` — explicit path to a JSON file
2. `skills/paper-prism/assets/config.json` — next to the module
3. `~/.config/paper-prism/config.json` — XDG-style user config
4. built-in defaults — so paper-prism still imports with no config at all

Key fields:

| Key | Meaning | Default |
|---|---|---|
| `vault_path` | your Obsidian vault root (`~` expanded) | `~/Documents/Obsidian Vault` |
| `notes_folder` / `default_project` | `{vault}/{notes_folder}/{project}/` | `papers` / `Research` |
| `concepts_folder` · `moc_folder` · `slides_subdir` | where concepts, indexes, and decks live | `_concepts` · `_MOC` · `_slides` |
| `zotero_db` / `zotero_storage` | only for Zotero input modes (read-only) | `~/Zotero/...` |
| `models` | subagent tiers for the fan-out | `analysis: opus`, `figures/tables: sonnet` |
| `parallel` / `concept_budget` | papers per loop iteration / max new concepts per paper | `4` / `8` |
| `git_commit` / `git_push` | opt-in vault git automation | `false` / `false` |
| `lang` | **`en` or `zh`** — language of generated headings | `en` |
| `labels` | override any individual heading label | `{}` |

**i18n.** paper-prism's generated headings are configurable. Set `"lang": "en"` (default) or `"lang": "zh"` to flip every output heading — "Resources" ↔ "资源", "TL;DR" ↔ "一句话总结", the MOC column names, the inbox folder, and so on — and override any single label under `"labels"`. The skill logic and your prompts stay in whatever language you like; only the *written headings* follow `lang`.

```bash
python3 skills/paper-prism/assets/prism_config.py   # prints the resolved config + active labels
```

---

## Zotero linkback (optional)

If a paper is in your Zotero library, paper-prism adds a one-click link to the note's resources block:

```text
- 📦 Zotero: [Open in Zotero (annotations)](zotero://select/library/items/{key})
```

Click it → Zotero jumps to the item → open the PDF to see your **annotations** (annotations live in Zotero's database, not in the PDF file).

**Zero plugins, and no configuration beyond two one-time clicks:**

1. **Zotero must be running** when you click the link (the link wakes it up).
2. The **first** time you click a `zotero://` link, Obsidian asks whether to allow opening external links — **allow it once** and it won't ask again.

That's it. paper-prism matches the note title to your Zotero item by *normalized title* (**read-only** — it never modifies your library) and uses the stable 8-char item key, so the link survives citekey changes and attachment re-organization.

> **You do _not_ need** the Zotero-Integration plugin, Better BibTeX, or PDF Utility. Those sync annotation *text* into notes (a different feature) and depend on fragile citekeys — paper-prism deliberately avoids them. Wanting annotation text pulled into Obsidian is a separate plugin setup, outside paper-prism.

---

## Output layout

**Plan C — three-piece binding.** Mode A (vault, the default): each paper is a self-contained unit, plus a global index.

```text
{vault}/{notes_folder}/{project}/
├── {method}.md                 main note (Obsidian entry point)
└── {slides_subdir}/{method}/
    ├── {method}.pdf            original paper (copied in)
    ├── {method}.slides.md      Marp source
    ├── {method}.slides.pdf     deck (embed / browse)
    ├── {method}.slides.pptx    editable deck
    └── assets/                 {method}_fig_*.png, {method}_table_*.png
{vault}/{moc_folder}/Slide Library.md   ← global deck index
```

Mode B (`local` / `next to the PDF` / `don't put it in Obsidian`): everything lands in `{pdf_dir}/_slides/{method}/` with no PDF copy, no note binding, and no MOC update.

In Obsidian, the deck PDF and the source PDF embed inline at the top of the note (`![[...]]`); the `.slides.md` previews with the Marp / Advanced-Slides plugin; the `.pptx` opens in Keynote/PowerPoint.

---

## Why paper-prism?

The single-paper experience is nice. The reason paper-prism exists is what happens **at scale** — turning 100 papers into a knowledge base instead of 100 disconnected dumps.

| At scale, the thing that bites you | What paper-prism does |
|---|---|
| All-Opus reading is slow and expensive per paper | **Parallel subagent fan-out** — analysis (Opus) + figures (Sonnet) + tables (Sonnet) run as three concurrent agents; ~8 min/paper, ~3× cheaper than all-Opus (50 papers ≈ Opus×50 + Sonnet×100). |
| 100 papers naively → ~2000 half-defined `[[wikilinks]]` and a broken graph | **Concept budget** (default ≤8 new concepts/paper) + **alias dedup**, so `Mamba` / `Mamba SSM` / `Selective SSM` never become three files; extras downgrade to bold. |
| A batch crashes at paper 60 of 100 and you've lost the work | **Checkpoint & resume (断点重连)** — a per-project state file + a per-paper durable cache mean a re-run skips finished papers *and* resumes a half-finished one from its missing phase (a crash at "render" never re-runs the Opus analysis). Bindings replace-in-place; failures are isolated and never block the next paper. |
| Notes, slides, and the source PDF drift apart | **Three-piece binding (Plan C)** — main note + deck + the original PDF live as one self-contained unit, linked by a resources block, and indexed in both a project MOC and a global Slide Library. |
| An AI that re-types result tables corrupts the numbers | **The table-screenshot iron rule** — every main-result and ablation table is embedded as a *screenshot of the original*, never re-drawn as markdown. Re-typing corrupts numbers, bold, arrows, and merged cells. |
| Filenames like `de2021continual.pdf` get a garbage method name | **Method-name extraction** by confidence (Zotero title → "we propose X" → repeated acronym → ask), so batches name notes correctly instead of calling a paper `Continual`. |

Everything above is implemented in `skills/paper-prism/SKILL.md` and the Python helpers — not aspirational.

---

## The twelve-question framework

paper-prism never jumps straight to output. Before any note or deck, it answers **twelve questions** about the paper — and every answer carries a **"how I'd know I understood it" self-check**. That self-check is the whole point: it is what turns a summary into something *you can re-explain unaided*, rather than a fluent paraphrase of the abstract.

| # | Question | # | Question |
|---|---|---|---|
| Q1 | What problem? | Q7 | How validated? (data · baselines · metrics · ablations) |
| Q2 | Gap in prior work? | Q8 | Where do the gains come from? |
| Q3 | Core insight ⭐ (intuition, not a module list) | Q9 | Limitations (≥2; unstated ones marked 【inferred】) |
| Q4 | Pipeline (input → modules → output) | Q10 | Transferable? |
| Q5 | Module roles (what breaks without each) | Q11 | How to improve? |
| Q6 | What do the equations *do*? | Q12 | Explain it in 2–3 sentences |

In batch mode paper-prism runs a condensed five-question pass (Q1 + Q3 + Q4-brief + Q9 + Q12) per paper and expands on request — but it **never skips** the framework. Full template, self-check wording, and the passage-intent follow-up mode live in `skills/paper-prism/references/twelve-questions.md`.

---

## Project status

**v0.1.0** — works, and has been used on real papers. The note/deck/graph artifacts and the binding are stable; the skill's *internal* prompts, phase wiring, and config keys may still shift as it is hardened. Test suite is **153 checks, zero external dependencies** (`python3 tests/test_prism.py`). See [CHANGELOG.md](CHANGELOG.md).

---

## Acknowledgments

paper-prism is a major rework of the **`paper-reader`** skill by **[huangkiki](https://github.com/huangkiki)**, from the [**dailypaper-skills**](https://github.com/huangkiki/dailypaper-skills) project, used under **Apache-2.0**. (On the dev machine it was encountered bundled inside the [ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep) skill collection.) Full attribution and the Apache-2.0 statement of changes are in [NOTICE](NOTICE).

| What `paper-reader` provided | What paper-prism adds |
|---|---|
| Zotero integration patterns | Twelve-question framework with per-answer self-checks |
| The Obsidian concept-library framework | Plan-C three-piece binding (note + deck + source PDF) |
| The paper-note template | Marp deck generation (PDF + editable PPTX) |
| Multi-source figure fallback | The table-screenshot iron rule |
| | Parallel subagent fan-out (analysis / figures / tables) |
| | Method-name extraction for batch correctness |
| | Project + global MOC auto-update |
| | Concept budget + alias dedup |
| | Config-driven i18n (`en`/`zh`, overridable labels) |
| | Checkpoint/resume + reference/`.bib` import |
| | A zero-dependency test suite |

See [NOTICE](NOTICE) for the full attribution.

---

## License

MIT — see [LICENSE](LICENSE). Copyright © 2026 yangjc27.
