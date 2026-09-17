#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""（论文定义：“…”，PDF 第 N 页）标签核验：每个标签都必须同时具备逐字引文与页码，且引文命中所标页。

用法：python3 tools/audit/check_defs.py
口径（与 defaudit 手工审计一致）：
  - 不做 NFKC 归一化：照抄 PDF 文本层字形（含数学斜体）才算命中；
  - 引文按 … 分段，短于 15 个硬字符的片段不核验；
  - 「同页」沿用本行上一条引文的页码；无页码即 NOPAGE；
  - 仅大小写不同记 CASEONLY（例如句首字母被改写）；
  - 移植时收紧一处：原脚本的 NOPAGE 只记 problem 不计数，本脚本计入 bad。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import PIN_LOOSE, hard, notes, pages_for, read, summary  # noqa: E402

PAT = re.compile(r"（论文定义：“(.+?)”([^）]*)）")
MIN = 15


def main():
    tot = bad = 0
    for f in notes():
        txt = read(f)
        key = re.search(r'zotero_key: "(\w+)"', txt).group(1)
        pages = pages_for(key)
        probs = []
        for i, l in enumerate(txt.split("\n"), 1):
            lastpg = [None]
            if not PIN_LOOSE.match(l):
                continue
            for m in PAT.finditer(l):
                q, tail = m.group(1), m.group(2)
                tot += 1
                if "PDF 第" in tail:
                    pg = [int(x) for x in re.findall(r"\d+", tail)]
                    lastpg[0] = pg
                elif "同页" in tail and lastpg[0]:
                    pg = lastpg[0]
                else:
                    probs.append((i, "NOPAGE", q[:55]))
                    bad += 1
                    continue
                okfrag = True
                caseonly = False
                for fr in re.split("\u2026", q):
                    h = hard(fr)
                    if len(h) < MIN:
                        continue
                    if {j + 1 for j, t in enumerate(pages) if h in t} & set(pg):
                        continue
                    okfrag = False
                    lc = h.lower()
                    if {j + 1 for j, t in enumerate(pages) if lc in t.lower()} & set(pg):
                        caseonly = True
                    break
                if not okfrag:
                    bad += 1
                    probs.append((i, "CASEONLY" if caseonly else "MISS", q[:55]))
        print("%-40s %s" % (os.path.basename(f)[:38], "OK" if not probs else "PROBLEM %d" % len(probs)))
        for p in probs[:12]:
            print("     L%-5d %-9s %r" % (p[0], str(p[1]), p[2]))
    summary("check_defs", bad == 0, "total_defs=%d bad=%d" % (tot, bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
