#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""体例与残留体检（这些项在 AGENTS.md「校验」小节里被要求恒为 0）。

用法：python3 tools/audit/check_hygiene.py

覆盖：
  H1 旧目录路径残留：`论文库/DataLake/YiGraph`（YiGraph 已归位到 论文库/YiGraph/）
  H2 会话临时目录残留：字符串 `/tmp/`（仓库里不得出现一次性工作目录路径）
     —— 检查范围只限 02vault/ 与 01knowledge/；AGENTS.md 与本文档把旧路径当规则示例写出，不计。
  H3 省略号体例：`“…”` 内不得出现 ASCII `...`（表示省略一律用 U+2026 …）；
     唯一合法例外是原文自带的代码形参占位（见 ELLIPSIS_OK）。
  H4 log.md 行式：每条事件行（以 `| 20` 开头）恰好 8 个 `|`（7 列），正文不得出现裸竖线；
     且不得出现 8 位「字母+数字混合」的 Zotero key（key 属于机器字段，不进人读日志）。
  H5 文献索引单元格括号平衡：表格每个单元格里全角（ 与 ）数量必须相等，
     否则说明改写登记时漏掉了外层括号。
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import INDEX_DIR, LOG, ROOT, QUOTE, body_lines, notes, read, summary  # noqa: E402

OLD_PATHS = ("论文库/DataLake/YiGraph",)
ELLIPSIS_OK = ("llm(...)",)          # 论文原文里代码示例自带的 ASCII 省略号
# 与 tools/validate_ingest.py 的 key_like_tokens() 同口径：先掩码路径 token（全文文件名合法携带 key），
# 再找「8 位 [0-9A-Z] 且字母数字混合」的裸 key。
PATH_TOKEN = re.compile(r"(?:03fulltext|02vault|01knowledge|论文库|storage|_index)/[^\s|，。；）\]]*")
MIXED_KEY = re.compile(r"\b[0-9A-Z]{8}\b")


def raw_keys(text):
    masked = PATH_TOKEN.sub("<path>", text)
    return {t for t in MIXED_KEY.findall(masked)
            if any(c.isdigit() for c in t) and any(c.isalpha() for c in t)}
SCAN_DIRS = [os.path.join(ROOT, "02vault"), os.path.join(ROOT, "01knowledge")]


def md_files():
    for d in SCAN_DIRS:
        for p in sorted(glob.glob(os.path.join(d, "**", "*.md"), recursive=True)):
            if os.path.isfile(p):
                yield p


def main():
    problems = []
    n_old = n_tmp = n_ell = n_log = n_par = 0

    for p in md_files():
        txt = read(p)
        rel = os.path.relpath(p, ROOT)
        for pat in OLD_PATHS:
            for i, l in enumerate(txt.split("\n"), 1):
                if pat in l:
                    n_old += 1
                    problems.append((rel, i, "H1 旧路径", pat))
        for i, l in enumerate(txt.split("\n"), 1):
            if "/tmp/" in l:
                n_tmp += 1
                problems.append((rel, i, "H2 临时目录路径", l.strip()[:70]))
        if rel.endswith("文献索引.md"):
            for i, l in enumerate(txt.split("\n"), 1):
                if not l.startswith("| ") or l.startswith("| ---"):
                    continue
                for j, cell in enumerate(l.split("|")):
                    if cell.count("（") != cell.count("）"):
                        n_par += 1
                        problems.append((rel, i, "H5 第%d格括号不平衡" % j, cell.strip()[:60]))

    for f in notes():
        rel = os.path.basename(f)
        for i, l in body_lines(read(f)):
            for q in QUOTE.finditer(l):
                body = q.group(1)
                if "..." in body and not any(e in body for e in ELLIPSIS_OK):
                    n_ell += 1
                    problems.append((rel, i, "H3 ASCII 省略号", body[:60]))

    for i, l in enumerate(read(LOG).split("\n"), 1):
        if not l.startswith("| 20"):
            continue
        if l.count("|") != 8:
            n_log += 1
            problems.append(("01knowledge/log.md", i, "H4 竖线数=%d（应为 8）", l[:60]))
        ks = raw_keys(l)
        if ks:
            n_log += len(ks)
            problems.append(("01knowledge/log.md", i, "H4 出现裸 8 位混合 key", ";".join(sorted(ks))))

    for x in problems[:40]:
        print("   %-34s L%-5s %-26s %s" % x)
    if len(problems) > 40:
        print("   ...共 %d 条" % len(problems))
    bad = n_old + n_tmp + n_ell + n_log + n_par
    summary("check_hygiene", bad == 0,
            "old_paths=%d tmp_paths=%d ascii_ellipsis=%d log_rows=%d index_paren=%d (files=%d)"
            % (n_old, n_tmp, n_ell, n_log, n_par, len(list(md_files()))))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
