# Figure Acquisition Troubleshooting Guide

## The arXiv HTML figure-URL pitfall

The arXiv HTML asset numbering (x1.png, x2.png, ...) **does not necessarily correspond to the paper's Figure numbers**! That is, the x-number ≠ the printed Figure number.

Common problems:
- Small icons / arrows / symbol images also take up numbers, so it is easy to download the wrong image
- The subfigures of one Figure (a/b/c) may use non-contiguous numbers
- Some Figures are composed of several small images stitched together

**How to fix**:
1. When fetching the page, extract each Figure's caption and its corresponding img src. `prism_helpers.fetch_arxiv_html(arxiv_id)` retrieves the HTML, and `prism_helpers.parse_arxiv_figures(html, arxiv_id)` returns the (Figure caption ↔ img src) mapping.
2. After downloading, **you must verify** — Read each image to confirm the content is correct.
3. When a file is < 10KB, you must re-check it (a tiny file is almost always an icon, not the real figure).

## Multi-source fallback strategy

When arXiv HTML retrieval fails or the figures are incomplete, try the following sources in order: **arXiv HTML → project page → pdfimages**.

### Source A: arXiv HTML (preferred)
- `prism_helpers.fetch_arxiv_html(arxiv_id)` to get `https://arxiv.org/html/{arxiv_id}`, then `prism_helpers.parse_arxiv_figures(...)` to extract the img src of each `<figure>`
- First count the paper's total number of Figures to ensure complete extraction
- `prism_helpers.download_figures(figures, dest_dir)` downloads the parsed figures

### Source B: project page (supplementary)
- Find the project page from the paper's abstract / HTML (keywords: `project page`, `github.io`, `our website`)
- Fetch the project page and extract its showcase images (teaser / demo figures)
- Good for obtaining the method-overview figure that is missing from the arXiv HTML

### Source C: PDF extraction (final fallback)
```bash
wget -O /tmp/paper.pdf "https://arxiv.org/pdf/{arxiv_id}.pdf"
mkdir -p {note directory}/assets/
pdfimages -png /tmp/paper.pdf {note directory}/assets/{method name}_fig
```
For figures embedded as vector regions or full pages, use `prism_helpers.render_pdf_pages(pdf_path, pages)` to render pages to images and `prism_helpers.crop_region(image_path, box)` to crop out the specific figure region.
After extraction, verify: file >10KB, and Read to confirm the content is correct.

## Selective localization (resolving unreachable external links) — OPTIONAL

arXiv external links are unstable in some network environments. If you have an image-reachability script, run it on the saved note to localize unreachable links; otherwise skip this step — it is not blocking.

A reachability script typically behaves as follows:
- Concurrently check the HTTP reachability of all external-link images (10s timeout)
- **Reachable** → leave the external link unchanged
- **Unreachable** → download to `assets/{method name}_fig{N}.{ext}` and replace with an `![[...]]` wikilink
- If the download also fails, try extracting the corresponding figure from the PDF (see Source C above)
- When any localization happens, update frontmatter `image_source: online` → `mixed`

## Image-URL normalization (preventing path duplication)

The image paths returned by an HTML fetch may be **relative** (e.g. `2603.05312v1/x1.png`) or **already-resolved absolute** paths.
When concatenating the URL, a path-duplication bug is very easy to hit (e.g. `.../2603.05312v1/2603.05312v1/x1.png`) — the duplicated arXiv-id path segment.

**Iron rule**: before writing to the note, run the following checks on every image URL:

1. If the URL is already the full `https://arxiv.org/html/...` form, use it directly — do not concatenate again.
2. If it is a relative path, use **only** `https://arxiv.org/html/` as the base — do not add `{arxiv_id}/` again.
   - Because the relative path usually already contains `{arxiv_id}/` (e.g. `2603.05312v1/x1.png`).
3. **Final validation**: check whether the URL contains two consecutive identical arxiv_id segments (e.g. `2603.05312v1/2603.05312v1/`); if so, delete the duplicated segment.

Example:
```
✗ https://arxiv.org/html/2603.05312v1/2603.05312v1/x1.png  ← duplicated
✓ https://arxiv.org/html/2603.05312v1/x1.png               ← correct
```

(`prism_helpers.parse_arxiv_figures` already returns normalized absolute URLs; apply this rule whenever you build a URL by hand.)

## Image reference format in notes

**External link** (default):
```markdown
![Figure 1](https://arxiv.org/html/xxxx/x1.png)
```

**Local** (fallback when the external link is unavailable):
```markdown
![[{method name}_fig1_overview.png]]
![[{method name}_fig1_overview.png|600]]  <!-- specify width -->
```

## Recording the image source in frontmatter

```yaml
---
image_source: online  # default online; set to mixed when some images are local
arxiv_id: "2501.12345"
---
```
