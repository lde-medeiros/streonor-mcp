"""Inspect and safely prepare offline edits to STREONOR profile manifests."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import sys
import warnings
from PIL import Image, ImageOps, ImageDraw
from .devices import DEVICES, get_device
from .paths import profiles_dir, data_dir, icons_dir, vendor_dir
from .locking import serialized_profile_edit
from .flows import build_flow

ROOT = profiles_dir()
BACKUPS = data_dir() / 'backups'
PROFILE_ID = re.compile(r'^[A-Za-z0-9-]+\.sdProfile$')
MAX_MANIFEST_BYTES = 32 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000


def read_bounded(path, limit):
    with Path(path).open('rb') as f:
        data = f.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f'File exceeds the {limit}-byte limit')
    return data


def parse_manifest(data):
    def reject_constant(value):
        raise ValueError(f'Invalid JSON constant: {value}')
    parsed = json.loads(data.decode('utf-8-sig'), parse_constant=reject_constant)
    if not isinstance(parsed, dict) or not isinstance(parsed.get('Actions'), dict):
        raise ValueError('Unrecognized STREONOR manifest')
    return parsed


def write_new_file(output, data):
    """Publish a complete file atomically without overwriting an existing path."""
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.streonor-image-', delete=False) as f:
            temp = Path(f.name)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.link(temp, output)
    finally:
        if temp:
            temp.unlink(missing_ok=True)


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
    data = read_bounded(path, MAX_MANIFEST_BYTES)
    parsed = parse_manifest(data)
    return parsed, fingerprint(data)


def list_profiles(root=ROOT):
    result = []
    for manifest in sorted(root.glob('*.sdProfile/manifest.json')):
        try:
            data, digest = read_manifest(manifest.parent.name, root=root)
            software_id = data.get('DeviceUUID')
            spec = next((d for d in DEVICES if software_id in d.software_ids), None)
            result.append({'id': manifest.parent.name, 'name': data.get('Name'), 'device': software_id, 'device_model': spec.id if spec else None, 'pages': data.get('Pages'), 'sha256': digest})
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return result


def prepare(profile, page, coordinate, setting, new_value, root=ROOT, auto_icon=True, icon_query=''):
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
    json.dumps(new_value, allow_nan=False)
    result = {'profile': profile, 'page': page, 'coordinate': coordinate, 'action': action.get('Name'), 'uuid': action.get('UUID'), 'setting': setting, 'old_value': old, 'new_value': new_value, 'sha256': digest}
    if auto_icon and setting in ('path', 'appId') and old != new_value:
        import copy
        from .icons import for_action, label_for_action
        future = copy.deepcopy(action)
        future['Settings'][setting] = new_value
        _, result['auto_icon'] = for_action(future, profile_path(profile, page, root).parent, icon_query or label_for_action(future))
    return result


def vendor_running():
    if sys.platform != 'win32':
        result = subprocess.run(['ps', '-axo', 'comm='], capture_output=True, text=True, timeout=5, check=True)
        return any(Path(line.strip()).name.casefold() in ('streonor', 'streonor.exe', 'streamdock', 'streamdock.exe') for line in result.stdout.splitlines())
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Streonor.exe', '/NH'], capture_output=True, text=True, timeout=5, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), check=True)
    return 'streonor.exe' in result.stdout.lower()


@serialized_profile_edit
def apply(profile, page, coordinate, setting, new_value, expected_sha256, root=ROOT, backups=BACKUPS, auto_icon=True, icon_query='', expected_auto_icon_sha256=''):
    if vendor_running():
        raise RuntimeError('Quit STREONOR completely before editing profiles; it can overwrite external changes.')
    preview = prepare(profile, page, coordinate, setting, new_value, root, auto_icon, icon_query)
    if preview['sha256'] != expected_sha256:
        raise ValueError('Profile changed since preview; inspect and preview again')
    path = profile_path(profile, page, root)
    original = read_bounded(path, MAX_MANIFEST_BYTES)
    if fingerprint(original) != expected_sha256:
        raise ValueError('Profile changed while preparing edit')
    doc = parse_manifest(original)
    doc['Actions'][coordinate]['Settings'][setting] = new_value
    icon_data = None
    if auto_icon and setting in ('path', 'appId') and preview['old_value'] != new_value:
        from .icons import for_action, label_for_action
        action = doc['Actions'][coordinate]
        icon_data, info = for_action(action, path.parent, icon_query or label_for_action(action))
        if expected_auto_icon_sha256 and info.get('sha256') != expected_auto_icon_sha256:
            raise ValueError('Automatic icon changed since preview; preview again')
    return commit_edit(profile, page, coordinate, path, original, doc, expected_sha256, root, backups, icon_data)

def read_icon(image_path):
    path = Path(image_path)
    data = read_bounded(path, 16 * 1024 * 1024)
    if path.suffix.lower() == '.svg':
        from .svg import render
        data = render(data)
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in ('PNG', 'JPEG', 'BMP', 'GIF', 'WEBP'):
                raise ValueError('Use a PNG, JPEG, BMP, GIF, or WebP icon')
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise ValueError('Icon must contain no more than 16 million pixels')
            image.verify()
    return data


def normalize_icon(data, background_color='', replace_edge_background=False):
    """Preserve the whole first frame and alpha while enforcing the icon canvas."""
    with Image.open(io.BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source).convert('RGBA')
        if background_color and not re.fullmatch(r'#[0-9a-fA-F]{6}', background_color):
            raise ValueError('Background color must use #RRGGBB')
        if replace_edge_background and not background_color:
            raise ValueError('Edge replacement requires a background color')
        if replace_edge_background:
            color = tuple(bytes.fromhex(background_color[1:])) + (255,)
            ImageDraw.floodfill(image, (0, 0), color, thresh=24)
        image = ImageOps.contain(image, (1254, 1254), Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA', (1254, 1254), background_color or (0, 0, 0, 0))
        canvas.alpha_composite(image, ((1254-image.width)//2, (1254-image.height)//2))
        output = io.BytesIO()
        canvas.save(output, format='PNG')
        return output.getvalue()


def prepare_icon(image_path, output_path, background_color='', replace_edge_background=False):
    """Create a square PNG without changing profiles or device storage."""
    output = Path(output_path).expanduser().resolve()
    if output.suffix.lower() != '.png':
        raise ValueError('Icon output must use the .png extension')
    data = normalize_icon(read_icon(image_path), background_color, replace_edge_background)
    write_new_file(output, data)
    return {'path': str(output), 'width': 1254, 'height': 1254, 'format': 'PNG', 'sha256': fingerprint(data)}


def prepare_boot_logo(device_id, image_path, output_path, fit="cover"):
    """Prepare an image using model metadata. This never writes device storage."""
    spec = get_device(device_id)
    if not spec.supported:
        raise ValueError(f'{spec.name} is listed but not yet supported')
    if not spec.boot_logo_size:
        raise ValueError(f'{spec.name} has no registered boot-logo dimensions')
    if fit not in ('cover', 'contain'):
        raise ValueError('Boot artwork fit must be cover or contain')
    data = read_icon(image_path)
    output = Path(output_path).expanduser().resolve()
    if output.suffix.lower() != '.png':
        raise ValueError('Boot logo output must use the .png extension')
    with Image.open(io.BytesIO(data)) as source:
        source = ImageOps.exif_transpose(source).convert('RGBA')
        image = Image.new('RGBA', source.size, 'black')
        image.alpha_composite(source)
        image = image.convert('RGB')
        if fit == 'cover':
            image = ImageOps.fit(image, spec.boot_logo_size, method=Image.Resampling.LANCZOS)
        else:
            image = ImageOps.pad(image, spec.boot_logo_size, method=Image.Resampling.LANCZOS, color='black')
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        encoded = buffer.getvalue()
        write_new_file(output, encoded)
    return {'path': str(output), 'sha256': fingerprint(encoded), 'fit': fit, 'device': spec.id, 'width': spec.boot_logo_size[0], 'height': spec.boot_logo_size[1], 'format': 'PNG', 'device_written': False}


def prepare_action(profile, page, operation, coordinate, source_coordinate='', image_path='', root=ROOT, flow_steps=None, flow_title='', auto_icon=True, icon_query='', action_name='', action_settings=None, controller='Keypad', hotkey=''):
    doc, digest = read_manifest(profile, page, root)
    actions = doc['Actions']
    if not re.fullmatch(r'\d+,\d+', coordinate):
        raise ValueError('Coordinate must use the app format, for example 0,0')
    before = actions.get(coordinate)
    if hotkey and operation != 'create_by_name':
        raise ValueError('Use hotkey with create_by_name for an installed Hotkey action')
    if operation == 'create_by_name':
        if before is not None:
            raise ValueError('Destination already has an action. Remove it explicitly first')
        from .catalog import build_action
        source, metadata = build_action(action_name, action_settings, controller, hotkey=hotkey)
        detail = {'action': source['Name'], **metadata}
        if hotkey:
            detail['hotkey'] = hotkey
    elif operation == 'configure_action':
        if not isinstance(before, dict) or not isinstance(action_settings, dict):
            raise ValueError('Choose an existing action and provide action_settings')
        json.dumps(action_settings, allow_nan=False)
        detail = {'action': before.get('Name'), 'old_settings': before.get('Settings'), 'new_settings': action_settings, 'configuration_note': 'Plugin validates settings at runtime'}
    elif operation == 'set_flow':
        flow = build_flow(actions, coordinate, flow_steps, flow_title)
        detail = {'replaces': before.get('Name') if before else None, 'title': flow_title, 'steps': [{'source': step.get('source_coordinate') or step.get('action_name'), 'action': child['Name'], 'delay_ms': child['Settings']['delay']} for step, child in zip(flow_steps, flow['Actions'])]}
    elif operation in ('clone', 'create_from_template'):
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
            detail.update(image_path=image_path, image_sha256=fingerprint(image), width=1254, height=1254, format='PNG')
    else:
        raise ValueError('Operation must be clone, create_from_template, remove, set_icon, use_existing_icon, clear_icon, set_flow, create_by_name or configure_action')
    if (auto_icon or image_path) and operation in ('clone', 'create_from_template', 'create_by_name', 'set_flow'):
        from .icons import for_action
        candidate = flow if operation == 'set_flow' else source
        _, detail['auto_icon'] = for_action(candidate, profile_path(profile, page, root).parent, icon_query, image_path)
    return {'profile': profile, 'page': page, 'coordinate': coordinate, 'operation': operation, 'sha256': digest, **detail}


@serialized_profile_edit
def apply_action(profile, page, operation, coordinate, expected_sha256, source_coordinate='', image_path='', expected_image_sha256='', root=ROOT, backups=BACKUPS, flow_steps=None, flow_title='', auto_icon=True, icon_query='', expected_auto_icon_sha256='', action_name='', action_settings=None, controller='Keypad', hotkey=''):
    import copy
    import uuid
    if vendor_running():
        raise RuntimeError('Quit STREONOR completely before editing profiles.')
    preview = prepare_action(profile, page, operation, coordinate, source_coordinate, image_path, root, flow_steps, flow_title, auto_icon, icon_query, action_name, action_settings, controller, hotkey)
    if preview['sha256'] != expected_sha256:
        raise ValueError('Profile changed since preview; inspect and preview again')
    if operation in ('set_icon', 'use_existing_icon') and preview['image_sha256'] != expected_image_sha256:
        raise ValueError('Icon changed since preview; inspect and preview again')
    path = profile_path(profile, page, root)
    original = read_bounded(path, MAX_MANIFEST_BYTES)
    if fingerprint(original) != expected_sha256:
        raise ValueError('Profile changed while preparing edit')
    doc = parse_manifest(original)
    actions = doc['Actions']
    icon = None
    icon_data = None
    if operation == 'create_by_name':
        from .catalog import build_action
        actions[coordinate], _ = build_action(action_name, action_settings, controller, hotkey=hotkey)
    elif operation == 'configure_action':
        actions[coordinate]['Settings'] = copy.deepcopy(action_settings)
    elif operation == 'set_flow':
        actions[coordinate] = build_flow(actions, coordinate, flow_steps, flow_title)
    elif operation in ('clone', 'create_from_template'):
        action = copy.deepcopy(actions[source_coordinate])
        action['ActionID'] = str(uuid.uuid4())
        actions[coordinate] = action
    elif operation == 'remove':
        del actions[coordinate]
    elif operation == 'clear_icon':
        actions[coordinate]['States'][0]['Image'] = ''
    else:
        source_data = read_icon(image_path)
        if fingerprint(source_data) != expected_image_sha256:
            raise ValueError('Icon changed while preparing edit')
        icon_data = normalize_icon(source_data)
    auto_info = None
    if (auto_icon or image_path) and operation in ('clone', 'create_from_template', 'create_by_name', 'set_flow'):
        from .icons import for_action
        icon_data, auto_info = for_action(actions[coordinate], path.parent, icon_query, image_path)
        if expected_auto_icon_sha256 and (auto_info or {}).get('sha256') != expected_auto_icon_sha256:
            raise ValueError('Automatic icon changed since preview; preview again')
    result = commit_edit(profile, page, coordinate, path, original, doc, expected_sha256, root, backups, icon_data)
    result['auto_icon'] = auto_info
    return result


def commit_edit(profile, page, coordinate, path, original, doc, expected_sha256, root, backups, icon_data=None):
    import uuid
    icon = None
    if icon_data is not None:
        icon = uuid.uuid4().hex.upper() + '.png'
        action = doc['Actions'][coordinate]
        if not action.get('States'):
            action['States'] = [{}]
        action['States'][0]['Image'] = icon
    backups.mkdir(parents=True, exist_ok=True)
    backup = backups / f'{profile}--{page or profile}--{time.time_ns()}.json'
    with backup.open('xb') as f:
        f.write(original)
        f.flush()
        os.fsync(f.fileno())
    encoded = (json.dumps(doc, indent=4, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
    if len(encoded) > MAX_MANIFEST_BYTES:
        raise ValueError('Updated manifest exceeds the 32 MiB limit')
    temp = None
    created_icon = None
    committed = False
    try:
        if icon:
            images = path.parent / 'Images'
            images.mkdir(exist_ok=True)
            if not images.resolve().is_relative_to(root.resolve()):
                raise ValueError('Image directory escapes profile directory')
            with (images / icon).open('xb') as f:
                created_icon = images / icon
                f.write(icon_data)
                f.flush()
                os.fsync(f.fileno())
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.streonor-mcp-', delete=False) as f:
            temp = Path(f.name)
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
        if profile_path(profile, page, root) != path or vendor_running() or fingerprint(read_bounded(path, MAX_MANIFEST_BYTES)) != expected_sha256:
            raise RuntimeError('STREONOR started or the profile changed; no manifest change was applied.')
        os.replace(temp, path)
        committed = True
        temp = None
    finally:
        if temp:
            temp.unlink(missing_ok=True)
        if created_icon and not committed:
            created_icon.unlink(missing_ok=True)
    return {'updated': True, 'backup': str(backup), 'new_sha256': fingerprint(encoded), 'icon': icon, 'reopen_app': True}



def prepare_page_order(profile, page_order, root=ROOT):
    path = profile_path(profile, root=root)
    original = read_bounded(path, MAX_MANIFEST_BYTES)
    doc = parse_manifest(original)
    registry = doc.get('Pages')
    existing = registry.get('Pages') if isinstance(registry, dict) else None
    if (not isinstance(existing, list)
            or any(not isinstance(page, str) or not PROFILE_ID.fullmatch(page) for page in existing)
            or len(set(existing)) != len(existing)
            or profile not in existing
            or registry.get('Current') not in existing):
        raise ValueError('Unrecognized scene page registry')
    if len(page_order) != len(existing) or set(page_order) != set(existing):
        raise ValueError('Page order must include every registered page exactly once')
    for page in existing:
        if not profile_path(profile, page, root).is_relative_to(path.parent):
            raise ValueError('Registered page escapes its scene')
    preview = {'profile': profile, 'old_order': existing, 'new_order': page_order,
               'current_page': registry['Current'], 'sha256': fingerprint(original)}
    registry['Pages'] = page_order
    return preview, path, original, doc


@serialized_profile_edit
def reorder_pages(profile, page_order, expected_sha256, root=ROOT, backups=BACKUPS):
    if vendor_running():
        raise RuntimeError('Quit STREONOR completely before reordering pages')
    preview, path, original, doc = prepare_page_order(profile, page_order, root)
    if preview['sha256'] != expected_sha256:
        raise ValueError('Scene changed since preview')
    if preview['old_order'] == page_order:
        return {'updated': False, 'new_sha256': expected_sha256}
    return commit_edit(profile, None, None, path, original, doc, expected_sha256, root, backups)


def prepare_restore(profile, page, backup_name, root=ROOT, backups=BACKUPS):
    path = profile_path(profile, page, root)
    target = page or profile
    pattern = re.escape(f'{profile}--{target}--') + r'[0-9]+\.json'
    if not re.fullmatch(pattern, backup_name):
        raise ValueError('Choose a backup created for this exact scene and page')
    backup = backups / backup_name
    if backup.is_symlink() or not backup.is_file():
        raise ValueError('Backup must be a regular file in the MCP backup directory')
    saved = read_bounded(backup, MAX_MANIFEST_BYTES)
    previous = parse_manifest(saved)
    original = read_bounded(path, MAX_MANIFEST_BYTES)
    current = parse_manifest(original)
    if previous.get('DeviceUUID') != current.get('DeviceUUID'):
        raise ValueError('Backup belongs to a different device')
    changed = sorted(key for key in previous['Actions'].keys() | current['Actions'].keys()
                     if previous['Actions'].get(key) != current['Actions'].get(key))
    preview = {'profile': profile, 'page': page, 'backup_name': backup_name,
               'sha256': fingerprint(original), 'backup_sha256': fingerprint(saved),
               'changed_coordinates': changed}
    current['Actions'] = previous['Actions']
    return preview, path, original, current


@serialized_profile_edit
def restore_controls(profile, page, backup_name, expected_sha256, expected_backup_sha256,
                     root=ROOT, backups=BACKUPS):
    if vendor_running():
        raise RuntimeError('Quit STREONOR completely before restoring controls')
    preview, path, original, doc = prepare_restore(profile, page, backup_name, root, backups)
    if (preview['sha256'], preview['backup_sha256']) != (expected_sha256, expected_backup_sha256):
        raise ValueError('Scene or backup changed since preview')
    if not preview['changed_coordinates']:
        return {'updated': False, 'new_sha256': expected_sha256}
    return commit_edit(profile, page, None, path, original, doc, expected_sha256, root, backups)


def list_installed_actions():
    roots = [vendor_dir() / 'plugins']
    if sys.platform == 'win32':
        roots.insert(0, Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Streonor' / 'plugins')
    found = {}
    for root in roots:
        for path in sorted(root.glob('*.sdPlugin/manifest.json')):
            try:
                manifest = json.loads(path.read_text(encoding='utf-8-sig'))
            except (OSError, ValueError):
                continue
            if not isinstance(manifest, dict) or not isinstance(manifest.get('Actions'), list):
                continue
            plugin = manifest.get('Name')
            for action in manifest['Actions']:
                if not isinstance(action, dict):
                    continue
                uuid = action.get('UUID')
                name = action.get('Name')
                if not isinstance(uuid, str) or not uuid.strip() or (name is not None and not isinstance(name, str)):
                    continue
                found[uuid] = {'uuid': uuid, 'name': name, 'plugin': plugin if isinstance(plugin, str) else None, 'category': manifest.get('Category'), 'controllers': action.get('Controllers'), 'description': action.get('Tooltip'), 'default_settings': action.get('Settings', action.get('DefaultSettings', {})), 'states': action.get('States', []), 'supported_in_flows': action.get('SupportedInMultiActions'), 'only_in_flows': bool(action.get('OnlySupportedInMultiActions'))}
    return sorted(found.values(), key=lambda action: (action['name'] or '').lower())


def find_icons(query, limit=50):
    if not isinstance(query, str) or not query.strip() or len(query) > 100:
        raise ValueError('Enter a non-empty icon search term')
    if not 1 <= limit <= 100:
        raise ValueError('Limit must be between 1 and 100')
    root = icons_dir()
    matches = []
    for path in root.rglob('*'):
        if path.is_file() and path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.svg') and query.casefold() in path.stem.casefold():
            matches.append({'name': path.stem, 'path': str(path), 'supported': True})
            if len(matches) >= limit:
                break
    return matches
