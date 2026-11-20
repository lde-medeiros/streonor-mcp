# Configuration and development reference

Community MCP tools for STREONOR profiles, actions, knobs and icons. Use the same local server with Claude, Codex, or another MCP client. Not affiliated with STREONOR.

**S6 Mini is the only hardware-verified device.** S10 Pro, S15 Standard and S32 Max are listed as unsupported. The server runs on Windows, macOS and Linux. Hardware and vendor app integration have only been tested on Windows.

## Quick start

Python 3.12+ is required. Clone this repository (GitHub authentication is required while private), then install in a virtual environment:

```sh
git clone https://github.com/lde-medeiros/streonor-mcp.git
cd streonor-mcp
python -m venv .venv
# Windows:
.venv\Scripts\python.exe -m pip install -e .
# macOS / Linux:
.venv/bin/python -m pip install -e .
```

The installed entry point is `.venv\Scripts\streonor-mcp.exe` on Windows and `.venv/bin/streonor-mcp` on macOS/Linux. Use its **absolute path** in clients so no shell activation or working directory is required. No PyPI release is published. `pip install streonor-mcp` is not the setup instruction yet.

## Connect Claude or Codex

Stdio is the recommended setup: the client starts the native server when needed, with no background service, network port or HTTP token. Replace `/absolute/path/to/streonor-mcp` with your installed entry point, including `.exe` on Windows.

Claude Code:

```sh
claude mcp add --transport stdio --scope user streonor -- /absolute/path/to/streonor-mcp
```

Codex:

```sh
codex mcp add streonor -- /absolute/path/to/streonor-mcp
```

Claude Desktop JSON configuration:

```json
{
  "mcpServers": {
    "streonor": {
      "command": "/absolute/path/to/streonor-mcp",
      "args": []
    }
  }
}
```

On Windows, use a JSON-escaped path such as `C:\\path\\streonor-mcp\\.venv\\Scripts\\streonor-mcp.exe`. Merge the entry into your existing configuration instead of replacing other servers.

Codex TOML alternative:

```toml
[mcp_servers.streonor]
command = "/absolute/path/to/streonor-mcp"
args = []
```

Reload the client's MCP connection after changing configuration. Start with: “Use STREONOR MCP to list my profiles. Inspect Development before changing anything.” Do not configure both stdio and HTTP entries for the same server name.

Client syntax references: [Claude Code MCP](https://code.claude.com/docs/en/mcp), [Codex MCP](https://developers.openai.com/codex/mcp/).

## Platform support and paths

| Capability | Windows | macOS | Linux |
| --- | --- | --- | --- |
| MCP stdio / localhost HTTP | Implemented | Implemented | Implemented |
| Image preparation and exported profile edits | Implemented | Implemented | Implemented |
| Vendor app profile discovery | Verified | Set explicit paths | Set explicit paths |
| Automatic vendor app restart | Implemented | Unsupported | Unsupported |
| S6 hardware with vendor app | Verified in prior testing | Unverified | Unverified |
| Direct USB control | Unimplemented | Unimplemented | Unimplemented |

Set these environment variables **in the MCP server's environment before startup**:

| Variable | Purpose |
| --- | --- |
| `STREONOR_PROFILES_DIR` | Absolute directory containing `*.sdProfile` folders |
| `STREONOR_ICONS_DIR` | Imported icon pack directory |
| `STREONOR_DATA_DIR` | MCP backups, HTTP token and logs directory |

Windows defaults to `%APPDATA%\HotSpot\StreamDock\profiles` and `%LOCALAPPDATA%\STREONOR-MCP`. On macOS the MCP data default is `~/Library/Application Support/STREONOR-MCP`. on Linux it is `$XDG_DATA_HOME/STREONOR-MCP` or `~/.local/share/STREONOR-MCP`. Non-Windows profiles default to a separate `vendor/profiles` directory under MCP data. These are workspace defaults, not claims about vendor installation layouts. Point `STREONOR_PROFILES_DIR` at an exported copy or a verified installation.

Example client entry for exported profiles:

```json
{
  "mcpServers": {
    "streonor": {
      "command": "/absolute/path/to/streonor-mcp",
      "env": {"STREONOR_PROFILES_DIR": "/absolute/path/to/exported/profiles"}
    }
  }
}
```

Running this server on Linux does not provide access to a Windows app through localhost or a shared path automatically. Do not edit a profile shared with a running vendor app on another OS: local process checks cannot detect remote processes. Configure a local copy for offline edits.

## Tools and edit workflow

MCP clients can show plain-language titles alongside the tool identifiers used below.

| Tool | Purpose |
| --- | --- |
| `list_supported_devices` | Device registry and known capabilities |
| `list_available_actions` | Installed plugin action types, including knob actions |
| `list_profiles`, `read_profile` | Profiles, pages, settings and current content hash |
| `find_icons` | Search imported icon packs, including SVG assets |
| `resolve_icon` | Resolve a local icon or generate a label image |
| `prepare_icon` | Create a 1254 x 1254 PNG without editing a profile |
| `prepare_boot_logo` | Prepare model-sized PNG artwork for the Devices menu |
| `preview_scene_creation`, `create_scene` | Create a blank scene or copy selected controls |
| `preview_scene_change`, `apply_scene_change` | Rename or archive a registered scene |
| `preview_page_order`, `reorder_pages` | Preview and reorder existing pages |
| `preview_control_restore`, `restore_controls` | Restore controls from a scoped MCP backup |
| `preview_setting_change`, `apply_setting_change` | Guarded changes to existing settings |
| `preview_action_change`, `apply_action_change` | Create, clone, configure, or remove actions, build flows, and manage icons |
| `preview_scene_layout`, `apply_scene_layout` | Preview and import edits across existing pages as a named scene copy |

Read the intended scene and page, preview the edit, then pass the returned hash to the matching apply tool. A stale hash requires a new preview. In-place writes create backups and require the app to close. On Windows, `manage_app=true` handles closing and reopening. If the app stays in the tray, `force_close=true` explicitly permits termination and may discard unsaved settings.

Actions can be cloned from an existing same-page action or created with create_by_name from installed Toolbox metadata. configure_action replaces a slot's complete settings object. Creation alone does not verify plugin-specific runtime behavior. Knob settings are editable where present in the vendor profile. Scenes can be created, renamed and deleted using the scene tools. Page creation and deletion, live event streaming, and direct Toolbox invocation are pending. Unknown settings require the same JSON type as their existing value.

Imported PNG/JPEG/BMP/GIF/WebP icons become exactly **1254 x 1254 pixels, 1:1, PNG**, with transparent padding, preserved proportions and no cropping. The first frame of animated inputs is used. Small source images are enlarged without adding detail. Original imported files are preserved. `prepare_icon` refuses to overwrite its output. Self-contained SVG icons are rendered to PNG. External resources, scripts and SVG text are rejected.

## Edit while STREONOR stays open

Two live workflows are available on the unreleased branch. For an in-place change, install the Windows `live` extra (`pip install -e ".[live]"` from the checkout). With STREONOR visible and the intended S6 Mini scene selected, preview `set_icon` at `4,1` and pass `live_in_place=true` to `apply_action_change`. Use `clear_icon` with the same workflow to restore the default icon. This works for the Scene Shift control on a single-page scene. The MCP uses STREONOR’s icon picker, saves a manifest backup, and verifies the original scene ID, settings, and image after the app saves.

Live scene copies are verified with the S6 Mini and the default profile directory. STREONOR imports a new named scene and keeps running. Select the new scene in the app. For other changes that must keep the original scene ID, use the guarded restart workflow.

For one change, preview normally and pass `live_scene_name` to `apply_action_change` or `apply_setting_change`. Use the returned profile ID for follow-up edits.

For a full layout, pass `profile`, a unique `name`, and the same `pages` to `preview_scene_layout` and `apply_scene_layout`. Use the preview's `layout_sha256` as `expected_layout_sha256` when applying. This example replaces the main page with two controls and patches an existing control on another page.

```json
[
  {
    "replace": true,
    "controls": {
      "0,0": {"action_name": "com.hotspot.streamdock.system.website", "settings": {"path": "https://example.org"}},
      "1,0": {"action_name": "com.hotspot.streamdock.system.hotkey", "hotkey": "Ctrl+Shift+M"}
    }
  },
  {
    "page": "SECOND-PAGE.sdProfile",
    "controls": {
      "0,0": {"settings": {"path": "https://example.com"}},
      "1,0": null
    }
  }
]
```

Omit `page` for the main page. The default preserves unlisted controls. Set `replace=true` to clear them. Use `action_name` or an installed action UUID to place a new control, settings to patch an existing one, `image_path` to choose a local icon, and `null` to remove a listed control. Set `state_index` when changing an icon on a multi-state key. To place an Action Flow in a layout, use `flow_steps` and `flow_title`. Flow steps can use installed actions or existing controls from the source page, even when replacing that page. Scene copies do not inherit the source scene's automatic application switching rules.

## Optional HTTP and Windows executable

Run `streonor-mcp --http` to bind only to `http://127.0.0.1:29606/mcp`. Configure the Bearer token from the MCP data directory's `token.txt`. Keep it secret. Do not expose this port publicly. use stdio for the easiest local setup.

Build a Windows executable with `pyinstaller STREONOR-MCP.spec` after installing PyInstaller separately. Existing `install.ps1` and `setup.cmd` install the executable, Windows sign-in shortcut and HTTP Codex entry. That installer is Windows-only. The portable Python package needs no startup service. The existing installer does not overwrite a pre-existing `streonor` client entry.

## Development and community devices

```sh
python -m pip install -e .
python -m unittest discover -s tests
streonor-mcp --version
```

CI runs on Windows, macOS and Linux with Python 3.12/3.13. A CI configuration is not evidence that all hosted jobs or hardware tests have run.

Add hardware metadata in `streonor_mcp/devices.py`. leave unknown capabilities unset. Keep generic profile/image logic reusable, platform paths in `paths.py`, and lifecycle handling in `app.py`. See [CONTRIBUTING.md](../CONTRIBUTING.md), [SECURITY.md](../SECURITY.md) and [CHANGELOG.md](../CHANGELOG.md). Never add undocumented USB writes or commit personal profiles/tokens.

File safety limits: manifests are capped at 32 MiB, icon inputs at 16 MiB and 16 million pixels. Non-finite JSON numbers are rejected. Icon and boot-artwork preparation refuse to overwrite existing outputs. Profile-root locks serialize cooperating MCP clients on the same local filesystem. they do not lock the vendor app or arbitrary editors. Atomic replacement still has a small race with unrelated writers. Backups should be retained according to your own policy. no automatic pruning removes them.

## Scene management

`preview_scene_creation` and `create_scene` create blank scenes or copy selected source controls with `include_coordinates`. `preview_scene_change` and `apply_scene_change` rename or delete a registered scene. Rename/delete require both the manifest and registry hashes. Scene deletion archives the full scene folder and backs up the catalog. The last scene for a device cannot be deleted.

## Icon backgrounds

`prepare_icon` accepts `background_color` as a hex RGB color such as `#000000`. Optional `replace_edge_background=true` recolors the area connected to the top-left pixel with tolerance 24. Keep this false when you only want to flatten transparency. Both options produce a new 1254 x 1254 PNG and preserve the original input.

## Automatic icons

New actions and flows have automatic icons by default. Destination changes also refresh their matching icon. Existing custom template icons are preserved unless an icon query requests a replacement. Explicit images take priority. Then installed application images and exact icon-pack matches are considered. If no local match exists, a black label icon is generated. No network requests occur. auto_icon=false disables automatic assignment. clear_icon removes an existing image. Previews disclose origin and image hash. Pass expected_auto_icon_sha256 when pinning that choice across preview/apply.

## Name-based actions and hotkeys

create_by_name takes action_name as an installed name, qualified plugin/name or exact UUID. action_settings is optional. Unknown settings have no published schema and require verification in the native app. configure_action accepts a complete replacement settings object with that limitation. Controller restrictions and flow-only items are enforced. Flow steps can use action_name instead of source_coordinate, and native Hotkey steps accept a hotkey chord such as Ctrl+Shift+P. Modifiers and delays are independent per step.

To put one chord on a key, use `create_by_name` with the native Hotkey action and `hotkey="Ctrl+Shift+P"`. To add multiple chords or delays, use `set_flow`.

## Restore controls from a backup

Use the backup filename returned by a profile edit. Preview it for the same scene and page, review the changed coordinates, and pass both hashes to `restore_controls`. The current controls are backed up before the restore. Backups created before scene and page identifiers were included in their filenames require manual recovery.

## Change the boot logo

Use `prepare_boot_logo` to make a 320 × 240 PNG for the S6 Mini. Choose `fit="cover"` to fill the frame or `fit="contain"` to keep the entire image with black padding. In STREONOR, open **Setting → Device** and select **Replace the boot logo (Resolution 320*240)**. Choose the prepared PNG. The MCP prepares the image locally. The vendor app applies it to the device.

HotkeySwitch can be created by name with `hotkey` to assign the same chord to both states. Use `state_index` with icon preview and apply operations to select a state. Verify shortcut behavior in the vendor app.
