# paper-prism · Examples

| File / Folder | What it is |
|---|---|
| `papers.example.yaml` | Runnable batch queue of landmark public ML papers (Transformer, Mamba, LoRA, ViT, CLIP, CoT, LLaMA). Mix of `arxiv:`, `path:`, and `zotero:` entries. |
| `showcase/` | Screenshots of real paper-prism output — main note, slide deck, concept graph, project MOC. |

## Try it

1. Copy `papers.example.yaml` to your project folder (or just use it as-is for a demo).
2. Edit entries: swap in your own papers, set `skip: false` on the local-PDF entry if you have a real file.
3. Open Claude Code in a terminal and run: **"batch from examples/papers.example.yaml"**
4. Prism downloads arXiv PDFs, processes all papers in parallel, and writes notes + slides + MOC into your Obsidian vault under the `Demo` project folder.
