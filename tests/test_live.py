import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from streonor_mcp.live import _write_archive


class LiveArchiveTests(unittest.TestCase):
    def test_copies_a_folder_and_its_assets_without_writing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'original.sdProfile'
            nested = folder / 'profiles' / 'nested.sdProfile'
            (nested / 'Images').mkdir(parents=True)
            (folder / 'manifest.json').write_bytes(b'{"Actions": {}}')
            (folder / 'manifest.json.A.bak').write_bytes(b'backup')
            (nested / 'manifest.json').write_bytes(b'{"Actions": {}}')
            (nested / 'Images' / 'old.gif').write_bytes(b'old')
            path = root / 'draft.streamDockProfile'
            _write_archive(path, folder,
                           {Path('manifest.json'): b'{"Actions": {}, "Name": "Copy"}'},
                           {Path('Images/added.png'): b'new'})
            with ZipFile(path) as archive:
                self.assertEqual(set(archive.namelist()), {
                    'manifest.json', 'Images/added.png',
                    'profiles/nested.sdProfile/manifest.json',
                    'profiles/nested.sdProfile/Images/old.gif',
                })
                self.assertEqual(json.loads(archive.read('manifest.json'))['Name'], 'Copy')
                self.assertEqual(archive.read('profiles/nested.sdProfile/Images/old.gif'), b'old')
            self.assertEqual(json.loads((folder / 'manifest.json').read_bytes()), {'Actions': {}})
            self.assertFalse((folder / 'Images').exists())
