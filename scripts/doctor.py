#!/usr/bin/env python3
"""Check whether a terminal can run the ResearchVault ingest workflow."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys

SKILL_NAMES = [
    "research-vault-ingest-orchestrator",
    "zotero-data-fetcher",
    "zotero-fulltext-archiver",
    "zotero-analytical-writer",
    "research-vault-knowledge-maintainer",
    "research-vault-literature-retrieval",
    "zotero-collection-manager",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", default=os.environ.get("RESEARCH_VAULT_ROOT", "."))
    parser.add_argument("--codex-home", default=os.environ.get("CODEX_HOME", "~/.codex"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    data_dir = Path(os.environ.get("ZOTERO_DATA_DIR", "~/Zotero")).expanduser()
    db = Path(os.environ.get("ZOTERO_DB", data_dir / "zotero.sqlite")).expanduser()
    storage = Path(os.environ.get("ZOTERO_STORAGE", data_dir / "storage")).expanduser()
    codex_skills = Path(args.codex_home).expanduser() / "skills"

    results: list[dict] = []

    def add(name: str, ok: bool, level: str, detail: str) -> None:
        results.append({"name": name, "ok": ok, "level": level, "detail": detail})

    add("vault.exists", vault.is_dir(), "error", str(vault))
    for rel in [
        "AGENTS.md",
        "01knowledge",
        "02vault",
        "03fulltext",
        "模板/论文精读模板.md",
        "模板/精读笔记写作规范.md",
        "tools/extract_item_json.py",
        "tools/run_mineru_production.py",
        "tools/validate_ingest.py",
    ]:
        path = vault / rel
        add(f"vault.{rel}", path.exists(), "error", str(path))

    add("zotero.db", db.is_file(), "warning", str(db))
    add("zotero.storage", storage.is_dir(), "warning", str(storage))
    if db.is_file():
        try:
            conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            conn.close()
            add("zotero.schema", {"items", "itemAttachments"}.issubset(tables), "error", "items + itemAttachments")
        except sqlite3.Error as exc:
            add("zotero.schema", False, "error", str(exc))

    mineru = os.environ.get("MINERU_BIN") or shutil.which("mineru")
    if not mineru and os.environ.get("CONDA_PREFIX"):
        candidate = Path(os.environ["CONDA_PREFIX"]) / "bin" / "mineru"
        mineru = str(candidate) if candidate.exists() else None
    add("mineru.binary", bool(mineru), "warning", mineru or "set MINERU_BIN or activate its environment")

    for module in ["yaml", "pypdf"]:
        add(f"python.{module}", importlib.util.find_spec(module) is not None, "warning", module)

    for skill in SKILL_NAMES:
        p = codex_skills / skill / "SKILL.md"
        add(f"skill.{skill}", p.is_file(), "warning", str(p))

    add("git.binary", shutil.which("git") is not None, "error", shutil.which("git") or "not found")

    errors = [r for r in results if not r["ok"] and r["level"] == "error"]
    warnings = [r for r in results if not r["ok"] and r["level"] == "warning"]
    if args.json:
        print(json.dumps({"vault": str(vault), "results": results, "errors": len(errors), "warnings": len(warnings)}, ensure_ascii=False, indent=2))
    else:
        for r in results:
            mark = "PASS" if r["ok"] else ("WARN" if r["level"] == "warning" else "FAIL")
            print(f"{mark:4} {r['name']}: {r['detail']}")
        print(f"Summary: errors={len(errors)} warnings={len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
