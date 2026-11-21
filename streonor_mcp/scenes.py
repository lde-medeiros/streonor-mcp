"""Create blank scenes and register them in the observed vendor SQLite catalog."""
import json
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


def preview(source_profile, name, root=profiles.ROOT):
    if not isinstance(name, str) or not name.strip() or len(name) > 80 or any(ord(c) < 32 for c in name):
        raise ValueError('Scene name must be 1 to 80 printable characters')
    if any((p.get('name') or '').casefold() == name.strip().casefold() for p in profiles.list_profiles(root)):
        raise ValueError('A scene with this name already exists')
    source, digest = profiles.read_manifest(source_profile, root=root)
    spec = get_device(source.get('DeviceUUID'))
    if not spec.supported:
        raise ValueError('Scene creation is not verified for this device')
    device = source['DeviceUUID']
    path = catalog(root, device)
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as connection:
        registry = registry_hash(connection, device)
    return {'source_profile': source_profile, 'name': name.strip(), 'device': device, 'source_sha256': digest, 'registry_sha256': registry, 'blank': True}


def create(source_profile, name, expected_source_sha256, expected_registry_sha256, root=profiles.ROOT, backups=profiles.BACKUPS):
    if profiles.vendor_running():
        raise RuntimeError('Close STREONOR before creating a scene')
    change = preview(source_profile, name, root)
    if change['source_sha256'] != expected_source_sha256 or change['registry_sha256'] != expected_registry_sha256:
        raise ValueError('Scene source or catalog changed; preview again')
    source, digest = profiles.read_manifest(source_profile, root=root)
    if digest != expected_source_sha256:
        raise ValueError('Source changed; preview again')
    profile = str(uuid.uuid4()).upper() + '.sdProfile'
    doc = {k: v for k, v in source.items() if k not in ('Actions', 'Pages', 'Name') and not k.startswith('AppIdentifier')}
    doc.update(Name=change['name'], Actions={}, Pages={'Current': profile, 'Pages': [profile]}, AppIdentifier='', AppIdentifier0='', AppIdentifier1='', AppIdentifier2='')
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
            profiles.write_new_file(folder / 'manifest.json', (json.dumps(doc, indent=4, ensure_ascii=False) + '\n').encode())
            connection.execute(f'INSERT INTO "{change["device"]}" (Profile) VALUES (?)', (profile,))
            connection.commit()
        except Exception:
            connection.rollback()
            if created:
                (folder / 'manifest.json').unlink(missing_ok=True)
                folder.rmdir()
            raise
    return {'created': True, 'profile': profile, 'name': change['name'], 'catalog_backup': str(backup), 'reopen_app': True}
