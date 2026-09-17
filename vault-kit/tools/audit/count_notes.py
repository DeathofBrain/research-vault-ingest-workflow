#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实测每篇笔记的术语备注条数 N 及其取证构成（登记数字的唯一来源）。

用法：python3 tools/audit/count_notes.py [MIN_硬字符数]        # 默认 15
      python3 tools/audit/count_notes.py 15 --verbose          # 打印非 M 行号

口径（与 02vault/_index/文献索引.md 首段、AGENTS.md「M 的机器口径」一致）：
  - N：以 `> 📌 **术语｜` 起始的备注行数；图例行（`> 📌 本笔记中所有以…`）不计。
  - M：该行内至少有一段**非中文**、NFKC 归一化并去掉空白/引号/破折号后 >= MIN(默认 15)
        个字符、且能在该行所标页码处（含跨页拼接）的 PDF 文本层命中的 `“…”` 引文片段。
        判定前先把引文按 CJK 切段，故 `“iterator execution semantics（迭代器执行语义）”`
        这类「英文 + 中文夹注」同样可取证。
  - G：该行标了 PDF 页码，但引文全部是中文释义/自造短语（无可定位英文片段）——只算页码定位。
  - B：该行没有任何页码标记——纯补充背景或本笔记判断。
  恒等式 N = M + G + B。否定语境（「论文里没有 “X” 这个说法」）与已就地声明
  「该页无文本层、改由 MinerU 核对」的行按例外处理（前者不作证据，后者豁免命中要求）。
登记时只写 N 与 M；G/B 用于解释 N − M 的构成，避免把「中文释义 + 页码」误称为逐字英文引文。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (PIN_LOOSE, QUOTE, UNVERIFIABLE, declared_no_textlayer,  # noqa: E402
                     hard, is_negated, notes, page_union, pages_for, read, spans, summary)

CJK_RUN = re.compile(r"[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]")


def evidence(pages, line, pgs, uv, min_hard):
    """返回 (可定位英文片段数, 未能定位的英文片段数)。"""
    exempt = (pgs <= uv) or declared_no_textlayer(line)
    got = miss = 0
    for q in QUOTE.finditer(line):
        if is_negated(line, q):
            continue
        for fr in re.split("\u2026", q.group(1)):
            for sub in CJK_RUN.split(fr):
                h = hard(sub, True)
                if len(h) < min_hard:
                    continue
                hit = {j + 1 for j, t in enumerate(pages) if h in t}
                if (hit & pgs) or exempt or spans(pages, h, pgs):
                    got += 1
                else:
                    miss += 1
    return got, miss


def measure(min_hard=15):
    """返回 [(文件名, N, M, G, B, 未定位片段行数, [非 M 行号])]，按路径排序。"""
    out = []
    for f in notes():
        txt = read(f)
        key = re.search(r'zotero_key: "(\w+)"', txt).group(1)
        pages = pages_for(key, nfkc=True)
        uv = UNVERIFIABLE.get(key, set())
        m = g = b = sus = 0
        nonm = []
        for i, l in enumerate(txt.split("\n"), 1):
            if not PIN_LOOSE.match(l):
                continue
            pgs = page_union(l)
            if not pgs:
                b += 1
                nonm.append(i)
                continue
            got, miss = evidence(pages, l, pgs, uv, min_hard)
            if got:
                m += 1
            else:
                g += 1
                nonm.append(i)
            if miss and not got:
                sus += 1                      # 有英文片段但全未命中：交由 check_pins_quotes 定性
        out.append((os.path.basename(f), m + g + b, m, g, b, sus, nonm))
    return out


def main():
    min_hard = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    verbose = "--verbose" in sys.argv[2:]
    rows = measure(min_hard)
    t = [sum(r[i] for r in rows) for i in (1, 2, 3, 4, 5)]
    for name, n, m, g, b, sus, nonm in rows:
        print("%-52s N=%2d M=%2d G=%2d B=%2d%s"
              % (name[:50], n, m, g, b, "   未定位=%d" % sus if sus else ""))
        if verbose:
            print("      非 M 行号：%s" % nonm)
    print("合计 N=%d = M=%d（逐字英文可定位）+ G=%d（仅页码/中文释义）+ B=%d（无页码）"
          % tuple(t[:4]))
    ok = all(r[1] == r[2] + r[3] + r[4] for r in rows) and t[4] == 0
    summary("count_notes", ok,
            "notes=%d N=%d M=%d G=%d B=%d unlocated_english_lines=%d (min_hard=%d)"
            % (len(rows), t[0], t[1], t[2], t[3], t[4], min_hard))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
