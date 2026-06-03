# Contributing to paper-prism

Thanks for helping refract papers better. paper-prism is a Claude Code skill plus a
small, deliberately boring Python toolbox. Contributions that keep it boring —
deterministic, stdlib-first, well-tested — are the most welcome.

## Run the tests first

```bash
python3 tests/test_prism.py
```

The suite is **186 checks with zero external dependencies** and it must stay
green and dependency-free. It gates everything: config/label resolution, the
three-piece binding (idempotency + user-content protection), both MOC writers,
and the queue parsers. If your change touches `skills/paper-prism/assets/*.py`, add or
update a check; a feature without a check is treated as unfinished.

## Common changes

### Add a concept bucket
Concept notes are filed into categories. To add or rename a bucket, edit
`skills/paper-prism/references/concept-categories.md` — that file is the single source
of truth for the category list, the per-paper concept budget, and the
alias-dedup rules. No code change is needed; the skill reads the categories from
there.

### Add or change an output language label
Generated headings are i18n. Each language is a flat label dict in
`skills/paper-prism/assets/prism_config.py`:

- to tweak a single English/Chinese heading, edit `LABELS_EN` / `LABELS_ZH`;
- to add a new language, add a `LABELS_<XX>` dict with the same keys and register
  it in the `_PRESETS` map.

Keep every preset key-for-key complete with `LABELS_EN` — the binding helpers
look labels up by key and will `KeyError` on a missing one. Add a `get_labels`
check in `tests/test_prism.py` for any new preset.

## Code style

- **Stdlib-first.** Prefer the standard library. A third-party import (Pillow,
  PyYAML, Marp via subprocess) must be *optional* and lazily imported, so the
  config and binding logic always run on a bare Python 3.10+.
- **Type hints** on every public function signature.
- **Docstrings explain *why*, not *what*.** The interesting docstrings in
  `prism_helpers.py` say things like "always pass a paper-specific prefix or
  `/tmp/page-01.png` collides across coordinators" — that is the bar.
- **Idempotent file writers.** Anything that edits a note or a MOC must be safe
  to re-run and must never swallow user prose. There are tests that enforce this;
  do not weaken them.
- Target **Python 3.10+** syntax (`str | None`, `list[dict]`, etc.).

## Pull requests

- Keep PRs focused — one bucket, one helper, one fix.
- State what you changed and why, and confirm `python3 tests/test_prism.py`
  passes (paste the `OK — N checks passed` line).
- If you change skill behavior, update the relevant section of
  `skills/paper-prism/SKILL.md` and any affected `references/*.md` in the same PR.
- New behavior in `*.py` ⇒ new or updated checks in `tests/test_prism.py`.
- Be honest about provenance. If you port an idea from another skill, note it.

## Attribution

paper-prism derives from the community skill `paper-reader` (see [NOTICE](NOTICE)). If
you recognize that skill or are its author, please open an issue — credit is
owed and we want to give it.
