# STREONOR MCP

Community MCP tools for STREONOR profiles, actions, knobs and icons. Use the same local server with Claude, Codex, or another MCP client. Not affiliated with STREONOR.

**S6 Mini is the only hardware-verified device.** S10 Pro, S15 Standard and S32 Max are listed as unsupported. The server runs on Windows, macOS and Linux; hardware and vendor app integration have only been tested on Windows.

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

The installed entry point is `.venv\Scripts\streonor-mcp.exe` on Windows and `.venv/bin/streonor-mcp` on macOS/Linux. Use its **absolute path** in clients so no shell activation or working directory is required. No PyPI release is published; `pip install streonor-mcp` is not the setup instruction yet.

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

Windows defaults to `%APPDATA%\HotSpot\StreamDock\profiles` and `%LOCALAPPDATA%\STREONOR-MCP`. On macOS the MCP data default is `~/Library/Application Support/STREONOR-MCP`; on Linux it is `$XDG_DATA_HOME/STREONOR-MCP` or `~/.local/share/STREONOR-MCP`. Non-Windows profiles default to a separate `vendor/profiles` directory under MCP data. These are workspace defaults, not claims about vendor installation layouts. Point `STREONOR_PROFILES_DIR` at an exported copy or a verified installation.

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

| Tool | Purpose |
| --- | --- |
| `list_supported_devices` | Device registry and known capabilities |
| `list_available_actions` | Installed plugin action types, including knob actions |
| `list_profiles`, `read_profile` | Profiles, pages, settings and current content hash |
| `find_icons` | Search imported icon packs (SVG listing only) |
| `prepare_icon` | Create a 1254 x 1254 PNG without editing a profile |
| `prepare_boot_logo` | Prepare model-sized artwork; does not upload to device |
| `preview_setting_change`, `apply_setting_change` | Guarded changes to existing settings |
| `preview_action_change`, `apply_action_change` | Clone/remove actions and set/clear icons |

Read the intended profile and page, preview the edit, then pass the returned hash to the matching apply tool. Every profile write creates a backup. The app must be closed for writes; the UI updates after reopening. Windows apply tools accept `manage_app=true` to handle closing and reopening. If the app stays in the tray, explicit `force_close=true` permits termination and may discard unsaved settings. A changed hash still blocks the edit; inspect and preview again. This is editing with an app restart, not live editing.

Actions can be cloned only from an existing action on that page. Knob settings are editable where present in the vendor profile. Profile/page creation, deletion, live event streaming and invoking arbitrary Toolbox actions are not implemented. Unknown settings require the same JSON type as their existing value.

Imported PNG/JPEG/BMP/GIF/WebP icons become exactly **1254 x 1254 pixels, 1:1, PNG**, with transparent padding, preserved proportions and no cropping. The first frame of animated inputs is used. Small source images are enlarged without adding detail. Original imported files are preserved. `prepare_icon` refuses to overwrite its output. SVG application is not implemented.

## Optional HTTP and Windows executable

Run `streonor-mcp --http` to bind only to `http://127.0.0.1:29606/mcp`. Configure the Bearer token from the MCP data directory's `token.txt`. Keep it secret. Do not expose this port publicly; use stdio for the easiest local setup.

Build a Windows executable with `pyinstaller STREONOR-MCP.spec` after installing PyInstaller separately. Existing `install.ps1` and `setup.cmd` install the executable, Windows sign-in shortcut and HTTP Codex entry. That installer is Windows-only. The portable Python package needs no startup service. The existing installer does not overwrite a pre-existing `streonor` client entry.

## Development and community devices

```sh
python -m pip install -e .
python -m unittest discover -s tests
streonor-mcp --version
```

CI runs on Windows, macOS and Linux with Python 3.12/3.13. A CI configuration is not evidence that all hosted jobs or hardware tests have run.

Add hardware metadata in `streonor_mcp/devices.py`; leave unknown capabilities unset. Keep generic profile/image logic reusable, platform paths in `paths.py`, and lifecycle handling in `app.py`. See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and [CHANGELOG.md](CHANGELOG.md). Never add undocumented USB writes or commit personal profiles/tokens. The repository remains private until its owner chooses to publish it.
