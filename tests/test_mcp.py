"""Exercise the real stdio protocol without reading or editing personal profiles."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_discovery_and_icon_preparation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.png'
            output = root / 'result.png'
            Image.new('RGBA', (24, 12), 'red').save(source)
            profile = 'test-123.sdProfile'
            folder = root / 'profiles' / profile
            folder.mkdir(parents=True)
            manifest = {'Name': 'Fixture', 'DeviceUUID': 'StreonorS6', 'Actions': {'0,0': {'Name': 'Website', 'UUID': 'website', 'Settings': {'path': 'https://old.test'}, 'States': [{'Image': ''}]}, '3,0': {'Name': 'Dial', 'Settings': {'step': 1}}}}
            (folder / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            icons = root / 'icons'
            icons.mkdir()
            Image.new('RGB', (8, 8), 'blue').save(icons / 'test.png')
            plugin = root / 'plugins' / 'fixture.sdPlugin'
            plugin.mkdir(parents=True)
            (plugin / 'manifest.json').write_text(json.dumps({'Name': 'Fixture', 'Actions': [{'Name': 'Website', 'UUID': 'website'}]}))
            # Process lifecycle is simulated; never close or edit the user's app.
            params = StdioServerParameters(command=sys.executable, args=['-c', 'from streonor_mcp import profiles, server; profiles.vendor_running = lambda: False; server.main()'], env={'STREONOR_DATA_DIR': str(root / 'data'), 'STREONOR_PROFILES_DIR': str(root / 'profiles'), 'STREONOR_ICONS_DIR': str(icons)})
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                    self.assertTrue(tools['read_profile'].annotations.readOnlyHint)
                    self.assertTrue(tools['apply_action_change'].annotations.destructiveHint)
                    called = set()
                    async def call(name, **args):
                        called.add(name)
                        result = await session.call_tool(name, args)
                        self.assertFalse(result.isError, result.content)
                        return [json.loads(c.text) for c in result.content if c.type == 'text']
                    self.assertTrue(await call('list_supported_devices'))
                    self.assertTrue(await call('list_available_actions'))
                    self.assertEqual((await call('list_profiles'))[0]['name'], 'Fixture')
                    self.assertTrue(await call('find_icons', query='test'))
                    self.assertEqual((await call('prepare_icon', image_path=str(source), output_path=str(output)))[0]['width'], 1254)
                    await call('prepare_boot_logo', device_id='streonor-s6-mini', image_path=str(source), output_path=str(root / 'boot.png'))
                    with Image.open(output) as image:
                        self.assertEqual(image.size, (1254, 1254))
                        self.assertEqual(image.format, 'PNG')
                    change = (await call('preview_setting_change', profile=profile, coordinate='0,0', setting='path', new_value='https://new.test'))[0]
                    await call('apply_setting_change', profile=profile, coordinate='0,0', setting='path', new_value='https://new.test', expected_sha256=change['sha256'])
                    stale = await session.call_tool('apply_setting_change', {'profile': profile, 'coordinate': '0,0', 'setting': 'path', 'new_value': 'https://bad.test', 'expected_sha256': change['sha256']})
                    self.assertTrue(stale.isError)
                    for operation, coord, extra in [('clone', '1,0', {'source_coordinate': '0,0'}), ('set_icon', '1,0', {'image_path': str(source)}), ('clear_icon', '1,0', {}), ('remove', '1,0', {})]:
                        args = dict(profile=profile, coordinate=coord, operation=operation, **extra)
                        preview = (await call('preview_action_change', **args))[0]
                        args['expected_sha256'] = preview['sha256']
                        if 'image_sha256' in preview:
                            args['expected_image_sha256'] = preview['image_sha256']
                        await call('apply_action_change', **args)
                    final = (await call('read_profile', profile=profile))[0]['profile']
                    self.assertEqual(final['Actions']['0,0']['Settings']['path'], 'https://new.test')
                    self.assertEqual(final['Actions']['3,0'], manifest['Actions']['3,0'])
                    self.assertEqual(set(tools), called, 'Every exposed MCP tool must be exercised')
