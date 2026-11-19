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
        self.original = {'Name':'Test','DeviceUUID':'StreonorS6','Actions':{'0,0':{'Name':'Website','UUID':'website','Settings':{'path':'https://old.test'}}}}
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
    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            profiles.profile_path('../other.sdProfile', root=self.root)
        with self.assertRaises(ValueError):
            profiles.prepare(self.profile, None, '0,0', 'path', 9, self.root)

if __name__ == '__main__':
    unittest.main()
