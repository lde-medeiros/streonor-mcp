"""Exercise the real stdio protocol without reading or editing personal profiles."""
import json
import sqlite3
from contextlib import closing
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
            page = 'second-page.sdProfile'
            manifest['Pages'] = {'Current': profile, 'Pages': [profile, page]}
            page_folder = folder / 'profiles' / page
            page_folder.mkdir(parents=True)
            (page_folder / 'manifest.json').write_text(json.dumps({'Actions': {}}), encoding='utf-8')
            (folder / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            (root / 'config').mkdir()
            with closing(sqlite3.connect(root / 'config' / 'DataCache.db')) as db:
                db.execute('CREATE TABLE StreonorS6 (Profile TEXT)')
                db.execute('INSERT INTO StreonorS6 VALUES (?)', (profile,))
                db.commit()
            icons = root / 'icons'
            icons.mkdir()
            Image.new('RGB', (8, 8), 'blue').save(icons / 'test.png')
            plugin = root / 'plugins' / 'fixture.sdPlugin'
            plugin.mkdir(parents=True)
            (plugin / 'manifest.json').write_text(json.dumps({'Name': 'Fixture', 'Actions': [{'Name': 'Website', 'UUID': 'website'}, {'Name': 'Hotkey fixture', 'UUID': 'com.hotspot.streamdock.system.hotkey', 'Controllers': ['Keypad', 'Knob']}]}))
            # Process lifecycle is simulated; never close or edit the user's app.
            params = StdioServerParameters(command=sys.executable, args=['-c', 'from streonor_mcp import profiles, server; profiles.vendor_running = lambda: False; server.main()'], env={'STREONOR_DATA_DIR': str(root / 'data'), 'STREONOR_PROFILES_DIR': str(root / 'profiles'), 'STREONOR_ICONS_DIR': str(icons)})
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                    self.assertTrue(tools['read_profile'].annotations.readOnlyHint)
                    self.assertTrue(tools['apply_action_change'].annotations.destructiveHint)
                    self.assertEqual(tools['read_profile'].annotations.title, 'Inspect a Scene or Page')
                    self.assertTrue(all(tool.annotations.title for tool in tools.values()))
                    called = set()
                    async def call(tool_name, **args):
                        called.add(tool_name)
                        result = await session.call_tool(tool_name, args)
                        self.assertFalse(result.isError, result.content)
                        return [json.loads(c.text) for c in result.content if c.type == 'text']
                    self.assertTrue(await call('list_supported_devices'))
                    self.assertTrue(await call('list_available_actions'))
                    self.assertEqual((await call('list_profiles'))[0]['name'], 'Fixture')
                    self.assertTrue(await call('find_icons', query='test'))
                    resolved = (await call('resolve_icon', query='test'))[0]
                    self.assertEqual(resolved['origin'], 'installed')
                    self.assertTrue(Path(resolved['path']).exists())
                    generated = (await call('resolve_icon', query='Unlisted Service'))[0]
                    self.assertEqual(generated['origin'], 'generated_label')
                    self.assertEqual((await call('prepare_icon', image_path=str(source), output_path=str(output)))[0]['width'], 1254)
                    boot = (await call('prepare_boot_logo', device_id='streonor-s6-mini', image_path=str(source), output_path=str(root / 'boot.png'), fit='contain'))[0]
                    self.assertFalse(boot['device_written'])
                    with Image.open(boot['path']) as image:
                        self.assertEqual(image.size, (320, 240))
                        self.assertEqual(image.getpixel((0, 0)), (0, 0, 0))
                        self.assertEqual(image.getpixel((160, 120)), (255, 0, 0))
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
                    args = dict(profile=profile, operation='set_flow', coordinate='1,0', flow_steps=[{'source_coordinate': '0,0'}, {'source_coordinate': '0,0', 'settings': {'path': 'https://second.test'}, 'delay_ms': 500}], flow_title='Two steps')
                    change = (await call('preview_action_change', **args))[0]
                    await call('apply_action_change', **args, expected_sha256=change['sha256'])
                    final = (await call('read_profile', profile=profile))[0]['profile']
                    self.assertEqual(final['Actions']['1,0']['Actions'][1]['Settings']['path'], 'https://second.test')
                    scene = (await call('preview_scene_creation', source_profile=profile, name='Temp'))[0]
                    created = (await call('create_scene', source_profile=profile, name='Temp', expected_source_sha256=scene['source_sha256'], expected_registry_sha256=scene['registry_sha256']))[0]
                    blank = (await call('read_profile', profile=created['profile']))[0]['profile']
                    self.assertEqual(blank['Actions'], {})
                    self.assertEqual(blank['Name'], 'Temp')
                    with closing(sqlite3.connect(root / 'config' / 'DataCache.db')) as db:
                        self.assertEqual(db.execute('SELECT COUNT(*) FROM StreonorS6 WHERE Profile=?', (created['profile'],)).fetchone()[0], 1)
                    duplicate = await session.call_tool('preview_scene_creation', {'source_profile': profile, 'name': 'Temp'})
                    self.assertTrue(duplicate.isError)
                    change = (await call('preview_scene_change', profile=created['profile'], operation='rename', new_name='Renamed'))[0]
                    await call('apply_scene_change', profile=created['profile'], operation='rename', new_name='Renamed', expected_sha256=change['sha256'], expected_registry_sha256=change['registry_sha256'])
                    self.assertEqual((await call('read_profile', profile=created['profile']))[0]['profile']['Name'], 'Renamed')
                    change = (await call('preview_scene_change', profile=created['profile'], operation='delete'))[0]
                    deleted = (await call('apply_scene_change', profile=created['profile'], operation='delete', expected_sha256=change['sha256'], expected_registry_sha256=change['registry_sha256']))[0]
                    self.assertTrue(Path(deleted['scene_archive']).is_dir())
                    self.assertFalse((root / 'profiles' / created['profile']).exists())
                    selected = ['0,0', '3,0']
                    scene = (await call('preview_scene_creation', source_profile=profile, name='Work', include_coordinates=selected))[0]
                    copied = (await call('create_scene', source_profile=profile, name='Work', include_coordinates=selected, expected_source_sha256=scene['source_sha256'], expected_registry_sha256=scene['registry_sha256']))[0]
                    doc = (await call('read_profile', profile=copied['profile']))[0]['profile']
                    self.assertEqual(set(doc['Actions']), set(selected))
                    self.assertEqual(doc['Actions']['3,0']['Settings'], manifest['Actions']['3,0']['Settings'])
                    self.assertNotEqual(doc['Actions']['0,0']['ActionID'], manifest['Actions']['0,0'].get('ActionID'))
                    args = dict(profile=profile, operation='create_by_name', coordinate='2,0', action_name='website', action_settings={'path': 'https://github.com'}, icon_query='GitHub')
                    c = (await call('preview_action_change', **args))[0]
                    self.assertFalse(c['execution_verified'])
                    await call('apply_action_change', **args, expected_sha256=c['sha256'], expected_auto_icon_sha256=c['auto_icon']['sha256'])
                    doc = (await call('read_profile', profile=profile))[0]['profile']
                    self.assertTrue(doc['Actions']['2,0']['States'][0]['Image'].endswith('.png'))
                    args = dict(profile=profile, operation='configure_action', coordinate='2,0', action_settings={'path': 'https://github.com/issues'})
                    c = (await call('preview_action_change', **args))[0]
                    await call('apply_action_change', **args, expected_sha256=c['sha256'])
                    args = dict(profile=profile, operation='set_flow', coordinate='2,1', flow_title='Copy and paste', flow_steps=[{'action_name': 'com.hotspot.streamdock.system.hotkey', 'hotkey': 'Ctrl+C'}, {'action_name': 'com.hotspot.streamdock.system.hotkey', 'hotkey': 'Ctrl+V', 'delay_ms': 250}])
                    c = (await call('preview_action_change', **args))[0]
                    await call('apply_action_change', **args, expected_sha256=c['sha256'])
                    doc = (await call('read_profile', profile=profile))[0]['profile']
                    self.assertEqual([a['Settings']['Hotkeys'][0]['VKeyCode'] for a in doc['Actions']['2,1']['Actions']], [67, 86])
                    args = dict(profile=profile, operation='create_by_name', coordinate='1,1', action_name='Hotkey fixture', hotkey='Ctrl+Shift+P')
                    c = (await call('preview_action_change', **args))[0]
                    self.assertEqual(c['hotkey'], 'Ctrl+Shift+P')
                    saved = (await call('apply_action_change', **args, expected_sha256=c['sha256']))[0]
                    doc = (await call('read_profile', profile=profile))[0]['profile']
                    keys = doc['Actions']['1,1']['Settings']['Hotkeys']
                    self.assertEqual([key['VKeyCode'] for key in keys], [80, -1, -1])
                    self.assertTrue(keys[0]['KeyCtrl'] and keys[0]['KeyShift'])
                    backup_name = Path(saved['backup']).name
                    restore = (await call('preview_control_restore', profile=profile, backup_name=backup_name))[0]
                    self.assertEqual(restore['changed_coordinates'], ['1,1'])
                    restore_args = dict(profile=profile, backup_name=backup_name,
                                        expected_sha256=restore['sha256'], expected_backup_sha256=restore['backup_sha256'])
                    stale_restore = await session.call_tool('restore_controls', {**restore_args, 'expected_backup_sha256': '0' * 64})
                    self.assertTrue(stale_restore.isError)
                    await call('restore_controls', **restore_args)
                    restored = (await call('read_profile', profile=profile))[0]['profile']
                    self.assertNotIn('1,1', restored['Actions'])
                    self.assertEqual(restored['Actions']['3,0'], manifest['Actions']['3,0'])
                    order = [page, profile]
                    preview = (await call('preview_page_order', profile=profile, page_order=order))[0]
                    invalid = await session.call_tool('preview_page_order', {'profile': profile, 'page_order': [profile, profile]})
                    self.assertTrue(invalid.isError)
                    await call('reorder_pages', profile=profile, page_order=order, expected_sha256=preview['sha256'])
                    reordered = (await call('read_profile', profile=profile))[0]['profile']
                    self.assertEqual(reordered['Pages'], {'Current': profile, 'Pages': order})
                    self.assertEqual(reordered['Actions'], restored['Actions'])
                    self.assertEqual(set(tools), called, 'Every exposed MCP tool must be exercised')
