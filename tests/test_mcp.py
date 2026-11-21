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
            params = StdioServerParameters(command=sys.executable, args=['-m', 'streonor_mcp.server'], env={'STREONOR_DATA_DIR': str(root / 'data'), 'STREONOR_PROFILES_DIR': str(root / 'profiles')})
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                    self.assertTrue(tools['read_profile'].annotations.readOnlyHint)
                    self.assertTrue(tools['apply_action_change'].annotations.destructiveHint)
                    result = await session.call_tool('prepare_icon', {'image_path': str(source), 'output_path': str(output)})
                    self.assertFalse(result.isError)
                    self.assertEqual(json.loads(result.content[0].text)['width'], 1254)
                    with Image.open(output) as image:
                        self.assertEqual(image.size, (1254, 1254))
                        self.assertEqual(image.format, 'PNG')
