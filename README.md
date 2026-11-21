# STREONOR MCP

Control STREONOR profiles from Claude, Codex and other MCP clients.

Create scenes, build button flows, change knob settings, and add icons using natural-language requests. Changes are previewed and backed up before they are saved. This is a community project, not an official STREONOR integration.

## Devices

| Device | Model | MCP support |
| --- | --- | --- |
| <img src="https://streonor.net/cdn/shop/files/3.jpg?v=1777519053&width=280" alt="STREONOR S6 Mini" width="140"> | **S6 Mini** | Supported and tested on Windows |
| <img src="https://streonor.net/cdn/shop/files/S10_2.jpg?v=1777519449&width=280" alt="STREONOR S10 Pro" width="140"> | S10 Pro | Not supported yet |
| <img src="https://streonor.net/cdn/shop/files/S15_2.jpg?v=1776650324&width=280" alt="STREONOR S15 Standard" width="140"> | S15 Standard | Not supported yet |
| <img src="https://streonor.net/cdn/shop/files/32_-2.jpg?v=1794382927&width=280" alt="STREONOR S32 Max" width="140"> | S32 Max | Not supported yet |

Product images and model names: [STREONOR](https://streonor.net/). Images belong to their respective owner. Listing a model does not imply hardware compatibility.

## Get started

First, install the STREONOR app and connect your device. Then add this MCP connection to your AI app. You can ask your coding assistant to run the matching command below for you.

The commands download STREONOR MCP and its Python dependencies automatically. You need [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git available to your client. No manual clone, virtual environment or pip setup is needed. GitHub access is required while this repository is private.

**Claude Code**

```sh
claude mcp add --transport stdio --scope user streonor -- uvx --python 3.12 --from git+https://github.com/lde-medeiros/streonor-mcp@v0.6.0 streonor-mcp
```

**Codex**

```sh
codex mcp add streonor -- uvx --python 3.12 --from git+https://github.com/lde-medeiros/streonor-mcp@v0.6.0 streonor-mcp
```

**Claude Desktop or another JSON client**

```json
{
  "mcpServers": {
    "streonor": {
      "command": "uvx",
      "args": ["--python", "3.12", "--from", "git+https://github.com/lde-medeiros/streonor-mcp@v0.6.0", "streonor-mcp"]
    }
  }
}
```

Merge the entry into your existing configuration, then reload the MCP connection. If the client cannot find `uvx`, use its absolute path. STREONOR's own app is still needed to operate the device.

## Everyday examples

**Create a work setup**

> “Make a Work scene with buttons for my email, calendar and GitHub. Copy my volume knob from Daily.”

> “Add a Calculator button in the empty top-right position.”

**Check your setup**

> “Show me what each Work button and knob does before changing anything.”

**Update a shortcut**

> “Change the GitHub button to open my project's issues page. Keep its black background.”

> “Make Start Coding open VS Code, wait half a second, then open Terminal.”

**Build a hotkey sequence**

> “Make a button that copies the selected text, switches to the previous app, and pastes it. Add a short pause between steps.”

**Remove what you no longer use**

> “Remove the test flow and its knob assignment. Leave my volume knob alone.”

> “Delete the Weekend scene. Keep a backup.”

New shortcuts get matching icons by default. MCP checks installed app images and icon packs first. If no match is available, it creates a simple label icon. You do not need to ask for an icon separately. You can supply your own image or ask for no icon.

See [everyday workflows](docs/examples.md) for what the agent does behind these requests.

## How changes work

The agent reads the target, previews the change, and applies it using the returned hashes. STREONOR must close while its profiles are edited. On Windows, the agent can request `manage_app=true` to close and reopen it. Force closing additionally requires `force_close=true` and may discard unsaved app settings.

Scene deletion removes the scene from the app and retains its folder and catalog backup. Other profile edits retain manifest backups. Icons are saved as **1254 × 1254 square PNGs**. This release does not update the app live.

## Platforms and limits

- **Windows:** S6 Mini profiles, app restart and hardware behavior tested.
- **macOS/Linux:** MCP, image tools and exported-profile editing tested in CI. Native device operation and app restart are unverified or unsupported. Configure profile paths when needed.
- Installed Toolbox actions can be added by name or UUID. Some still need a URL, file path, plugin connection or other settings before they work. Name-based creation does not mean every plugin has been execution-tested. Selected controls can be copied into a new scene.
- Direct USB control, firmware updates, boot-logo uploading, page management and live device events are not implemented.

[Tool and configuration reference](docs/reference.md) · [Examples](docs/examples.md) · [Capability coverage](docs/capabilities.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md)
