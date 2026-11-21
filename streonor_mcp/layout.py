"""Plan several page changes together before asking STREONOR to import them."""
import json
import re
import uuid

from pydantic import BaseModel, ConfigDict

from . import live, profiles, scenes
from .catalog import build_action
from .flows import build_flow
from .icons import for_action


class ControlEdit(BaseModel):
    model_config = ConfigDict(extra='forbid')

    action_name: str = ''
    settings: dict | None = None
    controller: str = ''
    hotkey: str = ''
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


def _preview_action(action):
    result = {key: value for key, value in action.items() if key != 'ActionID'}
    if 'Actions' in result:
        result['Actions'] = [_preview_action(child) for child in result['Actions']]
    return result


def plan(profile, name, pages, root):
    if not 1 <= len(pages) <= 16 or sum(len(p.controls) for p in pages) > 128:
        raise ValueError('Provide 1 to 16 pages and at most 128 control edits')
    root_doc, root_hash, order = live.scene_pages(profile, root)
    name = scenes.validate_new_name(name, root)
    edits, images, details = {}, {}, {}
    image_bytes = 0
    source_hashes = {profile: root_hash}
    for update in pages:
        page = update.page or profile
        if page not in order or page in edits:
            raise ValueError('Each page must be registered to the scene and appear once')
        if not update.controls and not update.replace:
            raise ValueError('Provide controls to edit or explicitly replace the page')
        member = live.page_member(profile, page)
        path = profiles.profile_path(profile, page, root)
        if path != root.resolve() / profile / member:
            raise ValueError('Live imports require a page stored directly in its scene')
        doc, digest = (root_doc, root_hash) if page == profile else profiles.read_manifest(profile, page, root)
        source_hashes[page] = digest
        before = doc['Actions']
        actions = {} if update.replace else dict(before)
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
            if control.flow_title and control.flow_steps is None:
                raise ValueError(f'Provide flow_steps with flow_title at {coordinate}')
            if control.flow_steps is not None:
                if control.action_name or control.settings is not None or control.controller or control.hotkey:
                    raise ValueError(f'Use flow_steps and flow_title to define the flow at {coordinate}')
                action = build_flow(before, coordinate, control.flow_steps, control.flow_title)
                operation = 'replace' if coordinate in before else 'create'
            elif control.action_name:
                controller = control.controller or (old or {}).get('Controller') or 'Keypad'
                action, _ = build_action(control.action_name, control.settings, controller, hotkey=control.hotkey)
                operation = 'replace' if coordinate in before else 'create'
            else:
                if old is None or control.controller or control.hotkey:
                    raise ValueError(f'Choose an installed action to create or replace {coordinate}')
                if control.settings is None and not (control.image_path or control.icon_query or control.auto_icon):
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
            change = {'operation': operation, 'action': (
                dict(action) if operation == 'edit' else _preview_action(action)
            )}
            destination_changed = (operation == 'edit'
                                   and any(key in (control.settings or {})
                                           and old.get('Settings', {}).get(key) != control.settings[key]
                                           for key in ('path', 'appId')))
            if (control.image_path or control.icon_query or control.auto_icon is True
                    or control.auto_icon is not False and (operation != 'edit' or destination_changed)):
                states = list(action.get('States') or [{}])
                index = control.state_index
                if not 0 <= index < len(states) or not isinstance(states[index], dict):
                    raise ValueError(f'No editable icon at state {index} on {coordinate}')
                data, icon = for_action({**action, 'States': [states[index]]},
                                        path.parent, control.icon_query, control.image_path)
                change['icon'] = {**icon, 'state_index': index}
                if data is not None:
                    image_bytes += len(data)
                    if image_bytes > live.MAX_ARCHIVE_BYTES:
                        raise ValueError('New icons exceed the live import size limit')
                    filename = uuid.uuid4().hex.upper() + '.png'
                    states[index] = {**states[index], 'Image': filename}
                    action['States'] = states
                    images[member.parent / 'Images' / filename] = data
            elif control.state_index:
                raise ValueError(f'Choose an icon when specifying a state at {coordinate}')
            actions[coordinate] = action
            changes[coordinate] = change
        edits[page] = {**doc, 'Actions': actions}
        details[page] = {'replace': update.replace, 'changes': changes,
                         'cleared': sorted(before.keys() - actions.keys())}
    preview = {'source_profile': profile, 'name': name, 'source_hashes': source_hashes,
               'pages': details}
    digest = profiles.fingerprint(json.dumps(preview, sort_keys=True, allow_nan=False).encode())
    return {**preview, 'layout_sha256': digest}, edits, images
