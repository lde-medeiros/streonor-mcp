# STREONOR MCP

Experimental Windows MCP integration for STREONOR's own stream controller app. S6 Mini is the first device under investigation. This community project is not affiliated with STREONOR.

**Status: early prototype, not a finished installer or live integration.** The current MCP tools can list and read STREONOR profiles and preview a change to an existing action setting. An offline edit mechanism has been tested with simulated files and with one approved, temporary change to an S6 website action; the user confirmed the change appeared in STREONOR and the original value was restored. Do not rely on it without a backup and explicit approval. It cannot yet add or delete actions, edit icons, create profiles, or update the running app live.

STREONOR stores profiles under `%APPDATA%\HotSpot\StreamDock\profiles`. `preview_setting_change` identifies the previous and new values and hashes the file. `apply_setting_change` requires STREONOR to be closed, checks the hash, creates a backup under `%LOCALAPPDATA%\STREONOR-MCP\backups`, and replaces the manifest. Closing the app avoids its in-memory data overwriting external changes, but does not eliminate a race if the app starts during the operation. Never assume an unknown setting is safe to edit. Reopen STREONOR to check the result. Do not use this mechanism for unattended edits.

Tools: `list_profiles`, `read_profile`, `preview_setting_change`, and `apply_setting_change`. Only existing settings of matching JSON type are accepted. Exact supported device and action behavior is not yet verified. The MCP server does not control USB hardware and can run with STREONOR open for reading.

## Developer setup

Install Python 3.12+ on Windows, then create a virtual environment and install `requirements.txt`. Run `python run.py --http` for a localhost-only MCP endpoint at `http://127.0.0.1:29606/mcp`. Its bearer token is created in `%LOCALAPPDATA%\STREONOR-MCP\token.txt`. Keep it secret and connect only trusted clients: they can read profile contents and request changes. For stdio run `python -m streonor_mcp.server` instead. Do not run more than one server on the same port.

Run simulated tests with `python -m unittest discover -s tests`. `tests/smoke_http.py` tests a running HTTP server without changing profiles.

## Next steps

Investigate the [StreamDock plugin SDK](https://github.com/MiraboxSpace/StreamDock-Plugin-SDK) and test whether the STREONOR version allows changes through its running UI. Implement and verify app-visible editing, conflict handling, user approval, and a native installer before calling this complete. Other models need independent testing.

A Windows executable can be built with `pyinstaller STREONOR-MCP.spec`. Place it beside `install.ps1` and `setup.cmd`, then run `setup.cmd` to install the background server and startup shortcut. If Codex is installed, the installer adds its MCP connection unless one named `streonor` already exists. This is an early installer, not a STREONOR app plugin.
