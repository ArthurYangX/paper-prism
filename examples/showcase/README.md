# paper-prism · Output Showcase

This folder is for screenshots and recordings of real paper-prism output.
If you have run paper-prism on a paper queue, capture the images listed below and
drop them here so newcomers can see what finished output looks like before
they try it themselves.

---

## What a finished paper-prism run produces

For each paper, paper-prism writes a **three-piece folder** inside your Obsidian vault
under `{project}/_slides/{MethodName}/`:

1. **Main note** (`{MethodName}.md`) — a structured, heavily-linked Obsidian note
   answering twelve canonical questions about the paper (problem, method,
   key equations, experiments, limitations, connections to your project, …).
   The note embeds the PDF inline so you can read the source without leaving
   Obsidian, and it carries YAML front-matter tags that the MOC query reads.

2. **Slide deck** (`{MethodName}.slides.pdf` + `.pptx`) — a ~30-page Marp deck
   exported in both formats. Slides follow a consistent template: title /
   problem statement / method overview / key figures / ablations / takeaways /
   your-project relevance. The PPTX is editable for lab presentations.

3. **Concept graph** (written as wiki-links inside the main note) — every method,
   dataset, and concept mentioned gets a `[[WikiLink]]`, so Obsidian's Graph View
   automatically builds a knowledge graph across all papers you have read.

After the whole queue finishes, paper-prism appends a row for each paper into the
**Project MOC** (`{project}/MOC.md`) — a Dataview table with columns: method
name, category, relevance, priority, status emoji, and a direct link to the
main note. The MOC is idempotent: re-running the queue only adds rows for
papers not yet present.

---

## Screenshots to capture

Add images here and update the links below. Each caption describes what the
screenshot should show so the list is useful before any images exist.

### Main note

![main note](note.png)

*The rendered Obsidian note for one paper: YAML front-matter, the twelve-question
body with headers and callouts, and the embedded PDF panel at the bottom.*

### Slide deck (PDF)

![slide deck PDF](slides-pdf.png)

*The exported Marp slide deck open in a PDF viewer, showing the title slide and
two or three content slides so the layout and density are visible.*

### Concept graph

![concept graph](graph.png)

*Obsidian Graph View after reading 5–10 papers: nodes for each method linked by
shared concepts (dataset names, loss functions, benchmark tasks), coloured by
project category.*

### Project MOC table

![project MOC](moc.png)

*The MOC.md file rendered in Obsidian, showing the Dataview table with all
processed papers, their category / relevance columns, priority badges, and
status emojis (some ⏳, some ✅).*

### Batch run terminal output

![batch terminal](terminal.png)

*Terminal output of a parallel batch run: the progress lines showing papers
being processed concurrently, download messages for arXiv PDFs, and the final
summary line.*

---

## Contributing a screenshot

1. Run paper-prism on `examples/papers.example.yaml` (see `examples/README.md`).
2. Take a screenshot of each artifact above.
3. Save them as `note.png`, `slides-pdf.png`, `graph.png`, `moc.png`,
   `terminal.png` in this folder.
4. Open a PR — maintainers will merge once images look representative.
