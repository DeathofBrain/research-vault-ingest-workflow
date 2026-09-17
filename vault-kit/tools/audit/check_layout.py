#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""术语备注排版审计（图例位置 / 前后空行 / 缩进容器链 / 堆叠上限）。

用法：python3 tools/audit/check_layout.py [笔记路径 ...]      # 默认全部 10 篇
判定模型：备注的缩进必须等于其所属列表容器链上任一层的「内容列」（顶层 0 恒合法）。
`1. `=3、`- `=2、`   - `=5、`   1)`=6。少一个空格就会把备注踢出容器或拆断子列表编号。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ITEM, LEG_KEY, PIN, notes, read, summary  # noqa: E402
import yaml  # noqa: E402


def audit(path):
    name = os.path.basename(path)[:50]
    raw = read(path)
    lines = raw.split("\n")
    probs = []
    fm = {}
    if raw.startswith("---\n"):
        try:
            fm = yaml.safe_load(raw.split("\n---\n", 1)[0][4:]) or {}
        except yaml.YAMLError:
            return ["frontmatter_invalid"]
    if not isinstance(fm, dict):
        return ["frontmatter_invalid"]
    version = str(fm.get("template_version", 1))
    if version not in {"1", "2"}:
        return ["unsupported_template_version:" + version]
    pins = {i: m for i, l in enumerate(lines) for m in [PIN.match(l)] if m}
    n = len(pins)
    lg = [i for i, l in enumerate(lines) if LEG_KEY in l]
    if version == "2" and not n and not lg:
        print("%-52s legend=none pins=  0 OK" % name)
        return []
    if len(lg) != 1:
        print("%-52s legend_count=%d" % (name, len(lg)))
        return ["legend_count"]
    li = lg[0]
    if n and min(pins) < li:
        probs.append("legend_after_first_pin(legend=%d first_pin=%d)" % (li + 1, min(pins) + 1))
    if li == 0 or not lines[li - 1].startswith(">"):
        probs.append("legend_not_glued(line=%d prev=%r)" % (li + 1, lines[li - 1][:24]))
    if not lines[li].startswith("> \U0001F4CC 本笔记中所有以"):
        probs.append("legend_indented(line=%d)" % (li + 1))
    if version == "1" and not (20 <= n <= 40):
        probs.append("pin_count=%d" % n)
    chain = []                      # 活动列表项的内容列栈
    for i, line in enumerate(lines):
        m = ITEM.match(line)
        if m and i not in pins:
            ind, mark = len(m.group(1)), m.group(2)
            col = ind + len(mark) + 1
            while chain and chain[-1][0] > ind:
                chain.pop()
            if chain and chain[-1][0] == ind:
                chain[-1] = (ind, col)
            elif not chain or col > chain[-1][1]:
                chain.append((ind, col))
            else:
                chain[-1] = (ind, col)
            continue
        if i in pins:
            k = len(pins[i].group(1))
            allowed = {0} | {c for _, c in chain}
            if "\t" in pins[i].group(1):
                probs.append("tab_indent:%d" % (i + 1))
            elif k not in allowed:
                probs.append("indent_not_in_container_chain:%d got=%d chain=%s(%s)"
                             % (i + 1, k, sorted(allowed), pins[i].group(2)[:12]))
            if i - 1 < 0 or (lines[i - 1].strip() != "" and LEG_KEY not in lines[i - 1]):
                probs.append("no_blank_before:%d(%s)" % (i + 1, pins[i].group(2)[:12]))
            if i + 1 >= len(lines) or lines[i + 1].strip() != "":
                probs.append("no_blank_after:%d(%s)" % (i + 1, pins[i].group(2)[:12]))
            b = pins[i].group(3)
            if "论文定义" in b:
                if "PDF 第" not in b:
                    probs.append("def_no_page:%d(%s)" % (i + 1, pins[i].group(2)[:14]))
                if chr(0x201C) not in b:
                    probs.append("def_no_quote:%d(%s)" % (i + 1, pins[i].group(2)[:14]))
            continue
    run = worst = 0
    for i in range(len(lines)):
        if i in pins:
            run += 1
            worst = max(worst, run)
        else:
            run = 0
    if worst > 6:
        probs.append("stacked_pins=%d" % worst)
    print("%-52s legend=%4d pins=%3d %s" % (name, li + 1, n, "OK" if not probs else "PROBLEMS"))
    for p in probs[:6]:
        print("      -", p)
    return probs


def main():
    files = sys.argv[1:] or notes()
    tot = sum(len(audit(f)) for f in files)
    summary("check_layout", tot == 0, "notes=%d total_problems=%d" % (len(files), tot))
    return 0 if tot == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
