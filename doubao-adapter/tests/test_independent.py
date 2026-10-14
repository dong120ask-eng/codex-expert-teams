import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills' / 'expert-workgroup' / 'scripts' / 'expert_group.py'
spec = importlib.util.spec_from_file_location('independent_helper', SCRIPT)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

class IndependentTests(unittest.TestCase):
    def test_junction_parent_cannot_redirect_install_outside_home(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            home, outside = base / 'home', base / 'outside'
            home.mkdir()
            outside.mkdir()
            link = home / 'skills'
            if os.name == 'nt':
                env = dict(os.environ, EXPERT_TEST_LINK=str(link), EXPERT_TEST_TARGET=str(outside))
                created = subprocess.run(['powershell', '-NoProfile', '-Command',
                    'New-Item -ItemType Junction -Path $env:EXPERT_TEST_LINK -Target $env:EXPERT_TEST_TARGET | Out-Null'],
                    capture_output=True, env=env)
                self.assertEqual(created.returncode, 0, created.stderr)
            else:
                link.symlink_to(outside, target_is_directory=True)
            with self.assertRaises((ValueError, OSError)):
                helper.install(home, None)
            self.assertFalse((outside / 'expert-workgroup').exists())

    def test_malformed_settings_returns_structured_error(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / 'home'
            helper.install(home, None)
            skill = home / 'skills' / 'expert-workgroup'
            (skill / 'local-settings.json').write_text('[]', encoding='utf-8')
            result = subprocess.run([sys.executable, '-X', 'utf8', str(skill / 'scripts' / 'expert_group.py'), 'catalog'],
                capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn('error', json.loads(result.stderr))

    def test_cli_missing_catalog_rejects_without_success_output(self):
        result = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), 'catalog', '--catalog',
            str(ROOT / 'nonexistent-independent-catalog.json')], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertIn('error', json.loads(result.stderr))

    def test_roles_have_unique_ids_and_no_paths_as_candidates(self):
        items = helper.roles()
        self.assertEqual(len({item['id'] for item in items}), len(items))
        for item in items:
            self.assertRegex(item['id'], r'^[a-z][a-z0-9_]*$')
            for skill in item['skills']:
                self.assertRegex(skill, r'^[a-z][a-z0-9-]*$')

    def test_install_preserves_other_skill_and_agent(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            existing = home / 'skills' / 'another' / 'SKILL.md'
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b'other skill')
            agent = home / 'agents' / 'my_agent.toml'
            agent.parent.mkdir()
            agent.write_bytes(b'other agent')
            helper.install(home, None)
            self.assertEqual(existing.read_bytes(), b'other skill')
            self.assertEqual(agent.read_bytes(), b'other agent')

if __name__ == '__main__':
    unittest.main()
