#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""整篇笔记的英文逐字引文回 PDF 文本层核验（检查面 = 正文，不只是备注行）。

用法：python3 tools/audit/check_all_quotes.py            # 全部 10 篇
      python3 tools/audit/check_all_quotes.py LEDD       # 只查文件名含 LEDD 的笔记
口径：
  - 跳过 YAML frontmatter、围栏代码块、表格分隔行；
  - 引文内含反引号（代码示例）或含中文（中文改写）者不比对；
  - 文本比对先做 NFKC 归一化（连字 ﬁ/ﬀ、数学斜体 𝜎 与字母等价）；
  - 「版本说明」行的 PVLDB 著录字符串会落在 quotes_without_page 里，属已知例外（不是漏页码）；
  - 页码取该行并集；跨页引用允许 … 两段在相邻两页拼接命中；
  - 行内没有任何页码的引文只列入 quotes_without_page，交人工判定。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (PIN_LOOSE, QUOTE, UNVERIFIABLE, body_lines,  # noqa: E402
                     declared_no_textlayer, hard, is_negated, notes, page_union,
                     pages_for, read, spans, summary)

MIN = 15


def main():
    filt = sys.argv[1] if len(sys.argv) > 1 else ""
    tot = bad = nopg = skipneg = 0
    nowithpage = []
    for f in notes():
        if filt and filt not in os.path.basename(f):
            continue
        txt = read(f)
        key = re.search(r'zotero_key: "(\w+)"', txt).group(1)
        pages = pages_for(key, nfkc=True)
        uv = UNVERIFIABLE.get(key, set())
        probs = []
        for i, l in body_lines(txt):
            if not ("“" in l and "”" in l):
                continue
            pgs = page_union(l)
            for q in QUOTE.finditer(l):
                body = q.group(1)
                if "`" in body or any("\u4e00" <= c <= "\u9fff" for c in body):
                    continue
                frags = [fr for fr in re.split("\u2026", body) if len(hard(fr, True)) >= MIN]
                if not frags:
                    continue
                if is_negated(l, q):
                    skipneg += 1
                    continue
                if not pgs:
                    nopg += 1
                    nowithpage.append((os.path.basename(f)[:26], i, body[:70]))
                    continue
                tot += 1
                ok = True
                for fr in frags:
                    h = hard(fr, True)
                    if {j + 1 for j, t in enumerate(pages) if h in t} & pgs:
                        continue
                    if not spans(pages, h, pgs):
                        ok = False
                        break
                if ok:
                    continue
                if declared_no_textlayer(l) or pgs <= uv:
                    continue
                bad += 1
                probs.append((i, sorted(pgs), frags[0][:60]))
        print("%-40s probs=%d" % (os.path.basename(f)[:38], len(probs)))
        for p in probs[:15]:
            print("     L%-5d pages=%s %r" % (p[0], p[1], p[2]))
    if nowithpage:
        print("quotes_without_page:")
        for x in nowithpage[:40]:
            print("   ", x)
    summary("check_all_quotes", bad == 0,
            "total_locatable=%d bad=%d quotes_without_page=%d skipped_negation=%d"
            % (tot, bad, nopg, skipneg))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
