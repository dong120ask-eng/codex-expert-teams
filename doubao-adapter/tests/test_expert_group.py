import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "expert-workgroup" / "scripts" / "expert_group.py"
spec = importlib.util.spec_from_file_location("expert_group", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WorkgroupTests(unittest.TestCase):
    def test_route_reports_actual_file_availability(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            path = home / "skills" / "wb-backend-implementation" / "SKILL.md"
            path.parent.mkdir(parents=True)
            path.write_text("test", encoding="utf-8")
            result = module.route("实现后端接口并验证", home)
            backend = next(item for item in result["roles"] if item["id"] == "backend_engineer")
            self.assertTrue(backend["skill_availability"]["wb-backend-implementation"])
            self.assertFalse(backend["skill_availability"]["cli-creator"])
            self.assertFalse(backend["role_config_available"])
            self.assertTrue(result["suggestion_only"])

    def test_empty_demand_rejected(self):
        with self.assertRaises(ValueError):
            module.route("  ", Path("."))

    def test_catalog_search_does_not_return_source_text(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / "catalog.json"
            catalog.write_text(json.dumps({"entries":[{"id":"one","name":"办公",
                "capabilities":["表格分析"],"source_text":"not public"},
                {"id":"two","name":"其他"}]}), encoding="utf-8")
            result = module.catalog_entries(catalog, "表格")
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["entries"][0]["id"], "one")
            self.assertNotIn("source_text", result["entries"][0])

    def test_bad_catalog_no_install_side_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            catalog = Path(directory) / "bad.json"
            catalog.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                module.install(home, catalog)
            self.assertFalse(home.exists())

    def test_install_self_contained_and_preserves_existing(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            home.mkdir()
            config = home / "config.toml"
            config.write_text("untouched", encoding="utf-8")
            catalog = Path(directory) / "catalog.json"
            catalog.write_text('{"entries":[]}', encoding="utf-8")
            module.install(home, catalog)
            installed = home / "skills" / "expert-workgroup"
            self.assertEqual(config.read_text(), "untouched")
            command = subprocess.run([sys.executable, "-X", "utf8",
                str(installed / "scripts" / "expert_group.py"), "catalog"],
                capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(command.returncode, 0, command.stderr)
            self.assertEqual(json.loads(command.stdout)["count"], 0)
            before = (installed / "SKILL.md").read_bytes()
            with self.assertRaises(ValueError):
                module.install(home, catalog)
            self.assertEqual((installed / "SKILL.md").read_bytes(), before)

    def test_cli_error_is_json_and_nonzero(self):
        command = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), "catalog"],
            capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(command.returncode, 2)
        self.assertIn("error", json.loads(command.stderr))


if __name__ == "__main__":
    unittest.main()
