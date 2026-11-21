"""Create blank scenes and register them in the observed vendor SQLite catalog."""
import json
import copy
import os
from pathlib import Path
import re
import sqlite3
from contextlib import closing
import time
import uuid
from . import profiles
from .devices import get_device


def catalog(root, device):
    if not re.fullmatch(r'[A-Za-z0-9_]+', device):
        raise ValueError('Invalid device catalog name')
    path = (root.parent / 'config' / 'DataCache.db').resolve(strict=True)
    if not path.is_relative_to(root.parent.resolve()):
        raise ValueError('Catalog path escapes the vendor directory')
    return path


def registry_hash(connection, device):
    columns = connection.execute(f'PRAGMA table_info("{device}")').fetchall()
    if [row[1] for row in columns] != ['Profile']:
        raise ValueError('Unsupported vendor scene catalog schema')
    rows = connection.execute(f'SELECT Profile FROM "{device}" ORDER BY Profile').fetchall()
    return profiles.fingerprint(json.dumps(rows, ensure_ascii=False).encode())


def validate_new_name(name, root):
    if not isinstance(name, str) or not name.strip() or len(name) > 80 or any(ord(c) < 32 for c in name):
        raise ValueError('Scene name must be 1 to 80 printable characters')
    if any((p.get('name') or '').casefold() == name.strip().casefold() for p in profiles.list_profiles(root)):
        raise ValueError('A scene with this name already exists')
    return name.strip()


def preview(source_profile, name, root=profiles.ROOT, include_coordinates=None):
    name = validate_new_name(name, root)
    source, digest = profiles.read_manifest(source_profile, root=root)
    spec = get_device(source.get('DeviceUUID'))
    if not spec.supported:
        raise ValueError('Scene creation is not verified for this device')
    selected = include_coordinates or []
    if not isinstance(selected, list) or len(selected) > 128 or any(not isinstance(c, str) or c not in source['Actions'] for c in selected) or len(set(selected)) != len(selected):
        raise ValueError('Select unique coordinates that exist on the source scene')
    device = source['DeviceUUID']
    path = catalog(root, device)
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as connection:
        registry = registry_hash(connection, device)
    return {'source_profile': source_profile, 'name': name, 'device': device, 'source_sha256': digest, 'registry_sha256': registry, 'blank': not selected, 'include_coordinates': selected}


def create(source_profile, name, expected_source_sha256, expected_registry_sha256, root=profiles.ROOT, backups=profiles.BACKUPS, include_coordinates=None, *, layout_actions=None, layout_images=None):
    if profiles.vendor_running():
        raise RuntimeError('Close STREONOR before creating a scene')
    change = preview(source_profile, name, root, include_coordinates)
    if change['source_sha256'] != expected_source_sha256 or change['registry_sha256'] != expected_registry_sha256:
        raise ValueError('Scene source or catalog changed; preview again')
    source, digest = profiles.read_manifest(source_profile, root=root)
    if digest != expected_source_sha256:
        raise ValueError('Source changed; preview again')
    profile = str(uuid.uuid4()).upper() + '.sdProfile'
    doc = {k: v for k, v in source.items() if k not in ('Actions', 'Pages', 'Name') and not k.startswith('AppIdentifier')}
    selected_actions = copy.deepcopy(
        {c: source['Actions'][c] for c in change['include_coordinates']}
        if layout_actions is None else layout_actions
    )
    layout_images = {member.name: data for member, data in (layout_images or {}).items()}
    doc.update(Name=change['name'], Actions=selected_actions, Pages={'Current': profile, 'Pages': [profile]}, AppIdentifier='', AppIdentifier0='', AppIdentifier1='', AppIdentifier2='')
    path = catalog(root, change['device'])
    backups.mkdir(parents=True, exist_ok=True)
    backup = backups / f'scene-catalog-{time.time_ns()}.sqlite'
    folder = root / profile
    created = False
    with closing(sqlite3.connect(path, timeout=5)) as connection:
        with closing(sqlite3.connect(backup)) as destination:
            connection.backup(destination)
        try:
            connection.execute('BEGIN IMMEDIATE')
            if profiles.vendor_running() or registry_hash(connection, change['device']) != expected_registry_sha256:
                raise ValueError('Vendor app started or catalog changed; preview again')
            folder.mkdir()
            created = True
            source_folder = profiles.profile_path(source_profile, root=root).parent
            def copy_action(action):
                action['ActionID'] = str(uuid.uuid4())
                for state in action.get('States', []):
                    image = state.get('Image', '')
                    if image.lower().endswith('.png') and image not in layout_images:
                        candidate = source_folder / ('Images/' + image if '/' not in image and '\\' not in image else image)
                        candidate = candidate.resolve(strict=True)
                        if not candidate.is_relative_to(source_folder.resolve()):
                            raise ValueError('Source icon escapes the scene')
                        name = candidate.name
                        output = folder / 'Images' / name
                        if not output.exists():
                            profiles.write_new_file(output, profiles.normalize_icon(profiles.read_icon(candidate)))
                        state['Image'] = name
                for child in action.get('Actions', []):
                    copy_action(child)
            for action in selected_actions.values():
                copy_action(action)
            for name, data in layout_images.items():
                profiles.write_new_file(folder / 'Images' / name, data)
            from .live import _encode
            encoded = _encode(doc)
            profiles.write_new_file(folder / 'manifest.json', encoded)
            connection.execute(f'INSERT INTO "{change["device"]}" (Profile) VALUES (?)', (profile,))
            connection.commit()
        except Exception:
            connection.rollback()
            if created:
                import shutil
                shutil.rmtree(folder)
            raise
    return {'created': True, 'profile': profile, 'name': change['name'], 'catalog_backup': str(backup), 'new_sha256': profiles.fingerprint(encoded), 'reopen_app': True}


def preview_change(profile, operation, new_name='', root=profiles.ROOT):
    if operation not in ('rename', 'delete'):
        raise ValueError('Scene operation must be rename or delete')
    doc, digest = profiles.read_manifest(profile, root=root)
    device = doc.get('DeviceUUID')
    if not get_device(device).supported:
        raise ValueError('Unsupported device')
    if operation == 'rename':
        preview(profile, new_name, root)
    path = catalog(root, device)
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        registry = registry_hash(db, device)
        rows = [row[0] for row in db.execute(f'SELECT Profile FROM "{device}"')]
    if rows.count(profile) != 1:
        raise ValueError('Scene must be registered exactly once')
    if operation == 'delete' and len(rows) < 2:
        raise ValueError('Cannot delete the last scene for a device')
    folder = root / profile
    if folder.is_symlink() or folder.resolve().parent != root.resolve():
        raise ValueError('Scene directory must be directly inside the profile root')
    return {'profile': profile, 'operation': operation, 'name': doc.get('Name'), 'new_name': new_name.strip() if operation == 'rename' else None, 'sha256': digest, 'registry_sha256': registry, 'device': device}


def apply_change(profile, operation, expected_sha256, expected_registry_sha256, new_name='', root=profiles.ROOT, backups=profiles.BACKUPS):
    if profiles.vendor_running():
        raise RuntimeError('Close STREONOR before editing scenes')
    change = preview_change(profile, operation, new_name, root)
    if change['sha256'] != expected_sha256 or change['registry_sha256'] != expected_registry_sha256:
        raise ValueError('Scene or catalog changed; preview again')
    path = profiles.profile_path(profile, root=root)
    original = profiles.read_bounded(path, profiles.MAX_MANIFEST_BYTES)
    backups.mkdir(parents=True, exist_ok=True)
    backup = backups / f'scene-{profile}-{time.time_ns()}.json'
    profiles.write_new_file(backup, original)
    if operation == 'rename':
        doc = profiles.parse_manifest(original)
        doc['Name'] = change['new_name']
        temp = path.parent / ('.scene-rename-' + uuid.uuid4().hex)
        try:
            profiles.write_new_file(temp, (json.dumps(doc, indent=4, ensure_ascii=False) + '\n').encode())
            if profiles.vendor_running() or profiles.fingerprint(path.read_bytes()) != expected_sha256:
                raise ValueError('Scene changed; preview again')
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)
        return {'renamed': True, 'profile': profile, 'name': change['new_name'], 'backup': str(backup), 'reopen_app': True}
    # Retain the whole folder on the same filesystem so rollback is a rename.
    archive_root = root / '.streonor-deleted-scenes'
    archive_root.mkdir(exist_ok=True)
    if archive_root.is_symlink():
        raise ValueError('Scene archive must not be a symbolic link')
    archived = archive_root / (profile + '-' + uuid.uuid4().hex)
    catalog_backup = backups / f'scene-catalog-{time.time_ns()}.sqlite'
    moved = False
    with closing(sqlite3.connect(catalog(root, change['device']), timeout=5)) as db:
        with closing(sqlite3.connect(catalog_backup)) as destination:
            db.backup(destination)
        try:
            db.execute('BEGIN IMMEDIATE')
            if profiles.vendor_running() or registry_hash(db, change['device']) != expected_registry_sha256 or profiles.fingerprint(path.read_bytes()) != expected_sha256:
                raise ValueError('Scene or catalog changed; preview again')
            os.replace(root / profile, archived)
            moved = True
            db.execute(f'DELETE FROM "{change["device"]}" WHERE Profile=?', (profile,))
            db.commit()
        except Exception:
            db.rollback()
            if moved:
                os.replace(archived, root / profile)
            raise
    return {'deleted': True, 'profile': profile, 'scene_archive': str(archived), 'catalog_backup': str(catalog_backup), 'reopen_app': True}
