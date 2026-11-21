"""Plan and apply batches of controls for existing and new scenes."""
import json
import os
import re
import time
import uuid

from pydantic import BaseModel, ConfigDict

from . import live, profiles, scenes
from .catalog import build_action
from .devices import DEVICES
from .flows import build_flow
from .icons import for_action
from .steam import app_id_from_action


class ControlEdit(BaseModel):
    model_config = ConfigDict(extra='forbid')

    action_name: str = ''
    settings: dict | None = None
    controller: str = ''
    hotkey: str = ''
    steam_app_id: str = ''
    title: str = ''
    show_title: bool | None = None
    flow_steps: list[dict] | None = None
    flow_title: str = ''
    state_index: int = 0
    image_path: str = ''
    icon_query: str = ''
    auto_icon: bool | None = None


class PageEdit(BaseModel):
    model_config = ConfigDict(extra='forbid')

    page: str = ''
    replace: bool = False
    controls: dict[str, ControlEdit | None]
    keep_coordinates: tuple[str, ...] = ()


def _preview_action(action):
    result = {key: value for key, value in action.items() if key != 'ActionID'}
    if 'Actions' in result:
        result['Actions'] = [_preview_action(child) for child in result['Actions']]
    return result


def plan(profile, name, pages, root, mode='auto', include_coordinates=None, clear_all=False):
    profile = profiles.resolve_scene(profile, root)
    root_doc, root_hash, order = live.scene_pages(profile, root)
    current_name = root_doc.get('Name', '')
    if mode == 'auto':
        mode = 'edit' if not name or name.strip().casefold() == current_name.casefold() else 'copy'
    if mode not in ('edit', 'copy', 'create'):
        raise ValueError('Layout mode must be auto, edit, copy or create')
    if clear_all:
        if pages or mode != 'edit':
            raise ValueError('clear_all is only for editing an existing scene without pages')
        pages = [PageEdit(page=page, replace=True, controls={}) for page in order]
    if not pages or len(pages) > 16 or sum(len(page.controls) for page in pages) > 128:
        raise ValueError('Provide 1 to 16 pages and at most 128 control edits, or use clear_all')
    if mode == 'edit':
        if name and name.strip().casefold() != current_name.casefold():
            raise ValueError('Use apply_scene_change to rename an existing scene')
        name = current_name
    elif mode == 'copy':
        name = scenes.validate_new_name(name, root)
    if include_coordinates is not None and mode != 'create':
        raise ValueError('include_coordinates is only for a new scene in create mode')
    seed = None
    if mode == 'create':
        if len(pages) != 1 or pages[0].page not in ('', profile):
            raise ValueError('Create mode starts with one main page; use copy to import multiple pages')
        seed = scenes.preview(profile, name, root, include_coordinates)
        if seed['source_sha256'] != root_hash:
            raise ValueError('Source scene changed while planning; preview again')
        name = seed['name']

    edits, images, details = {}, {}, {}
    image_bytes = 0
    installed = None
    source_hashes = {profile: root_hash}
    keypad = next((d.keypad_coordinates for d in DEVICES if root_doc.get('DeviceUUID') in d.software_ids), ())
    for update in pages:
        page = update.page or profile
        if page not in order or page in edits:
            raise ValueError('Each page must be registered to the scene and appear once')
        if not update.controls and not update.replace and mode != 'create':
            raise ValueError('Provide controls to edit or explicitly replace the page')
        member = live.page_member(profile, page)
        path = profiles.profile_path(profile, page, root)
        if path != root.resolve() / profile / member:
            raise ValueError('Layouts require a page stored directly in its scene')
        doc, digest = (root_doc, root_hash) if page == profile else profiles.read_manifest(profile, page, root)
        source_hashes[page] = digest
        before = doc['Actions']
        if seed is not None:
            before = {coordinate: before[coordinate] for coordinate in seed['include_coordinates']}
        keep = set(update.keep_coordinates)
        if keep and (not update.replace or not keep <= before.keys() or keep & update.controls.keys()):
            raise ValueError('keep_coordinates must select existing, unedited controls on a replaced page')
        actions = {key: before[key] for key in keep} if update.replace and seed is None else dict(before)
        changes = {}
        for coordinate, control in update.controls.items():
            if not re.fullmatch(r'(0|[1-9][0-9]{0,2}),(0|[1-9][0-9]{0,2})', coordinate):
                raise ValueError(f'Invalid coordinate: {coordinate}')
            old = actions.get(coordinate)
            if control is None:
                if old is None:
                    raise ValueError(f'No control to remove at {coordinate}')
                del actions[coordinate]
                changes[coordinate] = {'operation': 'remove'}
                continue
            if control.steam_app_id:
                if keypad and coordinate not in keypad:
                    raise ValueError(f'Steam launches require a keypad slot. Use one of: {", ".join(keypad)}')
                if (not re.fullmatch(r'[1-9][0-9]{0,9}', control.steam_app_id)
                        or int(control.steam_app_id) > 4294967295):
                    raise ValueError(f'Invalid Steam app ID at {coordinate}')
                if control.action_name or control.settings is not None or control.hotkey or control.flow_steps is not None or control.flow_title:
                    raise ValueError(f'Use steam_app_id and title to define a Steam launch at {coordinate}')
                control = control.model_copy(update={
                    'action_name': 'com.hotspot.streamdock.system.website',
                    'settings': {'path': f'steam://rungameid/{control.steam_app_id}'},
                })
            if control.flow_title and control.flow_steps is None:
                raise ValueError(f'Provide flow_steps with flow_title at {coordinate}')
            if control.flow_steps is not None:
                if control.action_name or control.settings is not None or control.controller or control.hotkey:
                    raise ValueError(f'Use flow_steps and flow_title to define the flow at {coordinate}')
                action = build_flow(before, coordinate, control.flow_steps, control.flow_title)
                operation = 'replace' if coordinate in before else 'create'
            elif control.action_name:
                if installed is None:
                    installed = profiles.list_installed_actions()
                controller = control.controller or (old or {}).get('Controller') or 'Keypad'
                action, _ = build_action(control.action_name, control.settings, controller, hotkey=control.hotkey, installed=installed)
                operation = 'replace' if coordinate in before else 'create'
            else:
                if old is None or control.controller or control.hotkey:
                    raise ValueError(f'Choose an installed action to create or replace {coordinate}')
                if control.settings is None and not (control.image_path or control.icon_query or control.auto_icon or control.title or control.show_title is False):
                    raise ValueError(f'Provide settings or an icon for {coordinate}')
                action = dict(old)
                settings = dict(old.get('Settings') or {})
                for key, value in (control.settings or {}).items():
                    if key in settings and type(settings[key]) is not type(value):
                        raise ValueError(f'New value for {coordinate} {key} must match its existing JSON type')
                    settings[key] = value
                if control.settings is not None:
                    action['Settings'] = settings
                operation = 'edit'
            if control.title and (len(control.title) > 120 or any(ord(char) < 32 for char in control.title)):
                raise ValueError(f'Invalid title at {coordinate}')
            destination_changed = (operation == 'edit'
                                   and any(key in (control.settings or {})
                                           and (old.get('Settings') or {}).get(key) != control.settings[key]
                                           for key in ('path', 'appId')))
            change = {'operation': operation}
            steam_id = app_id_from_action(action)
            data = None
            update_icon = (control.image_path or control.icon_query or control.auto_icon is True
                           or control.auto_icon is not False and (operation != 'edit' or destination_changed))
            if update_icon or control.title or control.show_title is False:
                states = list(action.get('States') or [{}])
                index = control.state_index
                if not 0 <= index < len(states) or not isinstance(states[index], dict):
                    raise ValueError(f'No editable state at {index} on {coordinate}')
                state = dict(states[index])
                title = control.title or state.get('Title') or ''
                if not isinstance(title, str):
                    title = ''
                if update_icon:
                    query = control.icon_query or (title[:100] if steam_id else '')
                    data, icon = for_action({**action, 'States': [state]}, path.parent,
                                            query, control.image_path, refresh=control.auto_icon is True)
                    change['icon'] = {**icon, 'state_index': index}
                if control.show_title is False or (steam_id and data is not None and control.show_title is None):
                    state.pop('Title', None)
                elif control.title:
                    state['Title'] = control.title
                if title:
                    change['title'] = title
                states[index] = state
                if state != (action.get('States') or [{}])[index]:
                    action['States'] = states
            elif control.state_index:
                raise ValueError(f'Choose an icon or title when specifying a state at {coordinate}')
            change['action'] = dict(action) if operation == 'edit' else _preview_action(action)
            if data is not None:
                image_bytes += len(data)
                if image_bytes > live.MAX_ARCHIVE_BYTES:
                    raise ValueError('New icons exceed the live import size limit')
                filename = uuid.uuid4().hex.upper() + '.png'
                action['States'] = [*states[:index], {**states[index], 'Image': filename}, *states[index + 1:]]
                images[member.parent / 'Images' / filename] = data
            actions[coordinate] = action
            changes[coordinate] = change
        edits[page] = {**doc, 'Actions': actions}
        details[page] = {'replace': update.replace, 'updated': actions != before, 'changes': changes,
                         'cleared': sorted(before.keys() - actions.keys())}
    preview = {'source_profile': profile, 'name': name, 'source_hashes': source_hashes,
               'pages': details, 'mode': mode, 'creates_scene': mode != 'edit',
               'needs_artwork': [
                   {'page': page, 'coordinate': coordinate, 'query': change['icon']['query']}
                   for page, detail in details.items() for coordinate, change in detail['changes'].items()
                   if change.get('icon', {}).get('needs_artwork')
               ]}
    if seed is not None:
        preview['registry_sha256'] = seed['registry_sha256']
        preview['include_coordinates'] = seed['include_coordinates']
    digest = profiles.fingerprint(json.dumps(preview, sort_keys=True, allow_nan=False).encode())
    return {**preview, 'layout_sha256': digest}, edits, images


def apply_in_place(profile, edits, hashes, images, root, backups):
    """Write all prepared pages with rollback on failure and a backup per changed page."""
    if profiles.vendor_running():
        raise RuntimeError('Close STREONOR or use manage_app=True to edit this scene')
    folder = root.resolve() / profile
    staged, created_icons, replaced = {}, [], []
    results = {}
    committed = False
    try:
        for page, doc in edits.items():
            path = profiles.profile_path(profile, page, root)
            original = profiles.read_bounded(path, profiles.MAX_MANIFEST_BYTES)
            if profiles.fingerprint(original) != hashes[page]:
                raise ValueError('Scene changed; preview the layout again')
            if doc == profiles.parse_manifest(original):
                results[page] = {'id': page, 'sha256': hashes[page], 'updated': False}
                continue
            data = live._encode(doc)
            temp = path.with_name('.streonor-layout-' + uuid.uuid4().hex)
            backup = backups / f'{profile}--{page}--{time.time_ns()}.json'
            profiles.write_new_file(backup, original)
            profiles.write_new_file(temp, data)
            staged[path] = (temp, backup)
            results[page] = {'id': page, 'sha256': profiles.fingerprint(data),
                             'updated': True, 'backup': str(backup)}
        for member, data in images.items():
            output = folder / member
            if not output.parent.resolve().is_relative_to(folder):
                raise ValueError('Image directory escapes the scene')
            profiles.write_new_file(output, data)
            created_icons.append(output)
        if profiles.vendor_running() or any(profiles.read_manifest(profile, page, root)[1] != digest
                                            for page, digest in hashes.items()):
            raise ValueError('STREONOR started or the scene changed; preview again')
        for path, (temp, backup) in staged.items():
            os.replace(temp, path)
            replaced.append((path, backup))
        committed = True
    finally:
        for temp, _ in staged.values():
            temp.unlink(missing_ok=True)
        if not committed:
            for path, backup in reversed(replaced):
                restore = path.with_name('.streonor-rollback-' + uuid.uuid4().hex)
                try:
                    profiles.write_new_file(restore, profiles.read_bounded(backup, profiles.MAX_MANIFEST_BYTES))
                    os.replace(restore, path)
                except OSError as error:
                    raise RuntimeError(f'Layout rollback failed. Restore the affected page from {backup}') from error
                finally:
                    restore.unlink(missing_ok=True)
            for output in created_icons:
                output.unlink(missing_ok=True)
    return {'updated': bool(replaced), 'profile': profile, 'pages': results}
