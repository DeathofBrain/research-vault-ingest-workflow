#!/usr/bin/env python3
"""MinerU 生产运行器（macOS 适配版）。

用法：
  run_mineru_production.py <input.pdf> <output_dir> [--key <zotero_key>] [--backend pipeline]

生产规则（与 research-vault-ingest-orchestrator 一致）：
  - 使用 ASCII 工作副本 input_<zotero_key>.pdf，并校验源文件与副本 SHA-256 一致；
  - 单篇执行，不并发；
  - 显式指定 backend（本机默认 pipeline，CPU 友好；Apple Silicon 可选 hybrid-engine）；
  - 标准输出/错误带时间戳写入 <output_dir>/logs/run_<时间戳>.log。
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata

def default_mineru_bin() -> str:
    configured = os.environ.get("MINERU_BIN")
    if configured:
        return os.path.expanduser(configured)
    discovered = shutil.which("mineru")
    if discovered:
        return discovered
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        candidate = os.path.join(conda_prefix, "bin", "mineru")
        if os.path.exists(candidate):
            return candidate
    return "mineru"


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def to_ascii(name: str) -> str:
    out = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return "".join(c if (c.isalnum() or c in "._-") else "_" for c in out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", help="输入 PDF 路径")
    parser.add_argument("output", help="输出目录（正式 Fulltext 建议 03fulltext/<collection>）")
    parser.add_argument("--key", default="unknown", help="Zotero Item Key，用于 ASCII 工作副本命名")
    parser.add_argument(
        "--backend",
        default=os.environ.get("MINERU_BACKEND", "pipeline"),
        choices=["pipeline", "hybrid-engine", "vlm-engine"],
        help="解析后端（默认 pipeline，CPU 友好）",
    )
    parser.add_argument(
        "--mineru-bin",
        default=default_mineru_bin(),
        help="MinerU 可执行文件；也可设置 MINERU_BIN（默认从 PATH/CONDA_PREFIX 查找）",
    )
    args = parser.parse_args()

    mineru_bin = os.path.expanduser(args.mineru_bin)
    if os.path.sep in mineru_bin and not os.path.exists(mineru_bin):
        sys.stderr.write(f"❌ MinerU 未安装或路径不存在: {mineru_bin}\n")
        sys.stderr.write('请安装 MinerU，或设置 MINERU_BIN/--mineru-bin。\n')
        return 2
    if os.path.sep not in mineru_bin and not shutil.which(mineru_bin):
        sys.stderr.write(f"❌ PATH 中找不到 MinerU: {mineru_bin}\n")
        sys.stderr.write('请安装 MinerU，或设置 MINERU_BIN/--mineru-bin。\n')
        return 2
    if not os.path.exists(args.pdf):
        sys.stderr.write(f"❌ 输入 PDF 不存在: {args.pdf}\n")
        return 1

    os.makedirs(args.output, exist_ok=True)
    log_dir = os.path.join(args.output, "logs")
    os.makedirs(log_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    log_path = os.path.join(log_dir, f"run_{ts}.log")
    log_fh = open(log_path, "w", encoding="utf-8")

    def log(msg: str) -> None:
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        print(line, file=log_fh, flush=True)
        print(line, flush=True)

    src_hash = sha256(args.pdf)
    workdir = tempfile.mkdtemp(prefix="mineru-prod-")
    work_pdf = os.path.join(workdir, f"input_{to_ascii(args.key)}.pdf")
    shutil.copy2(args.pdf, work_pdf)
    if sha256(work_pdf) != src_hash:
        log("❌ 工作副本 SHA-256 与源文件不一致，终止。")
        shutil.rmtree(workdir, ignore_errors=True)
        log_fh.close()
        return 1
    log(f"✅ SHA-256 校验通过: {src_hash[:16]}…")

    cmd = [mineru_bin, "-p", work_pdf, "-o", args.output, "-b", args.backend, "-m", "auto"]
    log(f"🚀 执行: {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, stdout=log_fh, stderr=log_fh, text=True)
        log(f"🔚 MinerU 退出码: {proc.returncode}")
        shutil.rmtree(workdir, ignore_errors=True)
        log_fh.close()
        return proc.returncode
    except Exception as e:  # noqa: BLE001
        log(f"❌ 执行异常: {e}")
        shutil.rmtree(workdir, ignore_errors=True)
        log_fh.close()
        return 1


if __name__ == "__main__":
    sys.exit(main())
