#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给正文里「有逐字英文引文但整行没有任何页码」的引文补 PDF 页码（默认 dry-run）。

用法：python3 tools/audit/add_quote_pages.py [--write] [文件名子串...]
      不带 --write 只报告将要插入的位置；带 --write 时先把原文件备份到
      tools/audit/_backups/<今天日期>/<原文件名>.<时间戳>.bak，再就地改写。

只在这种情况下自动写入（其余一律留给人工，宁缺毋滥）：
  - 该行没有任何 `第 N 页` 标记（已有页码的行不改动，避免与既有声明冲突）；
  - 引文不含反引号与中文（即真为论文英文原句），且按 … 分成的每一段都 >= 15 硬字符；
  - 各段命中页的交集恰好为 1 页；或恰好两段各命中唯一一页且两页相邻（跨页引用 → 写「第 a–b 页」）；
  - 「版本说明」行跳过：那里的引号是 PVLDB 著录字符串，不是论文主张。
插入形态：下一个字符是 `）` 时写「，PDF 第 N 页」，否则写「（PDF 第 N 页）」。

期望输出：auto_annotated=0（正文逐字引文的页码已在 2026-09-05 全部补齐）。
"""
import datetime
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (PAGE, QUOTE, ROOT, body_lines, hard, notes, page_union,  # noqa: E402
                     pages_for, read, summary)

MIN = 15
SKIP_TERM = re.compile(r"非论文|本笔记措辞|术语拼写")   # 行内已声明「不是原文」→ 不补页码
TAIL_PAGE = re.compile(r"[，,]?\s*（?PDF\s*第|[，,]?\s*PDF\s*第")


def main():
    args = [a for a in sys.argv[1:]]
    write = "--write" in args
    filt = [a for a in args if not a.startswith("--")]
    stamp = datetime.date.today().isoformat()
    bdir = os.path.join(ROOT, "tools", "audit", "_backups", stamp)
    manual = []
    changed_total = 0
    for f in notes():
        if filt and not any(s in os.path.basename(f) for s in filt):
            continue
        txt = read(f)
        key = re.search(r'zotero_key: "(\w+)"', txt).group(1)
        pages = pages_for(key, nfkc=True)
        lines = txt.split("\n")
        out = list(lines)
        changed = 0
        for idx, l in body_lines(txt):
            idx -= 1
            if not ("“" in l and "”" in l) or page_union(l) or "版本说明" in l:
                continue
            nl = l
            for q in reversed(list(QUOTE.finditer(l))):
                body = q.group(1)
                if "`" in body or any("\u4e00" <= c <= "\u9fff" for c in body):
                    continue
                frags = [fr for fr in re.split("\u2026", body) if len(hard(fr, True)) >= MIN]
                if not frags:
                    continue
                if SKIP_TERM.search(nl[max(0, q.start() - 40):q.start()]):
                    continue
                if TAIL_PAGE.match(nl[q.end():q.end() + 30]):
                    continue
                hits = [{j + 1 for j, t in enumerate(pages) if hard(fr, True) in t} for fr in frags]
                if any(not h for h in hits):
                    manual.append((os.path.basename(f)[:26], idx + 1, "NOWHERE", body[:46]))
                    continue
                common = set.intersection(*hits)
                if len(common) == 1:
                    ann = "PDF 第 %d 页" % common.pop()
                elif len(hits) == 2 and len({p for h in hits for p in h}) == 2 and all(len(h) == 1 for h in hits):
                    a, b = sorted(p for h in hits for p in h)
                    if b - a != 1:
                        manual.append((os.path.basename(f)[:26], idx + 1, "FARPAGES", body[:46]))
                        continue
                    ann = "PDF 第 %d–%d 页" % (a, b)
                else:
                    manual.append((os.path.basename(f)[:26], idx + 1, "AMBIG%s" % sorted(common)[:3], body[:46]))
                    continue
                nxt = nl[q.end()] if q.end() < len(nl) else ""
                ins = ("，" + ann) if nxt == "）" else ("（" + ann + "）")
                nl = nl[:q.end()] + ins + nl[q.end():]
                changed += 1
                print("   %s L%-5d %s%s" % (os.path.basename(f)[:28], idx + 1,
                                            "WRITE " if write else "DRY   ", ins))
            out[idx] = nl
        if changed:
            changed_total += changed
            if write:
                os.makedirs(bdir, exist_ok=True)
                dst = os.path.join(bdir, os.path.basename(f) + "." + datetime.datetime.now().strftime("%H%M%S") + ".bak")
                shutil.copy2(f, dst)
                with open(f, "w", encoding="utf-8") as fh:
                    fh.write("\n".join(out))
                print("%-40s +%d 页码（备份 %s）" % (os.path.basename(f)[:38], changed,
                                                os.path.relpath(dst, ROOT)))
    for m in manual:
        print("   需人工判定：%s L%-5d %-10s %s" % m)
    ok = True   # 本脚本是「补齐工具」，报告为主；AMBIG/NOWHERE 不算失败，交人工
    summary("add_quote_pages", ok,
            "auto_annotated=%d manual_left=%d mode=%s%s"
            % (changed_total, len(manual), "write" if write else "dry-run",
               " backup=%s" % os.path.relpath(bdir, ROOT) if write and changed_total else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
