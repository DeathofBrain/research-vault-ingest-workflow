#!/usr/bin/env python3
"""MinerU 生产运行器（跨平台，兼容 MinerU 3/4）。

用法：
  run_mineru_production.py <input.pdf> <output_dir> [--key <zotero_key>] [--backend pipeline]

生产规则（与 research-vault-ingest-orchestrator 一致）：
  - 使用 ASCII 工作副本 input_<zotero_key>.pdf，并校验源文件与副本 SHA-256 一致；
  - 单篇执行，不并发；
  - MinerU 3 显式指定 backend；MinerU 4 将 backend 映射到 tier；
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
    for executable in ("mineru-kit", "mineru"):
        discovered = shutil.which(executable)
        if discovered:
            return discovered
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        candidates = [
            os.path.join(conda_prefix, "Scripts", "mineru-kit.exe"),
            os.path.join(conda_prefix, "Scripts", "mineru.exe"),
            os.path.join(conda_prefix, "bin", "mineru-kit"),
            os.path.join(conda_prefix, "bin", "mineru"),
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
    return "mineru"


def select_mineru_cli(mineru_bin: str) -> str:
    """Return the command family for a configured MinerU executable."""
    executable = os.path.basename(mineru_bin).lower()
    return "kit" if executable in {"mineru-kit", "mineru-kit.exe"} else "legacy"


def default_tier(backend: str) -> str:
    return {
        "pipeline": "basic",
        "hybrid-engine": "standard",
        "vlm-engine": "advanced",
    }[backend]


def build_mineru_command(
    mineru_bin: str,
    work_pdf: str,
    output: str,
    backend: str,
    tier: str,
) -> list[str]:
    if select_mineru_cli(mineru_bin) == "kit":
        return [
            mineru_bin,
            "parse",
            work_pdf,
            "-o",
            output,
            "-p",
            "all",
            "-f",
            "markdown",
            "--tier",
            tier,
            "--ocr-mode",
            "auto",
        ]
    return [mineru_bin, "-p", work_pdf, "-o", output, "-b", backend, "-m", "auto"]


def contains_path_separator(value: str) -> bool:
    separators = {separator for separator in (os.path.sep, os.path.altsep) if separator}
    return any(separator in value for separator in separators)


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
    parser.add_argument(
        "--tier",
        default=os.environ.get("MINERU_TIER"),
        choices=["flash", "basic", "standard", "advanced"],
        help="MinerU 4 解析档位（默认按 backend 映射；pipeline 对应 basic）",
    )
    args = parser.parse_args()

    mineru_bin = os.path.expanduser(args.mineru_bin)
    if contains_path_separator(mineru_bin) and not os.path.exists(mineru_bin):
        sys.stderr.write(f"[ERROR] MinerU 未安装或路径不存在: {mineru_bin}\n")
        sys.stderr.write('请安装 MinerU，或设置 MINERU_BIN/--mineru-bin。\n')
        return 2
    if not contains_path_separator(mineru_bin) and not shutil.which(mineru_bin):
        sys.stderr.write(f"[ERROR] PATH 中找不到 MinerU: {mineru_bin}\n")
        sys.stderr.write('请安装 MinerU，或设置 MINERU_BIN/--mineru-bin。\n')
        return 2
    if not os.path.exists(args.pdf):
        sys.stderr.write(f"[ERROR] 输入 PDF 不存在: {args.pdf}\n")
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
        log("[ERROR] 工作副本 SHA-256 与源文件不一致，终止。")
        shutil.rmtree(workdir, ignore_errors=True)
        log_fh.close()
        return 1
    log(f"[OK] SHA-256 校验通过: {src_hash[:16]}...")

    tier = args.tier or default_tier(args.backend)
    cmd = build_mineru_command(mineru_bin, work_pdf, args.output, args.backend, tier)
    log(f"[RUN] 执行: {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, stdout=log_fh, stderr=log_fh, text=True)
        log(f"[DONE] MinerU 退出码: {proc.returncode}")
        shutil.rmtree(workdir, ignore_errors=True)
        log_fh.close()
        return proc.returncode
    except Exception as e:  # noqa: BLE001
        log(f"[ERROR] 执行异常: {e}")
        shutil.rmtree(workdir, ignore_errors=True)
        log_fh.close()
        return 1


if __name__ == "__main__":
    sys.exit(main())
