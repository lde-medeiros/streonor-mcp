"""Construct native action slots from installed Toolbox metadata, without user templates."""
import copy
import json
import uuid


def build_action(name, settings=None, controller='Keypad', in_flow=False):
    from .profiles import list_installed_actions
    if not isinstance(name, str) or not name.strip():
        raise ValueError('Provide an installed action name or UUID')
    query = name.strip().casefold()
    installed = list_installed_actions()
    matches = [a for a in installed if query == a['uuid'].casefold()]
    if not matches:
        matches = [a for a in installed if query in ((a['name'] or '').casefold(), ((a['plugin'] or '') + '/' + (a['name'] or '')).casefold())]
    if len(matches) != 1:
        raise ValueError('Action not found or ambiguous. Use an exact UUID or plugin/name from list_available_actions')
    metadata = matches[0]
    if metadata.get('only_in_flows') and not in_flow:
        raise ValueError('This Toolbox item can only be added inside a flow')
    if in_flow and metadata.get('supported_in_flows') is False:
        raise ValueError('This Toolbox item declares that it does not support flows')
    if controller not in ('Keypad', 'Knob', 'SecondaryScreen', 'Information'):
        raise ValueError('Controller must be Keypad, Knob, SecondaryScreen or Information')
    if metadata.get('controllers') and controller not in metadata['controllers']:
        raise ValueError('Action does not declare support for this controller')
    defaults = copy.deepcopy(metadata.get('default_settings') or {})
    if metadata['uuid'] == 'com.hotspot.streamdock.system.website':
        defaults = {'browser': '', 'openInBrowser': True, 'path': ''}
    elif metadata['uuid'] == 'com.hotspot.streamdock.system.hotkey':
        key = {'KeyCmd': False, 'KeyCtrl': False, 'KeyModifiers': 65536, 'KeyOption': False, 'KeyShift': False, 'NativeCode': -1, 'QTKeyCode': -1, 'RKeyCmd': False, 'RKeyCtrl': False, 'RKeyOption': False, 'RKeyShift': False, 'VKeyCode': -1}
        defaults = {'Coalesce': True, 'Hotkeys': [copy.deepcopy(key) for _ in range(3)]}
    if settings is not None:
        if not isinstance(settings, dict):
            raise ValueError('Action settings must be an object')
        for key, value in settings.items():
            if key in defaults and type(defaults[key]) is not type(value):
                raise ValueError('Settings must match declared default JSON types')
            defaults[key] = value
    json.dumps(defaults, allow_nan=False)
    states = copy.deepcopy(metadata.get('states') or [{'Image': ''}])
    return {'ActionID': str(uuid.uuid4()), 'Controller': '' if in_flow else controller,
            'Name': metadata['name'], 'Settings': defaults, 'State': 0,
            'States': states, 'UUID': metadata['uuid']}, {
                'uuid': metadata['uuid'], 'name': metadata['name'],
                'execution_verified': False,
                'configuration_note': 'Created from installed metadata. Required plugin-specific settings and runtime connections must be verified in the native app.'}
