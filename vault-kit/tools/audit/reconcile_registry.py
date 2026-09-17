#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三方对账：笔记实测(N,M,G,B) ↔ 02vault/_index/文献索引.md ↔ AGENTS.md 存量表。

用法：python3 tools/audit/reconcile_registry.py

登记格式（两处都必须严格匹配，否则视为「未登记」并计入 bad）：
  - 文献索引 fulltext_status 内：
    含 📌 术语备注 N 条（其中 M 条附可回原文定位的逐字英文引文与 PDF 页码，
    G 条仅给 PDF 页码定位而引文为中文释义，B 条为无页码的补充背景或本笔记判断）
  - AGENTS.md 存量表行：
    | `论文库/<collection>/` | <简称> | N | M | G | B |

数字的唯一来源是 count_notes.py（同一 measure() 函数，不走子进程、不读登记值自证）。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import AGENTS, INDEX_DIR, notes, note_key, read, summary  # noqa: E402
from count_notes import measure  # noqa: E402

# AGENTS.md 存量表用的「简称」→ zotero_key（与文献索引行顺序无关，按 key 对齐）
LABEL_KEY = {
    "Lakehouse": "WQM4P79Q",
    "Integrating Data Lake Tables（ALITE）": "BSI58UYV",
    "Semantics-Aware Dataset Discovery（Starmie）": "XXJ2SMWV",
    "QueryArtisan": "UMF6U7QM",
    "Deep Research is the New Analytics System": "96W4NDEL",
    "Supporting Our AI Overlords": "P57MDKPC",
    "A Query Engine for the Agents": "F8W3WHCZ",
    "LEDD": "KIZR24J6",
    "Text-to-SQL Empowered by LLMs（DAIL-SQL）": "NZVWAQIE",
    "Semantic Operators and Their Optimization（LOTUS）": "39H2AVZM",
    "Language Models Enable Simple Systems（Evaporate）": "Y54WGSDR",
    "DocETL": "EMDVINL5",
    "AOP": "XX4MQR7W",
    "CADENZA": "9UTW8VCM",
    "YiGraph": "4ZDDTY9M",
    "Towards Autonomous Graph Data Analytics（AAG）": "7SYLJYXN",
}

IDX_PHRASE = re.compile(
    r"含 📌 术语备注 (\d+) 条（其中 (\d+) 条附可回原文定位的逐字英文引文与 PDF 页码，"
    r"(\d+) 条仅给 PDF 页码定位而引文为中文释义，(\d+) 条为无页码的补充背景或本笔记判断）")
AG_ROW = re.compile(r"^\| `论文库/[^`]+` \| (.+?) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \|$")


def actual():
    """{zotero_key: (N, M, G, B)}——直接调用 count_notes.measure()。"""
    base_key = {os.path.basename(f): note_key(f) for f in notes()}
    out = {}
    for name, n, m, g, b, _sus, _nonm in measure(15):
        out[base_key[name]] = (n, m, g, b)
    return out


def from_index():
    path = os.path.join(INDEX_DIR, "文献索引.md")
    out = {}
    for line in read(path).split("\n"):
        if not line.startswith("| ") or line.startswith("| ---"):
            continue
        cells = line.split("|")
        if len(cells) < 6:
            continue
        key = cells[4].strip()
        hits = IDX_PHRASE.findall(line)
        if len(hits) == 1:
            out[key] = tuple(int(x) for x in hits[0])
        elif len(hits) > 1:
            out[key] = "重复登记"
    return out


def from_agents():
    out = {}
    for line in read(AGENTS).split("\n"):
        m = AG_ROW.match(line.strip())
        if m and m.group(1) in LABEL_KEY:
            out[LABEL_KEY[m.group(1)]] = tuple(int(x) for x in m.groups()[1:])
    return out


def main():
    act, idx, ag = actual(), from_index(), from_agents()
    bad = 0
    tn = tm = tg = tb = 0
    for key in sorted(act):
        a = act[key]
        i = idx.get(key, "索引缺登记")
        g = ag.get(key, "AGENTS 缺登记")
        same = (a == i == g)
        if not same:
            bad += 1
        tn += a[0]; tm += a[1]; tg += a[2]; tb += a[3]
        print("%-10s actual=%-14s index=%-14s agents=%-14s%s"
              % (key, a, i, g, "" if same else "   <<< MISMATCH"))
    for extra in set(idx) - set(act):
        print("索引里出现未知 key：%s" % extra)
        bad += 1
    for extra in set(ag) - set(act):
        print("AGENTS 表里出现未知简称（检查 LABEL_KEY）：%s" % extra)
        bad += 1
    if len(idx) != len(act) or len(ag) != len(act):
        bad += 1
        print("登记条目数与实测篇数不一致：index=%d agents=%d notes=%d" % (len(idx), len(ag), len(act)))
    print("合计 actual N=%d M=%d G=%d B=%d（恒等式 N=M+G+B：%s）"
          % (tn, tm, tg, tb, tn == tm + tg + tb))
    ok = bad == 0 and tn == tm + tg + tb
    summary("reconcile_registry", ok, "notes=%d bad=%d N=%d M=%d G=%d B=%d"
            % (len(act), bad, tn, tm, tg, tb))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
