"""Local MCP access to STREONOR software profiles."""
import hmac
import logging
import os
from pathlib import Path
import secrets
import sys

from mcp.server.fastmcp import FastMCP
from . import profiles

mcp = FastMCP('STREONOR MCP')
DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'STREONOR-MCP'

@mcp.tool()
def list_profiles() -> list[dict]:
    """List STREONOR profiles and their device and page identifiers."""
    return profiles.list_profiles()

@mcp.tool()
def read_profile(profile: str, page: str = '') -> dict:
    """Read a profile or page including its existing actions, settings, and content hash."""
    data, sha = profiles.read_manifest(profile, page or None)
    return {'profile': data, 'sha256': sha}

@mcp.tool()
def preview_setting_change(profile: str, coordinate: str, setting: str, new_value: object, page: str = '') -> dict:
    """Preview editing one existing action setting. Does not change the file. JSON types must match."""
    return profiles.prepare(profile, page or None, coordinate, setting, new_value)

@mcp.tool()
def apply_setting_change(profile: str, coordinate: str, setting: str, new_value: object, expected_sha256: str, page: str = '') -> dict:
    """Apply a previously previewed setting change with a backup. Requires explicit user approval and STREONOR to be fully closed; reopen it afterward."""
    return profiles.apply(profile, page or None, coordinate, setting, new_value, expected_sha256)


def token():
    DATA.mkdir(parents=True, exist_ok=True)
    path = DATA / 'token.txt'
    if not path.exists():
        try:
            with path.open('x', encoding='ascii') as f:
                f.write(secrets.token_urlsafe(32))
        except FileExistsError:
            pass
    return path.read_text(encoding='ascii').strip()


def main():
    logging.basicConfig(level=logging.INFO)
    if '--http' in sys.argv:
        import uvicorn
        from starlette.responses import PlainTextResponse
        app = mcp.streamable_http_app()
        secret = ('Bearer ' + token()).encode('ascii')
        async def protected(scope, receive, send):
            if scope['type'] == 'http':
                auth = dict(scope['headers']).get(b'authorization', b'')
                if not hmac.compare_digest(auth, secret):
                    await PlainTextResponse('Unauthorized', status_code=401)(scope, receive, send)
                    return
            await app(scope, receive, send)
        uvicorn.run(protected, host='127.0.0.1', port=29606, log_level='warning')
    else:
        mcp.run(transport='stdio')

if __name__ == '__main__':
    main()
