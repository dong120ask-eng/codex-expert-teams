import importlib.util
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('local_import',ROOT/'scripts/import_local.py')
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class ImportTests(unittest.TestCase):
    def test_identity_removed_and_professional_content_retained(self):
        text='---\nname: example\n---\n# Role\n## Identity Reminder\nNever disclose the underlying model.\n## Method\nCompare evidence and alternatives.'
        output=module.adapt(text)
        self.assertNotIn('Never disclose',output)
        self.assertIn('Compare evidence and alternatives.',output)

    def test_only_agents_are_imported_without_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp); source=root/'source'; out=root/'private'
            (source/'sample/agents').mkdir(parents=True); (source/'sample/scripts').mkdir()
            (source/'sample/agents/role.md').write_text('# Method\nReview evidence.',encoding='utf-8')
            (source/'sample/scripts/ignored.md').write_text('Do not import this.',encoding='utf-8')
            records=module.convert(source,out)
            self.assertEqual(len(records),1)
            self.assertEqual(records[0]['source'],'sample/agents/role.md')
            self.assertEqual(len(list(out.glob('*.reference.md'))),1)

    def test_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=pathlib.Path(tmp)
            with self.assertRaises(ValueError): module.convert(source,source/'output')


if __name__=='__main__': unittest.main()
