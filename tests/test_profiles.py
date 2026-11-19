import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streonor_mcp import profiles

class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'profiles'
        self.backups = Path(self.temp.name) / 'backups'
        self.profile = 'test-123.sdProfile'
        path = self.root / self.profile
        path.mkdir(parents=True)
        self.path = path / 'manifest.json'
        self.original = {'Name':'Test','DeviceUUID':'StreonorS6','Actions':{'0,0':{'Name':'Website','UUID':'website','Settings':{'path':'https://old.test'},'States':[{'Image':'old.png'}]}}}
        self.path.write_text(json.dumps(self.original), encoding='utf-8')
    def tearDown(self):
        self.temp.cleanup()
    def test_preview_and_apply_backup(self):
        change = profiles.prepare(self.profile, None, '0,0', 'path', 'https://new.test', self.root)
        self.assertEqual(change['old_value'], 'https://old.test')
        with patch('streonor_mcp.profiles.vendor_running', return_value=False):
            result = profiles.apply(self.profile, None, '0,0', 'path', 'https://new.test', change['sha256'], self.root, self.backups)
        self.assertEqual(json.loads(self.path.read_text())['Actions']['0,0']['Settings']['path'], 'https://new.test')
        self.assertEqual(json.loads(Path(result['backup']).read_text()), self.original)
    def test_prevents_lost_updates_and_running_app(self):
        change = profiles.prepare(self.profile, None, '0,0', 'path', 'https://new.test', self.root)
        with patch('streonor_mcp.profiles.vendor_running', return_value=True):
            with self.assertRaises(RuntimeError):
                profiles.apply(self.profile, None, '0,0', 'path', 'https://new.test', change['sha256'], self.root, self.backups)
        self.path.write_text(json.dumps(self.original) + ' ', encoding='utf-8')
        with patch('streonor_mcp.profiles.vendor_running', return_value=False):
            with self.assertRaises(ValueError):
                profiles.apply(self.profile, None, '0,0', 'path', 'https://new.test', change['sha256'], self.root, self.backups)
    def test_action_and_icon_changes(self):
        image = Path(self.temp.name) / 'test.png'
        from PIL import Image
        Image.new('RGB', (8, 8), 'red').save(image)
        with patch('streonor_mcp.profiles.vendor_running', return_value=False):
            c = profiles.prepare_action(self.profile, None, 'clone', '1,0', '0,0', root=self.root)
            profiles.apply_action(self.profile, None, 'clone', '1,0', c['sha256'], '0,0', root=self.root, backups=self.backups)
            c = profiles.prepare_action(self.profile, None, 'set_icon', '1,0', image_path=str(image), root=self.root)
            result = profiles.apply_action(self.profile, None, 'set_icon', '1,0', c['sha256'], image_path=str(image), expected_image_sha256=c['image_sha256'], root=self.root, backups=self.backups)
            self.assertTrue((self.path.parent / 'Images' / result['icon']).read_bytes().startswith(b'\x89PNG'))
            c = profiles.prepare_action(self.profile, None, 'clear_icon', '1,0', root=self.root)
            profiles.apply_action(self.profile, None, 'clear_icon', '1,0', c['sha256'], root=self.root, backups=self.backups)
            self.assertEqual(json.loads(self.path.read_text())['Actions']['1,0']['States'][0]['Image'], '')
            c = profiles.prepare_action(self.profile, None, 'remove', '1,0', root=self.root)
            profiles.apply_action(self.profile, None, 'remove', '1,0', c['sha256'], root=self.root, backups=self.backups)
            self.assertNotIn('1,0', json.loads(self.path.read_text())['Actions'])

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            profiles.profile_path('../other.sdProfile', root=self.root)
        with self.assertRaises(ValueError):
            profiles.prepare(self.profile, None, '0,0', 'path', 9, self.root)

if __name__ == '__main__':
    unittest.main()
