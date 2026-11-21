"""Local MCP access to STREONOR software profiles."""
import hmac
import logging
import os
from pathlib import Path
import secrets
import sys

from mcp.server.fastmcp import FastMCP
from . import profiles
from .app import edit_with_restart
from .paths import data_dir
from mcp.types import ToolAnnotations
from .devices import DEVICES, describe

mcp = FastMCP('STREONOR MCP', instructions='Inspect the target profile and preview before applying changes. Use returned hashes. Close the vendor app or explicitly request manage_app on Windows. Force closing may discard unsaved edits. Device support does not imply direct USB control.')
DATA = data_dir()

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def find_icons(query: str, limit: int = 50) -> list[dict]:
    """Search icon packs imported into STREONOR. SVG results are listed but cannot yet be applied directly."""
    return profiles.find_icons(query, limit)

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=False))
def prepare_icon(image_path: str, output_path: str) -> dict:
    """Create a 1254 x 1254 square PNG with transparent padding; output must not exist. Does not edit a profile."""
    return profiles.prepare_icon(image_path, output_path)

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=False))
def prepare_boot_logo(device_id: str, image_path: str, output_path: str) -> dict:
    """Prepare an image at the selected model's registered dimensions; does not write the device."""
    return profiles.prepare_boot_logo(device_id, image_path, output_path)

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def list_supported_devices() -> list[dict]:
    """List models and known controls and logo specifications from the community registry."""
    return [describe(spec.id) for spec in DEVICES]

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def list_available_actions() -> list[dict]:
    """List action types from installed STREONOR plugin manifests, including Toolbox and dial actions."""
    return profiles.list_installed_actions()

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def list_profiles() -> list[dict]:
    """List STREONOR profiles and their device and page identifiers."""
    return profiles.list_profiles()

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def read_profile(profile: str, page: str = '') -> dict:
    """Read a profile or page including its existing actions, settings, and content hash."""
    data, sha = profiles.read_manifest(profile, page or None)
    return {'profile': data, 'sha256': sha}

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def preview_setting_change(profile: str, coordinate: str, setting: str, new_value: object, page: str = '') -> dict:
    """Preview editing one existing action setting. Does not change the file. JSON types must match."""
    return profiles.prepare(profile, page or None, coordinate, setting, new_value)

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=False))
def apply_setting_change(profile: str, coordinate: str, setting: str, new_value: object, expected_sha256: str, page: str = '', manage_app: bool = False, force_close: bool = False) -> dict:
    """Apply a previewed setting edit with backup. manage_app=True closes and reopens STREONOR; force_close=True can discard unsaved app edits. A changed hash requires a new preview."""
    return edit_with_restart(lambda: profiles.apply(profile, page or None, coordinate, setting, new_value, expected_sha256), manage_app, force_close)



@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def preview_action_change(profile: str, operation: str, coordinate: str, source_coordinate: str = '', image_path: str = '', page: str = '') -> dict:
    """Preview action or icon edits. PNG, JPEG, BMP, GIF, and WebP imports become 1254 x 1254 PNG with transparent padding."""
    return profiles.prepare_action(profile, page or None, operation, coordinate, source_coordinate, image_path)

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=False))
def apply_action_change(profile: str, operation: str, coordinate: str, expected_sha256: str, source_coordinate: str = '', image_path: str = '', expected_image_sha256: str = '', page: str = '', manage_app: bool = False, force_close: bool = False) -> dict:
    """Apply a previewed action/icon edit with backup. manage_app=True closes and reopens STREONOR. force_close=True can discard unsaved app edits. Imports become 1254 x 1254 PNG."""
    return edit_with_restart(lambda: profiles.apply_action(profile, page or None, operation, coordinate, expected_sha256, source_coordinate, image_path, expected_image_sha256), manage_app, force_close)


def token():
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = DATA / 'token.txt'
    if not path.exists():
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w', encoding='ascii') as f:
                f.write(secrets.token_urlsafe(32))
        except FileExistsError:
            pass
    return path.read_text(encoding='ascii').strip()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Community STREONOR MCP server')
    parser.add_argument('--http', action='store_true', help='Serve authenticated HTTP on localhost:29606 (default: stdio)')
    parser.add_argument('--version', action='version', version='streonor-mcp 0.2.0')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if args.http:
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
