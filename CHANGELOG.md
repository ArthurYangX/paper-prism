# Changelog

All notable changes to paper-prism are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Zotero linkback (optional, zero-plugin)** — `zotero.py` gains `find_item_key` /
  `item_key`: a **read-only**, normalized-title match (collection-scoped, trashed items
  excluded) that returns the stable 8-char Zotero item key. The resources block now emits
  `zotero://select/library/items/{key}`, so one click jumps to the Zotero item and its
  annotations. No Better-BibTeX, no Zotero-Integration plugin, no `storage/` paths — all
  evaluated and rejected (unstable citekeys, breakable paths, annotations not in the
  file). Documented in SKILL.md Step 5-bis and a README "Zotero linkback" section. (+6
  tests → **138**.)
- **Two end-to-end showcases** (`examples/showcase/`) — Transformer (coordinator-serial)
  and Mamba (a real parallel A/B/C subagent fan-out, reconciled by the coordinator); each
  a full note + 35/39-page deck + figure/table screenshots, both indexed in shared MOCs.

### Changed
- **Renamed `prism` → `paper-prism`** (brand + command layer): the skill is now invoked
  as `/paper-prism` (the slash command follows the skill directory name). Python module
  names (`prism_*.py`), the `PRISM_CONFIG` env var, and all imports are unchanged — no
  code-level rename. Repo: `github.com/ArthurYangX/paper-prism`.
- **READMEs restructured install-first** (EN + 简体中文): Install + Quick start moved to
  the top; the why/how/rationale moved below a divider.

### Fixed
Two review passes (codex + an integral review) — every material finding addressed:
- **Concurrency / resume integrity**: `update_paper` now takes a cross-process `flock`,
  so parallel coordinators no longer last-writer-wins-drop each other's state entries;
  `is_paper_done` / `resume_plan` require the PDF `%%EOF` trailer, so a crash-truncated
  deck is no longer mistaken for done and silently skipped on resume.
- **Skill correctness**: `allowed-tools` grants `Agent` (the fan-out's subagent tool —
  allowed-tools is enforced); `safe_name()` is ASCII-only (was keeping CJK/Greek);
  `quality-standards.md` replaced a markdown-table example with the screenshot SOP (it
  contradicted the iron rule); `image-troubleshooting.md` signatures aligned to source.
- **New deterministic helpers**: `download_arxiv_pdf()` (id-validated, `%PDF-` verified),
  and `extract_concepts()` / `plan_concepts()` (the mechanical half of Step 6).
- **Hardening**: `find_item_key` prefers the copy that has a PDF; a no-PDF Zotero item
  emits an `arxiv:` source from metadata instead of `path:None`; malformed config /
  discovery JSON raises a clear `"not valid JSON: <path>"` error; the installer reports
  "installed but NOT ready" on a missing required dep; `copy_paper_pdf` compares the head,
  not just size; `/tmp`→`.cache` doc fixes for the durable Phase-2 artifacts;
  `zotero_helper.py`→`zotero.py` and other doc/code-name alignments.
- Tests: 132 → **153** (zero external dependencies).

## [0.1.0] - 2026-06-03

First public release. paper-prism is a major rework of the `paper-reader` skill by
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
- **Seven input modes** — single paper, folder, Zotero collection, YAML queue,
  Zotero query, **reference/.bib import**, and **discovery-source ingestion** —
  all driving the same pipeline; a git-versionable YAML queue spec
  (`assets/queue-format.md`) as the recommended batch entry.
- **Reference & `.bib` import** (`assets/prism_refs.py`) — turn a paper's whole
  bibliography (a LaTeX `.bib`, or a PDF's References section) into a queue:
  zero-dependency BibTeX parser, robust arXiv-id/DOI extraction (new + old id
  styles), and a prose-vs-author-list title heuristic for PDF references.
- **Discovery sources (Mode 7)** — paper-prism ingests the output of *separate* upstream
  discovery skills (a daily digest, a topic search, Semantic Scholar, arXiv) via a
  lenient JSON contract `{title, arxiv?, doi?, score?, why?}`; `load_discovery` +
  `discovery_to_queue` sort by score, take the top-K, and map score→priority /
  why→relevance. paper-prism stays the deep-processing backend and does not scrape or
  score itself.
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
  `~/.config/paper-prism/config.json` → built-in defaults.
- **Stdlib-first helper library** (`prism_helpers.py`, `prism_config.py`) for
  PDF rendering, PIL cropping, arXiv figure download, Marp rendering, the binding
  writers, and the queue parsers — optional deps lazily imported.
- **Test suite** — 132 checks, zero external dependencies
  (`python3 tests/test_prism.py`), covering config/labels, the three binders,
  both MOC writers, the queue parsers, checkpoint/resume, reference/discovery
  ingestion, a synthetic-SQLite Zotero fixture, and the security/robustness
  regressions below.

### Security & robustness (pre-release hardening from a parallel review swarm)

- **No-data-loss resources block** — the auto-managed links block is now delimited
  by `<!-- paper-prism:resources:start/end -->` sentinels and refreshed strictly between
  them, so a re-bind can never delete a metadata table or prose a user wrote below
  the links (previously a greedy regex could). Legacy blocks migrate safely.
- **Path-traversal guard** — `safe_name()` sanitises any paper-derived
  `method_name`/`project` before it touches a vault path (no `../`, no escape).
- **Figure-download allowlist** — only `https` on `arxiv.org` is fetched; `file://`,
  `ftp://`, protocol-relative, and off-host URLs from parsed HTML are blocked
  (prevents SSRF / local-file reads). arXiv ids are shape-validated before use.
- **Queue validation** — `parse_paper_queue` enforces the documented contract
  (project ASCII, parallel 1–8, notes_strategy enum, one source per paper, `.pdf`
  paths, filesystem-safe `method_name`), honours `skip:` and `default_priority`/
  `default_status`, and no longer crashes on an empty/comment-only file.
- **Checkpoint schema gate** — the state file carries a `schema_version`; an
  incompatible/old state is reset rather than resumed from stale artifacts.
- **Zotero temp DB** — copied to a private `0600` temp file (unique name, removed
  at exit) instead of a world-readable fixed `/tmp` path; still strictly read-only.
- Subprocess timeouts (`pdftoppm`/`marp`/`pdftotext`), a small `urlopen` retry,
  stricter old-style arXiv-id matching, quote-aware mini-YAML comments, and a
  fixed `zotero.search` ordering bug found by the new fixture.

[0.1.0]: https://github.com/ArthurYangX/paper-prism/releases/tag/v0.1.0
