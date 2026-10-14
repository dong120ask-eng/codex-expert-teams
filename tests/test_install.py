"""Run with python -m unittest discover -s tests -v; uses temporary targets only."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("expert_installer", REPO / "scripts" / "install.py")
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        skill = self.source / "example"
        (skill / "references").mkdir(parents=True)
        (skill / "SKILL.md").write_text("new skill", encoding="utf-8")
        (skill / "references" / "method.md").write_text("method", encoding="utf-8")
        self.target = self.root / "destination"

    def make_existing(self):
        existing = self.target / "example"
        existing.mkdir(parents=True)
        (existing / "SKILL.md").write_text("private full skill", encoding="utf-8")
        (existing / "private.md").write_text("private", encoding="utf-8")
        return existing

    def test_install_copies_nested_files(self):
        report = INSTALLER.install_skills(self.source, self.target)
        self.assertEqual(report[0]["action"], "install")
        self.assertEqual((self.target / "example" / "references" / "method.md").read_text(), "method")

    def test_default_preserves_existing(self):
        existing = self.make_existing()
        report = INSTALLER.install_skills(self.source, self.target)
        self.assertEqual(report[0]["action"], "skip")
        self.assertEqual((existing / "SKILL.md").read_text(), "private full skill")
        self.assertTrue((existing / "private.md").is_file())
        self.assertEqual(list(self.target.iterdir()), [existing])

    def test_replace_retains_backup(self):
        self.make_existing()
        report = INSTALLER.install_skills(self.source, self.target, replace=True)
        backup = Path(report[0]["backup"])
        self.assertEqual(report[0]["action"], "replace")
        self.assertEqual((backup / "SKILL.md").read_text(), "private full skill")
        self.assertTrue((backup / "private.md").is_file())
        self.assertEqual((self.target / "example" / "SKILL.md").read_text(), "new skill")
        self.assertFalse((self.target / "example" / "private.md").exists())

    def test_dry_run_creates_nothing(self):
        report = INSTALLER.install_skills(self.source, self.target, dry_run=True)
        self.assertEqual(report[0]["action"], "install")
        self.assertFalse(self.target.exists())

    def test_dry_run_replace_preserves_everything(self):
        self.make_existing()
        before = sorted(str(p.relative_to(self.target)) for p in self.target.rglob("*"))
        report = INSTALLER.install_skills(self.source, self.target, replace=True, dry_run=True)
        self.assertEqual(report[0]["action"], "replace")
        self.assertEqual(before, sorted(str(p.relative_to(self.target)) for p in self.target.rglob("*")))
        self.assertEqual((self.target / "example" / "SKILL.md").read_text(), "private full skill")

    def test_defaults(self):
        with patch.dict(os.environ, {"CODEX_HOME": str(self.root / "codex")}):
            self.assertEqual(INSTALLER.default_skills_dir(), self.root / "codex" / "skills")
        with patch.dict(os.environ, dict(os.environ), clear=True):
            os.environ.pop("CODEX_HOME", None)
            self.assertEqual(INSTALLER.default_skills_dir(), Path.home() / ".codex" / "skills")

    def test_failed_copy_preserves_existing(self):
        existing = self.make_existing()
        with patch.object(INSTALLER.shutil, "copytree", side_effect=OSError("test copy failure")):
            with self.assertRaises(OSError):
                INSTALLER.install_skills(self.source, self.target, replace=True)
        self.assertEqual((existing / "SKILL.md").read_text(), "private full skill")
        self.assertEqual(list(self.target.iterdir()), [existing])

    def test_rejects_overlapping_paths(self):
        with self.assertRaises(ValueError):
            INSTALLER.install_skills(self.source, self.source / "nested")
        self.assertFalse((self.source / "nested").exists())

    def test_refuses_replacing_file(self):
        self.target.mkdir()
        (self.target / "example").write_text("keep")
        with self.assertRaises(ValueError):
            INSTALLER.install_skills(self.source, self.target, replace=True)
        self.assertEqual((self.target / "example").read_text(), "keep")

    def test_real_repository_cli(self):
        source = REPO / "skills"
        self.assertTrue(source.is_dir(), "repository skills must exist before delivery")
        expected = sorted(p.name for p in source.iterdir() if p.is_dir())
        self.assertTrue(expected)
        result = subprocess.run([sys.executable, str(REPO / "scripts" / "install.py"), "--skills-dir", str(self.target)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(p.name for p in self.target.iterdir()), expected)
        for name in expected:
            for original in (source / name).rglob("*"):
                if original.is_file():
                    copied = self.target / name / original.relative_to(source / name)
                    self.assertEqual(original.read_bytes(), copied.read_bytes())

    def role_source(self):
        roles = self.root / "roles"
        roles.mkdir()
        (roles / "researcher.toml").write_text('developer_instructions = "Read {{SKILLS_DIR}}/wb-deep-research/SKILL.md"\n', encoding="utf-8")
        return roles

    def test_roles_substitute_absolute_path(self):
        agents = self.root / "agents"
        report = INSTALLER.install_roles(self.role_source(), agents, self.target)
        self.assertEqual(report[0]["action"], "install")
        text = (agents / "researcher.toml").read_text(encoding="utf-8")
        self.assertIn(self.target.resolve().as_posix(), text)
        self.assertNotIn("{{SKILLS_DIR}}", text)

    def test_roles_preserve_and_backup(self):
        roles = self.role_source()
        agents = self.root / "agents"
        agents.mkdir()
        existing = agents / "researcher.toml"
        existing.write_text("private role", encoding="utf-8")
        report = INSTALLER.install_roles(roles, agents, self.target)
        self.assertEqual(report[0]["action"], "skip")
        self.assertEqual(existing.read_text(), "private role")
        report = INSTALLER.install_roles(roles, agents, self.target, replace=True)
        self.assertEqual(report[0]["action"], "replace")
        self.assertEqual(Path(report[0]["backup"]).read_text(), "private role")
        self.assertIn(self.target.resolve().as_posix(), existing.read_text())

    def test_roles_dry_run_never_writes(self):
        roles = self.role_source()
        agents = self.root / "agents"
        INSTALLER.install_roles(roles, agents, self.target, dry_run=True)
        self.assertFalse(agents.exists())
        agents.mkdir()
        existing = agents / "researcher.toml"
        existing.write_text("private role")
        INSTALLER.install_roles(roles, agents, self.target, replace=True, dry_run=True)
        self.assertEqual(list(agents.iterdir()), [existing])
        self.assertEqual(existing.read_text(), "private role")

    def test_agents_default(self):
        with patch.dict(os.environ, {"CODEX_HOME": str(self.root / "codex")}):
            self.assertEqual(INSTALLER.default_agents_dir(), self.root / "codex" / "agents")


if __name__ == "__main__":
    unittest.main()
