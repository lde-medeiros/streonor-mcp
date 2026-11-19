"""Inspect and safely prepare offline edits to STREONOR profile manifests."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

ROOT = Path(os.environ.get('APPDATA', '')) / 'HotSpot' / 'StreamDock' / 'profiles'
BACKUPS = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'STREONOR-MCP' / 'backups'
PROFILE_ID = re.compile(r'^[A-Za-z0-9-]+\.sdProfile$')


def fingerprint(data):
    return hashlib.sha256(data).hexdigest()


def profile_path(profile, page=None, root=ROOT):
    for item in (profile, page):
        if item is not None and not PROFILE_ID.fullmatch(item):
            raise ValueError('Invalid profile or page identifier')
    base = root / profile
    path = (base / 'profiles' / page / 'manifest.json') if page and page != profile else base / 'manifest.json'
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError('Profile path escapes profile directory')
    return resolved


def read_manifest(profile, page=None, root=ROOT):
    path = profile_path(profile, page, root)
    data = path.read_bytes()
    parsed = json.loads(data.decode('utf-8-sig'))
    if not isinstance(parsed, dict) or not isinstance(parsed.get('Actions'), dict):
        raise ValueError('Unrecognized STREONOR manifest')
    return parsed, fingerprint(data)


def list_profiles(root=ROOT):
    result = []
    for manifest in sorted(root.glob('*.sdProfile/manifest.json')):
        try:
            data, digest = read_manifest(manifest.parent.name, root=root)
            result.append({'id': manifest.parent.name, 'name': data.get('Name'), 'device': data.get('DeviceUUID'), 'pages': data.get('Pages'), 'sha256': digest})
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return result


def prepare(profile, page, coordinate, setting, new_value, root=ROOT):
    doc, digest = read_manifest(profile, page, root)
    action = doc['Actions'].get(coordinate)
    if not isinstance(action, dict):
        raise ValueError('No action exists at that coordinate')
    settings = action.get('Settings')
    if not isinstance(settings, dict) or setting not in settings:
        raise ValueError('Setting does not exist on this action')
    old = settings[setting]
    if type(old) is not type(new_value):
        raise ValueError('New value must have the same JSON type as the existing value')
    return {'profile': profile, 'page': page, 'coordinate': coordinate, 'action': action.get('Name'), 'uuid': action.get('UUID'), 'setting': setting, 'old_value': old, 'new_value': new_value, 'sha256': digest}


def vendor_running():
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Streonor.exe', '/NH'], capture_output=True, text=True, timeout=5, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), check=True)
    return 'streonor.exe' in result.stdout.lower()


def apply(profile, page, coordinate, setting, new_value, expected_sha256, root=ROOT, backups=BACKUPS):
    if vendor_running():
        raise RuntimeError('Quit STREONOR completely before editing profiles; it can overwrite external changes.')
    preview = prepare(profile, page, coordinate, setting, new_value, root)
    if preview['sha256'] != expected_sha256:
        raise ValueError('Profile changed since preview; inspect and preview again')
    path = profile_path(profile, page, root)
    original = path.read_bytes()
    if fingerprint(original) != expected_sha256:
        raise ValueError('Profile changed while preparing edit')
    doc = json.loads(original.decode('utf-8-sig'))
    doc['Actions'][coordinate]['Settings'][setting] = new_value
    encoded = (json.dumps(doc, indent=4, ensure_ascii=False) + '\n').encode('utf-8')
    backups.mkdir(parents=True, exist_ok=True)
    backup = backups / f'{profile}-{time.time_ns()}.json'
    with backup.open('xb') as f:
        f.write(original)
        f.flush()
        os.fsync(f.fileno())
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.streonor-mcp-', delete=False) as f:
            temp = Path(f.name)
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
        if vendor_running() or fingerprint(path.read_bytes()) != expected_sha256:
            raise RuntimeError('STREONOR started or the profile changed during the edit; no change was applied.')
        os.replace(temp, path)
        temp = None
    finally:
        if temp:
            temp.unlink(missing_ok=True)
    return {'updated': True, 'backup': str(backup), 'new_sha256': fingerprint(encoded), 'reopen_app': True}
