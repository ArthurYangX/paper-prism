# Showcase · "Attention Is All You Need" → a full prism package

An end-to-end run of prism on a single **public** paper
([arXiv 1706.03762](https://arxiv.org/abs/1706.03762)), kept here as a worked
example of what one paper looks like after prism refracts it.

Everything was produced by the real pipeline — `load_config` → page render →
`crop_region` figure/table screenshots → twelve-question analysis → main note →
Marp deck → Plan-C binding (`inject_resources_block`, `append_to_slides_moc`,
`update_project_moc`). Output was written into an **isolated demo vault**
(`vault/`), never a real Obsidian vault.

## What's in the repo (the lightweight artifacts)

```
vault/papers/Showcase/
├── Transformer.md                 the main note — 12 questions, 5 formula
│                                  triplets, every figure/table, a concept graph
├── 00 Showcase.md                 per-project reading-queue MOC
└── _slides/Transformer/
    ├── Transformer.slides.md       the Marp deck source (35 pages)
    └── assets/                     the 7 figure/table screenshots (the iron rule:
                                    tables are screenshots, never re-typed)
vault/_MOC/Slide Library.md         global deck index
preview/                            4 rendered slides (cover · architecture ·
                                    results · take-away) so you can see the deck
```

## What's intentionally *not* committed (the heavy binaries)

To keep the repo small, the rendered binaries are git-ignored — regenerate them
in seconds:

| File | How to regenerate |
|------|-------------------|
| `Transformer.slides.pdf` / `.pptx` | `marp Transformer.slides.md --pdf --allow-local-files -o Transformer.slides.pdf` (and `--pptx`) |
| `Transformer.pdf` (the source paper) | download from arXiv: `curl -L -o Transformer.pdf https://arxiv.org/pdf/1706.03762` |
| `attention.pdf` (input) | same arXiv PDF |
| `prism-demo-config.json` | a local config pointing `vault_path` at this `vault/` (held out — it carries an absolute machine path) |

## Notes

- The deck's take-away page exercises (and validated a fix for) the
  `slide-template.md` dark-section contrast handling.
- Figures/tables were cropped with the manual `render → Read-verify → re-crop`
  loop; that Read-verify step is what catches truncated crops (see
  `docs/design-notes.md` → "Optional layout backend").
