#!/usr/bin/env python3
"""paper-prism · Zotero integration (self-contained, config-driven).

Reads a *copy* of the Zotero SQLite DB so it never locks your live library.
Paths come from prism_config (zotero_db, zotero_storage) — nothing personal is
baked in.

Library API (importable):
    list_collections()                      -> [{id, name, parent, count}]
    find_collection(name)                   -> [{id, name, path}]
    papers_in_collection(cid, recursive)    -> [{item_id, title, date}]
    search(keyword)                         -> [{item_id, title, date}]
    pdf_path(item_id)                        -> str | None
    item_info(item_id)                       -> {item_id, title, fields, collections}
    zotero_collection_to_queue(name|cid, recursive, project) -> [queue specs]
    zotero_query_to_queue(tag|keyword, project, by)          -> [queue specs]  # Mode 5

CLI:
    python3 zotero.py collections
    python3 zotero.py papers <collection_id> [--recursive]
    python3 zotero.py search <keyword>
    python3 zotero.py pdf <item_id>
    python3 zotero.py queue <collection_name> [--recursive] [--project NAME]
    python3 zotero.py query <tag_or_keyword> [--by auto|tag|title] [--project NAME]

Note: read-only by design — paper-prism never modifies your Zotero library.
"""
from __future__ import annotations

import argparse
import atexit
import contextlib
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prism_config import load_config  # noqa: E402


def _db_path() -> Path:
    return Path(load_config()["zotero_db"]).expanduser()


def _storage() -> Path:
    return Path(load_config()["zotero_storage"]).expanduser()


def _open_db() -> tuple[sqlite3.Connection, str]:
    """Open a read-only connection to a PRIVATE temp copy of the live DB.

    Returns (connection, temp_path); the caller owns the temp file's lifetime.
    The copy uses mkstemp (unique name, mode 0600) so other local users on a
    shared host can't read your Zotero library. The live DB is never opened for
    writing.
    """
    src = _db_path()
    if not src.exists():
        raise FileNotFoundError(f"Zotero DB not found: {src} (set zotero_db in config)")
    fd, tmp = tempfile.mkstemp(prefix="prism_zotero_", suffix=".sqlite")
    os.close(fd)
    try:
        shutil.copyfile(src, tmp)        # data only — keeps mkstemp's 0600 perms
        os.chmod(tmp, 0o600)             # belt-and-braces
        return sqlite3.connect(tmp), tmp
    except BaseException:                 # copyfile/chmod/connect failed: never strand a
        with contextlib.suppress(OSError):  # full 0600 copy of the user's private library
            os.unlink(tmp)
        raise


def _connect() -> sqlite3.Connection:
    """A standalone read-only connection; its temp copy is unlinked at exit.

    Each call copies the WHOLE DB, so on a hot path (one call per paper) prefer
    `_temp_conn()` or thread an existing `conn=` through the helper — that copies
    the DB once and reclaims the temp file immediately, instead of one full-DB
    copy (and a lingering atexit closure) per call.
    """
    conn, tmp = _open_db()
    atexit.register(lambda: os.path.exists(tmp) and os.unlink(tmp))
    return conn


@contextlib.contextmanager
def _temp_conn():
    """One temp-copy connection for multi-item work, removed the moment we're done.

    This is the O(1) path behind `zotero_collection_to_queue` /
    `zotero_query_to_queue`: copy the DB ONCE, thread the connection through every
    per-item helper (`pdf_path`/`item_info`/`_arxiv_from_item`), then delete the
    temp file on exit — rather than a full-DB copy per item (the old O(2N) cost)
    plus an unbounded pile of atexit closures.
    """
    conn, tmp = _open_db()
    try:
        yield conn
    finally:
        conn.close()
        with contextlib.suppress(OSError):
            os.unlink(tmp)


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------
def _child_collections(conn, cid: int) -> list[int]:
    rows = conn.execute("SELECT collectionID, parentCollectionID FROM collections").fetchall()
    children: dict = {}
    for c, parent in rows:
        children.setdefault(parent, []).append(c)
    result = [cid]

    def walk(c):
        for ch in children.get(c, []):
            result.append(ch)
            walk(ch)

    walk(cid)
    return result


def list_collections() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT c.collectionID, c.collectionName, c.parentCollectionID,
                   COUNT(ci.itemID)
            FROM collections c
            LEFT JOIN collectionItems ci ON c.collectionID = ci.collectionID
            GROUP BY c.collectionID
            ORDER BY c.parentCollectionID, c.collectionName
            """
        ).fetchall()
        return [{"id": r[0], "name": r[1], "parent": r[2], "count": r[3]} for r in rows]
    finally:
        conn.close()


def _collection_path(conn, cid: int) -> str:
    rows = {r[0]: (r[1], r[2]) for r in
            conn.execute("SELECT collectionID, collectionName, parentCollectionID FROM collections")}
    parts, cur = [], cid
    while cur and cur in rows:
        name, parent = rows[cur]
        parts.insert(0, name)
        cur = parent
    return "/".join(parts)


def find_collection(name: str, conn=None) -> list[dict]:
    c = conn or _connect()
    try:
        rows = c.execute(
            "SELECT collectionID, collectionName FROM collections WHERE collectionName LIKE ?",
            (f"%{name}%",),
        ).fetchall()
        return [{"id": r[0], "name": r[1], "path": _collection_path(c, r[0])} for r in rows]
    finally:
        if conn is None:
            c.close()


# ---------------------------------------------------------------------------
# Papers
# ---------------------------------------------------------------------------
_PAPER_SELECT = """
    SELECT DISTINCT i.itemID, idv.value AS title,
        (SELECT value FROM itemData id2
         JOIN itemDataValues idv2 ON id2.valueID = idv2.valueID
         JOIN fields f2 ON id2.fieldID = f2.fieldID
         WHERE id2.itemID = i.itemID AND f2.fieldName = 'date' LIMIT 1) AS date
    FROM items i
    JOIN collectionItems ci ON i.itemID = ci.itemID
    JOIN itemData id ON i.itemID = id.itemID
    JOIN itemDataValues idv ON id.valueID = idv.valueID
    JOIN fields f ON id.fieldID = f.fieldID
    WHERE f.fieldName = 'title' AND i.itemTypeID != 14
"""


def papers_in_collection(collection_id: int, recursive: bool = False, conn=None) -> list[dict]:
    c = conn or _connect()
    try:
        if recursive:
            ids = _child_collections(c, collection_id)
            ph = ",".join("?" * len(ids))
            rows = c.execute(
                _PAPER_SELECT + f" AND ci.collectionID IN ({ph}) ORDER BY date DESC", ids
            ).fetchall()
        else:
            rows = c.execute(
                _PAPER_SELECT + " AND ci.collectionID = ? ORDER BY date DESC",
                (collection_id,),
            ).fetchall()
        return [{"item_id": r[0], "title": r[1], "date": (r[2] or "")[:10]} for r in rows]
    finally:
        if conn is None:
            c.close()


def search(keyword: str, conn=None) -> list[dict]:
    c = conn or _connect()
    try:
        rows = c.execute(
            """
            SELECT i.itemID, idv.value,
                (SELECT value FROM itemData id2
                 JOIN itemDataValues idv2 ON id2.valueID = idv2.valueID
                 JOIN fields f2 ON id2.fieldID = f2.fieldID
                 WHERE id2.itemID = i.itemID AND f2.fieldName = 'date' LIMIT 1) AS date
            FROM items i
            JOIN itemData id ON i.itemID = id.itemID
            JOIN itemDataValues idv ON id.valueID = idv.valueID
            JOIN fields f ON id.fieldID = f.fieldID
            WHERE f.fieldName = 'title' AND i.itemTypeID != 14 AND idv.value LIKE ?
            ORDER BY date DESC LIMIT 25
            """,
            (f"%{keyword}%",),
        ).fetchall()
        return [{"item_id": r[0], "title": r[1], "date": (r[2] or "")[:10]} for r in rows]
    finally:
        if conn is None:
            c.close()


def pdf_path(item_id: int, conn=None) -> str | None:
    c = conn or _connect()
    try:
        row = c.execute(
            """
            SELECT ia.path, items.key
            FROM itemAttachments ia
            JOIN items ON ia.itemID = items.itemID
            WHERE ia.parentItemID = ? AND ia.contentType = 'application/pdf'
            """,
            (item_id,),
        ).fetchone()
        if not row:
            return None
        path, key = row
        if path and path.startswith("storage:"):
            full = _storage() / key / path.replace("storage:", "")
            # CONTAINMENT: a malformed `path` row (`..`, absolute) must never point
            # outside storage/. Resolve only to VERIFY containment, but return the
            # UNRESOLVED path so we don't rewrite the user's symlinks.
            try:
                full.resolve().relative_to(_storage().resolve())
            except ValueError:
                return None
            return str(full) if full.exists() else None
        return path
    finally:
        if conn is None:
            c.close()


def item_info(item_id: int, conn=None) -> dict:
    c = conn or _connect()
    try:
        fields = {
            r[0]: r[1]
            for r in c.execute(
                """
                SELECT f.fieldName, idv.value
                FROM itemData id
                JOIN itemDataValues idv ON id.valueID = idv.valueID
                JOIN fields f ON id.fieldID = f.fieldID
                WHERE id.itemID = ?
                """,
                (item_id,),
            )
        }
        return {"item_id": item_id, "title": fields.get("title", "Unknown"), "fields": fields}
    finally:
        if conn is None:
            c.close()


# ---------------------------------------------------------------------------
# Item key — for zotero:// linkback (read-only)
# ---------------------------------------------------------------------------
def _has_table(conn, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _norm(s: str) -> str:
    """Normalize a title for matching: strip LaTeX/braces, drop non-ASCII-alphanumerics, lowercase.

    This makes note-title ↔ Zotero-title matching robust against LaTeX, braces,
    punctuation, and casing. NOTE: it keeps only `[a-z0-9]`, so a title made
    entirely of non-ASCII characters normalizes to "" — `find_item_key` treats an
    empty target as "no match" (a safe miss, never a false hit). A name like
    `S²ENet` therefore matches another `S²ENet` only via its ASCII letters
    (`senet`), which is the intended, conservative behaviour.
    """
    s = re.sub(r"\$.*?\$|[{}\\]", "", s or "")
    return re.sub(r"[^a-z0-9]", "", s.lower())


def item_key(item_id: int, conn=None) -> str | None:
    """The 8-char Zotero item key for an itemID — used to build zotero:// links."""
    c = conn or _connect()
    try:
        row = c.execute("SELECT key FROM items WHERE itemID = ?", (item_id,)).fetchone()
        return row[0] if row else None
    finally:
        if conn is None:
            c.close()


def find_item_key(title: str, collection_id: int | None = None, conn=None) -> str | None:
    """Find a Zotero item key by NORMALIZED-title match (read-only).

    Pass a `collection_id` (recommended) to restrict the match and avoid
    whole-library ambiguity from duplicate copies; trashed items are excluded.
    Returns the 8-char key (e.g. `4MQSQNYC`) or None. paper-prism NEVER writes
    the Zotero DB — this only reads a copy of it. The returned key is stable
    (it does not change with citekey format or attachment re-organization), which
    is exactly why the linkback uses it instead of a Better-BibTeX citekey.
    """
    target = _norm(title)
    if not target:
        return None
    c = conn or _connect()
    try:
        q = (
            "SELECT i.key, i.itemID, idv.value FROM items i "
            "JOIN itemData id ON i.itemID = id.itemID "
            "JOIN itemDataValues idv ON id.valueID = idv.valueID "
            "JOIN fields f ON id.fieldID = f.fieldID "
            "WHERE f.fieldName = 'title' AND i.itemTypeID != 14"
        )
        params: list = []
        if _has_table(c, "deletedItems"):
            q += " AND i.itemID NOT IN (SELECT itemID FROM deletedItems)"
        if collection_id is not None:
            ids = _child_collections(c, collection_id)
            ph = ",".join("?" * len(ids))
            q += f" AND i.itemID IN (SELECT itemID FROM collectionItems WHERE collectionID IN ({ph}))"
            params = ids
        # Deterministic order so the PDF-preference loop below is exercised
        # predictably: the lowest itemID (often a no-PDF duplicate) comes first,
        # and the loop must still skip past it to the copy that has a PDF.
        q += " ORDER BY i.itemID"
        matches = [(k, iid) for k, iid, t in c.execute(q, params).fetchall()
                   if _norm(t) == target]
        if not matches:
            return None
        # Duplicate copies are common; prefer the one that actually has a PDF
        # attachment (most likely the copy that also carries the annotations) —
        # per SKILL.md's "prefer the copy that has a PDF attachment".
        for k, iid in matches:
            if c.execute(
                "SELECT 1 FROM itemAttachments "
                "WHERE parentItemID = ? AND contentType = 'application/pdf' LIMIT 1",
                (iid,),
            ).fetchone():
                return k
        return matches[0][0]
    finally:
        if conn is None:
            c.close()


# ---------------------------------------------------------------------------
# Queue bridge
# ---------------------------------------------------------------------------
# arXiv id inside a Zotero url/extra/DOI blob — new-style (YYMM.NNNNN[vN]) OR
# old-style (archive(.subclass)?/7digits). Anchored to an `arxiv:`/`arxiv.org`
# prefix so a random `word/1234567` path can't be mistaken for an id.
_ARXIV_IN_TEXT = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf)/|arxiv:\s*)"
    r"(\d{4}\.\d{4,5}(?:v\d+)?|[a-z][a-z\-]*(?:\.[A-Z]{2})?/\d{7})", re.I)


def _arxiv_from_item(item_id: int, conn=None) -> str | None:
    """Best-effort arXiv id from a Zotero item's url / extra / archive fields.

    Used when a collection item has no attached PDF, so the queue can still carry an
    explicit `arxiv:` source instead of an unusable `path: None`.
    """
    fields = item_info(item_id, conn=conn)["fields"]
    blob = " ".join(str(fields.get(k, "")) for k in
                    ("url", "extra", "archiveID", "archive", "archiveLocation", "DOI"))
    m = _ARXIV_IN_TEXT.search(blob)
    return m.group(1) if m else None


def _item_to_spec(item_id: int, title: str, project: str, conn) -> dict:
    """Build one queue spec for a Zotero item, reusing a single open `conn`.

    PDF attached → `path:`; else an `arxiv:` id from metadata; else just
    `zotero_item` + title (the skill resolves it via arXiv-HTML / DOI / web).
    Never emits a None `path` that the queue contract would reject.
    """
    spec = {"id": f"zotero-{item_id}", "zotero_item": item_id,
            "title": title, "project": project}
    pdf = pdf_path(item_id, conn=conn)
    if pdf:
        spec["path"] = pdf
    else:
        arx = _arxiv_from_item(item_id, conn=conn)
        if arx:
            spec["arxiv"] = arx
    return spec


def zotero_collection_to_queue(
    collection: str | int,
    recursive: bool = True,
    project: str = "",
) -> list[dict]:
    """Resolve a Zotero collection (name or id) to a paper-prism queue spec list.

    Each entry carries the PDF path (if attached) and Zotero item id so the
    binding step can link back via zotero:// . Opens ONE temp-copy DB connection
    for the whole resolution (O(1) full-DB copies), not one per item.
    """
    with _temp_conn() as conn:
        if isinstance(collection, str):
            matches = find_collection(collection, conn=conn)
            if not matches:
                raise ValueError(f"No Zotero collection matches '{collection}'")
            cid = matches[0]["id"]
        else:
            cid = collection
        return [_item_to_spec(p["item_id"], p["title"], project, conn)
                for p in papers_in_collection(cid, recursive=recursive, conn=conn)]


def _title_of(item_id: int, conn) -> str:
    row = conn.execute(
        "SELECT idv.value FROM itemData id "
        "JOIN itemDataValues idv ON id.valueID = idv.valueID "
        "JOIN fields f ON id.fieldID = f.fieldID "
        "WHERE id.itemID = ? AND f.fieldName = 'title' LIMIT 1",
        (item_id,),
    ).fetchone()
    return row[0] if row else ""


def _items_with_tag(conn, tag: str) -> list[int]:
    """itemIDs carrying a tag (case-insensitive exact name), excluding attachments.

    Tolerates Zotero schemas without the tag tables (returns [])."""
    if not (_has_table(conn, "tags") and _has_table(conn, "itemTags")):
        return []
    rows = conn.execute(
        "SELECT DISTINCT it.itemID FROM itemTags it "
        "JOIN tags t ON it.tagID = t.tagID "
        "JOIN items i ON it.itemID = i.itemID "
        "WHERE LOWER(t.name) = LOWER(?) AND i.itemTypeID != 14",
        (tag,),
    ).fetchall()
    return [r[0] for r in rows]


def zotero_query_to_queue(
    query: str,
    project: str = "",
    by: str = "auto",
) -> list[dict]:
    """Resolve a Zotero TAG (or title keyword) to a queue spec list — input Mode 5.

    - ``by="tag"``   : items carrying the tag `query` (case-insensitive exact).
    - ``by="title"`` : items whose title contains `query` (same as `search`).
    - ``by="auto"``  : tag first; if nothing carries that tag, fall back to title.

    Read-only; opens ONE temp-copy DB connection for the whole resolution. Each
    spec carries a PDF path (if attached), else an `arxiv:` id from metadata, else
    just `zotero_item` — never a None path.
    """
    with _temp_conn() as conn:
        ids_titles: list[tuple[int, str]] = []
        if by in ("tag", "auto"):
            ids_titles = [(iid, _title_of(iid, conn)) for iid in _items_with_tag(conn, query)]
        if not ids_titles and by in ("title", "auto"):
            ids_titles = [(p["item_id"], p["title"]) for p in search(query, conn=conn)]
        return [_item_to_spec(iid, title, project, conn) for iid, title in ids_titles]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="paper-prism Zotero helper (read-only)")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("collections")
    p = sub.add_parser("papers"); p.add_argument("collection_id", type=int); p.add_argument("--recursive", "-r", action="store_true")
    s = sub.add_parser("search"); s.add_argument("keyword")
    d = sub.add_parser("pdf"); d.add_argument("item_id", type=int)
    q = sub.add_parser("queue"); q.add_argument("collection"); q.add_argument("--recursive", "-r", action="store_true"); q.add_argument("--project", default="")
    qq = sub.add_parser("query"); qq.add_argument("query"); qq.add_argument("--by", choices=("auto", "tag", "title"), default="auto"); qq.add_argument("--project", default="")
    args = ap.parse_args()

    if args.cmd == "collections":
        for c in list_collections():
            print(f"{c['id']:>5}  {c['name']:<30}  items={c['count']}")
    elif args.cmd == "papers":
        for p_ in papers_in_collection(args.collection_id, args.recursive):
            print(f"{p_['item_id']:>7}  {p_['date']:<10}  {p_['title'][:60]}")
    elif args.cmd == "search":
        for p_ in search(args.keyword):
            print(f"{p_['item_id']:>7}  {p_['date']:<10}  {p_['title'][:60]}")
    elif args.cmd == "pdf":
        print(pdf_path(args.item_id) or "(no PDF attachment)")
    elif args.cmd == "queue":
        print(json.dumps(
            zotero_collection_to_queue(args.collection, args.recursive, args.project),
            ensure_ascii=False, indent=2))
    elif args.cmd == "query":
        print(json.dumps(
            zotero_query_to_queue(args.query, args.project, args.by),
            ensure_ascii=False, indent=2))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
