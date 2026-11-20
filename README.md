# STREONOR MCP

An MCP server for managing STREONOR profiles, actions and icons from Claude, Codex and other MCP clients.

- Inspect profiles and installed actions.
- Update key and knob settings with preview checks and automatic backups.
- Add, remove and clone actions from existing templates.
- Build ordered action flows and create blank scenes.
- Prepare square PNG icons and device-sized boot artwork.

**Device support:** S6 Mini on Windows. Profile and image tools also run on macOS and Linux. This is a community project, not an official STREONOR integration.

## Installation

Use `uvx` to fetch the server, a compatible Python runtime and its dependencies automatically. No manual clone, virtual environment or `pip install` is required. The MCP client must be able to run [uv](https://docs.astral.sh/uv/getting-started/installation/). The Git source requires Git and access to this private repository; it will work for other users after the repository is published.

### Claude Code

```sh
claude mcp add --transport stdio --scope user streonor -- uvx --python 3.12 --from git+https://github.com/lde-medeiros/streonor-mcp@v0.4.0 streonor-mcp
```

### Codex

```sh
codex mcp add streonor -- uvx --python 3.12 --from git+https://github.com/lde-medeiros/streonor-mcp@v0.4.0 streonor-mcp
```

### Claude Desktop and other JSON clients

Merge this entry into your MCP configuration:

```json
{
  "mcpServers": {
    "streonor": {
      "command": "uvx",
      "args": [
        "--python", "3.12",
        "--from", "git+https://github.com/lde-medeiros/streonor-mcp@v0.4.0",
        "streonor-mcp"
      ]
    }
  }
}
```

Reload the MCP connection after adding it. If the client cannot find `uvx`, use its absolute path. Pinning the release tag avoids an unexpected upgrade when the client starts. See [uv tool sources](https://docs.astral.sh/uv/guides/tools/) for installation and caching behavior.

The default stdio connection needs no port, token or background service. HTTP remains optional. STREONOR's own app is still required for Windows device operation; MCP does not install or replace the vendor software.

## Usage

Try these prompts:

> List my STREONOR profiles and inspect Development.

> Change Development's Coolify icon to this PNG. Preview the change, back up the profile, and close and reopen STREONOR for the edit.

> Inspect the knobs in Development and preview a change to an existing setting.

The server checks that the profile and source image still match the preview before writing. It serializes cooperating editors, backs up the preceding manifest, and refuses to write while the vendor app is running. On Windows, `manage_app=true` allows the apply tools to close and reopen the app. `force_close=true` additionally permits termination and can discard unsaved app settings.

## Tools

| Tool | Description |
| --- | --- |
| `list_supported_devices` | List known models and verified capabilities |
| `list_available_actions` | List installed plugin action types |
| `list_profiles` | List profiles and pages |
| `read_profile` | Read actions, settings and the profile hash |
| `preview_scene_creation` | Preview a blank scene and check its vendor catalog |
| `create_scene` | Create and register a previewed scene with a catalog backup |
| `find_icons` | Search imported icon packs |
| `prepare_icon` | Create a 1254 x 1254 PNG with transparent padding |
| `prepare_boot_logo` | Prepare artwork at the model's registered dimensions |
| `preview_setting_change` | Preview an existing action setting change |
| `apply_setting_change` | Apply a setting change with a hash check and backup |
| `preview_action_change` | Preview cloning, removal or icon changes |
| `apply_action_change` | Apply an action or icon change with a backup |

## Compatibility

| Feature | Windows | macOS / Linux |
| --- | --- | --- |
| MCP, image preparation and exported profile edits | Supported | Supported |
| Vendor profile discovery | Verified | Configure paths |
| Vendor app restart | Supported | Not implemented |
| S6 Mini hardware | Verified | Not verified |

Only the S6 Mini is hardware-verified. S10 Pro, S15 Standard and S32 Max remain listed as unsupported. This server does not provide direct USB control, firmware updates, boot-logo uploads, page management, arbitrary Toolbox execution or live device event streaming. Edits appear after the vendor app reloads its profile; this is not live editing.

## Configuration

Windows profiles are discovered from the installed app. Set these variables in the MCP client's server environment when using another installation or exported profiles:

| Variable | Purpose |
| --- | --- |
| `STREONOR_PROFILES_DIR` | Directory containing `*.sdProfile` folders |
| `STREONOR_ICONS_DIR` | Imported icon packs |
| `STREONOR_DATA_DIR` | Backups, HTTP token and logs |

Use a local exported copy if the vendor app runs on another OS. Local process checks cannot detect a remote app writing a shared profile. Paths, optional HTTP setup, development installation and Windows builds are covered in the [reference](docs/reference.md).

## Development

```sh
python -m pip install -e .
python -m unittest discover -s tests
```

Tests exercise every MCP tool against disposable fixtures. App lifecycle tests are simulated; they do not certify new hardware. CI covers Windows, macOS and Linux with Python 3.12/3.13.

See [Contributing](CONTRIBUTING.md), [Security](SECURITY.md) and [Changelog](CHANGELOG.md). Device definitions live in `streonor_mcp/devices.py`.

### Ordered flows and scenes

Use `preview_action_change` with `operation="set_flow"`, `flow_title` and `flow_steps`. Each step specifies a same-page `source_coordinate`, optional `settings` overrides matching existing names/types, and `delay_ms` from 0 to 60000. Apply with the same arguments and the preview hash. This replaces the target action in one guarded write. Application launches are requested in order; completion/loading is not awaited.

`preview_scene_creation(source_profile, name)` returns source/catalog hashes. Pass them to `create_scene` to create a blank scene for that device. The observed single-column `Profile` catalog schema is required. Existing scene names are rejected. The app must be closed, or explicitly managed on Windows. A new scene does not inherit automatic app associations. Source profiles are not changed.

See the [capability coverage](docs/capabilities.md) for implemented, tested and unsupported features.
