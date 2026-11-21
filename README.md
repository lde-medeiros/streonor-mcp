# STREONOR MCP

Set up your STREONOR stream controller from Claude or Codex. Build scenes, assign shortcuts, and choose icons by describing what you want.

> “Make a Work scene with buttons for email, calendar, and GitHub. Copy the volume knob from Daily.”

[Get started](#get-started) · [Devices](#devices) · [Examples](docs/examples.md) · [Changelog](CHANGELOG.md)

An independent community project. Unaffiliated with STREONOR.

## Get started

1. Install the STREONOR app on Windows, connect your STREONOR device, and make sure you have [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git. While this repo is private, Git needs access to it.
2. Run the command for your client.

   **Codex**

   ```sh
   codex mcp add streonor -- uvx --python 3.12 --from git+https://github.com/lde-medeiros/streonor-mcp@v0.8.0 streonor-mcp
   ```

   **Claude Code**

   ```sh
   claude mcp add --transport stdio --scope user streonor -- uvx --python 3.12 --from git+https://github.com/lde-medeiros/streonor-mcp@v0.8.0 streonor-mcp
   ```

3. Restart your client and ask: “Use STREONOR MCP to list my scenes.”

[Claude Desktop and other clients](docs/reference.md#connect-claude-or-codex) · [macOS and Linux exported profiles](docs/reference.md#platform-support-and-paths)

## What you can do

- **Build or edit a scene.** Fill a page with app launchers, shortcuts, knobs, or multi-step Action Flows. The MCP previews changes and keeps backups.
- **Give each state its own icon.** Use an installed icon or supply your own, including separate images for a Hotkey Switch.
- **Keep the Windows app open.** Change supported icons in the original S6 Mini scene or import a full layout as a scene copy. Other edits to the original scene use an app restart. [Live editing setup](docs/reference.md#edit-while-streonor-stays-open).

## Devices

The S6 Mini is verified on Windows. Have a different model? Try the setup above and start by listing your scenes. [Share your model and results](CONTRIBUTING.md) to help us document device support.

| Product photo | Model | MCP support |
| --- | --- | --- |
| <img src="https://streonor.net/cdn/shop/files/S6_Mini_Black_White_Website_Main_V3.png?v=1784532906&amp;width=320" alt="STREONOR S6 Mini" width="128"> | **S6 Mini** | Supported and tested on Windows |
| <img src="https://streonor.net/cdn/shop/files/S10_Pro_Black_Website_Main_V2.png?v=1784533717&amp;width=320" alt="STREONOR S10 Pro" width="128"> | S10 Pro | [Contribute today](CONTRIBUTING.md) |
| <img src="https://streonor.net/cdn/shop/files/S15_1.jpg?v=1776650323&amp;width=320" alt="STREONOR S15 Standard" width="128"> | S15 Standard | [Contribute today](CONTRIBUTING.md) |
| <img src="https://streonor.net/cdn/shop/files/32_-2.jpg?v=1794382927&amp;width=320" alt="STREONOR S32 Max" width="128"> | S32 Max | [Contribute today](CONTRIBUTING.md) |

Product photos are served by the [STREONOR storefront](https://streonor.net/).

## Available actions

The MCP creates actions from your installed Toolbox. Ask it to list the actions available on your computer. Some actions need extra plugin settings or connections. Configure Create Folder in the STREONOR app.

<details>
<summary>See the action types found on one installation</summary>

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

</details>

## Learn more

[Example workflows](docs/examples.md) · [Tool reference](docs/reference.md) · [Capability coverage](docs/capabilities.md) · [Contribute](CONTRIBUTING.md)

## License

The original Streonor MCP code and documentation are available under the [MIT License](LICENSE). STREONOR’s name identifies compatible products. The vendor software, trademarks, and linked material belong to their respective owners and are outside the scope of this license.
