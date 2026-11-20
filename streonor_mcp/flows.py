"""Native sequential Multi Actions, based on observed vendor profile structure."""
import copy
import json
import uuid


def build_flow(actions, coordinate, steps, title):
    if not isinstance(steps, list) or not 1 <= len(steps) <= 32:
        raise ValueError('Provide 1 to 32 flow steps')
    if not isinstance(title, str) or not title.strip() or len(title) > 80:
        raise ValueError('Provide a flow title of 1 to 80 characters')
    children = []
    for step in steps:
        if not isinstance(step, dict) or set(step) - {'source_coordinate', 'action_name', 'settings', 'delay_ms', 'hotkey'}:
            raise ValueError('Steps accept source_coordinate or action_name, settings, delay_ms and hotkey')
        if bool(step.get('source_coordinate')) == bool(step.get('action_name')):
            raise ValueError('Choose exactly one source_coordinate or action_name for each step')
        if step.get('action_name'):
            from .catalog import build_action
            source, _ = build_action(step['action_name'], step.get('settings'), in_flow=True)
        else:
            source = actions.get(step.get('source_coordinate'))
        if not isinstance(source, dict) or 'Actions' in source or not isinstance(source.get('Settings'), dict) or not isinstance(source.get('States'), list):
            raise ValueError('Each source must be an existing single action on this page')
        overrides = step.get('settings', {})
        delay = step.get('delay_ms', 0)
        if not isinstance(overrides, dict) or type(delay) is not int or not 0 <= delay <= 60000:
            raise ValueError('Settings must be an object; delay_ms must be 0 to 60000')
        action = copy.deepcopy(source)
        for key, value in ({} if step.get('action_name') else overrides).items():
            if key not in action['Settings'] or type(value) is not type(action['Settings'][key]):
                raise ValueError('Flow setting overrides must match existing setting names and JSON types')
            json.dumps(value, allow_nan=False)
            action['Settings'][key] = value
        if 'hotkey' in step:
            if action.get('UUID') != 'com.hotspot.streamdock.system.hotkey' or 'Hotkeys' in overrides:
                raise ValueError('A hotkey step requires a native Hotkey source and no Hotkeys override')
            from .hotkeys import settings_for_chord
            action['Settings'] = settings_for_chord(action['Settings'], step['hotkey'])
        if action.get('UUID') == 'com.hotspot.streamdock.system.openApps':
            selected = action['Settings'].get('appId')
            apps = action['Settings'].get('applications', [])
            if type(selected) is not int or not 0 <= selected < len(apps):
                raise ValueError('Selected application is outside the source action application list')
        action['ActionID'] = str(uuid.uuid4())
        action['Controller'] = ''
        action['Settings']['delay'] = delay
        children.append(action)
    states = copy.deepcopy(actions.get(coordinate, {}).get('States', [{'Image': ''}]))
    if not states or not isinstance(states[0], dict):
        states = [{'Image': ''}]
    states[0]['Title'] = title
    return {'ActionID': str(uuid.uuid4()), 'Actions': children,
            'Controller': actions.get(coordinate, {}).get('Controller', 'Keypad'),
            'Name': 'Multi Action', 'Settings': {'cycleDelay': 100, 'cycleMode': 0, 'cycleNumber': 1, 'enablingCycle': 0},
            'State': 0, 'States': states, 'UUID': 'com.hotspot.streamdock.multiactions.routine'}
