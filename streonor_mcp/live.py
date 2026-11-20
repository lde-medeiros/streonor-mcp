"""Send a new scene to the running Windows app through its native importer."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from contextlib import closing
import sqlite3
from zipfile import ZipFile, ZIP_DEFLATED

from . import profiles, scenes
from .devices import get_device

MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_FILES = 1024


def _vendor_pid():
    result = subprocess.run(
        ['tasklist', '/FI', 'IMAGENAME eq Streonor.exe', '/FO', 'CSV', '/NH'],
        capture_output=True, text=True, timeout=5, check=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    pids = [row[1] for row in csv.reader(result.stdout.splitlines())
            if len(row) > 1 and row[0].casefold() == 'streonor.exe']
    return pids[0] if len(pids) == 1 else None


def _registered(root, device):
    catalog = scenes.catalog(root, device)
    with closing(sqlite3.connect(catalog.as_uri() + '?mode=ro', uri=True, timeout=1)) as db:
        return {row[0] for row in db.execute(f'SELECT Profile FROM "{device}"')}


def _encode(doc):
    encoded = json.dumps(doc, ensure_ascii=False, allow_nan=False).encode('utf-8')
    if len(encoded) > profiles.MAX_MANIFEST_BYTES:
        raise ValueError('Updated manifest exceeds the 32 MiB limit')
    return encoded


def _write_archive(output, folder, manifests, images):
    total = 0
    with ZipFile(output, 'x', ZIP_DEFLATED) as archive:
        def add(relative, data):
            nonlocal total
            if len(archive.filelist) >= MAX_ARCHIVE_FILES or total + len(data) > MAX_ARCHIVE_BYTES:
                raise ValueError('Scene exceeds the live import size or file count limit')
            archive.writestr(relative.as_posix(), data)
            total += len(data)

        def check(entry, is_directory):
            correct_type = entry.is_dir() if is_directory else entry.is_file()
            if entry.is_symlink() or not correct_type or not entry.resolve().is_relative_to(folder):
                raise ValueError('Scene archive entry must be a local file or directory')

        def copy_scene(directory, depth=0):
            if depth > 16:
                raise ValueError('Scene folders are nested too deeply')
            for entry in directory.iterdir():
                if entry.name in ('manifest.json.A.bak', 'manifest.json.B.bak'):
                    continue
                relative = entry.relative_to(folder)
                if entry.name == 'manifest.json':
                    check(entry, False)
                    data = manifests.get(relative)
                    if data is None:
                        data = profiles.read_bounded(entry, profiles.MAX_MANIFEST_BYTES)
                    add(relative, data)
                elif entry.name == 'Images':
                    check(entry, True)
                    for asset in entry.iterdir():
                        check(asset, False)
                        add(asset.relative_to(folder),
                            profiles.read_bounded(asset, MAX_ARCHIVE_BYTES - total))
                elif entry.name == 'profiles':
                    check(entry, True)
                    for child in entry.iterdir():
                        if not profiles.PROFILE_ID.fullmatch(child.name):
                            raise ValueError('Unknown folder or page identifier in scene')
                        check(child, True)
                        copy_scene(child, depth + 1)
                else:
                    raise ValueError(f'Unsupported scene archive entry: {relative.as_posix()}')

        copy_scene(folder)
        for image, data in images.items():
            add(image, data)


def scene_pages(profile, root):
    doc, digest = profiles.read_manifest(profile, root=root)
    registry = doc.get('Pages')
    order = registry.get('Pages') if isinstance(registry, dict) else None
    if (not isinstance(order, list) or profile not in order or registry.get('Current') not in order
            or any(not isinstance(p, str) or not profiles.PROFILE_ID.fullmatch(p) for p in order)
            or len(set(order)) != len(order)):
        raise ValueError('Unrecognized scene page registry')
    return doc, digest, order


def page_member(profile, page):
    return Path('manifest.json') if page == profile else Path('profiles', page, 'manifest.json')


def import_copy(profile, page, path, doc, expected_sha256, root, name, icon, icon_data):
    page = page or profile
    relative = page_member(profile, page)
    if path != root.resolve() / profile / relative:
        raise ValueError('Live imports require a page stored directly in its scene')
    images = {relative.parent / 'Images' / icon: icon_data} if icon else {}
    result = import_scene(profile, root, name, {page: doc}, {page: expected_sha256}, images)
    imported = result['pages'][page]
    return {**result, 'page': imported['id'], 'new_sha256': imported['sha256'], 'icon': icon}


def import_scene(profile, root, name, edits, source_hashes, images):
    if sys.platform != 'win32':
        raise RuntimeError('Live scene imports require the Windows STREONOR app')
    default_root = Path(os.environ['APPDATA']) / 'HotSpot' / 'StreamDock' / 'profiles'
    if root.resolve() != default_root.resolve():
        raise ValueError('Live imports require the default STREONOR profiles directory')
    root_doc, root_sha256, order = scene_pages(profile, root)
    if not edits.keys() <= set(order):
        raise ValueError('Only pages registered to this scene can be edited live')
    device = root_doc.get('DeviceUUID')
    if not get_device(device).supported:
        raise ValueError('Live import is not verified for this device')
    name = scenes.validate_new_name(name, root)
    executable = Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Streonor' / 'Streonor.exe'
    if not executable.is_file():
        raise RuntimeError('Cannot find the STREONOR importer')
    pid = _vendor_pid()
    if pid is None:
        raise RuntimeError('Open STREONOR before using live scene import')
    before = _registered(root, device)
    copy = {key: value for key, value in edits.get(profile, root_doc).items()
            if not key.startswith('AppIdentifier')}
    copy.update(Name=name, AppIdentifier='')
    manifests = {page_member(profile, page): _encode(doc) for page, doc in edits.items() if page != profile}
    manifests[Path('manifest.json')] = _encode(copy)
    source_hashes = {profile: root_sha256, **source_hashes}
    with tempfile.TemporaryDirectory(prefix='streonor-live-') as temp:
        archive = Path(temp) / 'scene.streamDockProfile'
        _write_archive(archive, root.resolve() / profile, manifests, images)
        if any(profiles.read_manifest(profile, page, root)[1] != digest
               for page, digest in source_hashes.items()):
            raise ValueError('Source scene changed while preparing the import; preview again')
        scenes.validate_new_name(name, root)
        if _vendor_pid() != pid:
            raise RuntimeError('STREONOR changed processes before import')
        # Windows uses this same file argument when opening a .streamDockProfile.
        subprocess.Popen([str(executable), str(archive)], cwd=executable.parent,
                         creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            for candidate in _registered(root, device) - before:
                try:
                    imported, _ = profiles.read_manifest(candidate, root=root)
                except (FileNotFoundError, ValueError):
                    continue
                if imported.get('Name') != name:
                    continue
                new_order = [candidate if value == profile else value for value in order]
                new_current = candidate if root_doc['Pages']['Current'] == profile else root_doc['Pages']['Current']
                if imported.get('Pages') != {'Pages': new_order, 'Current': new_current}:
                    raise RuntimeError(f'STREONOR added scene {candidate}, but its page layout changed')
                result = {}
                for page, desired in edits.items():
                    imported_page = candidate if page == profile else page
                    saved, digest = profiles.read_manifest(candidate, imported_page, root)
                    if saved['Actions'] != desired['Actions']:
                        raise RuntimeError(f'STREONOR added scene {candidate}, but page {imported_page} did not match the edit')
                    result[page] = {'id': imported_page, 'sha256': digest}
                if any(not (root / candidate / image).is_file() for image in images):
                    raise RuntimeError(f'STREONOR added scene {candidate}, but some new icons were missing')
                if _vendor_pid() != pid:
                    raise RuntimeError(f'STREONOR added scene {candidate}, but its process changed')
                return {'created': True, 'updated': True, 'profile': candidate,
                        'source_profile': profile, 'name': name, 'pages': result,
                        'app_restarted': False}
            time.sleep(0.2)
    raise RuntimeError('Live import was not confirmed. Check the STREONOR scene list before retrying.')
