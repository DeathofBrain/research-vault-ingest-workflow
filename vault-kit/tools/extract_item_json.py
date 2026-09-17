#!/usr/bin/env python3
"""从 Zotero SQLite 数据库只读提取条目元数据，供 zotero-data-fetcher 使用。

用法：
  python3 extract_item_json.py --key <ZOTERO_KEY>
  python3 extract_item_json.py --title <关键词>
  python3 extract_item_json.py --collection <分类名>

可选参数：
  --db <path>        Zotero 数据库路径（默认 ~/Zotero/zotero.sqlite）
  --storage <path>   附件根目录（默认 ~/Zotero/storage）

输出：标准 JSON。绝不修改数据库，只读连接（mode=ro）。
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile

DEFAULT_DATA_DIR = os.path.expanduser(os.environ.get("ZOTERO_DATA_DIR", "~/Zotero"))
DEFAULT_DB = os.path.expanduser(os.environ.get("ZOTERO_DB", os.path.join(DEFAULT_DATA_DIR, "zotero.sqlite")))
DEFAULT_STORAGE = os.path.expanduser(os.environ.get("ZOTERO_STORAGE", os.path.join(DEFAULT_DATA_DIR, "storage")))

FIELD_SQL = """
SELECT f.fieldName, idv.value
FROM itemData id
JOIN fields f ON f.fieldID = id.fieldID
JOIN itemDataValues idv ON idv.valueID = id.valueID
WHERE id.itemID = ?
"""

CREATOR_SQL = """
SELECT ct.creatorType, c.firstName, c.lastName
FROM itemCreators ic
JOIN creators c ON c.creatorID = ic.creatorID
JOIN creatorTypes ct ON ct.creatorTypeID = ic.creatorTypeID
WHERE ic.itemID = ?
ORDER BY ic.orderIndex
"""

ATTACH_SQL = """
SELECT i.key AS attachment_key, ia.path, ia.contentType, ia.linkMode
FROM itemAttachments ia
JOIN items i ON i.itemID = ia.itemID
WHERE ia.parentItemID = ?
"""

COLLECTION_SQL = """
SELECT c.collectionName
FROM collectionItems ci
JOIN collections c ON c.collectionID = ci.collectionID
WHERE ci.itemID = ?
"""

TAG_SQL = """
SELECT t.name
FROM itemTags it
JOIN tags t ON t.tagID = it.tagID
WHERE it.itemID = ?
"""


def connect(db_path: str) -> tuple[sqlite3.Connection, str | None]:
    """优先只读直连；WAL 需要写 -shm 时复制到临时目录再读。"""
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.execute("SELECT 1")
        return conn, None
    except sqlite3.OperationalError:
        tmpdir = tempfile.mkdtemp(prefix="zotero-ro-")
        dst = os.path.join(tmpdir, "zotero.sqlite")
        shutil.copy2(db_path, dst)
        for suffix in ("-wal", "-shm"):
            src = db_path + suffix
            if os.path.exists(src):
                shutil.copy2(src, dst + suffix)
        conn = sqlite3.connect(f"file:{dst}?mode=ro", uri=True)
        conn.execute("SELECT 1")
        return conn, tmpdir


def fetch_item(conn: sqlite3.Connection, item_id: int, storage: str) -> dict:
    cur = conn.cursor()
    row = cur.execute(
        "SELECT key, dateAdded, dateModified FROM items WHERE itemID = ?", (item_id,)
    ).fetchone()
    if not row:
        return {}
    item_key, date_added, date_modified = row

    fields = {}
    for field, value in cur.execute(FIELD_SQL, (item_id,)):
        fields[field] = value

    creators = []
    for ctype, first, last in cur.execute(CREATOR_SQL, (item_id,)):
        name = " ".join(x for x in (first or "", last or "") if x).strip()
        creators.append({"type": ctype, "name": name, "firstName": first, "lastName": last})

    attachments = []
    for attach_key, path, ctype, link_mode in cur.execute(ATTACH_SQL, (item_id,)):
        filename = ""
        if path and path.startswith("storage:"):
            filename = path[len("storage:") :].lstrip("/")
        elif path and path.startswith("attachments:"):
            filename = path[len("attachments:") :].lstrip("/")
        ft_cache = os.path.join(storage, attach_key, ".zotero-ft-cache")
        pdf_path = os.path.join(storage, attach_key, filename) if filename else ""
        attachments.append(
            {
                "key": attach_key,
                "filename": filename,
                "contentType": ctype,
                "linkMode": link_mode,
                "pdf_path": pdf_path if os.path.exists(pdf_path) else None,
                "fulltext_cache": ft_cache if os.path.exists(ft_cache) else None,
            }
        )

    collections = [r[0] for r in cur.execute(COLLECTION_SQL, (item_id,))]
    tags = [r[0] for r in cur.execute(TAG_SQL, (item_id,))]
    notes_count = cur.execute(
        "SELECT COUNT(*) FROM itemNotes WHERE parentItemID = ?", (item_id,)
    ).fetchone()[0]

    year = fields.get("publicationYear") or ""
    if not year and fields.get("date"):
        m = re.search(r"\b(19|20)\d{2}\b", fields.get("date") or "")
        year = m.group(0) if m else ""

    return {
        "key": item_key,
        "title": fields.get("title") or "",
        "creators": creators,
        "year": year,
        "doi": fields.get("DOI") or "",
        "abstract": fields.get("abstractNote") or "",
        "publicationTitle": fields.get("publicationTitle") or "",
        "volume": fields.get("volume") or "",
        "issue": fields.get("issue") or "",
        "pages": fields.get("pages") or "",
        "date": fields.get("date") or "",
        "url": fields.get("url") or "",
        "collections": collections,
        "tags": tags,
        "notes_count": notes_count,
        "attachments": attachments,
        "date_added": date_added,
        "date_modified": date_modified,
    }


def resolve_item_ids(conn: sqlite3.Connection, mode: str, value: str) -> list[int]:
    cur = conn.cursor()
    excluded = tuple(
        r[0]
        for r in cur.execute(
            "SELECT itemTypeID FROM itemTypes WHERE typeName IN ('attachment','note')"
        )
    )
    if mode == "key":
        row = cur.execute(
            "SELECT itemID FROM items WHERE key = ? COLLATE NOCASE", (value,)
        ).fetchone()
        return [row[0]] if row else []
    if mode == "title":
        placeholders = ",".join("?" for _ in excluded) if excluded else "''"
        sql = f"""
        SELECT id.itemID
        FROM itemData id
        JOIN fields f ON f.fieldID = id.fieldID AND f.fieldName = 'title'
        JOIN itemDataValues idv ON idv.valueID = id.valueID
        JOIN items i ON i.itemID = id.itemID
        WHERE idv.value LIKE ?
        """
        params: list = [f"%{value}%"]
        if excluded:
            sql += f" AND i.itemTypeID NOT IN ({placeholders})"
            params += list(excluded)
        return [r[0] for r in cur.execute(sql, params)]
    if mode == "collection":
        sql = """
        SELECT ci.itemID
        FROM collectionItems ci
        JOIN collections c ON c.collectionID = ci.collectionID
        JOIN items i ON i.itemID = ci.itemID
        WHERE c.collectionName = ?
        """
        if excluded:
            sql += f" AND i.itemTypeID NOT IN ({','.join('?' for _ in excluded)})"
            return [
                r[0]
                for r in cur.execute(sql, [value, *excluded])
            ]
        return [r[0] for r in cur.execute(sql, (value,))]
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--key", help="Zotero Item Key")
    group.add_argument("--title", help="标题关键词（LIKE 搜索）")
    group.add_argument("--collection", help="Zotero 分类名")
    parser.add_argument("--db", default=os.path.expanduser(DEFAULT_DB))
    parser.add_argument("--storage", default=os.path.expanduser(DEFAULT_STORAGE))
    args = parser.parse_args()

    if not os.path.exists(args.db):
        sys.stderr.write(f"❌ 找不到 Zotero 数据库: {args.db}\n")
        sys.exit(1)

    conn, tmpdir = connect(args.db)
    try:
        if args.key:
            ids = resolve_item_ids(conn, "key", args.key)
        elif args.title:
            ids = resolve_item_ids(conn, "title", args.title)
        else:
            ids = resolve_item_ids(conn, "collection", args.collection)

        items = [fetch_item(conn, i, args.storage) for i in ids]
        items = [x for x in items if x]
    finally:
        conn.close()
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)

    if not items:
        sys.stderr.write("⚠️  未找到匹配条目。\n")
        sys.exit(1)
    print(json.dumps(items if len(items) > 1 else items[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
