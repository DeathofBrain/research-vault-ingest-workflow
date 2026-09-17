#!/usr/bin/env python3
"""Install the portable ResearchVault kit and Codex skills without deleting user files."""

from __future__ import annotations

import argparse
import filecmp
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime

REPO = Path(__file__).resolve().parents[1]
VAULT_KIT = REPO / "vault-kit"
SKILLS = REPO / "skills"


def same_file(src: Path, dst: Path) -> bool:
    return dst.is_file() and filecmp.cmp(src, dst, shallow=False)


def backup_path(dst: Path, backup_root: Path, relative: Path) -> None:
    out = backup_root / relative
    out.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink():
        out.write_text(f"SYMLINK -> {os.readlink(dst)}\n", encoding="utf-8")
        dst.unlink()
    elif dst.is_dir():
        shutil.copytree(dst, out)
        shutil.rmtree(dst)
    else:
        shutil.copy2(dst, out)
        dst.unlink()


def install_tree(src_root: Path, dst_root: Path, force: bool, backup_root: Path) -> tuple[int, int, int]:
    copied = skipped = unchanged = 0
    for src in sorted(p for p in src_root.rglob("*") if p.is_file()):
        rel = src.relative_to(src_root)
        dst = dst_root / rel
        if same_file(src, dst):
            unchanged += 1
            continue
        if dst.exists() or dst.is_symlink():
            if not force:
                print(f"SKIP existing: {dst}")
                skipped += 1
                continue
            backup_path(dst, backup_root, rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"COPY: {rel}")
        copied += 1
    return copied, skipped, unchanged


def install_skill(skill: Path, skill_root: Path, mode: str, force: bool, backup_root: Path) -> str:
    dst = skill_root / skill.name
    if mode == "symlink" and dst.is_symlink() and Path(os.path.realpath(dst)) == skill.resolve():
        return "unchanged"
    if mode == "copy" and dst.is_dir():
        src_files = sorted(p.relative_to(skill) for p in skill.rglob("*") if p.is_file())
        if all((dst / rel).is_file() and same_file(skill / rel, dst / rel) for rel in src_files):
            return "unchanged"
    if dst.exists() or dst.is_symlink():
        if not force:
            print(f"SKIP skill existing: {dst}")
            return "skipped"
        backup_path(dst, backup_root, Path("skills") / skill.name)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if mode == "symlink":
        dst.symlink_to(skill, target_is_directory=True)
        print(f"LINK skill: {dst} -> {skill}")
    else:
        shutil.copytree(skill, dst)
        print(f"COPY skill: {dst}")
    return "installed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, help="ResearchVault root")
    parser.add_argument("--force", action="store_true", help="backup and overwrite changed managed files")
    parser.add_argument("--install-skills", action="store_true")
    parser.add_argument("--skill-mode", choices=["copy", "symlink"], default="symlink")
    parser.add_argument("--codex-home", default=os.environ.get("CODEX_HOME", "~/.codex"))
    parser.add_argument(
        "--audit-profile",
        choices=["generic", "researchvault"],
        default="generic",
        help="install empty exceptions or the current ResearchVault text-layer exceptions",
    )
    args = parser.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    vault.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = vault / ".research-vault-workflow-backups" / timestamp

    copied, skipped, unchanged = install_tree(VAULT_KIT, vault, args.force, backup_root)

    # User-data skeleton: create only when absent; never overwrite, even with --force.
    for rel in [
        "01knowledge/.meta/claims",
        "01knowledge/.meta/gaps",
        "02vault/_index",
        "02vault/论文库",
        "03fulltext",
    ]:
        (vault / rel).mkdir(parents=True, exist_ok=True)
    skeleton_files = {
        "01knowledge/index.md": "# Research Knowledge\n",
        "01knowledge/log.md": "| 日期 | 来源论文 | Fulltext | Analytical Note | Knowledge 动作 | 更新页面 | Claims | 校验 | 备注 |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n",
        "02vault/_index/文献索引.md": "# 文献索引\n",
        "02vault/_index/研究主题索引.md": "# 研究主题索引\n",
        "02vault/_index/研究方法索引.md": "# 研究方法索引\n",
        "02vault/_index/字段补全检查.md": "# 字段补全检查\n",
    }
    for rel, content in skeleton_files.items():
        path = vault / rel
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            print(f"CREATE: {rel}")
            copied += 1

    agents = vault / "AGENTS.md"
    if not agents.exists():
        shutil.copy2(REPO / "AGENTS.example.md", agents)
        copied += 1
        print("COPY: AGENTS.md")
    else:
        print("KEEP existing: AGENTS.md")

    config_dir = vault / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    profile = REPO / "config" / (
        "audit_exceptions.researchvault.json"
        if args.audit_profile == "researchvault"
        else "audit_exceptions.example.json"
    )
    exceptions = config_dir / "audit_exceptions.json"
    if not exceptions.exists():
        shutil.copy2(profile, exceptions)
        copied += 1
        print(f"COPY: config/audit_exceptions.json ({args.audit_profile})")
    elif args.force and not same_file(profile, exceptions):
        backup_path(exceptions, backup_root, Path("config/audit_exceptions.json"))
        shutil.copy2(profile, exceptions)
        copied += 1
        print(f"UPDATE: config/audit_exceptions.json ({args.audit_profile})")
    else:
        print("KEEP existing: config/audit_exceptions.json")

    skill_counts = {"installed": 0, "skipped": 0, "unchanged": 0}
    if args.install_skills:
        skill_root = Path(args.codex_home).expanduser().resolve() / "skills"
        for skill in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
            state = install_skill(skill, skill_root, args.skill_mode, args.force, backup_root)
            skill_counts[state] += 1

    if backup_root.exists():
        print(f"Backups: {backup_root}")
    print(
        "Summary: "
        f"vault copied={copied} skipped={skipped} unchanged={unchanged}; "
        f"skills={skill_counts}"
    )
    print(f'export RESEARCH_VAULT_ROOT="{vault}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
