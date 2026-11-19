import unittest
from streonor_mcp.device import make_image, packet, parse_input

class ProtocolTest(unittest.TestCase):
    def test_events(self):
        report = lambda code, state: b'ACK\0\0OK\0\0' + bytes([code, state])
        self.assertEqual(parse_input(report(1, 1)), ('key1', 'press'))
        self.assertEqual(parse_input(report(6, 0)), ('key6', 'release'))
        self.assertEqual(parse_input(report(0x90, 0)), ('dial1', 'left'))
        self.assertEqual(parse_input(report(0x61, 0)), ('dial2', 'right'))
        self.assertEqual(parse_input(report(0x35, 1)), ('dial3', 'press'))
        self.assertEqual(parse_input(report(0x31, 1)), ('scene3', 'press'))
        self.assertIsNone(parse_input(b'ACK'))
    def test_image_and_packets(self):
        self.assertEqual(len(packet('DIS')), 1024)
        self.assertTrue(make_image('Test', '#202838').startswith(b'\xff\xd8'))

if __name__ == '__main__':
    unittest.main()
