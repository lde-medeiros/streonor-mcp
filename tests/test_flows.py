import copy
import unittest
from streonor_mcp.flows import build_flow


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.actions = {'5,0': {'Name': 'OpenApps', 'UUID': 'com.hotspot.streamdock.system.openApps', 'Settings': {'appId': 0, 'applications': [{'name': 'Code'}, {'name': 'Terminal'}]}, 'States': [{'Image': ''}]}, '5,2': {'Name': 'Text', 'Controller': '', 'States': [{'Image': 'Images/btn_text'}]}}

    def test_order_and_independent_copies(self):
        original = copy.deepcopy(self.actions)
        flow = build_flow(self.actions, '5,2', [{'source_coordinate': '5,0', 'settings': {'appId': 0}}, {'source_coordinate': '5,0', 'settings': {'appId': 1}, 'delay_ms': 500}], 'Code + Terminal')
        self.assertEqual([a['Settings']['appId'] for a in flow['Actions']], [0, 1])
        self.assertEqual([a['Settings']['delay'] for a in flow['Actions']], [0, 500])
        self.assertEqual(flow['UUID'], 'com.hotspot.streamdock.multiactions.routine')
        self.assertEqual(flow['States'][0]['Title'], 'Code + Terminal')
        self.assertNotEqual(flow['Actions'][0]['ActionID'], flow['Actions'][1]['ActionID'])
        self.assertEqual(self.actions, original)

    def test_invalid_steps(self):
        for steps in [[], [{'source_coordinate': 'missing'}], [{'source_coordinate': '5,0', 'settings': {'appId': 99}}], [{'source_coordinate': '5,0', 'delay_ms': -1}], [{'source_coordinate': '5,0', 'settings': {'unknown': 'x'}}]]:
            with self.subTest(steps=steps), self.assertRaises(ValueError):
                build_flow(self.actions, '5,2', steps, 'Flow')
