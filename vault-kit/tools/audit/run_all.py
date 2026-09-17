#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一条命令跑完全套「术语备注 / 引文可核验性 / 登记一致性」审计。

用法：python3 tools/audit/run_all.py                 # 全部
      python3 tools/audit/run_all.py --skip validate_all
      python3 tools/audit/run_all.py --only check_defs count_notes
      python3 tools/audit/run_all.py --quiet         # 只打印看板（默认失败项才回吐明细）

退出码 0 = 全部 PASS；非 0 = 至少一项 FAIL（可直接用于提交前门禁）。
各脚本共享同一份 PDF 文本层缓存（在同一进程内 import，只解析一次 10 个 PDF）。
看板每行末列是该脚本自报的机器可读指标，含义见 服务与工具说明.md 第 6 节。
"""
import argparse
import contextlib
import importlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# 顺序：先便宜的结构体检，再文本层核验，再计数对账，最后跑外部校验器与补齐工具
ORDER = ["check_hygiene", "check_layout", "check_defs", "check_pins_quotes",
         "check_all_quotes", "count_notes", "reconcile_registry",
         "validate_all", "add_quote_pages"]
WHAT = {
    "check_hygiene": "体例与旧路径/临时目录残留、log 行式、索引括号",
    "check_layout": "备注排版（图例位置、空行、缩进容器链、堆叠上限）",
    "check_defs": "（论文定义）标签是否同时带逐字引文与 PDF 页码",
    "check_pins_quotes": "📌 备注行内全部英文引文回 PDF 文本层",
    "check_all_quotes": "整篇笔记正文英文引文回 PDF 文本层（含跨页拼接）",
    "count_notes": "实测 N/M/G/B（登记数字唯一来源）",
    "reconcile_registry": "笔记实测 ↔ 文献索引 ↔ AGENTS 存量表",
    "validate_all": "逐篇调用 tools/validate_ingest.py（模板+引用可追溯）",
    "add_quote_pages": "缺页码的逐字英文引文补齐（dry-run，仅报告）",
}


def run(name, extra):
    mod = importlib.import_module(name)
    saved = sys.argv
    sys.argv = [os.path.join("tools", "audit", name + ".py")] + extra
    buf = io.StringIO()
    rc = 0
    try:
        with contextlib.redirect_stdout(buf):
            rc = mod.main() or 0
    except SystemExit as e:                      # 个别脚本用 sys.exit 收尾
        rc = e.code if isinstance(e.code, int) else 0
    finally:
        sys.argv = saved
    out = buf.getvalue()
    summ = [l for l in out.split("\n") if l.startswith("SUMMARY|")]
    if not summ:
        return "NO-SUMMARY", out.strip(), rc
    _, label, status, detail = (summ[-1].split("|") + [""])[:4]
    return status, (detail or out.strip()), out


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--skip", nargs="*", default=None)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--list", action="store_true", help="列出各检查项与口径归属")
    a = ap.parse_args()
    if a.list:
        for n in ORDER:
            print("%-20s %s" % (n, WHAT[n]))
        return 0
    todo = [n for n in ORDER
            if (a.only is None or n in a.only) and not (a.skip and n in a.skip)]
    print("ResearchVault 审计看板  (%d 项)" % len(todo))
    width = max(len(x) for x in todo)
    fails = []
    for n in todo:
        status, detail, full = run(n, [])
        mark = {"PASS": "✅ PASS", "FAIL": "❌ FAIL"}.get(status, "❓ " + status)
        print("  %-*s %s  %s" % (width, n, mark, detail if len(detail) < 120 else detail[:117] + "..."))
        if status != "PASS":
            fails.append(n)
            if not a.quiet:
                print("\n".join("        " + l for l in str(full).split("\n")
                                if l and not l.startswith("SUMMARY|"))[:4000])
    print("-" * (width + 20))
    if fails:
        print("结果：%d/%d 失败 -> %s" % (len(fails), len(todo), ", ".join(fails)))
        return 1
    print("结果：全部 %d 项通过（配置的 PDF 文本层例外已在 validate_all 内标注）" % len(todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
