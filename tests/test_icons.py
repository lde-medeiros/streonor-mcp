import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from streonor_mcp import icons, profiles


class IconTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.pack = self.root / 'icons'
        self.pack.mkdir()
        self.patch = patch('streonor_mcp.profiles.icons_dir', return_value=self.pack)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def test_installed_svg_and_contrast(self):
        (self.pack / 'github.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#181717"><rect x="4" y="4" width="16" height="16"/></svg>')
        data, info = icons.resolve('GitHub')
        self.assertEqual(info['origin'], 'installed')
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.size, (1254, 1254))
            self.assertEqual(image.getpixel((627, 627)), (255, 255, 255, 255))
            self.assertEqual(image.getpixel((0, 0)), (0, 0, 0, 255))

    def test_fallback_is_deterministic(self):
        first, info = icons.resolve('My Work App')
        second, _ = icons.resolve('My Work App')
        self.assertEqual(first, second)
        self.assertEqual(info['origin'], 'generated_label')

    def test_svg_external_resources_rejected(self):
        path = self.pack / 'unsafe.svg'
        path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="file:///private.png"/></svg>')
        with self.assertRaises(ValueError):
            profiles.read_icon(path)

    def test_svg_aspect_ratio_is_preserved(self):
        path = self.pack / 'wide.svg'
        path.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50"><rect width="100" height="50" fill="white"/></svg>')
        data = profiles.normalize_icon(profiles.read_icon(path))
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.size, (1254, 1254))
            self.assertEqual(image.getpixel((627, 0))[3], 0)
            self.assertEqual(image.getpixel((627, 627))[3], 255)

    def test_new_key_auto_icon_and_opt_out(self):
        root = self.root / 'profiles'
        folder = root / 'test.sdProfile'
        folder.mkdir(parents=True)
        manifest = folder / 'manifest.json'
        original = {'Actions': {'0,0': {'Name': 'Website', 'Settings': {'path': 'https://example.test'}, 'States': [{'Image': ''}]}}}
        manifest.write_text(json.dumps(original))
        with patch('streonor_mcp.profiles.vendor_running', return_value=False):
            preview = profiles.prepare_action('test.sdProfile', None, 'clone', '1,0', '0,0', root=root)
            self.assertEqual(preview['auto_icon']['origin'], 'generated_label')
            result = profiles.apply_action('test.sdProfile', None, 'clone', '1,0', preview['sha256'], '0,0', root=root, backups=self.root / 'backups', expected_auto_icon_sha256=preview['auto_icon']['sha256'])
            self.assertTrue((folder / 'Images' / result['icon']).exists())
            preview = profiles.prepare_action('test.sdProfile', None, 'clone', '2,0', '0,0', root=root, auto_icon=False)
            profiles.apply_action('test.sdProfile', None, 'clone', '2,0', preview['sha256'], '0,0', root=root, backups=self.root / 'backups', auto_icon=False)
        doc = json.loads(manifest.read_text())
        self.assertEqual(doc['Actions']['2,0']['States'][0]['Image'], '')
        self.assertEqual(doc['Actions']['0,0'], original['Actions']['0,0'])
