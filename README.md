# STREONOR MCP

A native Windows MCP server for controlling a STREONOR stream controller. Currently supported: **S6 Mini** (VID 1500, PID 3006). This is an independent community project, not affiliated with STREONOR.

The server owns the S6 USB interface and executes assigned Windows hotkeys, opens files/apps or URLs when physical keys, scene buttons, and dial controls are used. An MCP client can list, set and remove assignments and inspect the latest input. LCD keys show a label or a supplied image. Assignments are stored in `%LOCALAPPDATA%\STREONOR-MCP\actions.json`; they are separate from STREONOR's own profiles. No firmware or boot logo is modified.

**Early development:** S6 protocol and mappings are based on hardware observed during earlier DeckBridge testing. This implementation has not yet been validated end to end. Quit STREONOR and any other controller software before connecting; only one program should control the device.

## Setup

Requires Windows 10/11, Python 3.12 or newer and a USB-connected S6 Mini. Run `py -m venv .venv` and `.venv\Scripts\python.exe -m pip install -r requirements.txt` from this folder. Connect an MCP client using stdio, with the working directory set to this project folder:

```json
{"command":"C:\\path\\to\\streonor-mcp\\.venv\\Scripts\\python.exe","args":["-m","streonor_mcp.server"],"cwd":"C:\\path\\to\\streonor-mcp"}
```

The MCP client must keep the server running for buttons to work; reconnecting the client restarts it. It automatically reconnects after USB disconnection. Do not run multiple copies. On opening, the device's current on-screen images are replaced for the session. Close the MCP server before opening STREONOR software again.

Tools: `device_status`, `list_assignments`, `set_assignment`, `remove_assignment`. Example: set `control=key1`, `event=press`, `action_type=hotkey`, `value=ctrl+shift+s`, `label=Save`. For dial rotation use `control=dial1`, `event=left` or `right`; for dial clicks use `press`. Numbers run left to right, top to bottom for keys. Example media shortcuts: `volumeup`, `volumedown`, `mute`, `playpause`.

The server runs with your Windows account's permissions; only connect trusted MCP clients. `open` may launch executable files. The server cannot edit STREONOR software profiles, run its plugins, or make its UI display these assignments.

Run tests with `.venv\Scripts\python.exe -m unittest discover -s tests`.

## Protocol sources

S6 input mappings and orientation were captured in prior tests. CRT packets are based on [EspUsbHost's MacroPadN3 example](https://github.com/tanakamasayuki/EspUsbHost/tree/main/examples/HID/EspUsbHostMacroPadN3) and the [DeckBridge Mirabox driver](https://github.com/lukasMega/DeckBridge/blob/main/ts/src/devices/mirabox/protocol.ts). Other models require separate validation.
