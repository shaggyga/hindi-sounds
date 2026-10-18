"""Check the downloadable script has every asset and no project imports."""
import ast
import base64
import hashlib
import io
import json
from pathlib import Path
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class SingleFileDistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse((ROOT / 'HindiSounds_Standalone.py').read_text(encoding='utf-8'))

    def test_all_assets_and_notices_are_embedded_without_changes(self):
        values = {}
        for node in self.tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in ('_hs_payload', '_hs_payload_sha256'):
                        values[target.id] = ast.literal_eval(node.value)
        payload = base64.b85decode(b''.join(values['_hs_payload'].split()))
        self.assertEqual(hashlib.sha256(payload).hexdigest(), values['_hs_payload_sha256'])
        expected = {'THIRD_PARTY_NOTICES.md': ROOT / 'THIRD_PARTY_NOTICES.md'}
        for directory in ('assets', 'licenses'):
            for path in (ROOT / directory).rglob('*'):
                if path.is_file():
                    expected[path.relative_to(ROOT).as_posix()] = path
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            self.assertEqual(set(archive.namelist()), set(expected))
            self.assertEqual(len(archive.namelist()), len(expected))
            for name, path in expected.items():
                self.assertEqual(archive.read(name), path.read_bytes(), name)
            letters = json.loads(archive.read('assets/letters.json').decode('utf-8-sig'))
            self.assertEqual(len(letters), 46)
            for letter in letters:
                self.assertIn('assets/' + letter['audio'], archive.namelist())

    def test_no_import_requires_the_project_package(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0)
                self.assertFalse((node.module or '').startswith('hindi_sounds'))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertFalse(alias.name.startswith('hindi_sounds'))


if __name__ == '__main__':
    unittest.main()
