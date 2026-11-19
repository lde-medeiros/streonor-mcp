import ctypes
import json
import logging
import os
from pathlib import Path
import threading
import time
import webbrowser

import hid
from mcp.server.fastmcp import FastMCP
from .device import PID, VID, S6, make_image, packet

log = logging.getLogger('streonor-mcp')
DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'STREONOR-MCP'
CONFIG = DATA / 'actions.json'
lock = threading.RLock()
config = {}
status = {'connected': False, 'error': None, 'last_event': None}
redraw = threading.Event()
stop = threading.Event()


def load():
    global config
    if CONFIG.exists():
        with CONFIG.open(encoding='utf-8') as f:
            config = json.load(f)
        if not isinstance(config, dict):
            raise ValueError('The actions file must contain an object')


def save():
    DATA.mkdir(parents=True, exist_ok=True)
    temp = CONFIG.with_suffix('.tmp')
    with temp.open('w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    os.replace(temp, CONFIG)


def validate_control(control, event):
    controls = [f'key{i}' for i in range(1, 7)] + [f'scene{i}' for i in range(1, 4)] + [f'dial{i}' for i in range(1, 4)]
    if control not in controls:
        raise ValueError('Control must be key1–key6, scene1–scene3, or dial1–dial3')
    if event not in (('press', 'left', 'right') if control.startswith('dial') else ('press',)):
        raise ValueError('Use press, or left/right for a dial')


def shortcut(value):
    names = {'ctrl': 0x11, 'shift': 0x10, 'alt': 0x12, 'win': 0x5b, 'enter': 0x0d, 'tab': 0x09, 'space': 0x20, 'escape': 0x1b, 'backspace': 0x08, 'delete': 0x2e, 'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27, 'volumeup': 0xaf, 'volumedown': 0xae, 'mute': 0xad, 'playpause': 0xb3}
    keys = []
    for part in value.lower().split('+'):
        part = part.strip()
        if part in names:
            keys.append(names[part])
        elif len(part) == 1 and part.isascii() and part.isalnum():
            keys.append(ord(part.upper()))
        elif part.startswith('f') and part[1:].isdigit() and 1 <= int(part[1:]) <= 24:
            keys.append(0x6f + int(part[1:]))
        else:
            raise ValueError(f'Unsupported hotkey: {part}')
    if not keys or len(keys) > 5 or len(set(keys)) != len(keys):
        raise ValueError('Use one to five distinct hotkeys')
    return keys


def execute(action):
    kind, value = action.get('type'), action.get('value', '')
    if kind == 'hotkey':
        keys = shortcut(value)
        try:
            for key in keys:
                ctypes.windll.user32.keybd_event(key, 0, 0, 0)
        finally:
            for key in reversed(keys):
                ctypes.windll.user32.keybd_event(key, 0, 2, 0)
    elif kind == 'open':
        os.startfile(value)
    elif kind == 'url':
        webbrowser.open(value)


def run_device():
    while not stop.is_set():
        device = None
        try:
            infos = [d for d in hid.enumerate(VID, PID) if d.get('usage_page') == 0xffa0 and d.get('usage') == 1]
            if not infos:
                with lock:
                    status.update(connected=False, error='S6 Mini not found; connect it to Windows.')
                stop.wait(2)
                continue
            device = S6(infos[0])
            with lock:
                status.update(connected=True, error=None)
            redraw.set()
            heartbeat = time.monotonic()
            while not stop.is_set():
                if redraw.is_set():
                    redraw.clear()
                    with lock:
                        keys = [dict(config.get(f'key{i}:press', {})) for i in range(1, 7)]
                    for i, action in enumerate(keys, 1):
                        device.image(i, make_image(action.get('label', ''), action.get('color', '#202838'), action.get('image_path', '')))
                if time.monotonic() - heartbeat >= 5:
                    device.send(packet('CONNECT'))
                    heartbeat = time.monotonic()
                event = device.read()
                if event:
                    control, kind = event
                    with lock:
                        status['last_event'] = {'control': control, 'event': kind}
                        action = dict(config.get(f'{control}:{kind}', {}))
                    if action:
                        try:
                            execute(action)
                        except Exception as exc:
                            with lock:
                                status['error'] = f'Action failed: {exc}'
                            log.exception('Action failed')
        except Exception as exc:
            with lock:
                status.update(connected=False, error=str(exc))
            log.exception('S6 connection failed')
            stop.wait(2)
        finally:
            if device:
                device.close()


mcp = FastMCP('STREONOR MCP')

@mcp.tool()
def device_status() -> dict:
    """Show connection status and the most recent physical control event."""
    with lock:
        return dict(status)

@mcp.tool()
def list_assignments() -> dict:
    """List assignments. Controls: key1–key6, scene1–scene3, dial1–dial3."""
    with lock:
        return dict(config)

@mcp.tool()
def set_assignment(control: str, event: str, action_type: str, value: str, label: str = '', color: str = '#202838', image_path: str = '') -> dict:
    """Assign a Windows hotkey, file/app, or URL. Dials support press, left and right; keys and scenes support press. image_path is optional and used for LCD keys."""
    validate_control(control, event)
    if action_type not in ('hotkey', 'open', 'url'):
        raise ValueError('action_type must be hotkey, open, or url')
    if not value or len(value) > 2048 or len(label) > 32:
        raise ValueError('Value is required and label must be at most 32 characters')
    if action_type == 'hotkey':
        shortcut(value)
    if action_type == 'url' and not value.lower().startswith(('https://', 'http://')):
        raise ValueError('URLs must begin with http:// or https://')
    if action_type == 'open' and not Path(value).is_file():
        raise ValueError('File or app does not exist')
    if control.startswith('key'):
        make_image(label, color, image_path)
    action = {'type': action_type, 'value': value, 'label': label, 'color': color, 'image_path': image_path}
    with lock:
        previous = config.get(f'{control}:{event}')
        config[f'{control}:{event}'] = action
        try:
            save()
        except Exception:
            if previous is None:
                config.pop(f'{control}:{event}', None)
            else:
                config[f'{control}:{event}'] = previous
            raise
    redraw.set()
    return {'control': control, 'event': event, 'action': action}

@mcp.tool()
def remove_assignment(control: str, event: str) -> dict:
    """Remove an assignment and clear its LCD label if applicable."""
    validate_control(control, event)
    with lock:
        previous = config.pop(f'{control}:{event}', None)
        try:
            save()
        except Exception:
            if previous is not None:
                config[f'{control}:{event}'] = previous
            raise
    redraw.set()
    return {'removed': previous is not None}


def main():
    logging.basicConfig(level=logging.INFO)
    load()
    thread = threading.Thread(target=run_device, daemon=True)
    thread.start()
    try:
        mcp.run(transport='stdio')
    finally:
        stop.set()
        thread.join(timeout=3)

if __name__ == '__main__':
    main()
