<h1 align="center">STREONOR MCP</h1>

<p align="center">
  <strong>Set up your STREONOR stream controller from Claude or Codex.</strong><br>
  A local Model Context Protocol server for scenes, shortcuts, knobs, and icons.
</p>

<p align="center">
  <a href="#highlights">Highlights</a> ·
  <a href="#get-started">Get started</a> ·
  <a href="#everyday-examples">Examples</a> ·
  <a href="#available-actions">Actions</a> ·
  <a href="#devices">Devices</a> ·
  <a href="#whats-next">What’s next</a> ·
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

> “Make a Work scene with buttons for my email, calendar and GitHub. Copy my volume knob from Daily.”

STREONOR MCP is an independent community project. It has no affiliation with, sponsorship from, or endorsement by STREONOR.

## Highlights

- **Build a scene for the way you work.** Start empty or copy selected buttons, knobs, and flows from an existing scene.
- **Put a sequence on one key.** Combine installed Toolbox actions and hotkeys with delays between steps.
- **Give shortcuts matching icons.** Use an imported asset, supply your own image, or let the server generate a label.
- **Review changes before applying them.** Inspect the target, preview the edit, and keep a backup when it is applied.

## Get started

First, install the STREONOR app and connect your device. Then add this MCP connection to your AI app. You can ask your coding assistant to run the matching command below for you.

The commands download STREONOR MCP and its Python dependencies automatically. You need [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git available to your client. No manual clone, virtual environment or pip setup is needed. If GitHub prompts you to sign in, authenticate Git before running the setup command.

**Claude Code**

```sh
claude mcp add --transport stdio --scope user streonor -- uvx --python 3.12 --from git+https://github.com/lde-medeiros/streonor-mcp@v0.7.1 streonor-mcp
```

**Codex**

```sh
codex mcp add streonor -- uvx --python 3.12 --from git+https://github.com/lde-medeiros/streonor-mcp@v0.7.1 streonor-mcp
```

**Claude Desktop or another JSON client**

```json
{
  "mcpServers": {
    "streonor": {
      "command": "uvx",
      "args": ["--python", "3.12", "--from", "git+https://github.com/lde-medeiros/streonor-mcp@v0.7.1", "streonor-mcp"]
    }
  }
}
```

Merge the entry into your existing configuration, then reload the MCP connection. If the client cannot find `uvx`, use its absolute path. STREONOR's own app is still needed to operate the device.

## Everyday examples

**Create a work setup**

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

## Available actions

The MCP can create actions from the Toolbox plugins installed on your computer using their name or UUID. The following actions were discovered in one installation. Your list depends on the plugins you have installed. Use `list_available_actions` to see your current choices.

Some actions require plugin-specific settings, connections, or a compatible controller. Creation does not verify that every action executes successfully. Create Folder must be configured in the STREONOR app.

| Plugin | Action types |
| --- | --- |
| Brightness | Brightness, devsleep |
| Browser | Back, Collect, Forward, Refresh |
| Calendario | Calendario |
| close | Close |
| ETS2 Hotkey | Boosting Speed, Cruise Control, Double Flashing Light, Downshift, Flashing Headlights, Handbrake, Headlight, High Beam, Horns, Ignition/Shutdown, Left Turn Signal, Reduce Speed, Right Turn Signal, Upshift, Windshield Wiper |
| Go back | Go back |
| Hotkey | Hotkey |
| HotkeySwitch | HotkeySwitch |
| K1ProLEDLight | LED-, LED+, LEDMODECHANGE, LEDSPEED-, LEDSPEED+, WinqMac |
| KnobOperatingGroup | KnobOperatingGroup |
| Mouse event | Mouse event |
| Multi Action | Delay, Multi Action, Multi Action ActionTrigger, Multi Action ActionWheel, Multi Action LunBo, Multi Action Toggle |
| Multimedia | Multimedia, SystemVolume |
| musicalrhythm | 图谱1, 图谱2, 图谱3, 图谱4, 图谱5 |
| Network | UDP |
| OBS Studio | Audio Mixer, Record, Scene, Screenshot, Source Visibility, Stream, Studio Mode, Transition, Virtual camera, 绿幕背景图 DN, 绿幕背景图 UP |
| OBS Tool | Browser Source, CPU Usage, Dropped Frames, Filter Switch, Image Settings, Input Monitor Settings, Input Mute Toggle, Input Volume, Input Volume Control, Input Volume Settings, Instant Replay, Next Scene, Previous Scene, Remote Recording Start/Stop/Pause, Remote Streaming Start/Stop, Scene Switcher, Set Profile, Set Scene Collection, Set Transition, Source Animation, Source Visibility, Studio Mode Toggle, Video Playback, Virtual Camera |
| Open | Open, OpenApps |
| Pages | change page, Go to page, Next page, Page Indicator, Previous page |
| Password | Password |
| Quick Control | Calculator, Control panel, Display desktop, Emoticons, Home page, Increase the volume, Lower the volume, Mail, Microphone, Music, Mute, Notification, Search bar, Sleep, Speech recognition, Switch screen, Task Manager |
| Scene Shift | Scene Shift |
| Soundboard | Play Audio, Stop Audio |
| Super Hotkeys | Super Hotkeys |
| Text | Text |
| Time Options | Countdown, Timer, World Time |
| Touchbar | Decrease screen brightness, Desktop Saver, Dictation, Dispatch Center, DND Mode, Fast Forward, Fast Rewind, Focus On Search, Increase screen brightness, Input Method, Launchpad, Mute, Next Track, Notification Center, Play/Pause, Previous Track, Screen brightness, Screen Lock, Screenshot, Show Desktop, Siri, Sleep, Volume, Volume down, Volume up |
| Useful notes | Record to-do, Remember things |
| Visual Studio Code | Change Language, Create Terminal, Execute Command, Execute Terminal Command, Insert Snippet, Open Folder |
| vMix | Shortcut |
| Weather query | Weather query |
| Website | Website |
| YouTube | Chat Message, Viewers |

## How changes work

The agent reads the target, previews the change, and applies it using the returned hashes.

- **Windows live scene copies (unreleased):** Update an action, setting, or icon while STREONOR stays open. Fill an entire page or edit several pages in one import. Open the new scene by its name in STREONOR. [Live editing workflow](docs/reference.md#edit-while-streonor-stays-open).
- **Windows live in-place icon edit (unreleased):** Set or reset keypad and Scene Shift icons on the selected S6 Mini scene and keep its name and ID. [Setup and supported controls](docs/reference.md#edit-while-streonor-stays-open).
- **Other in-place edits:** Close STREONOR first or request `manage_app=true` on Windows to close and reopen it. Use `force_close=true` only if you accept losing unsaved app settings.

In-place edits retain backups. Scene deletion retains the scene folder and catalog backup. Icons are saved as **1254 × 1254 square PNGs**.

## Devices

| Product photo | Model | MCP support |
| --- | --- | --- |
| [View photo](https://streonor.net/cdn/shop/files/S6_Mini_Black_White_Website_Main_V3.png?v=1784532906&width=320) | **S6 Mini** | Supported and tested on Windows |
| [View photo](https://streonor.net/cdn/shop/files/S10_Pro_Black_Website_Main_V2.png?v=1784533717&width=320) | S10 Pro | [Contribute today](CONTRIBUTING.md) |
| [View photo](https://streonor.net/cdn/shop/files/S15_1.jpg?v=1776650323&width=320) | S15 Standard | [Contribute today](CONTRIBUTING.md) |
| [View photo](https://streonor.net/cdn/shop/files/32_-2.jpg?v=1794382927&width=320) | S32 Max | [Contribute today](CONTRIBUTING.md) |

Product photo links open the [STREONOR storefront’s](https://streonor.net/) image files.

## Platforms and limits

- **Windows:** S6 Mini profiles, app restart and hardware behavior tested.
- **macOS/Linux:** MCP, image tools and exported-profile editing tested in CI. Native device operation and app restart are unverified or unsupported. Configure profile paths when needed.
- Installed Toolbox actions can be added by name or UUID. Some still need a URL, file path, plugin connection or other settings before they work. Name-based creation does not mean every plugin has been execution-tested. Selected controls can be copied into a new scene.
- Direct USB control, firmware updates, boot-logo uploading from MCP, page creation and deletion, and live device events are not implemented.

## What's next

- Create folders and pages, and move controls between pages.
- Export native scene files and investigate in-place live editing.
- Verify common Toolbox workflows and document additional device support with contributor testing.

## Project links

[Tool and configuration reference](docs/reference.md) · [Examples](docs/examples.md) · [Capability coverage](docs/capabilities.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md)

## License

The original Streonor MCP code and documentation are available under the [MIT License](LICENSE). STREONOR’s name identifies compatible products. The vendor software, trademarks, and linked material belong to their respective owners and are outside the scope of this license.
