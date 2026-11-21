import asyncio
import os
from pathlib import Path
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    token = (Path(os.environ['LOCALAPPDATA']) / 'STREONOR-MCP' / 'token.txt').read_text().strip()
    async with httpx.AsyncClient(headers={'Authorization': 'Bearer ' + token}, timeout=10) as http:
        async with streamable_http_client('http://127.0.0.1:29606/mcp', http_client=http) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                print('tools:', ', '.join(tool.name for tool in tools.tools))
                result = await session.call_tool('list_profiles', {})
                if result.isError:
                    raise RuntimeError(str(result.content))
                print('list_profiles succeeded')

asyncio.run(main())
