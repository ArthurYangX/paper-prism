# Showcase · two public papers → full paper-prism packages

End-to-end runs of paper-prism on two **public** papers, kept as worked examples of
what a paper looks like after paper-prism refracts it — and of how a project's indexes
accumulate across papers:

1. **Transformer** — *Attention Is All You Need* ([arXiv 1706.03762](https://arxiv.org/abs/1706.03762))
2. **Mamba** — *Linear-Time Sequence Modeling with Selective State Spaces* ([arXiv 2312.00752](https://arxiv.org/abs/2312.00752))

Both were produced by the real pipeline and written into an **isolated demo
vault** (`vault/`), never a real Obsidian vault. (The folder is named
`run-attention` for the first run; it now holds the whole `Showcase` project.)

### How each was produced
- **Transformer** — coordinator-driven (serial), figures/tables cropped with the
  manual `render → Read-verify → re-crop` loop.
- **Mamba** — a real **parallel A/B/C subagent fan-out** (Opus analysis · Sonnet
  figures via arXiv HTML · Sonnet table screenshots), then reconciled by the
  coordinator (figure/table numbering aligned, a mislabeled "Table 2" corrected to
  a figure, the table-map finished). A demonstration that fan-out works *and* that
  the coordinator pass is what makes it correct.

## What's in the repo (the lightweight artifacts)

```
vault/papers/Showcase/
├── Transformer.md · Mamba.md        the main notes (12 questions, formula
│                                    triplets, every figure/table, concept graph)
├── 00 Showcase.md                   per-project reading-queue MOC (now 2 rows)
└── _slides/{Transformer,Mamba}/
    ├── *.slides.md                   the Marp deck sources (35 / 39 pages)
    └── assets/                       figure + table screenshots
                                      (tables = screenshots, never re-typed)
vault/_MOC/Slide Library.md           global deck index (now 2 rows)
preview/                              8 rendered slides (cover · architecture/
                                      overview · results · take-away, per paper)
```

## What's intentionally *not* committed (the heavy binaries)

To keep the repo small, the rendered binaries are git-ignored — regenerate in
seconds:

| File | How to regenerate |
|------|-------------------|
| `*.slides.pdf` / `*.slides.pptx` | `marp <name>.slides.md --pdf --allow-local-files -o <name>.slides.pdf` (and `--pptx`) |
| source PDFs (`Transformer.pdf`, `Mamba.pdf`, `attention.pdf`, `mamba.pdf`) | download from arXiv, e.g. `curl -L -o mamba.pdf https://arxiv.org/pdf/2312.00752` |
| `paper-prism-demo-config.json` | a local config pointing `vault_path` at this `vault/` (held out — it carries an absolute machine path) |

## Notes

- The take-away slide validated a fix to `slide-template.md`'s dark-section
  contrast/zebra-stripe handling.
- The Mamba run surfaced (and the coordinator fixed) a real fan-out failure mode:
  sub-agents can finish their mechanical work but not their self-check/finalize
  step — see `docs/design-notes.md` → "Optional layout backend" for why the
  Read-verify loop and coordinator review are load-bearing.
