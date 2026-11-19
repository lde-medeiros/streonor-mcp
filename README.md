# STREONOR MCP

Community Windows MCP integration for STREONOR controller profiles. The repository lists the S6 Mini, S10 Pro, S15 Standard, and S32 Max; only the S6 Mini is currently supported. This community project is not affiliated with STREONOR.

**Status: release candidate for profile inspection and offline edits.** MCP can discover installed actions, inspect profiles, preview edits, change existing action settings, create an action from an installed action template, remove actions, and set or clear icons. Changes are written to the app's profile files and appear after reopening STREONOR. This is not an official STREONOR plugin and cannot update the running app live. Profile creation, deletion, page management, and live Toolbox invocation are not supported. Action templates must already exist in a profile; use the app to add an action type once, then MCP can clone/configure it.

STREONOR stores profiles under `%APPDATA%\HotSpot\StreamDock\profiles`. `preview_setting_change` identifies the previous and new values and hashes the file. `apply_setting_change` requires STREONOR to be closed, checks the hash, creates a backup under `%LOCALAPPDATA%\STREONOR-MCP\backups`, and replaces the manifest. Closing the app avoids its in-memory data overwriting external changes, but does not eliminate a race if the app starts during the operation. Unknown action settings remain editable only when the JSON value type matches. Every edit makes a timestamped manifest backup. Reopen STREONOR to check changes.

Tools: `list_supported_devices`, `prepare_boot_logo`, `list_available_actions`, `list_profiles`, `read_profile`, `find_icons`, `preview_setting_change`, `apply_setting_change`, `preview_action_change`, and `apply_action_change`. Icon inputs accept PNG, JPEG, BMP, GIF, and WebP from this PC; image data is normalized to PNG. Imported app PNG icons can be reused by selecting the exact file from that profile’s `Images` folder. `find_icons` searches imported icon packs.

## Developer setup

Install Python 3.12+ on Windows, then create a virtual environment and install `requirements.txt`. Run `python run.py --http` for a localhost-only MCP endpoint at `http://127.0.0.1:29606/mcp`. Its bearer token is created in `%LOCALAPPDATA%\STREONOR-MCP\token.txt`. Keep it secret and connect only trusted clients: they can read profile contents and request changes. For stdio run `python -m streonor_mcp.server` instead. Do not run more than one server on the same port.

Run simulated tests with `python -m unittest discover -s tests`. `tests/smoke_http.py` tests a running HTTP server without changing profiles.

A Windows executable can be built with `pyinstaller STREONOR-MCP.spec`. Place it beside `install.ps1` and `setup.cmd`, then run `setup.cmd` to install the background server and startup shortcut. If Codex is installed, the installer adds its MCP connection unless one named `streonor` already exists. The installer starts the local server at Windows sign-in. Restart Codex after installation to load the MCP tools.

## Add a device

Hardware specs live in one place: `streonor_mcp/devices.py`. Add a `DeviceSpec` entry with its stable project ID, display name, STREONOR software device IDs, key and dial counts, and known boot-logo dimensions/format/upload method. Use `None` or `unknown` for facts that have not been verified. Shared profile/action/icon operations discover and edit profiles generically; do not add a model-specific copy of those tools. If a model uses a different profile format or needs direct HID support, add a separate adapter module and tests while keeping it isolated from generic profile handling. Never put an undocumented device-write command in the registry.
