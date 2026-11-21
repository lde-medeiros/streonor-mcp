"""Local MCP access to STREONOR software profiles."""
import hmac
import logging
import os
from pathlib import Path
import secrets
import sys

from mcp.server.fastmcp import FastMCP
from . import profiles
from . import scenes, layout, live
from .app import edit_with_restart
from .paths import data_dir
from .locking import edit_lock
from mcp.types import ToolAnnotations
from .devices import DEVICES, describe

mcp = FastMCP('STREONOR MCP', instructions=(
    'Use preview_scene_layout and apply_scene_layout to finish a batch in one preview and one apply. '
    'For an existing scene, use mode=edit (or omit name): keep its ID, name and unrelated controls. '
    'To clear controls but keep the scene, pass replace=true and controls={} for each requested page; '
    'do not delete the scene unless the user asks to delete it. '
    'For a new scene with new controls, use mode=create and include_coordinates for knobs or other controls '
    'to copy from an existing scene. Use mode=copy only when the user wants a separate edited copy. '
    'For Steam, call list_steam_games, then add each chosen game with steam_app_id and title in the layout. '
    'Steam manifests also include tools and utilities; select games for a game layout. If fewer games are installed than requested, use what exists and report the empty slots. '
    'Do not move dials or scene controls into game key slots. '
    'Pass the preview hash and perform the requested apply without asking the user to repeat the request. '
    'Managed layout edits and scene creation/deletion close and reopen the Windows app by default. '
    'Keep automatic icons enabled unless the user asks otherwise and pass any supplied images explicitly. '
    'Generated labels are not official logos. S6 Mini live icon editing still uses live_in_place.'
))
DATA = data_dir()

@mcp.tool(annotations=ToolAnnotations(title='Search Local Icon Packs', readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def find_icons(query: str, limit: int = 50) -> list[dict]:
    """Search icon packs imported into STREONOR. Safe self-contained SVG icons can be rendered to PNG."""
    return profiles.find_icons(query, limit)

@mcp.tool(annotations=ToolAnnotations(title='Choose or Generate a Shortcut Icon', readOnlyHint=False, destructiveHint=False, openWorldHint=False))
def resolve_icon(query: str, image_path: str = '') -> dict:
    """Prepare a matching 1254 PNG. Prefer an explicit image, then an exact installed icon match, otherwise generate a black label icon. No network requests. Return path, origin and hash for set_icon."""
    from .icons import resolve
    data, info = resolve(query, image_path)
    path = DATA / 'icons' / (info['sha256'] + '.png')
    try:
        profiles.write_new_file(path, data)
    except FileExistsError:
        if profiles.fingerprint(profiles.read_bounded(path, 16 * 1024 * 1024)) != info['sha256']:
            raise ValueError('Cached icon was modified')
    return {'path': str(path), 'width': 1254, 'height': 1254, 'format': 'PNG', **info}

@mcp.tool(annotations=ToolAnnotations(title='Convert an Image to a Shortcut Icon', readOnlyHint=False, destructiveHint=True, openWorldHint=False))
def prepare_icon(image_path: str, output_path: str, background_color: str = '', replace_edge_background: bool = False) -> dict:
    """Create a square 1254 PNG; output must not exist. Optional #RRGGBB background flattens transparency. replace_edge_background replaces the top-left connected background with tolerance 24. Does not edit a profile."""
    return profiles.prepare_icon(image_path, output_path, background_color, replace_edge_background)

@mcp.tool(annotations=ToolAnnotations(title='Prepare Device Boot Artwork', readOnlyHint=False, destructiveHint=True, openWorldHint=False))
def prepare_boot_logo(device_id: str, image_path: str, output_path: str, fit: str = 'cover') -> dict:
    """Prepare a PNG for STREONOR's Devices menu. Cover crops to fill. Contain preserves the whole image with black padding. The device is unchanged."""
    return profiles.prepare_boot_logo(device_id, image_path, output_path, fit)

@mcp.tool(annotations=ToolAnnotations(title='List STREONOR Device Models', readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def list_supported_devices() -> list[dict]:
    """List models and known controls and logo specifications from the community registry."""
    return [describe(spec.id) for spec in DEVICES]

@mcp.tool(annotations=ToolAnnotations(title='List Installed Toolbox Actions', readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def list_available_actions() -> list[dict]:
    """List action types from installed STREONOR plugin manifests, including Toolbox and dial actions."""
    return profiles.list_installed_actions()

@mcp.tool(annotations=ToolAnnotations(title='List Saved Scenes', readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def list_profiles() -> list[dict]:
    """List STREONOR profiles and their device and page identifiers."""
    return profiles.list_profiles()

@mcp.tool(annotations=ToolAnnotations(title='Inspect a Scene or Page', readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def read_profile(profile: str, page: str = '') -> dict:
    """Read a profile or page including its existing actions, settings, and content hash."""
    data, sha = profiles.read_manifest(profile, page or None)
    return {'profile': data, 'sha256': sha}

@mcp.tool(annotations=ToolAnnotations(title='Preview a New Scene', readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def preview_scene_creation(source_profile: str, name: str, include_coordinates: list[str] | None = None) -> dict:
    """Preview a new scene for the source device. Optionally copy include_coordinates from the source (buttons, knobs, flows and PNG icons). Checks catalog and duplicate names."""
    return scenes.preview(source_profile, name, include_coordinates=include_coordinates)

@mcp.tool(annotations=ToolAnnotations(title='Create a Previewed Scene', readOnlyHint=False, destructiveHint=True, openWorldHint=False))
def create_scene(source_profile: str, name: str, expected_source_sha256: str, expected_registry_sha256: str, manage_app: bool | None = None, force_close: bool = False, include_coordinates: list[str] | None = None) -> dict:
    """Create a previewed scene and register it in STREONOR, backing up its catalog. Optional include_coordinates copies selected source actions and PNG icons. Closes and reopens the Windows app by default."""
    with edit_lock(profiles.ROOT):
        change = scenes.preview(source_profile, name, include_coordinates=include_coordinates)
        if change['source_sha256'] != expected_source_sha256 or change['registry_sha256'] != expected_registry_sha256:
            raise ValueError('Source or catalog changed; preview again')
        return edit_with_restart(lambda: scenes.create(source_profile, name, expected_source_sha256, expected_registry_sha256, include_coordinates=include_coordinates), sys.platform == 'win32' if manage_app is None else manage_app, force_close)

@mcp.tool(annotations=ToolAnnotations(title='Preview a Scene Rename or Deletion', readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def preview_scene_change(profile: str, operation: str, new_name: str = '') -> dict:
    """Preview renaming or deleting a registered scene. Last-scene deletion is refused."""
    return scenes.preview_change(profile, operation, new_name)

@mcp.tool(annotations=ToolAnnotations(title='Apply a Scene Rename or Deletion', readOnlyHint=False, destructiveHint=True, openWorldHint=False))
def apply_scene_change(profile: str, operation: str, expected_sha256: str, expected_registry_sha256: str, new_name: str = '', manage_app: bool | None = None, force_close: bool = False) -> dict:
    """Rename/delete a previewed scene with backups. Deletion unregisters it and archives its entire folder. Closes and reopens Windows STREONOR by default."""
    with edit_lock(profiles.ROOT):
        change = scenes.preview_change(profile, operation, new_name)
        if change['sha256'] != expected_sha256 or change['registry_sha256'] != expected_registry_sha256:
            raise ValueError('Scene or catalog changed; preview again')
        return edit_with_restart(lambda: scenes.apply_change(profile, operation, expected_sha256, expected_registry_sha256, new_name), sys.platform == 'win32' if manage_app is None else manage_app, force_close)

@mcp.tool(annotations=ToolAnnotations(title='Preview a Control Setting Edit', readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def preview_setting_change(profile: str, coordinate: str, setting: str, new_value: object, page: str = '', auto_icon: bool = True, icon_query: str = '') -> dict:
    """Preview an existing setting change. URL/app destination changes select a matching icon by default. auto_icon=False preserves the icon. icon_query supplies a service/app name. Does not change the file. JSON types must match."""
    return profiles.prepare(profile, page or None, coordinate, setting, new_value, auto_icon=auto_icon, icon_query=icon_query)

@mcp.tool(annotations=ToolAnnotations(title='Apply a Control Setting Edit', readOnlyHint=False, destructiveHint=True, openWorldHint=False))
def apply_setting_change(profile: str, coordinate: str, setting: str, new_value: object, expected_sha256: str, page: str = '', manage_app: bool = False, force_close: bool = False, auto_icon: bool = True, icon_query: str = '', expected_auto_icon_sha256: str = '', live_scene_name: str = '') -> dict:
    """Apply a previewed setting edit with backup. manage_app=True closes and reopens STREONOR; force_close=True can discard unsaved app edits. Use live_scene_name on Windows to import the edit into a new scene while STREONOR runs. A changed hash requires a new preview."""
    with edit_lock(profiles.ROOT):
        preview = profiles.prepare(profile, page or None, coordinate, setting, new_value, auto_icon=auto_icon, icon_query=icon_query)
        if preview['sha256'] != expected_sha256:
            raise ValueError('Profile changed since preview; inspect and preview again')
        if expected_auto_icon_sha256 and preview.get('auto_icon', {}).get('sha256') != expected_auto_icon_sha256:
            raise ValueError('Automatic icon changed since preview. Preview again')

        def edit():
            return profiles.apply(profile, page or None, coordinate, setting, new_value, expected_sha256, auto_icon=auto_icon, icon_query=icon_query, expected_auto_icon_sha256=expected_auto_icon_sha256, live_scene_name=live_scene_name)

        if live_scene_name:
            if manage_app or force_close:
                raise ValueError('live_scene_name cannot be combined with app restart options')
            return edit()
        return edit_with_restart(edit, manage_app, force_close)



@mcp.tool(annotations=ToolAnnotations(title='Preview a Control or Flow Edit', readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def preview_action_change(profile: str, operation: str, coordinate: str, source_coordinate: str = '', image_path: str = '', page: str = '', flow_steps: list[dict] | None = None, flow_title: str = '', auto_icon: bool = True, icon_query: str = '', action_name: str = '', action_settings: dict | None = None, controller: str = 'Keypad', hotkey: str = '', state_index: int = 0, state_images: dict[int, str] | None = None) -> dict:
    """Preview action/icon edits. create_by_name fills an empty slot from installed action_name or UUID. replace_by_name swaps an occupied slot in one write and keeps existing state icons by default. Supply image_path, state_images, or an automatic icon_query to select a replacement. Supply hotkey, for example Ctrl+Shift+P, with create_by_name or replace_by_name and the installed Hotkey or HotkeySwitch action. HotkeySwitch sends the same chord in both states. configure_action replaces settings for an existing slot. Plugin-specific execution is not verified by creation alone. Other operations: set_flow replaces a key with ordered steps cloned from same-page source_coordinate actions, optional settings overrides and delay_ms. Supply flow_steps and flow_title. New actions and flows get matching icons by default. auto_icon=False opts out and icon_query supplies a name. For icon operations state_index selects the image state, starting at 0. Use set_state_icons or supply state_images with create_by_name or replace_by_name to apply preferred images by state index together. PNG, JPEG, BMP, GIF, and WebP imports become 1254 x 1254 PNG with transparent padding."""
    return profiles.prepare_action(profile, page or None, operation, coordinate, source_coordinate, image_path, flow_steps=flow_steps, flow_title=flow_title, auto_icon=auto_icon, icon_query=icon_query, action_name=action_name, action_settings=action_settings, controller=controller, hotkey=hotkey, state_index=state_index, state_images=state_images)

@mcp.tool(annotations=ToolAnnotations(title='Apply a Control or Flow Edit', readOnlyHint=False, destructiveHint=True, openWorldHint=False))
def apply_action_change(profile: str, operation: str, coordinate: str, expected_sha256: str, source_coordinate: str = '', image_path: str = '', expected_image_sha256: str = '', page: str = '', manage_app: bool = False, force_close: bool = False, flow_steps: list[dict] | None = None, flow_title: str = '', auto_icon: bool = True, icon_query: str = '', expected_auto_icon_sha256: str = '', action_name: str = '', action_settings: dict | None = None, controller: str = 'Keypad', hotkey: str = '', state_index: int = 0, live_scene_name: str = '', live_in_place: bool = False, state_images: dict[int, str] | None = None, expected_state_image_sha256: dict[int, str] | None = None) -> dict:
    """Apply a previewed action/icon edit with backup. manage_app=True closes and reopens STREONOR. force_close=True can discard unsaved app edits. Use live_scene_name on Windows to import the edit into a new scene while STREONOR runs. Use live_in_place=True to set or reset a keypad or Scene Shift icon state in the selected single-page S6 Mini scene on Windows. Imported icons become 1254 x 1254 PNG."""
    with edit_lock(profiles.ROOT):
        if manage_app or live_in_place:
            preview = profiles.prepare_action(profile, page or None, operation, coordinate, source_coordinate, image_path, flow_steps=flow_steps, flow_title=flow_title, auto_icon=auto_icon, icon_query=icon_query, action_name=action_name, action_settings=action_settings, controller=controller, hotkey=hotkey, state_index=state_index, state_images=state_images)
            if preview['sha256'] != expected_sha256 or (operation in ('set_icon', 'use_existing_icon') and preview['image_sha256'] != expected_image_sha256):
                raise ValueError('Profile or icon changed since preview; inspect and preview again')
            if expected_auto_icon_sha256 and preview.get('auto_icon', {}).get('sha256') != expected_auto_icon_sha256:
                raise ValueError('Automatic icon changed since preview. Preview again')
            if preview.get('state_image_sha256') != expected_state_image_sha256:
                raise ValueError('State icons changed since preview; inspect and preview again')

        if live_in_place:
            if operation not in ('set_icon', 'clear_icon') or live_scene_name or manage_app or force_close:
                raise ValueError('live_in_place supports set_icon and clear_icon without scene copy or restart options')
            from .live_ui import edit_icon
            return edit_icon(profile, page, coordinate, expected_sha256, image_path,
                             expected_image_sha256, state_index, operation)

        def edit():
            return profiles.apply_action(profile, page or None, operation, coordinate, expected_sha256, source_coordinate, image_path, expected_image_sha256, flow_steps=flow_steps, flow_title=flow_title, auto_icon=auto_icon, icon_query=icon_query, expected_auto_icon_sha256=expected_auto_icon_sha256, action_name=action_name, action_settings=action_settings, controller=controller, hotkey=hotkey, state_index=state_index, live_scene_name=live_scene_name, state_images=state_images, expected_state_image_sha256=expected_state_image_sha256)

        if live_scene_name:
            if manage_app or force_close:
                raise ValueError('live_scene_name cannot be combined with app restart options')
            return edit()
        return edit_with_restart(edit, manage_app, force_close)


@mcp.tool(annotations=ToolAnnotations(title='Preview Reordering Scene Pages', readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def preview_page_order(profile: str, page_order: list[str]) -> dict:
    """Preview a new order for all existing pages. Use the page IDs from the scene registry."""
    return profiles.prepare_page_order(profile, page_order)[0]


@mcp.tool(annotations=ToolAnnotations(title='Reorder Scene Pages', readOnlyHint=False, destructiveHint=True, openWorldHint=False))
def reorder_pages(profile: str, page_order: list[str], expected_sha256: str, manage_app: bool = False, force_close: bool = False) -> dict:
    """Apply a previewed page order with a backup. The current page stays selected."""
    with edit_lock(profiles.ROOT):
        preview = profiles.prepare_page_order(profile, page_order)[0]
        if preview['sha256'] != expected_sha256:
            raise ValueError('Scene changed since preview')
        if preview['old_order'] == page_order:
            return {'updated': False, 'new_sha256': expected_sha256}
        return edit_with_restart(lambda: profiles.reorder_pages(profile, page_order, expected_sha256), manage_app, force_close)


@mcp.tool(annotations=ToolAnnotations(title='Preview Restoring Saved Controls', readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def preview_control_restore(profile: str, backup_name: str, page: str = '') -> dict:
    """Preview replacing the controls on a scene or page with its own MCP backup. Use the filename returned by a prior edit."""
    return profiles.prepare_restore(profile, page or None, backup_name)[0]


@mcp.tool(annotations=ToolAnnotations(title='Restore Saved Controls', readOnlyHint=False, destructiveHint=True, openWorldHint=False))
def restore_controls(profile: str, backup_name: str, expected_sha256: str, expected_backup_sha256: str, page: str = '', manage_app: bool = False, force_close: bool = False) -> dict:
    """Restore a previewed control backup. The current controls are backed up before replacement."""
    page = page or None
    with edit_lock(profiles.ROOT):
        preview = profiles.prepare_restore(profile, page, backup_name)[0]
        if (preview['sha256'], preview['backup_sha256']) != (expected_sha256, expected_backup_sha256):
            raise ValueError('Scene or backup changed since preview')
        if not preview['changed_coordinates']:
            return {'updated': False, 'new_sha256': expected_sha256}
        return edit_with_restart(lambda: profiles.restore_controls(profile, page, backup_name, expected_sha256, expected_backup_sha256), manage_app, force_close)


@mcp.tool(annotations=ToolAnnotations(title='List Installed Steam Games', readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def list_steam_games(library_path: str = '') -> list[dict]:
    """Find locally installed Steam games across configured Steam libraries and common Windows drives. Optionally specify a library or steamapps directory. Returns app_id and name for steam_app_id and title in a scene layout. Recently played titles appear first. Includes installed Steam apps and demos; excludes uninstalled purchases."""
    from .steam import installed_games
    return installed_games(library_path)


@mcp.tool(annotations=ToolAnnotations(title='Preview a Page or Scene Layout', readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def preview_scene_layout(profile: str, pages: list[layout.PageEdit], name: str = '', mode: str = 'auto', include_coordinates: list[str] | None = None) -> dict:
    """Preview a batch using a scene name or ID. Edit the original with no name or mode=edit. Clear a page with replace=true and controls={} or keep selected existing controls via keep_coordinates. Mode=create creates a new named scene in one operation and optionally copies include_coordinates from the source. Mode=copy imports a separate named scene while STREONOR stays open on Windows. Use steam_app_id plus title for a Steam key, action_name plus settings for other new keys, or null to remove one control."""
    return layout.plan(profile, name, pages, profiles.ROOT, mode, include_coordinates)[0]


@mcp.tool(annotations=ToolAnnotations(title='Apply a Scene Layout', readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False))
def apply_scene_layout(profile: str, pages: list[layout.PageEdit], expected_layout_sha256: str, name: str = '', mode: str = 'auto', include_coordinates: list[str] | None = None, manage_app: bool | None = None, force_close: bool = False) -> dict:
    """Apply all controls from a preview with its layout_sha256. In-place edits retain the scene and back up changed pages. Create mode registers a fully configured scene. On Windows both manage one app restart by default. Copy mode uses the running app and requires a new name. Pass manage_app=false to edit with STREONOR closed."""
    with edit_lock(profiles.ROOT):
        preview, edits, images = layout.plan(profile, name, pages, profiles.ROOT, mode, include_coordinates)
        if preview['layout_sha256'] != expected_layout_sha256:
            raise ValueError('Layout, source or icon changed since preview; preview again')
        profile = preview['source_profile']
        if preview['mode'] == 'copy':
            if manage_app or force_close:
                raise ValueError('Copy mode imports a scene without an app restart')
            return live.import_scene(profile, profiles.ROOT, preview['name'], edits,
                                     preview['source_hashes'], images)

        def edit():
            if preview['mode'] == 'create':
                return scenes.create(profile, preview['name'], preview['source_hashes'][profile],
                                     preview['registry_sha256'], include_coordinates=include_coordinates,
                                     layout_actions=edits[profile]['Actions'], layout_images=images)
            return layout.apply_in_place(profile, edits, preview['source_hashes'], images,
                                         profiles.ROOT, profiles.BACKUPS)

        return edit_with_restart(edit, sys.platform == 'win32' if manage_app is None else manage_app, force_close)


def token():
    with edit_lock(DATA):
        return _token()


def _token():
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = DATA / 'token.txt'
    if not path.exists():
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w', encoding='ascii') as f:
                f.write(secrets.token_urlsafe(32))
        except FileExistsError:
            pass
    value = path.read_text(encoding='ascii').strip()
    if len(value) < 32 or not value.isascii() or any(c.isspace() for c in value):
        raise RuntimeError('Invalid HTTP token file; restore a valid token or remove it to regenerate credentials')
    return value


def authenticated_app(app, secret):
    """Authenticate every HTTP route before passing it to the MCP application."""
    from starlette.responses import PlainTextResponse
    expected = ('Bearer ' + secret).encode('ascii')
    async def protected(scope, receive, send):
        if scope['type'] == 'http':
            headers = [value for name, value in scope['headers'] if name.lower() == b'authorization']
            if len(headers) != 1 or not hmac.compare_digest(headers[0], expected):
                await PlainTextResponse('Unauthorized', status_code=401)(scope, receive, send)
                return
        await app(scope, receive, send)
    return protected


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Community STREONOR MCP server')
    parser.add_argument('--http', action='store_true', help='Serve authenticated HTTP on localhost:29606 (default: stdio)')
    parser.add_argument('--version', action='version', version='streonor-mcp 0.8.2')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if args.http:
        import uvicorn
        app = mcp.streamable_http_app()
        uvicorn.run(authenticated_app(app, token()), host='127.0.0.1', port=29606, log_level='warning')
    else:
        mcp.run(transport='stdio')

if __name__ == '__main__':
    main()
