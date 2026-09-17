#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ResearchVault 术语备注 / 引文可核验性审计公共层。

路径通过 RESEARCH_VAULT_ROOT、ZOTERO_DATA_DIR、ZOTERO_DB、ZOTERO_STORAGE
配置；PDF 根据 Analytical Note 的 zotero_key 从 Zotero SQLite 动态解析。
"""
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.expanduser(os.environ.get(
    "RESEARCH_VAULT_ROOT", os.path.join(HERE, "..", "..")
)))
VENDOR = os.path.join(ROOT, "tools", "vendor")
NOTES_GLOB = os.path.join(ROOT, "02vault", "论文库", "*", "*.md")
INDEX_DIR = os.path.join(ROOT, "02vault", "_index")
AGENTS = os.path.join(ROOT, "AGENTS.md")
LOG = os.path.join(ROOT, "01knowledge", "log.md")
VALIDATOR = os.path.join(ROOT, "tools", "validate_ingest.py")
DATA_DIR = os.path.expanduser(os.environ.get("ZOTERO_DATA_DIR", "~/Zotero"))
DB = os.path.expanduser(os.environ.get("ZOTERO_DB", os.path.join(DATA_DIR, "zotero.sqlite")))
STORAGE = os.path.expanduser(os.environ.get("ZOTERO_STORAGE", os.path.join(DATA_DIR, "storage")))

if VENDOR not in sys.path and os.path.isdir(VENDOR):
    sys.path.append(VENDOR)


def _open_zotero_db():
    """只读打开 Zotero SQLite；WAL 锁定时复制数据库与 sidecar 后读取。"""
    try:
        conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        conn.execute("SELECT 1")
        return conn, None
    except sqlite3.OperationalError:
        tmpdir = tempfile.mkdtemp(prefix="zotero-audit-ro-")
        dst = os.path.join(tmpdir, "zotero.sqlite")
        shutil.copy2(DB, dst)
        for suffix in ("-wal", "-shm"):
            if os.path.exists(DB + suffix):
                shutil.copy2(DB + suffix, dst + suffix)
        conn = sqlite3.connect(f"file:{dst}?mode=ro", uri=True)
        return conn, tmpdir


def resolve_pdf(key):
    if not os.path.isfile(DB):
        raise KeyError(f"Zotero 数据库不存在: {DB}")
    conn, tmpdir = _open_zotero_db()
    try:
        row = conn.execute("SELECT itemID FROM items WHERE key = ? COLLATE NOCASE", (key,)).fetchone()
        if not row:
            raise KeyError(f"Zotero 中没有父条目 key: {key}")
        rows = conn.execute(
            """SELECT child.key, ia.path, ia.contentType
               FROM itemAttachments ia
               JOIN items child ON child.itemID = ia.itemID
               WHERE ia.parentItemID = ?
               ORDER BY
                 CASE WHEN lower(ia.contentType) = 'application/pdf' THEN 0 ELSE 1 END,
                 CASE WHEN lower(coalesce(ia.path, '')) LIKE '%.zh-%'
                           OR lower(coalesce(ia.path, '')) LIKE '%no_watermark%'
                           OR lower(coalesce(ia.path, '')) LIKE '%.mono.%'
                           OR lower(coalesce(ia.path, '')) LIKE '%.dual.%'
                      THEN 1 ELSE 0 END,
                 ia.itemID""",
            (row[0],),
        ).fetchall()
        for attachment_key, path, content_type in rows:
            if content_type and content_type.lower() != "application/pdf" and not str(path or "").lower().endswith(".pdf"):
                continue
            if path and path.startswith("storage:"):
                candidate = os.path.join(STORAGE, attachment_key, path[len("storage:"):].lstrip("/"))
                if os.path.isfile(candidate):
                    return candidate
            elif path and os.path.isabs(path) and os.path.isfile(path):
                return path
        raise KeyError(f"条目 {key} 没有可读取的 PDF 附件")
    finally:
        conn.close()
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


class PdfMap:
    def __init__(self):
        self.cache = {}

    def __getitem__(self, key):
        if key not in self.cache:
            self.cache[key] = resolve_pdf(key)
        return self.cache[key]

    def __contains__(self, key):
        try:
            self[key]
            return True
        except (KeyError, OSError, sqlite3.Error):
            return False


PDF = PdfMap()


def _load_exceptions():
    path = os.path.expanduser(os.environ.get(
        "RESEARCH_VAULT_AUDIT_EXCEPTIONS",
        os.path.join(ROOT, "config", "audit_exceptions.json"),
    ))
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


_AUDIT_EXCEPTIONS = _load_exceptions()
UNVERIFIABLE = {
    key: set(pages)
    for key, pages in _AUDIT_EXCEPTIONS.get("unverifiable_pdf_pages", {}).items()
}

# 归一化时丢弃的字符（空白、软连字符、各种引号/破折号/反引号/省略号）
DROP = set(" \t\n\r\u00ad\u2018\u2019\u201c\u201d\"'-\u2014\u2013`\u2212\u2026")

# 「论文里没有 “X” 这个说法」——引文出现在否定语境里时不去原文比对
NEG = ("没有", "检索不到", "不存在", "未出现", "不出现", "没出现", "各 0 次", "检索 0 次", "无此", "没写",
       "未使用", "不用", "没有使用", "未报告", "未给", "不是论文用词", "非论文用词", "未采用", "没有这")

# 术语备注行 / 图例行 / 列表项 / 引文 / 页码
LEG_KEY = "本笔记中所有以"
PIN = re.compile(r"^([ \t]*)>[ \t]+\U0001F4CC[ \t]+\*\*术语｜(.+?)\*\*：(.*)$")
PIN_LOOSE = re.compile(r"^([ \t]*)>[ \t]+\U0001F4CC[ \t]*\*\*术语｜")
ITEM = re.compile(r"^([ \t]*)([-*+]|[0-9]+[.)])[ \t]+")
QUOTE = re.compile(r"\u201c(.+?)\u201d")
PAGE = re.compile(r"第\s*([\d、,，\s\u2013\u2014-]+?)\s*页")
MIN_HARD = 15          # 短于 15 个「硬字符」的片段不核验（短语太容易撞上）
MAX_PAGE = 60          # 页码合理性上界，挡掉「第 2021 页」这类误抓
NO_TEXTLAYERS = ("只余", "仅余", "无法", "无文本层")


def hard(s, nfkc=False):
    """去掉空白/引号/破折号等装饰字符，返回可比对的「硬字符」串。

    nfkc=True 时先做 NFKC 归一化：连字 ﬁ/ﬀ 与数学斜体 𝜎/𝑇 变成普通字母，
    这样「能照抄就照抄」与「按普通字母抄」两种写法都能命中 PDF 文本层。
    """
    if nfkc:
        s = unicodedata.normalize("NFKC", s)
    return "".join(c for c in s if c not in DROP)


def notes():
    """所有精读笔记，按路径排序。"""
    import glob
    return sorted(glob.glob(NOTES_GLOB))


def note_key(path):
    txt = read(path)
    m = re.search(r'zotero_key: "(\w+)"', txt)
    return m.group(1) if m else None


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


_PAGES = {}


def pages_for(key, nfkc=False):
    """返回该论文 PDF 每一页的硬字符串列表（带缓存）。"""
    ck = (key, nfkc)
    if ck not in _PAGES:
        from pypdf import PdfReader
        path = PDF[key]
        if not os.path.exists(path):
            raise SystemExit("PDF 不存在：%s（可用 ZOTERO_STORAGE 覆盖附件目录）" % path)
        _PAGES[ck] = [hard(p.extract_text() or "", nfkc) for p in PdfReader(path).pages]
    return _PAGES[ck]


def page_union(line):
    """一行里所有「第 N 页 / 第 N–M 页 / 第 a、b 页」的页码并集。"""
    pgs = set()
    for m in PAGE.finditer(line):
        nums = [int(n) for n in re.findall(r"\d+", m.group(1))]
        if not nums:
            continue
        if re.search(r"[\u2013\u2014-]", m.group(1)) and len(nums) >= 2:
            pgs |= set(range(min(nums), max(nums) + 1))
        else:
            pgs |= set(nums)
    return {p for p in pgs if p <= MAX_PAGE}


def body_lines(text):
    """跳过 YAML frontmatter 与围栏代码块后的正文行；yield (行号从 1 起, 该行)。"""
    infm = fence = False
    for i, l in enumerate(text.split("\n"), 1):
        if i == 1 and l.strip() == "---":
            infm = True
            continue
        if infm:
            if l.strip() == "---":
                infm = False
            continue
        if l.strip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        yield i, l


def quote_fragments(body, nfkc=False):
    """把一段引文按 … 拆成需要逐段核验的英文片段（忽略中文段与过短段）。"""
    return [fr for fr in re.split("\u2026", body) if len(hard(fr, nfkc)) >= MIN_HARD]


def is_negated(line, qm):
    """引文两侧是否是「论文里没有这个说法」式的否定语境。"""
    pre = line[max(0, qm.start() - 26):qm.start()]
    post = line[qm.end():qm.end() + 22]
    return any(w in pre or w in post for w in NEG)


def declared_no_textlayer(line):
    return "文本层" in line and any(w in line for w in NO_TEXTLAYERS)


def spans(pages, h, pgs):
    """跨页引用：前段止于一页页尾、后段起于下一页页首时，允许两段拼接命中。"""
    if len(pgs) < 2:
        return False
    for a in sorted(pgs):
        for b in sorted(pgs):
            if b <= a:
                continue
            for s in range(20, len(h) - 20):
                if h[:s] in pages[a - 1] and h[s:] in pages[b - 1]:
                    return True
    return False


def summary(name, ok, detail):
    """所有脚本统一的末行机器可读输出，run_all.py 依赖它。"""
    print("SUMMARY|%s|%s|%s" % (name, "PASS" if ok else "FAIL", detail))
