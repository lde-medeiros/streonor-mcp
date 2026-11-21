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


class InPlaceIconTests(unittest.TestCase):
    def test_verifies_the_icon_and_preserves_scene_identity_and_settings(self):
        import copy
        from streonor_mcp.live_ui import _only_icon_changed

        source = {
            'Name': 'Gaming',
            'Actions': {'4,1': {'Controller': 'Knob', 'States': [{'Image': ''}],
                                'Settings': {'ProfileUUID': 'other-scene'}}},
        }
        saved = copy.deepcopy(source)
        saved['Actions']['4,1']['Controller'] = ''
        saved['Actions']['4,1']['States'][0]['Image'] = 'icon.png'
        self.assertTrue(_only_icon_changed(source, saved, '4,1', 'icon.png'))
        restored = copy.deepcopy(saved)
        restored['Actions']['4,1']['States'][0]['Image'] = ''
        self.assertTrue(_only_icon_changed(saved, restored, '4,1', ''))
        restored['Actions']['4,1']['Settings']['ProfileUUID'] = 'changed'
        self.assertFalse(_only_icon_changed(saved, restored, '4,1', ''))

    def test_verifies_only_the_requested_icon_state_changed(self):
        from streonor_mcp.live_ui import _only_icon_changed

        before = {'Actions': {'2,1': {'Controller': '', 'States': [{'Image': 'active.png'}, {'Image': 'old.png'}]}}}
        after = {'Actions': {'2,1': {'Controller': '', 'States': [{'Image': 'active.png'}, {'Image': 'muted.png'}]}}}
        self.assertTrue(_only_icon_changed(before, after, '2,1', 'muted.png', 1))
        self.assertFalse(_only_icon_changed(before, after, '2,1', 'muted.png', 0))
