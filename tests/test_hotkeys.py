import unittest
from unittest.mock import patch
from streonor_mcp.catalog import build_action
from streonor_mcp.flows import build_flow
from streonor_mcp.hotkeys import settings_for_chord


class HotkeyTests(unittest.TestCase):
    def metadata(self):
        return [{'uuid': 'com.hotspot.streamdock.system.hotkey', 'name': 'Hotkey', 'plugin': 'Native', 'controllers': ['Keypad', 'Knob']}]

    def test_multi_step_modifiers_and_order(self):
        with patch('streonor_mcp.profiles.list_installed_actions', return_value=self.metadata()):
            flow = build_flow({}, '0,0', [{'action_name': 'Hotkey', 'hotkey': 'Ctrl+Shift+P'}, {'action_name': 'Hotkey', 'hotkey': 'Alt+Tab', 'delay_ms': 300}, {'action_name': 'Hotkey', 'hotkey': 'Ctrl+V', 'delay_ms': 200}], 'Sequence')
        first, second, third = flow['Actions']
        self.assertEqual(first['Settings']['Hotkeys'][0]['VKeyCode'], 80)
        self.assertTrue(first['Settings']['Hotkeys'][0]['KeyCtrl'])
        self.assertTrue(first['Settings']['Hotkeys'][0]['KeyShift'])
        self.assertFalse(second['Settings']['Hotkeys'][0]['KeyCtrl'])
        self.assertTrue(second['Settings']['Hotkeys'][0]['KeyOption'])
        self.assertFalse(third['Settings']['Hotkeys'][0]['KeyOption'])
        self.assertEqual([a['Settings']['delay'] for a in flow['Actions']], [0, 300, 200])
        self.assertEqual(first['Settings']['Hotkeys'][1]['VKeyCode'], -1)

    def test_invalid_chords_and_ambiguous_names(self):
        with patch('streonor_mcp.profiles.list_installed_actions', return_value=self.metadata()):
            action, _ = build_action('Hotkey')
        for chord in ['Ctrl+', 'Ctrl+Ctrl+C', 'Ctrl+C+V', 'Ctrl+unsupported']:
            with self.subTest(chord=chord), self.assertRaises(ValueError):
                settings_for_chord(action['Settings'], chord)
        with patch('streonor_mcp.profiles.list_installed_actions', return_value=self.metadata() * 2):
            with self.assertRaises(ValueError):
                build_action('Hotkey')
