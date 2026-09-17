from __future__ import annotations

import os
from pathlib import Path
import py_compile
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_skills_have_valid_frontmatter(self):
        for skill in sorted((ROOT / "skills").iterdir()):
            if not skill.is_dir():
                continue
            text = (skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), skill.name)
            _, frontmatter, _ = text.split("---", 2)
            meta = yaml.safe_load(frontmatter)
            self.assertEqual(meta["name"], skill.name)
            self.assertTrue(meta["description"].strip())

    def test_no_private_absolute_paths(self):
        forbidden = ["/Users/" + "azuki", "/opt/" + "anaconda3", "azuki178747" + "@gmail.com"]
        excluded = {"task_plan.md", "findings.md", "progress.md"}
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.name in excluded or ".git" in path.parts or "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for value in forbidden:
                self.assertNotIn(value, text, f"{value} in {path}")

    def test_python_files_compile(self):
        for base in [ROOT / "scripts", ROOT / "vault-kit"]:
            for path in base.rglob("*.py"):
                py_compile.compile(str(path), doraise=True)

    def test_bootstrap_creates_portable_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/bootstrap.py"), "--vault", str(vault)],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for rel in [
                "AGENTS.md",
                "01knowledge/index.md",
                "01knowledge/log.md",
                "02vault/_index/文献索引.md",
                "03fulltext",
                "tools/extract_item_json.py",
                "tools/run_mineru_production.py",
                "tools/validate_ingest.py",
                "模板/论文精读模板.md",
                "config/audit_exceptions.json",
            ]:
                self.assertTrue((vault / rel).exists(), rel)
            second = subprocess.run(
                [sys.executable, str(ROOT / "scripts/bootstrap.py"), "--vault", str(vault)],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertIn("KEEP existing: AGENTS.md", second.stdout)

    def test_cli_help(self):
        commands = [
            [sys.executable, str(ROOT / "vault-kit/tools/extract_item_json.py"), "--help"],
            [sys.executable, str(ROOT / "vault-kit/tools/run_mineru_production.py"), "--help"],
            [sys.executable, str(ROOT / "vault-kit/tools/validate_ingest.py"), "--help"],
            [sys.executable, str(ROOT / "scripts/doctor.py"), "--help"],
        ]
        for command in commands:
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
