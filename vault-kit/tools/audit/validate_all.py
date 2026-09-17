#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对全部精读笔记批量跑 tools/validate_ingest.py（模板结构 + 引用可追溯性校验）。

用法：python3 tools/audit/validate_all.py            # 全部笔记
      python3 tools/audit/validate_all.py LEDD YiGraph   # 只跑文件名含这些子串的笔记

期望：每篇 checks = 全局固定项 + Knowledge Page 固定项 + 知识层 sidecar 条数（见 expected_checks()）；
      除 QueryArtisan 外 failures=0。
      QueryArtisan 的 1 项失败（note.quotes.verified_in_pdf）是已知例外：本机 PDF 第 2、7 页
      是矢量轮廓页、无文本层，校验器无法命中，其引文改由 MinerU 全文核对（已在笔记与
      字段补全检查中就地声明）——校验器语义不因此放宽，故保留为 FAIL 并在此标注。

坑：checks 比 expected_checks() 少 1 说明 --pdf 路径传错（引文核验被静默跳过），
    不是「少一项检查」。
"""
import os
import glob
import json
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import PDF, ROOT, VENDOR, notes, note_key, summary  # noqa: E402

# 已知例外从 <vault>/config/audit_exceptions.json 读取。
_ex_path = os.path.expanduser(os.environ.get(
    "RESEARCH_VAULT_AUDIT_EXCEPTIONS",
    os.path.join(ROOT, "config", "audit_exceptions.json"),
))
if os.path.isfile(_ex_path):
    with open(_ex_path, encoding="utf-8") as _fh:
        _ex = json.load(_fh)
else:
    _ex = {}
KNOWN_FAIL = {
    key: tuple(values)
    for key, values in _ex.get("known_validate_failures", {}).items()
}

# 与 Knowledge Page 数无关的笔记、全局 Knowledge、日志和索引检查。
GLOBAL_CHECKS = 29
# validate_ingest.py 对每个正式 Knowledge Page 执行的固定检查；claim/gap schema 另计。
PER_PAGE_CHECKS = 26
KNOWLEDGE_TYPES = {
    "knowledge-theme", "knowledge-concept", "knowledge-method",
    "knowledge-relation", "knowledge-controversy", "knowledge-synthesis",
}


def knowledge_page_count():
    """按冻结 type 识别正式 Knowledge Page；排除 .meta、index.md 和 log.md。"""
    count = 0
    pattern = re.compile(r"^type:\s*['\"]?([^'\"\s]+)", re.M)
    for path in glob.glob(os.path.join(ROOT, "01knowledge", "**", "*.md"), recursive=True):
        if os.sep + ".meta" + os.sep in path:
            continue
        raw = open(path, encoding="utf-8").read()
        if not raw.startswith("---\n") or "\n---\n" not in raw:
            continue
        match = pattern.search(raw.split("\n---\n", 1)[0])
        if match and match.group(1) in KNOWLEDGE_TYPES:
            count += 1
    return count


def expected_checks():
    """总项数随正式 Knowledge Page 和 sidecar 增量变化。

    单页时期等价于 29 + 26 + sidecar；接入 AAG 后是 29 + 26 + 17 = 72。
    当前两页、14 claim、11 gap 时是 29 + 2*26 + 25 = 106。
    这里按当前页面与 sidecar 实测——写死会让正常知识层增量变成假红，
    也不削弱原有语义：--pdf 传错时少 1 项（note.quotes.verified_in_pdf 被静默跳过），
    仍低于期望值，照样判 PROBLEM。
    """
    sidecars = len(glob.glob(os.path.join(ROOT, "01knowledge", ".meta", "claims", "*.json"))) + \
        len(glob.glob(os.path.join(ROOT, "01knowledge", ".meta", "gaps", "*.json")))
    return GLOBAL_CHECKS + PER_PAGE_CHECKS * knowledge_page_count() + sidecars


def main():
    filt = sys.argv[1:]
    env = dict(os.environ)
    env["PYTHONPATH"] = VENDOR + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    bad = 0
    for f in notes():
        name = os.path.basename(f)
        if filt and not any(s in name for s in filt):
            continue
        key = note_key(f)
        if key not in PDF:
            print("%-46s 无法从 Zotero SQLite 解析 PDF" % name[:44])
            bad += 1
            continue
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "validate_ingest.py"),
             "--note", os.path.relpath(f, ROOT), "--pdf", PDF[key]],
            capture_output=True, text=True, cwd=ROOT, env=env)
        out = r.stdout + r.stderr
        summ = re.search(r"checks=(\d+) failures=(\d+)", out)
        fails = [l.strip() for l in out.split("\n") if l.strip().startswith("FAILED")]
        n_ck = int(summ.group(1)) if summ else -1
        n_fa = int(summ.group(2)) if summ else -1
        allowed = KNOWN_FAIL.get(key, ())
        real = [x for x in fails if not any(x.startswith("FAILED: " + a) for a in allowed)]
        known = len(fails) - len(real)
        want = expected_checks()
        flag = "OK" if not real and n_ck == want else "PROBLEM"
        if flag != "OK":
            bad += 1
        print("%-46s checks=%d/%d failures=%d（已知例外 %d）%s"
              % (name[:44], n_ck, want, n_fa, known, "" if flag == "OK" else "  <<< " + flag))
        for x in real[:5]:
            print("      ", x[:160])
        if known:
            print("       已知例外：%s" % "; ".join(x[:90] for x in fails if x not in real))
    summary("validate_all", bad == 0,
            "notes_checked_problems=%d expected_checks=%d (validator=tools/validate_ingest.py)"
            % (bad, expected_checks()))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
