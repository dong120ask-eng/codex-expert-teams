"""Offline public distribution checks; never execute third-party references."""
import collections
import json
from pathlib import Path
import re
import tomllib
import unittest
from urllib.parse import unquote

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / 'skills'
HUB = SKILLS / 'wb-expert-hub'
LICENSED = frozenset({
    'engineering-workflow-skills', 'enterprise-legal-team', 'fbsir-beike-yi',
    'fbsir-board-secretary-assistant', 'fbsir-industry-scene-researcher',
    'fbsir-super-independent-board', 'fbsir-super-partner', 'finance',
    'law-student-coach', 'legal-builder-hub', 'legal-clinic-supervisor',
    'litigation-legal', 'long-manuscript-expert', 'mvp-dev-expert-team',
    'product-management',
})


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def public_files():
    for path in REPO.rglob('*'):
        if path.is_file() and not {'.git', '__pycache__'}.intersection(path.relative_to(REPO).parts):
            yield path


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load(HUB / 'references/catalog.json')

    def local_target(self, base, target, directory_allowed=False):
        path = (base / target).resolve()
        self.assertTrue(path.is_relative_to(REPO.resolve()), target)
        self.assertTrue(path.is_file() or (directory_allowed and path.is_dir()), target)
        return path

    def test_coverage_and_truthful_completeness(self):
        rows = self.catalog
        self.assertEqual(len(rows), 448)
        self.assertEqual(len({r['id'] for r in rows}), 448)
        self.assertEqual(sum(r['type'] == 'team' for r in rows), 54)
        self.assertEqual(len({r['category'] for r in rows}), 15)
        self.assertEqual(collections.Counter(r['status'] for r in rows),
                         {'full-role': 15, 'catalog-only': 433})
        coverage = load(REPO / 'docs/coverage.json')
        for key, number in [('catalog_entries',448), ('teams',54), ('categories',15),
                            ('open_role_definitions',15), ('catalog_only_entries',433),
                            ('permissive_source_packages',15)]:
            self.assertEqual(coverage[key], number)
        self.assertEqual(coverage['third_party_services'], 'not-connected')
        self.assertEqual(coverage['model_weights'], 'not-included')

    def test_profiles_methods_members_and_categories(self):
        profiles = set()
        for row in self.catalog:
            with self.subTest(expert=row['id']):
                profile = self.local_target(HUB, row['profile'])
                profiles.add(profile)
                self.assertEqual(row['status']=='full-role', bool(row['methodology']))
                if row['methodology']:
                    self.assertIn(row['plugin'], LICENSED)
                    self.local_target(HUB, row['methodology'])
                else:
                    self.assertIn('catalog-only', profile.read_text(encoding='utf-8'))
                for member in row['members']:
                    self.assertEqual(member['status']=='full-role', bool(member['methodology']))
                    if member['methodology']:
                        self.assertIn(row['plugin'], LICENSED)
                        self.local_target(HUB, member['methodology'])
        self.assertEqual(profiles, {p.resolve() for p in (HUB/'references/profiles').glob('*.md')})
        categories = list((HUB/'references/categories').glob('*.json'))
        self.assertEqual(len(categories),15)
        indexed = [r for path in categories for r in load(path)]
        self.assertEqual(collections.Counter(r['id'] for r in indexed),
                         collections.Counter(r['id'] for r in self.catalog))
        by_id = {r['id']:r for r in self.catalog}
        for row in indexed:
            self.assertEqual(row,by_id[row['id']])

    def test_only_licensed_agent_text_and_all_file_indexes(self):
        library = HUB/'references/library'
        self.assertEqual({p.name for p in library.iterdir() if p.is_dir()},LICENSED)
        indexed = set()
        for package in LICENSED:
            directory = library/package
            entries = load(directory/'file-index.json')
            self.assertTrue(entries,package)
            for row in entries:
                self.assertRegex(row['source'],r'^agents/[^/]+\.md$')
                indexed.add(self.local_target(directory,row['reference']))
            self.assertEqual({p.name for p in directory.iterdir()},
                             {'file-index.json'}|{r['reference'] for r in entries})
        self.assertEqual(indexed,{p.resolve() for p in library.rglob('*.reference.md')})
        audit = load(REPO/'docs/license-audit.json')
        self.assertEqual(len(audit['packages']),447)
        self.assertEqual({p['package'] for p in audit['packages']
                          if p['status']=='permissive-root-text'},LICENSED)

    def test_license_text_travels_with_installed_skills(self):
        original = REPO/'THIRD_PARTY_LICENSES'
        installed = HUB/'references/licenses'
        self.assertEqual({p.name for p in original.iterdir() if p.is_dir()},LICENSED)
        self.assertEqual({p.name for p in installed.iterdir() if p.is_dir()},LICENSED)
        notices = (REPO/'THIRD_PARTY_NOTICES.md').read_text(encoding='utf-8')
        for package in LICENSED:
            self.assertIn(package,notices)
            licenses = [p for p in (original/package).rglob('*') if p.is_file()]
            self.assertTrue(licenses,package)
            for path in licenses:
                target = installed/package/path.relative_to(original/package)
                self.assertEqual(path.read_text(encoding='utf-8'),target.read_text(encoding='utf-8'),package)
                text = path.read_text(encoding='utf-8')
                self.assertTrue('Permission is hereby granted' in text or
                                'Apache License' in text,package)

    def test_all_rendered_markdown_local_links(self):
        checked = 0
        for path in public_files():
            if path.suffix != '.md':
                continue
            text = path.read_text(encoding='utf-8')
            text = re.sub(r'(?ms)^\s*(```|~~~).*?^\s*\1[^\n]*$','',text)
            text = re.sub(r'(`+)[^`\n]*?\1','',text)
            for match in re.finditer(r'(?:!\[[^\]\n]*\]|\[[^\]\n]+\])\(([^)\n]+)\)',text):
                target = match[1].strip().split(' "')[0].strip('<>')
                if re.match(r'[A-Za-z][A-Za-z0-9+.-]*:',target) or target.startswith('#'):
                    continue
                checked += 1
                with self.subTest(file=str(path.relative_to(REPO)),target=target):
                    self.local_target(path.parent,unquote(target.split('#')[0]),directory_allowed=True)
        self.assertGreater(checked,500)

    def test_skill_frontmatter_and_role_targets(self):
        skills = list(SKILLS.glob('*/SKILL.md'))
        self.assertEqual(len(skills),16)
        for path in skills:
            text = path.read_text(encoding='utf-8')
            front = re.match(r'\A---\nname: ([a-z0-9-]+)\ndescription: ("[^\n]*")\n---\n',text)
            self.assertIsNotNone(front,str(path))
            self.assertEqual(front[1],path.parent.name)
            description = json.loads(front[2])
            self.assertTrue(0<len(description)<=1024)
        roles = list((REPO/'roles').glob('*.toml'))
        self.assertEqual(len(roles),11)
        for path in roles:
            role = tomllib.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(role['name'],path.stem)
            instructions = role['developer_instructions']
            targets = re.findall(r'\{\{SKILLS_DIR\}\}/([^\s]+/SKILL\.md)',instructions)
            self.assertTrue(targets,path.name)
            for target in targets:
                self.local_target(SKILLS,target)

    def test_no_private_account_artifacts_or_source_executables(self):
        account_names = {'auth.json','credentials.json','cookies.json','token.json',
                         'config.toml','settings.json','.env','history.jsonl'}
        executable_suffixes = {'.exe','.dll','.bat','.cmd','.ps1','.sh','.sqlite','.db','.pem','.key'}
        for path in public_files():
            rel = path.relative_to(REPO)
            with self.subTest(file=str(rel)):
                self.assertNotIn(path.name.casefold(),account_names)
                self.assertNotEqual(path.suffix,'.jsonl')
                self.assertNotIn(path.suffix.casefold(),executable_suffixes)
                self.assertNotIn('hooks',rel.parts)
                if 'references' in rel.parts:
                    self.assertNotIn(path.suffix.casefold(),{'.py','.js','.ts','.mjs'})
                text = path.read_text(encoding='utf-8')
                self.assertIsNone(re.search(r'[A-Za-z]:[\\/]+Users[\\/]|/Users/[A-Za-z0-9_-]+/|/home/[A-Za-z0-9_-]+/',text))
                self.assertIsNone(re.search(r'(?:sk-proj-|sk-live-|sk_test_|AKIA)[A-Za-z0-9_-]{16,}',text))
                self.assertIsNone(re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',text))


if __name__ == '__main__':
    unittest.main()
