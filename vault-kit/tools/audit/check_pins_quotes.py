#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""📌 备注行内全部英文引文回 PDF 文本层核验（检查面 = 备注行）。

用法：python3 tools/audit/check_pins_quotes.py
口径：
  - 页码取该行所有「第 N 页 / 第 N–M 页 / 第 a、b 页」并集；引文先按 … 分段，
    再按中日韩字符切段（`“iterator execution semantics（迭代器执行语义）”` 只核验英文部分），
    长度 < 15 个硬字符的片段不比对；
  - 比对用 NFKC 归一化文本层（连字 ﬁ/ﬀ、数学斜体等价化），并允许跨页拼接命中；
  - 否定语境（「论文里没有 “X” 这个说法」）计入 skipped_negation 不比对；
  - 已就地声明无文本层、或整行页码都落在 UNVERIFIABLE 者，跳过其未命中片段。

移植期加固（相对旧 /tmp 版）：
  1. 修掉失败分支里 `tot += 1` 的重复计数；
  2. 原来「片段里只要含中文就整段跳过」→ 会漏掉「英文 + 中文夹注」引文里的英文部分，
     现按 CJK 切段后逐段核验（这次加固查出 2 处把自造英文术语写进 “” 的行，已就地改为反引号）；
  3. 原来命中判定用未归一化文本层 → 跨页/连字场景漏判，现统一 NFKC + spans()。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (PIN_LOOSE, QUOTE, UNVERIFIABLE, declared_no_textlayer,  # noqa: E402
                     hard, is_negated, notes, page_union, pages_for, read, spans, summary)

CJK_RUN = re.compile(r"[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]")
MIN = 15


def subruns(body):
    """引文正文 → 需要核验的英文片段（按 … 与 CJK 双重切段后过滤长度）。"""
    out = []
    for fr in re.split("\u2026", body):
        for sub in CJK_RUN.split(fr):
            if len(hard(sub, True)) >= MIN:
                out.append(sub)
    return out


def main():
    tot = bad = skipped = 0
    for f in notes():
        txt = read(f)
        key = re.search(r'zotero_key: "(\w+)"', txt).group(1)
        pages = pages_for(key, nfkc=True)
        uv = UNVERIFIABLE.get(key, set())
        probs = []
        for i, l in enumerate(txt.split("\n"), 1):
            if not PIN_LOOSE.match(l):
                continue
            pgs = page_union(l)
            if not pgs:
                continue
            exempt = declared_no_textlayer(l) or pgs <= uv
            for q in QUOTE.finditer(l):
                if is_negated(l, q):
                    skipped += 1
                    continue
                frags = subruns(q.group(1))
                if not frags:
                    continue
                tot += 1
                failed = None
                for fr in frags:
                    h = hard(fr, True)
                    if {j + 1 for j, t in enumerate(pages) if h in t} & pgs:
                        continue                       # 该段命中，继续查下一段
                    if spans(pages, h, pgs):
                        continue                       # 跨页拼接命中
                    if exempt:
                        continue                       # 无文本层例外
                    failed = (fr, h)
                    break
                if failed is None:
                    continue
                bad += 1
                fr, h = failed
                low = h.lower()
                if {j + 1 for j, t in enumerate(pages) if low in t.lower()} & pgs:
                    probs.append((i, "CASEONLY", sorted(pgs), fr[:56]))
                elif any(low in t.lower() for t in pages):
                    probs.append((i, "OTHERPAGE", sorted(pgs), fr[:56]))
                else:
                    probs.append((i, "NOWHERE", sorted(pgs), fr[:56]))
        print("%-38s probs=%d" % (os.path.basename(f)[:36], len(probs)))
        for p in probs[:12]:
            print("     L%-5d %-12s pages=%s %r" % p)
    summary("check_pins_quotes", bad == 0,
            "total_checked=%d bad=%d skipped_negation=%d" % (tot, bad, skipped))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
