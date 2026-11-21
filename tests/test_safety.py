import asyncio
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
import httpx
from PIL import Image
from streonor_mcp import profiles, server
from streonor_mcp.locking import edit_lock


class SafetyTests(unittest.TestCase):
    def test_cross_process_lock_and_reentry(self):
        with tempfile.TemporaryDirectory() as directory:
            code = 'import sys; from streonor_mcp.locking import edit_lock; from pathlib import Path;\nwith edit_lock(Path(sys.argv[1])):\n print("locked",flush=True); sys.stdin.readline()'
            child = subprocess.Popen([sys.executable, '-c', code, directory], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            try:
                self.assertEqual(child.stdout.readline().strip(), 'locked')
                with self.assertRaises(RuntimeError):
                    with edit_lock(directory):
                        pass
            finally:
                child.communicate('\n', timeout=10)
            with edit_lock(directory), edit_lock(directory):
                pass

    def test_invalid_token_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory, patch('streonor_mcp.server.DATA', Path(directory)):
            (Path(directory) / 'token.txt').write_text('')
            with self.assertRaises(RuntimeError):
                server.token()
            (Path(directory) / 'token.txt').unlink()
            value = server.token()
            self.assertGreaterEqual(len(value), 32)
            self.assertEqual(server.token(), value)

    def test_invalid_request_does_not_close_app(self):
        with tempfile.TemporaryDirectory() as directory, patch('streonor_mcp.server.profiles.ROOT', Path(directory)), patch('streonor_mcp.server.profiles.prepare', side_effect=ValueError('bad input')), patch('streonor_mcp.server.edit_with_restart') as restart:
            with self.assertRaises(ValueError):
                server.apply_setting_change('bad', '0,0', 'path', 'x', 'bad', manage_app=True)
            restart.assert_not_called()

    def test_failed_icon_write_cleans_uncommitted_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); profile = 'test.sdProfile'; folder = root / profile; folder.mkdir()
            path = folder / 'manifest.json'
            original = json.dumps({'Actions': {'0,0': {'States': [{'Image': ''}]}}})
            path.write_text(original)
            image = root / 'icon.png'; Image.new('RGB', (8, 8), 'red').save(image)
            c = profiles.prepare_action(profile, None, 'set_icon', '0,0', image_path=str(image), root=root)
            with patch('streonor_mcp.profiles.vendor_running', side_effect=[False, True]):
                with self.assertRaises(RuntimeError):
                    profiles.apply_action(profile, None, 'set_icon', '0,0', c['sha256'], image_path=str(image), expected_image_sha256=c['image_sha256'], root=root, backups=root / 'backup')
            self.assertEqual(path.read_text(), original)
            self.assertEqual(list((folder / 'Images').glob('*')), [])
            self.assertEqual(list(folder.glob('.streonor-mcp-*')), [])

    def test_size_and_json_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'large'
            path.write_bytes(b'1234')
            with self.assertRaises(ValueError):
                profiles.read_bounded(path, 3)
        with self.assertRaises(ValueError):
            profiles.parse_manifest(b'{"Actions":{},"value":NaN}')
        with self.assertRaises(ValueError):
            profiles.parse_manifest(b'[]')

    def test_boot_artwork_does_not_overwrite_source(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'source.png'
            Image.new('RGB', (8, 8), 'red').save(image)
            original = image.read_bytes()
            with self.assertRaises(FileExistsError):
                profiles.prepare_boot_logo('streonor-s6-mini', str(image), str(image))
            self.assertEqual(image.read_bytes(), original)
            self.assertEqual(list(image.parent.glob('.streonor-image-*')), [])


class HTTPTests(unittest.IsolatedAsyncioTestCase):
    async def test_authentication(self):
        from starlette.responses import PlainTextResponse
        async def app(scope, receive, send):
            await PlainTextResponse('ok')(scope, receive, send)
        transport = httpx.ASGITransport(app=server.authenticated_app(app, 'test-token'))
        async with httpx.AsyncClient(transport=transport, base_url='http://127.0.0.1') as client:
            self.assertEqual((await client.get('/mcp')).status_code, 401)
            self.assertEqual((await client.get('/mcp', headers={'Authorization': 'Bearer wrong'})).status_code, 401)
            self.assertEqual((await client.get('/mcp', headers={'Authorization': 'Bearer test-token'})).status_code, 200)
            duplicate = [('Authorization', 'Bearer test-token'), ('Authorization', 'Bearer test-token')]
            self.assertEqual((await client.get('/mcp', headers=duplicate)).status_code, 401)
