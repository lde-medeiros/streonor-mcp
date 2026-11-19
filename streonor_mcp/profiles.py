"""Inspect and safely prepare offline edits to STREONOR profile manifests."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from PIL import Image, ImageOps

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


def read_icon(image_path):
    path = Path(image_path)
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError('Icon must be no larger than 16 MiB')
    data = path.read_bytes()
    if len(data) > 16 * 1024 * 1024:
        raise ValueError('Icon must be no larger than 16 MiB')
    with Image.open(io.BytesIO(data)) as image:
        if image.format not in ('PNG', 'JPEG', 'BMP', 'GIF', 'WEBP'):
            raise ValueError('Use a PNG, JPEG, BMP, GIF, or WebP icon')
        image.verify()
    return data


def prepare_boot_logo(image_path, output_path):
    """Create a 320x240 PNG for manual use with a documented STREONOR import flow."""
    data = read_icon(image_path)
    output = Path(output_path).expanduser().resolve()
    if output.suffix.lower() != '.png':
        raise ValueError('Boot logo output must use the .png extension')
    with Image.open(io.BytesIO(data)) as source:
        image = ImageOps.fit(ImageOps.exif_transpose(source).convert('RGB'), (320, 240), method=Image.Resampling.LANCZOS)
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.s6-logo-', suffix='.png', delete=False) as f:
            temp = Path(f.name)
            image.save(f, format='PNG')
            f.flush()
            os.fsync(f.fileno())
        try:
            os.replace(temp, output)
        finally:
            temp.unlink(missing_ok=True)
    return {'path': str(output), 'width': 320, 'height': 240, 'format': 'PNG', 'device_written': False}


def prepare_action(profile, page, operation, coordinate, source_coordinate='', image_path='', root=ROOT):
    doc, digest = read_manifest(profile, page, root)
    actions = doc['Actions']
    if not re.fullmatch(r'\d+,\d+', coordinate):
        raise ValueError('Coordinate must use the app format, for example 0,0')
    before = actions.get(coordinate)
    if operation in ('clone', 'create_from_template'):
        if before is not None:
            raise ValueError('Destination already has an action; remove it explicitly first')
        source = actions.get(source_coordinate)
        if not isinstance(source, dict) or 'Actions' in source:
            raise ValueError('Choose an existing single action on this page as the source')
        if operation == 'create_from_template':
            if not isinstance(source.get('Settings'), dict) or not isinstance(source.get('States'), list):
                raise ValueError('Source action cannot be used as a template')
        detail = {'source': source_coordinate, 'action': source.get('Name'), 'uuid': source.get('UUID')}
    elif operation in ('remove', 'set_icon', 'clear_icon', 'use_existing_icon'):
        if not isinstance(before, dict):
            raise ValueError('No action exists at that coordinate')
        detail = {'action': before.get('Name'), 'uuid': before.get('UUID')}
        if operation in ('set_icon', 'clear_icon', 'use_existing_icon'):
            states = before.get('States')
            if not isinstance(states, list) or not states or not isinstance(states[0], dict):
                raise ValueError('This action has no editable first image state')
            detail['old_image'] = states[0].get('Image', '')
        if operation in ('set_icon', 'use_existing_icon'):
            if operation == 'use_existing_icon':
                image_dir = profile_path(profile, page, root).parent / 'Images'
                candidate = Path(image_path).resolve(strict=True)
                if candidate.parent != image_dir.resolve() or candidate.suffix.lower() != '.png':
                    raise ValueError('Existing icon must be a PNG in this profile image folder')
            image = read_icon(image_path)
            detail.update(image_path=image_path, image_sha256=fingerprint(image))
    else:
        raise ValueError('Operation must be clone, create_from_template, remove, set_icon, use_existing_icon, or clear_icon')
    return {'profile': profile, 'page': page, 'coordinate': coordinate, 'operation': operation, 'sha256': digest, **detail}


def apply_action(profile, page, operation, coordinate, expected_sha256, source_coordinate='', image_path='', expected_image_sha256='', root=ROOT, backups=BACKUPS):
    import copy
    import uuid
    if vendor_running():
        raise RuntimeError('Quit STREONOR completely before editing profiles.')
    preview = prepare_action(profile, page, operation, coordinate, source_coordinate, image_path, root)
    if preview['sha256'] != expected_sha256:
        raise ValueError('Profile changed since preview; inspect and preview again')
    if operation in ('set_icon', 'use_existing_icon') and preview['image_sha256'] != expected_image_sha256:
        raise ValueError('Icon changed since preview; inspect and preview again')
    path = profile_path(profile, page, root)
    original = path.read_bytes()
    if fingerprint(original) != expected_sha256:
        raise ValueError('Profile changed while preparing edit')
    doc = json.loads(original.decode('utf-8-sig'))
    actions = doc['Actions']
    icon = None
    icon_data = None
    if operation in ('clone', 'create_from_template'):
        action = copy.deepcopy(actions[source_coordinate])
        action['ActionID'] = str(uuid.uuid4())
        actions[coordinate] = action
    elif operation == 'remove':
        del actions[coordinate]
    elif operation == 'clear_icon':
        actions[coordinate]['States'][0]['Image'] = ''
    elif operation == 'use_existing_icon':
        if fingerprint(read_icon(image_path)) != expected_image_sha256:
            raise ValueError('Icon changed while preparing edit')
        actions[coordinate]['States'][0]['Image'] = Path(image_path).name
    else:
        source_data = read_icon(image_path)
        if fingerprint(source_data) != expected_image_sha256:
            raise ValueError('Icon changed while preparing edit')
        with Image.open(io.BytesIO(source_data)) as source:
            source.seek(0)
            image = ImageOps.exif_transpose(source).convert('RGBA')
            image.thumbnail((1024, 1024))
            output = io.BytesIO()
            image.save(output, format='PNG')
            icon_data = output.getvalue()
        icon = uuid.uuid4().hex.upper() + '.png'
        actions[coordinate]['States'][0]['Image'] = icon
    backups.mkdir(parents=True, exist_ok=True)
    backup = backups / f'{profile}-{time.time_ns()}.json'
    with backup.open('xb') as f:
        f.write(original)
        f.flush()
        os.fsync(f.fileno())
    encoded = (json.dumps(doc, indent=4, ensure_ascii=False) + '\n').encode('utf-8')
    temp = None
    try:
        if icon:
            images = path.parent / 'Images'
            images.mkdir(exist_ok=True)
            if not images.resolve().is_relative_to(root.resolve()):
                raise ValueError('Image directory escapes profile directory')
            with (images / icon).open('xb') as f:
                f.write(icon_data)
                f.flush()
                os.fsync(f.fileno())
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.streonor-mcp-', delete=False) as f:
            temp = Path(f.name)
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
        if vendor_running() or fingerprint(path.read_bytes()) != expected_sha256:
            raise RuntimeError('STREONOR started or the profile changed; no manifest change was applied.')
        os.replace(temp, path)
        temp = None
    finally:
        if temp:
            temp.unlink(missing_ok=True)
    return {'updated': True, 'backup': str(backup), 'new_sha256': fingerprint(encoded), 'icon': icon, 'reopen_app': True}


def list_installed_actions():
    roots = [Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Streonor' / 'plugins',
             Path(os.environ.get('APPDATA', '')) / 'HotSpot' / 'StreamDock' / 'plugins']
    found = {}
    for root in roots:
        for path in sorted(root.glob('*.sdPlugin/manifest.json')):
            try:
                manifest = json.loads(path.read_text(encoding='utf-8-sig'))
                for action in manifest.get('Actions', []):
                    if not isinstance(action, dict) or not action.get('UUID'):
                        continue
                    found[action['UUID']] = {'uuid': action['UUID'], 'name': action.get('Name'), 'plugin': manifest.get('Name'), 'category': manifest.get('Category'), 'controllers': action.get('Controllers'), 'description': action.get('Tooltip')}
            except (OSError, ValueError, TypeError):
                continue
    return sorted(found.values(), key=lambda action: (action['name'] or '').lower())


def find_icons(query, limit=50):
    if not isinstance(query, str) or not query.strip() or len(query) > 100:
        raise ValueError('Enter a non-empty icon search term')
    if not 1 <= limit <= 100:
        raise ValueError('Limit must be between 1 and 100')
    root = Path(os.environ.get('APPDATA', '')) / 'HotSpot' / 'StreamDock' / 'icons'
    matches = []
    for path in root.rglob('*'):
        if path.is_file() and path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.svg') and query.casefold() in path.stem.casefold():
            matches.append({'name': path.stem, 'path': str(path), 'supported': path.suffix.lower() != '.svg'})
            if len(matches) >= limit:
                break
    return matches
