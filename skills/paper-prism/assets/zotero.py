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

CLI:
    python3 zotero.py collections
    python3 zotero.py papers <collection_id> [--recursive]
    python3 zotero.py search <keyword>
    python3 zotero.py pdf <item_id>
    python3 zotero.py queue <collection_name> [--recursive] [--project NAME]

Note: read-only by design — paper-prism never modifies your Zotero library.
"""
from __future__ import annotations

import argparse
import atexit
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


def _connect() -> sqlite3.Connection:
    """Connect to a temp copy of the DB to avoid locking the live library.

    The copy goes to a PRIVATE temp file (mkstemp = unique name, mode 0600) so
    other local users on a shared host can't read your Zotero library, and it is
    removed at process exit. Read-only: the live DB is never opened for writing.
    """
    src = _db_path()
    if not src.exists():
        raise FileNotFoundError(f"Zotero DB not found: {src} (set zotero_db in config)")
    fd, tmp = tempfile.mkstemp(prefix="prism_zotero_", suffix=".sqlite")
    os.close(fd)
    shutil.copyfile(src, tmp)        # data only — keeps mkstemp's 0600 perms
    os.chmod(tmp, 0o600)             # belt-and-braces
    atexit.register(lambda: os.path.exists(tmp) and os.unlink(tmp))
    return sqlite3.connect(tmp)


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


def find_collection(name: str) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT collectionID, collectionName FROM collections WHERE collectionName LIKE ?",
            (f"%{name}%",),
        ).fetchall()
        return [{"id": r[0], "name": r[1], "path": _collection_path(conn, r[0])} for r in rows]
    finally:
        conn.close()


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


def papers_in_collection(collection_id: int, recursive: bool = False) -> list[dict]:
    conn = _connect()
    try:
        if recursive:
            ids = _child_collections(conn, collection_id)
            ph = ",".join("?" * len(ids))
            rows = conn.execute(
                _PAPER_SELECT + f" AND ci.collectionID IN ({ph}) ORDER BY date DESC", ids
            ).fetchall()
        else:
            rows = conn.execute(
                _PAPER_SELECT + " AND ci.collectionID = ? ORDER BY date DESC",
                (collection_id,),
            ).fetchall()
        return [{"item_id": r[0], "title": r[1], "date": (r[2] or "")[:10]} for r in rows]
    finally:
        conn.close()


def search(keyword: str) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
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
        conn.close()


def pdf_path(item_id: int) -> str | None:
    conn = _connect()
    try:
        row = conn.execute(
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
            return str(full) if full.exists() else None
        return path
    finally:
        conn.close()


def item_info(item_id: int) -> dict:
    conn = _connect()
    try:
        fields = {
            r[0]: r[1]
            for r in conn.execute(
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
        conn.close()


# ---------------------------------------------------------------------------
# Item key — for zotero:// linkback (read-only)
# ---------------------------------------------------------------------------
def _has_table(conn, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _norm(s: str) -> str:
    """Normalize a title for matching: strip LaTeX/braces, drop non-alphanumerics, lowercase.

    This is what makes note-title ↔ Zotero-title matching robust against LaTeX
    (`S²ENet`), punctuation, and casing — the same idea the spec uses.
    """
    s = re.sub(r"\$.*?\$|[{}\\]", "", s or "")
    return re.sub(r"[^a-z0-9]", "", s.lower())


def item_key(item_id: int) -> str | None:
    """The 8-char Zotero item key for an itemID — used to build zotero:// links."""
    conn = _connect()
    try:
        row = conn.execute("SELECT key FROM items WHERE itemID = ?", (item_id,)).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def find_item_key(title: str, collection_id: int | None = None) -> str | None:
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
    conn = _connect()
    try:
        q = (
            "SELECT i.key, idv.value FROM items i "
            "JOIN itemData id ON i.itemID = id.itemID "
            "JOIN itemDataValues idv ON id.valueID = idv.valueID "
            "JOIN fields f ON id.fieldID = f.fieldID "
            "WHERE f.fieldName = 'title' AND i.itemTypeID != 14"
        )
        params: list = []
        if _has_table(conn, "deletedItems"):
            q += " AND i.itemID NOT IN (SELECT itemID FROM deletedItems)"
        if collection_id is not None:
            ids = _child_collections(conn, collection_id)
            ph = ",".join("?" * len(ids))
            q += f" AND i.itemID IN (SELECT itemID FROM collectionItems WHERE collectionID IN ({ph}))"
            params = ids
        for key, t in conn.execute(q, params).fetchall():
            if _norm(t) == target:
                return key
        return None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Queue bridge
# ---------------------------------------------------------------------------
def zotero_collection_to_queue(
    collection: str | int,
    recursive: bool = True,
    project: str = "",
) -> list[dict]:
    """Resolve a Zotero collection (name or id) to a paper-prism queue spec list.

    Each entry carries the PDF path (if attached) and Zotero item id so the
    binding step can link back via zotero:// .
    """
    if isinstance(collection, str):
        matches = find_collection(collection)
        if not matches:
            raise ValueError(f"No Zotero collection matches '{collection}'")
        cid = matches[0]["id"]
    else:
        cid = collection
    out = []
    for paper in papers_in_collection(cid, recursive=recursive):
        pdf = pdf_path(paper["item_id"])
        out.append({
            "id": f"zotero-{paper['item_id']}",
            "path": pdf,                       # may be None -> skill falls back to arxiv
            "zotero_item": paper["item_id"],
            "title": paper["title"],
            "project": project,
        })
    return out


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
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
