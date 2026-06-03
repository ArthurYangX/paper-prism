"""paper-prism · pipeline helper functions.

These are the deterministic, file-touching building blocks the paper-prism skill
calls during Phase 2 (extraction) and Phase 4 (render + bind). Keeping them
in Python — rather than asking the model to hand-roll regex each run — is what
makes batch processing reproducible and idempotent.

Groups:
    1. PDF page rendering        render_pdf_pages
    2. Region cropping (PIL)     crop_region, page_size
    3. arXiv HTML figures        fetch_arxiv_html, parse_arxiv_figures, download_figures
    4. Slide rendering (marp)    marp_render
    5. Three-piece binding       copy_paper_pdf, inject_resources_block
    6. Global slide MOC          append_to_slides_moc
    7. Project reading-queue MOC update_project_moc, bootstrap_project
    8. Input queues              parse_paper_queue, folder_to_queue

All output-text functions accept an optional `cfg` and resolve headings via
the i18n label set (English by default; see prism_config). None of them
hard-code a personal path or assume Chinese.

CLI:
    python3 prism_helpers.py render  <pdf> <out_dir> <first> <last> [prefix]
    python3 prism_helpers.py crop    <png> <out> <l> <t> <r> <b>
    python3 prism_helpers.py figures <arxiv_id> <out_dir> [prefix]
    python3 prism_helpers.py marp    <md> <out_dir>
    python3 prism_helpers.py queue   <queue.yaml>
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

# prism_config sits next to this file
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prism_config import load_config, get_labels, safe_name, __version__  # noqa: E402

# Sentinels that delimit the auto-managed resources block inside a paper note.
# Refreshing replaces strictly between these — never touching user prose.
_RES_START = "<!-- paper-prism:resources:start -->"
_RES_END = "<!-- paper-prism:resources:end -->"

# arXiv id shape (new YYMM.NNNNN[vN] + old archive/7digits) — validated before
# it is ever interpolated into a URL.
_ARXIV_ID_RE = re.compile(
    r"^(?:\d{4}\.\d{4,5}(?:v\d+)?|[a-z][a-z\-]*(?:\.[A-Z]{2})?/\d{7})$")


def _valid_arxiv_id(arxiv_id: str) -> bool:
    return bool(_ARXIV_ID_RE.match(str(arxiv_id).strip()))


def _is_allowed_fig_url(url: str) -> bool:
    """Allow only http(s) on arxiv.org (or a subdomain). Blocks file:, ftp:,
    data:, protocol-relative `//host`, and any off-host absolute URL — so a
    malicious figure `src` in fetched HTML can't trigger SSRF or read local
    files via the default urllib opener's File/FTP handlers."""
    from urllib.parse import urlparse
    u = urlparse(url)
    if u.scheme not in ("http", "https"):
        return False
    host = (u.hostname or "").lower()
    return host == "arxiv.org" or host.endswith(".arxiv.org")


def _http_get(url: str, timeout: int = 30, retries: int = 2) -> bytes:
    """GET bytes with a small retry for transient arXiv hiccups."""
    req = urllib.request.Request(url, headers={"User-Agent": f"paper-prism/{__version__}"})
    last: Exception | None = None
    for _ in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
    raise last  # type: ignore[misc]


# ===========================================================================
# 1. Render PDF pages -> PNG  (for table screenshots)
# ===========================================================================
def render_pdf_pages(
    pdf: str,
    out_dir: str,
    first: int,
    last: int,
    dpi: int = 200,
    prefix: str = "page",
) -> list[str]:
    """Render pages [first, last] of `pdf` to PNG. Returns sorted output paths.

    ALWAYS pass a paper-specific `prefix` when several papers run in parallel,
    or `/tmp/page-01.png` collides across coordinators:
        render_pdf_pages(pdf, "/tmp", 9, 16, prefix="Mamba_page")
        -> /tmp/Mamba_page-09.png ...
    Requires `pdftoppm` (poppler).
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    full_prefix = Path(out_dir) / prefix
    subprocess.run(
        ["pdftoppm", "-png", "-r", str(dpi),
         pdf, str(full_prefix), "-f", str(first), "-l", str(last)],
        check=True, timeout=180,
    )
    return sorted(str(p) for p in Path(out_dir).glob(f"{prefix}-*.png"))


# ===========================================================================
# 2. Crop a region (PIL)
# ===========================================================================
def crop_region(src: str, out: str, box: tuple[int, int, int, int]) -> str:
    """Crop `box` = (left, top, right, bottom) pixels from `src` into `out`."""
    from PIL import Image  # local import: only needed when cropping
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Image.open(src).crop(box).save(out)
    return out


def page_size(src: str) -> tuple[int, int]:
    from PIL import Image
    return Image.open(src).size


# ===========================================================================
# 3. arXiv HTML figures  (recommended extraction path)
# ===========================================================================
def download_arxiv_pdf(arxiv_id: str, dest_dir: str, prefix: str = "") -> str | None:
    """Download an arXiv PDF deterministically. Returns the saved path, or None.

    Fetches `https://arxiv.org/pdf/{id}` via the retrying `_http_get` (the id is
    shape-validated; the host is fixed to arxiv.org over https). Verifies the bytes
    start with the `%PDF-` magic before writing, so a captcha / HTML error page is
    never saved as a `.pdf`. This is the deterministic downloader the `arxiv:` queue
    mode and SKILL §1.2 promise, so the skill never has to improvise a `curl`.
    """
    if not _valid_arxiv_id(arxiv_id):
        return None
    try:
        data = _http_get(f"https://arxiv.org/pdf/{arxiv_id}")
    except Exception:  # noqa: BLE001
        return None
    if not data or data[:5] != b"%PDF-":
        return None
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    out = Path(dest_dir) / f"{prefix or arxiv_id.replace('/', '_')}.pdf"
    out.write_bytes(data)
    return str(out)


def fetch_arxiv_html(arxiv_id: str, cache_path: str | None = None) -> str:
    """Download an arXiv HTML5 fulltext page (arxiv.org/html/{id}). Returns HTML."""
    if cache_path and os.path.exists(cache_path):
        return Path(cache_path).read_text()
    if not _valid_arxiv_id(arxiv_id):
        raise ValueError(f"refusing to fetch malformed arXiv id: {arxiv_id!r}")
    url = f"https://arxiv.org/html/{arxiv_id}"
    html = _http_get(url).decode("utf-8", errors="replace")
    if cache_path:
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        Path(cache_path).write_text(html)
    return html


def parse_arxiv_figures(html: str) -> list[dict]:
    """Parse <figure> blocks. Returns [{id, src, caption}, ...].

    This is the recommended path: download exactly the images the HTML
    references, with their captions — never a blind x1..x30 scan.
    """
    out: list[dict] = []
    pattern = r'<figure[^>]*id="([^"]+)"[^>]*>(.*?)</figure>'
    for fid, body in re.findall(pattern, html, re.DOTALL):
        img = re.search(r'src="([^"]+\.(?:png|jpg|jpeg|svg))"', body)
        cap = re.search(r"<figcaption[^>]*>(.*?)</figcaption>", body, re.DOTALL)
        if not img:
            continue
        caption = re.sub(r"<[^>]+>", "", cap.group(1) if cap else "").strip()
        out.append({"id": fid, "src": img.group(1), "caption": caption[:240]})
    return out


def download_figures(
    arxiv_id: str,
    figures: list[dict],
    out_dir: str,
    prefix: str = "fig",
    min_bytes: int = 10 * 1024,
) -> list[dict]:
    """Download exactly the figures in `figures` (from parse_arxiv_figures).

    Returns the list annotated with {"file": local_path, "ok": bool}. Skips
    anything smaller than `min_bytes` (icons/blanks). Caller should still Read
    each image to verify content matches caption (arXiv x-numbers do NOT map
    1:1 to printed Figure numbers).
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    base = f"https://arxiv.org/html/{arxiv_id}/" if _valid_arxiv_id(arxiv_id) else ""
    annotated = []
    for i, fig in enumerate(figures, 1):
        src = fig["src"]
        rec = dict(fig)
        # SECURITY: reject any non-http(s) scheme up front (file://, ftp://,
        # data://) so it can't be smuggled in as a "relative" src either.
        if "://" in src and not src.startswith(("http://", "https://")):
            rec.update(file=None, ok=False, reason="blocked_url")
            annotated.append(rec)
            continue
        # de-dup accidental repeated id segments e.g. 2312.00752v1/2312.00752v1/
        url = src if src.startswith("http") else (base + src.lstrip("/") if base else "")
        url = re.sub(r"/([^/]+)/\1/", r"/\1/", url)
        ext = os.path.splitext(src)[1] or ".png"
        dst = Path(out_dir) / f"{prefix}_{i:02d}{ext}"
        # SECURITY: only fetch https on arxiv.org — a hostile absolute `src`
        # (//evil, http://169.254.169.254) must never be fetched.
        if not _is_allowed_fig_url(url):
            rec.update(file=None, ok=False, reason="blocked_url")
            annotated.append(rec)
            continue
        try:
            data = _http_get(url)
            if len(data) >= min_bytes:
                dst.write_bytes(data)
                rec.update(file=str(dst), ok=True)
            else:
                rec.update(file=None, ok=False, reason="too_small")
        except Exception as e:  # noqa: BLE001
            rec.update(file=None, ok=False, reason=str(e)[:80])
        annotated.append(rec)
    return annotated


# ===========================================================================
# 4. Marp render  (slides -> PDF + PPTX)
# ===========================================================================
def marp_render(
    md: str,
    out_dir: str,
    formats: tuple[str, ...] = ("pdf", "pptx"),
) -> dict[str, str]:
    """Render a Marp markdown deck to the given formats. Returns {fmt: path}."""
    if shutil.which("marp") is None:
        raise RuntimeError("marp not found. Install: npm i -g @marp-team/marp-cli")
    stem = Path(md).stem
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    results = {}
    for fmt in formats:
        out = str(Path(out_dir) / f"{stem}.{fmt}")
        subprocess.run(
            ["marp", md, f"--{fmt}", "--allow-local-files", "-o", out],
            check=True, timeout=300,
        )
        results[fmt] = out
    return results


# ===========================================================================
# 5. Three-piece binding
# ===========================================================================
def copy_paper_pdf(src_pdf: str, dst_dir: str, method_name: str) -> str:
    """Copy the source PDF into the deck folder as {method}.pdf (idempotent).

    method_name is sanitised so a paper-derived name can't escape dst_dir.
    """
    method_name = safe_name(method_name)
    Path(dst_dir).mkdir(parents=True, exist_ok=True)
    dst = Path(dst_dir) / f"{method_name}.pdf"
    if dst.exists() and dst.stat().st_size == Path(src_pdf).stat().st_size:
        return str(dst)
    shutil.copy2(src_pdf, dst)
    return str(dst)


def inject_resources_block(
    note_path: str,
    method_name: str,
    *,
    arxiv_url: str = "",
    zotero_key: str = "",
    github_url: str = "",
    project: str = "",
    title: str = "",
    create_if_missing: bool = True,
    cfg: dict[str, Any] | None = None,
) -> None:
    """Insert or refresh the resources block at the top of a paper note.

    The block is delimited by `<!-- paper-prism:resources:start/end -->` sentinels, so a
    refresh replaces *strictly between them* and can never swallow user prose
    (e.g. a metadata table the user filled in below the links). Idempotent and
    safe to re-run across a batch / after a crash. If the note is missing and
    create_if_missing, a minimal stub is written.
    """
    cfg = cfg or load_config()
    L = get_labels(cfg)
    method_name = safe_name(method_name)
    project = safe_name(project) if project else ""
    sub = cfg["slides_subdir"]
    base = f"{sub}/{method_name}"
    heading = L["resources_heading"]

    lines = [
        heading,
        "",
        f"- {L['label_paper']}: ![[{base}/{method_name}.pdf]]",
        f"- {L['label_slides']}: ![[{base}/{method_name}.slides.pdf]]",
    ]
    if zotero_key:
        lines.append(f"- {L['label_zotero']}: [Open in Zotero (annotations)](zotero://select/library/items/{zotero_key})")
    if arxiv_url:
        lines.append(f"- {L['label_arxiv']}: {arxiv_url}")
    if github_url:
        lines.append(f"- {L['label_code']}: {github_url}")
    if project:
        lines.append(f"- {L['label_project']}: [[00 {project}]]")
    # sentinel-wrapped block (always ends with a newline)
    wrapped = _RES_START + "\n" + "\n".join(lines) + "\n" + _RES_END + "\n"

    p = Path(note_path)
    title_line = f"# {L['note_title_prefix']}{title or method_name}"

    if not p.exists():
        if not create_if_missing:
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        stub = (
            f'---\nmethod_name: "{method_name}"\ntitle: "{title}"\n---\n\n'
            f"{title_line}\n\n"
            f"{wrapped}\n"
            f"{L['tldr_heading']}\n\n> {L['todo']}\n\n"
            f"{L['contributions_heading']}\n\n- {L['todo']}\n"
        )
        p.write_text(stub)
        return

    content = p.read_text()

    # 1) Sentinels present -> replace strictly between them (always safe).
    if _RES_START in content and _RES_END in content:
        new = re.sub(
            re.escape(_RES_START) + r".*?" + re.escape(_RES_END) + r"\n?",
            wrapped,
            content,
            count=1,
            flags=re.DOTALL,
        )
    # 2) Legacy block (heading + a contiguous bullet list, no sentinels) ->
    #    replace ONLY the heading + that list, preserving anything after it
    #    (blockquotes, the metadata table, etc.). Adds sentinels for next time.
    elif heading in content and re.search(
            re.escape(heading) + r"\n(?:[ \t]*\n)*(?:[-*] .*\n)+", content):
        new = re.sub(
            re.escape(heading) + r"\n(?:[ \t]*\n)*(?:[-*] .*\n)+",
            wrapped,
            content,
            count=1,
        )
    # 3) No block yet -> insert after the title heading, else after frontmatter.
    else:
        title_re = rf"(^# {re.escape(L['note_title_prefix'])}.*?\n)"
        new, n = re.subn(title_re, r"\1\n" + wrapped + "\n", content, count=1, flags=re.MULTILINE)
        if n == 0:  # no title heading -> after frontmatter, else prepend
            new, n = re.subn(r"(^---\n.*?\n---\n)", r"\1\n" + wrapped + "\n", content,
                             count=1, flags=re.DOTALL)
            if n == 0:
                new = wrapped + "\n" + content
    p.write_text(new)


# ===========================================================================
# 6. Global slide-library MOC
# ===========================================================================
def _slides_moc_header(cfg: dict[str, Any]) -> str:
    L = get_labels(cfg)
    cols = L["slides_moc_columns"]
    sep = "|" + "|".join(["------"] * (cols.count("|") - 1)) + "|"
    return f"{L['slides_moc_title']}\n\n{L['slides_moc_note']}\n\n{cols}\n{sep}\n"


def append_to_slides_moc(
    moc_path: str,
    method_name: str,
    *,
    tag: str = "",
    venue: str = "",
    year: str = "",
    slides_pdf_rel: str = "",
    preview_width: int = 400,
    cfg: dict[str, Any] | None = None,
) -> None:
    """Append or update one row in the global slide-library MOC.

    Matches an existing row by `[[method_name]]` and updates in place; else
    inserts after the last table row (never at EOF after prose). Creates the
    file with a header if missing.
    """
    cfg = cfg or load_config()
    p = Path(moc_path)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_slides_moc_header(cfg))
    content = p.read_text()

    row = (
        f"| [[{method_name}]] | {tag or '—'} | {venue or '—'} {year} "
        f"| ![[{slides_pdf_rel}|{preview_width}]] |"
    )
    pattern = re.compile(rf"^\| \[\[{re.escape(method_name)}\]\] .*$", re.MULTILINE)
    if pattern.search(content):
        new = pattern.sub(row, content)
    else:
        rows = list(re.finditer(r"^\| \[\[.*\]\] .*$", content, re.MULTILINE))
        if rows:
            pos = rows[-1].end()
            new = content[:pos] + "\n" + row + content[pos:]
        else:
            new = content.rstrip() + "\n" + row + "\n"
    p.write_text(new)


# ===========================================================================
# 7. Project reading-queue MOC
# ===========================================================================
def bootstrap_project(project: str, cfg: dict[str, Any] | None = None) -> str:
    """Create `00 {project}.md` with a reading-queue table if it doesn't exist.

    Returns the path. Safe to call repeatedly (no-op if present).
    """
    cfg = cfg or load_config()
    L = get_labels(cfg)
    project = safe_name(project)
    notes = Path(cfg["vault_path"]).expanduser() / cfg["notes_folder"] / project
    notes.mkdir(parents=True, exist_ok=True)
    moc = notes / f"00 {project}.md"
    if moc.exists():
        return str(moc)
    cols = L["project_queue_columns"]
    sep = "|" + "|".join(["---"] * (cols.count("|") - 1)) + "|"
    moc.write_text(
        f"---\ntype: project-moc\nproject: {project}\n---\n\n"
        f"# 00 {project}\n\n"
        f"## Reading Queue\n\n"
        f"> Auto-maintained by paper-prism. Status: ✅ done / ◐ reading / ⏳ queued / ❌ dropped\n\n"
        f"{cols}\n{sep}\n"
    )
    return str(moc)


def update_project_moc(
    moc_path: str,
    method_name: str,
    *,
    method_label: str = "",
    category: str = "",
    venue: str = "",
    year: str = "",
    status: str = "✅",
    priority: str = "★★★",
    relevance: str = "",
) -> bool:
    """Append/update one row in a project MOC reading-queue table.

    Matches the queue table by its leading `| # |` header and the row by
    `[[method_name]]`. Maintains the running index. Returns True if written,
    False if the MOC or its queue table is absent (then it's skipped, not
    created — call bootstrap_project first if you want auto-creation).
    """
    p = Path(moc_path)
    if not p.exists():
        return False
    content = p.read_text()
    if not re.search(r"^\| # \|.*$", content, re.MULTILINE):
        return False

    pattern = re.compile(rf"^\| \d+ \| \[\[{re.escape(method_name)}\]\] .*$", re.MULTILINE)

    def build_row(num: int) -> str:
        return (
            f"| {num} | [[{method_name}]] | {method_label or method_name} "
            f"| {category or '—'} | {venue or '—'} {year} | {status} | {priority} "
            f"| {relevance or '—'} |"
        )

    if pattern.search(content):
        m = pattern.search(content)
        num = int(re.match(r"\| (\d+) \|", m.group(0)).group(1))
        new = pattern.sub(build_row(num), content)
    else:
        rows = list(re.finditer(r"^\| (\d+) \| \[\[.*\]\] .*$", content, re.MULTILINE))
        nxt = (int(rows[-1].group(1)) + 1) if rows else 1
        if rows:
            pos = rows[-1].end()
            new = content[:pos] + "\n" + build_row(nxt) + content[pos:]
        else:
            sep = re.search(r"^\|[-: ]+\|.*$", content, re.MULTILINE)
            if sep:
                pos = sep.end()
                new = content[:pos] + "\n" + build_row(1) + content[pos:]
            else:
                new = content.rstrip() + "\n" + build_row(1) + "\n"
    p.write_text(new)
    return True


# ===========================================================================
# 8. Input queues  (folder / YAML -> list of paper specs)
# ===========================================================================
def folder_to_queue(folder: str, project: str = "") -> list[dict]:
    """Every *.pdf in `folder` -> a queue spec list. Method name left blank
    (the skill resolves it via the §1.1 extraction rules)."""
    out = []
    for pdf in sorted(Path(folder).expanduser().glob("*.pdf")):
        out.append({"id": pdf.stem, "path": str(pdf), "project": project})
    return out


def parse_paper_queue(yaml_path: str) -> dict:
    """Parse a queue YAML (see assets/queue-format.md). Returns
    {project, parallel, notes_strategy, papers:[...]}.

    Uses PyYAML if available; otherwise a tiny built-in parser covers the
    documented subset (flat scalars under `papers:` list items) so paper-prism works
    with a stock Python.
    """
    text = Path(yaml_path).expanduser().read_text()
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text)
    except Exception:  # noqa: BLE001
        data = _mini_yaml(text)
    if not isinstance(data, dict):     # empty / comment-only / non-mapping file
        data = {}
    data.setdefault("project", "Research")
    data.setdefault("parallel", 4)
    data.setdefault("notes_strategy", "full")
    if not isinstance(data.get("papers"), list):   # `papers:` with null value
        data["papers"] = []

    # --- top-level validation (matches queue-format.md) ---
    if not str(data["project"]).isascii():
        raise ValueError(f"project must be ASCII, got {data['project']!r}")
    if not isinstance(data["parallel"], int) or not (1 <= data["parallel"] <= 8):
        raise ValueError(f"parallel must be an int in 1..8, got {data['parallel']!r}")
    if data["notes_strategy"] not in ("full", "deck-only", "analysis-only"):
        raise ValueError(
            f"notes_strategy must be full|deck-only|analysis-only, got {data['notes_strategy']!r}")
    default_priority = data.get("default_priority")
    default_status = data.get("default_status")

    # Fields that must stay strings. YAML turns an unquoted `arxiv: 2410.00001`
    # into a float and loses precision, so coerce defensively (and tell users
    # to quote arXiv IDs in queue-format.md).
    _str_fields = ("id", "arxiv", "arxiv_id", "zotero", "method_name",
                   "category", "relevance", "priority", "title", "status")
    kept: list[dict] = []
    for i, pp in enumerate(data["papers"]):
        if not isinstance(pp, dict):
            raise ValueError(f"paper #{i} must be a mapping, got {type(pp).__name__}")
        for k in _str_fields:
            if k in pp and pp[k] is not None and not isinstance(pp[k], str):
                pp[k] = str(pp[k])
        if pp.get("skip") in (True, "true", "True"):     # honour `skip:` (drop it)
            continue
        srcs = [k for k in ("path", "arxiv", "zotero") if pp.get(k)]
        if len(srcs) != 1:
            raise ValueError(
                f"paper #{i} ({pp.get('id','?')}): need exactly one of "
                f"path/arxiv/zotero, got {srcs}")
        if pp.get("path"):
            path = str(Path(pp["path"]).expanduser())
            if not path.lower().endswith(".pdf"):
                raise ValueError(
                    f"paper #{i} ({pp.get('id','?')}): path must end in .pdf, got {path}")
            pp["path"] = path
        mn = pp.get("method_name")
        if mn and (mn != safe_name(mn) or " " in mn):
            raise ValueError(
                f"paper #{i} ({pp.get('id','?')}): method_name must be "
                f"filesystem-safe with no spaces, got {mn!r}")
        if default_priority and not pp.get("priority"):    # apply queue defaults
            pp["priority"] = default_priority
        if default_status and not pp.get("status"):
            pp["status"] = default_status
        kept.append(pp)
    data["papers"] = kept
    return data


def _mini_yaml(text: str) -> dict:
    """Minimal YAML for the queue subset: top-level scalars + a `papers:` list
    of `- key: value` blocks. No anchors/flow/multiline. Good enough as a
    zero-dependency fallback; install PyYAML for the real thing."""
    out: dict[str, Any] = {}
    papers: list[dict] = []
    cur: dict | None = None
    in_papers = False
    for raw in text.splitlines():
        line = "" if raw.lstrip().startswith("#") else _strip_inline_comment(raw).rstrip()
        if not line.strip():
            continue
        if re.match(r"^papers:\s*$", line):
            in_papers = True
            continue
        if not in_papers:
            m = re.match(r"^(\w+):\s*(.+)$", line)
            if m:
                out[m.group(1)] = _scalar(m.group(2))
            continue
        item = re.match(r"^\s*-\s*(\w+):\s*(.+)$", line)
        if item:
            cur = {item.group(1): _scalar(item.group(2))}
            papers.append(cur)
            continue
        kv = re.match(r"^\s+(\w+):\s*(.+)$", line)
        if kv and cur is not None:
            cur[kv.group(1)] = _scalar(kv.group(2))
    out["papers"] = papers
    return out


def _strip_inline_comment(line: str) -> str:
    """Remove an inline `#` comment, but NOT a `#` inside a quoted value."""
    quote: str | None = None
    for j, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (j == 0 or line[j - 1] in " \t"):
            return line[:j]
    return line


def _scalar(v: str) -> Any:
    v = v.strip().strip('"').strip("'")
    if v in ("true", "True"):
        return True
    if v in ("false", "False"):
        return False
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return v


# ===========================================================================
# CLI
# ===========================================================================
def _main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "render":
        prefix = args[4] if len(args) > 4 else "page"
        for p in render_pdf_pages(args[0], args[1], int(args[2]), int(args[3]), prefix=prefix):
            print(p)
    elif cmd == "crop":
        crop_region(args[0], args[1], tuple(int(x) for x in args[2:6]))  # type: ignore
        print(args[1])
    elif cmd == "figures":
        out = args[1]
        html = fetch_arxiv_html(args[0])
        figs = parse_arxiv_figures(html)
        prefix = args[2] if len(args) > 2 else "fig"
        for rec in download_figures(args[0], figs, out, prefix=prefix):
            print(json.dumps(rec, ensure_ascii=False))
    elif cmd == "marp":
        for fmt, path in marp_render(args[0], args[1]).items():
            print(f"{fmt}: {path}")
    elif cmd == "queue":
        print(json.dumps(parse_paper_queue(args[0]), ensure_ascii=False, indent=2))
    else:
        print(f"unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    _main()
