import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(command='.venv/Scripts/python.exe', args=['-m', 'streonor_mcp.server'])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print('tools:', ', '.join(tool.name for tool in tools.tools))
            await asyncio.sleep(3)
            result = await session.call_tool('device_status', {})
            print('status:', result.content)

asyncio.run(main())
