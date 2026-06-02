"""prism · reference & .bib import (Mode 6).

Turn a paper's bibliography — a LaTeX `.bib` file, or the reference section of a
PDF — into a prism queue, so you can say "process this paper's references" or
"batch from refs.bib" and read a whole citation neighbourhood.

Capabilities:
    parse_bib(path)                 BibTeX → entries (zero-dep parser)
    parse_references_from_text(t)   a PDF's References section → entries
    extract_arxiv_ids(text)         all arXiv ids in free text (new + old style)
    extract_dois(text)              all DOIs in free text
    refs_to_queue(entries, project) entries → runnable prism queue specs

Each entry is a dict: {key?, title, authors?, year?, arxiv?, doi?, url?}.
refs_to_queue maps arXiv-bearing entries to `arxiv:` queue items and the rest to
`zotero:` (title search) items, so the result is a valid queue (see
queue-format.md). Optional PyYAML is used to emit YAML; otherwise JSON.

CLI:
    python3 prism_refs.py bib refs.bib [--project NAME]
    python3 prism_refs.py pdf paper.pdf [--project NAME]   (needs pdftotext)
    python3 prism_refs.py ids "<free text>"
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# arXiv id forms:
#   new:  1409.0473  /  2312.00752v2   (YYMM.NNNNN, optional vN)
#   old:  cs/0501001 /  math.GT/0309136 (archive(.subclass)?/7digits)
_ARXIV_NEW = r"\d{4}\.\d{4,5}(?:v\d+)?"
_ARXIV_OLD = r"[a-z\-]+(?:\.[A-Z]{2})?/\d{7}"
_ARXIV_ANY = rf"(?:{_ARXIV_NEW}|{_ARXIV_OLD})"
_DOI = r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+"


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------
def extract_arxiv_ids(text: str) -> list[str]:
    """All arXiv ids in `text`, de-duplicated, order preserved.

    Bare new-style ids are only accepted when 'arxiv' appears nearby OR the id
    is in an obvious arXiv context (abs/pdf URL, eprint), to avoid matching
    page ranges / years. Old-style ids are unambiguous enough to take directly.
    """
    found: list[str] = []
    seen: set[str] = set()

    def add(x: str) -> None:
        x = x.strip().rstrip(".,;)")
        if x and x not in seen:
            seen.add(x)
            found.append(x)

    # explicit contexts first (most reliable)
    for m in re.finditer(rf"arxiv[:\s]*({_ARXIV_ANY})", text, re.IGNORECASE):
        add(m.group(1))
    for m in re.finditer(rf"arxiv\.org/(?:abs|pdf)/({_ARXIV_ANY})", text, re.IGNORECASE):
        add(m.group(1))
    # bare new-style ids near the word arxiv (windowed)
    for m in re.finditer(_ARXIV_NEW, text):
        s = max(0, m.start() - 30)
        if "arxiv" in text[s:m.start()].lower():
            add(m.group(0))
    # old-style ids are distinctive — accept anywhere
    for m in re.finditer(_ARXIV_OLD, text):
        add(m.group(0))
    return found


def extract_dois(text: str) -> list[str]:
    out, seen = [], set()
    for m in re.finditer(_DOI, text):
        d = m.group(0).rstrip(".,;)")
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


# ---------------------------------------------------------------------------
# BibTeX
# ---------------------------------------------------------------------------
def parse_bib(path: str) -> list[dict]:
    """Parse a .bib file into entries. Zero-dependency, brace-aware."""
    text = Path(path).expanduser().read_text(errors="replace")
    return parse_bib_text(text)


def parse_bib_text(text: str) -> list[dict]:
    entries: list[dict] = []
    i, n = 0, len(text)
    while i < n:
        at = text.find("@", i)
        if at < 0:
            break
        m = re.match(r"@(\w+)\s*\{", text[at:])
        if not m:
            i = at + 1
            continue
        etype = m.group(1).lower()
        if etype in ("comment", "preamble", "string"):
            i = at + m.end()
            continue
        body_start = at + m.end()           # just after the opening '{'
        depth, j = 1, body_start
        while j < n and depth:
            c = text[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            j += 1
        body = text[body_start:j - 1]
        entries.append(_parse_bib_entry(etype, body))
        i = j
    return entries


def _parse_bib_entry(etype: str, body: str) -> dict:
    # first comma separates the cite key from the fields
    key, _, rest = body.partition(",")
    entry: dict[str, Any] = {"type": etype, "key": key.strip()}
    fields: dict[str, str] = {}
    pos, L = 0, len(rest)
    while pos < L:
        fm = re.match(r"\s*([\w\-]+)\s*=\s*", rest[pos:])
        if not fm:
            break
        name = fm.group(1).lower()
        pos += fm.end()
        if pos >= L:
            break
        ch = rest[pos]
        if ch == "{":
            depth, k = 1, pos + 1
            while k < L and depth:
                if rest[k] == "{":
                    depth += 1
                elif rest[k] == "}":
                    depth -= 1
                k += 1
            val = rest[pos + 1:k - 1]
            pos = k
        elif ch == '"':
            k = pos + 1
            while k < L and rest[k] != '"':
                k += 1
            val = rest[pos + 1:k]
            pos = k + 1
        else:  # bare value up to comma
            k = pos
            while k < L and rest[k] != ",":
                k += 1
            val = rest[pos:k]
            pos = k
        fields[name] = re.sub(r"\s+", " ", val).strip()
        nxt = rest.find(",", pos)
        pos = (nxt + 1) if nxt >= 0 else L

    entry["title"] = _clean_braces(fields.get("title", ""))
    entry["authors"] = _clean_braces(fields.get("author", ""))
    entry["year"] = fields.get("year", "")
    entry["doi"] = fields.get("doi", "")
    entry["url"] = fields.get("url", "")
    # arXiv: eprint (+archivePrefix), or anywhere in journal/note/url
    arxiv = ""
    if fields.get("archiveprefix", "").lower() == "arxiv" and fields.get("eprint"):
        arxiv = fields["eprint"].strip()
    elif re.fullmatch(_ARXIV_ANY, fields.get("eprint", "").strip()):
        arxiv = fields["eprint"].strip()
    else:
        blob = " ".join(fields.get(k, "") for k in ("journal", "note", "url", "howpublished"))
        ids = extract_arxiv_ids(blob)
        if ids:
            arxiv = ids[0]
    entry["arxiv"] = arxiv
    return entry


def _clean_braces(s: str) -> str:
    return s.replace("{", "").replace("}", "").strip()


# ---------------------------------------------------------------------------
# PDF reference section
# ---------------------------------------------------------------------------
def references_text_from_pdf(pdf_path: str) -> str:
    """pdftotext the PDF and return the text after the last References heading."""
    out = subprocess.run(["pdftotext", "-q", str(Path(pdf_path).expanduser()), "-"],
                         capture_output=True, text=True)
    return _slice_references(out.stdout)


def _slice_references(text: str) -> str:
    matches = list(re.finditer(r"(?im)^\s*(references|bibliography)\s*$", text))
    if matches:
        return text[matches[-1].end():]
    m = re.search(r"(?is)\bReferences\b", text)
    return text[m.end():] if m else text


def parse_references_from_text(text: str) -> list[dict]:
    """Heuristically split a References section into entries with arxiv/doi/title.

    Title is best-effort (PDF reference parsing is inherently fuzzy); arXiv ids
    and DOIs are extracted reliably. Prefer .bib when you have it.
    """
    refs = _slice_references(text) if re.search(r"(?im)^\s*references\s*$", text) else text
    # split on [1] / 1. / [12] markers; fall back to blank lines
    parts = re.split(r"\n(?=\[\d+\]|\d{1,3}\.\s)", refs)
    if len(parts) < 3:
        parts = re.split(r"\n\s*\n", refs)
    entries: list[dict] = []
    for raw in parts:
        chunk = re.sub(r"\s+", " ", raw).strip()
        # strip a leading "[N]" marker and any stray leading page number
        chunk = re.sub(r"^\d{1,4}\s+", "", chunk)        # leaked page number
        chunk = re.sub(r"^\[\d+\]\s*", "", chunk)        # [12] marker
        if len(chunk) < 20:
            continue
        ids = extract_arxiv_ids(chunk)
        dois = extract_dois(chunk)
        entries.append({
            "raw": chunk[:300],
            "title": _guess_title(chunk),
            "arxiv": ids[0] if ids else "",
            "doi": dois[0] if dois else "",
        })
    return entries


def _lowercase_word_ratio(clause: str) -> float:
    """Fraction of words starting lowercase — high for prose (titles), ~0 for
    author name-lists ('Jimmy Lei Ba, Jamie Ryan Kiros')."""
    words = re.findall(r"[A-Za-z][A-Za-z'-]+", clause)
    if not words:
        return 0.0
    return sum(1 for w in words if w[0].islower()) / len(words)


def _guess_title(chunk: str) -> str:
    """Best-effort title from a reference string.

    Prefers a quoted title; otherwise picks the clause that reads like prose
    (most lowercase-initial words) rather than an author list or a venue line.
    PDF reference parsing is inherently fuzzy — prefer .bib for fidelity.
    """
    chunk = re.sub(r"^\[\d+\]\s*", "", chunk).strip()
    q = re.search(r"[\"“]([^\"”]{8,180})[\"”]", chunk)
    if q:
        return q.group(1).strip()
    clauses = [c.strip(" .") for c in re.split(r"\.\s", chunk) if len(c.strip()) > 12]
    if not clauses:
        return ""
    # drop clauses that are clearly venues/urls
    cand = [c for c in clauses if not re.search(r"(?i)\b(in proceedings|arxiv|pages?|vol\.|https?://|conference|journal)\b", c)] or clauses
    best = max(cand, key=lambda c: (_lowercase_word_ratio(c), len(c)))
    return best[:180]


# ---------------------------------------------------------------------------
# Queue bridge
# ---------------------------------------------------------------------------
def refs_to_queue(entries: list[dict], project: str = "Refs",
                  parallel: int = 4, only_arxiv: bool = False) -> dict:
    """entries → a prism queue dict. arXiv-bearing → `arxiv:`; else `zotero:`
    (title search). Entries with neither an id nor a usable title are dropped."""
    papers, dropped = [], 0
    for i, e in enumerate(entries, 1):
        title = (e.get("title") or "").strip()
        arxiv = (e.get("arxiv") or "").strip()
        if arxiv:
            papers.append({"id": f"ref{i}", "arxiv": arxiv,
                           "title": title, "category": "reference"})
        elif title and not only_arxiv:
            papers.append({"id": f"ref{i}", "zotero": title,
                           "title": title, "category": "reference"})
        else:
            dropped += 1
    return {"project": project, "parallel": parallel, "notes_strategy": "full",
            "papers": papers, "_dropped": dropped}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _emit(queue: dict) -> None:
    try:
        import yaml  # type: ignore
        q = {k: v for k, v in queue.items() if not k.startswith("_")}
        print(yaml.safe_dump(q, sort_keys=False, allow_unicode=True))
    except Exception:  # noqa: BLE001
        print(json.dumps(queue, ensure_ascii=False, indent=2))
    if queue.get("_dropped"):
        print(f"# {queue['_dropped']} reference(s) dropped (no arXiv id or title)",
              file=sys.stderr)


def _main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        return
    cmd = sys.argv[1]
    project = "Refs"
    if "--project" in sys.argv:
        project = sys.argv[sys.argv.index("--project") + 1]
    if cmd == "bib":
        _emit(refs_to_queue(parse_bib(sys.argv[2]), project))
    elif cmd == "pdf":
        _emit(refs_to_queue(parse_references_from_text(
            references_text_from_pdf(sys.argv[2])), project))
    elif cmd == "ids":
        print("\n".join(extract_arxiv_ids(sys.argv[2])))
    else:
        print(f"unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    _main()
