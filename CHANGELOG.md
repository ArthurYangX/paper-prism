# Changelog

All notable changes to prism are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-03

First public release. prism is a major rework of the `paper-reader` skill by
huangkiki (from [dailypaper-skills](https://github.com/huangkiki/dailypaper-skills),
Apache-2.0 — see [NOTICE](NOTICE)); the items below are what this release adds on
top of, or substantially reworks from, that base.

### Added

- **Twelve-question framework** with a per-answer "how I'd know I understood it"
  self-check, so notes are re-explainable rather than fluent paraphrase; a
  condensed five-question pass for batch mode; a passage-intent follow-up mode.
- **Plan-C three-piece binding** — main note + slide deck + the original PDF as a
  single self-contained Obsidian unit, joined by an idempotent resources block.
- **Marp deck generation** — a ~30-page deck rendered to **PDF + editable PPTX**,
  one page per figure/table with a read-key box.
- **The table-screenshot iron rule** — every main-result and ablation table is
  embedded as a screenshot of the original, never re-typed as markdown.
- **Parallel subagent fan-out** — analysis (Opus) + figures (Sonnet) + tables
  (Sonnet) run concurrently; ~8 min/paper and ~3× cheaper than all-Opus.
- **Method-name extraction** by confidence tier (Zotero title → "we propose X" →
  repeated acronym → ask the user), so batches name notes correctly.
- **Six input modes** — single paper, folder, Zotero collection, YAML queue,
  Zotero query, and **reference/.bib import** — all driving the same pipeline; a
  git-versionable YAML queue spec (`assets/queue-format.md`) as the recommended
  batch entry.
- **Reference & `.bib` import** (`assets/prism_refs.py`) — turn a paper's whole
  bibliography (a LaTeX `.bib`, or a PDF's References section) into a queue:
  zero-dependency BibTeX parser, robust arXiv-id/DOI extraction (new + old id
  styles), and a prose-vs-author-list title heuristic for PDF references.
- **Checkpoint & resume (断点重连)** via a `/loop` master prompt and
  `prism_state.py`: a per-project state file (atomic writes) + a per-paper durable
  cache let a re-run skip finished papers *and* resume a half-finished one from its
  missing phase, so a crash at "render" never re-runs the Opus analysis. Failures
  are isolated and never block the next paper.
- **Project + global MOC auto-update** — a per-project reading-queue table and a
  global Slide Library index, both written and refreshed in place.
- **Concept budget + alias dedup** — default ≤8 new concepts per paper, with
  alias merging so one method never spawns three concept files.
- **Config-driven i18n** — `lang: en | zh` flips every generated heading, with
  per-label overrides; config resolves `$PRISM_CONFIG` → local `config.json` →
  `~/.config/prism/config.json` → built-in defaults.
- **Stdlib-first helper library** (`prism_helpers.py`, `prism_config.py`) for
  PDF rendering, PIL cropping, arXiv figure download, Marp rendering, the binding
  writers, and the queue parsers — optional deps lazily imported.
- **Test suite** — 76 checks, zero external dependencies
  (`python3 tests/test_prism.py`), covering config/labels, the three binders,
  both MOC writers, the queue parsers, and the checkpoint/resume logic.

[0.1.0]: https://github.com/yangjc27/prism/releases/tag/v0.1.0
