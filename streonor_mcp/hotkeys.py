"""Keypad chords using the observed native STREONOR Hotkeys record format."""
import copy
import re


def settings_for_chord(template, chord):
    if not isinstance(chord, str) or len(chord) > 80:
        raise ValueError('Provide one key combination such as Ctrl+Shift+P')
    parts = [p.strip().casefold() for p in chord.split('+')]
    if not parts or any(not p for p in parts):
        raise ValueError('Invalid hotkey combination')
    aliases = {'control': 'ctrl', 'option': 'alt', 'cmd': 'win', 'super': 'win'}
    parts = [aliases.get(p, p) for p in parts]
    modifiers = set(parts[:-1])
    if len(modifiers) != len(parts)-1 or modifiers - {'ctrl', 'alt', 'shift', 'win'}:
        raise ValueError('Use modifiers followed by exactly one key')
    key = parts[-1]
    named = {'enter': 13, 'tab': 9, 'escape': 27, 'esc': 27, 'space': 32, 'backspace': 8, 'delete': 46, 'insert': 45, 'home': 36, 'end': 35, 'pageup': 33, 'pagedown': 34, 'left': 37, 'up': 38, 'right': 39, 'down': 40}
    if len(key) == 1 and key.isascii() and key.isalnum():
        code = ord(key.upper())
    elif re.fullmatch(r'f(?:[1-9]|1[0-9]|2[0-4])', key):
        code = 111 + int(key[1:])
    elif key in named:
        code = named[key]
    else:
        raise ValueError('Unsupported hotkey. Use a letter, digit, F1-F24 or a named navigation key')
    entries = template.get('Hotkeys')
    if not isinstance(entries, list) or not entries or not isinstance(entries[0], dict):
        raise ValueError('Hotkey source has no native Hotkeys template')
    result = copy.deepcopy(template)
    first = copy.deepcopy(entries[0])
    required = {'KeyCtrl', 'KeyOption', 'KeyShift', 'KeyCmd', 'VKeyCode'}
    if not required.issubset(first):
        raise ValueError('Unrecognized native hotkey template')
    for field, modifier in [('KeyCtrl', 'ctrl'), ('KeyOption', 'alt'), ('KeyShift', 'shift'), ('KeyCmd', 'win')]:
        first[field] = modifier in modifiers
    first['VKeyCode'] = code
    for field in ('RKeyCtrl', 'RKeyOption', 'RKeyShift', 'RKeyCmd'):
        if field in first:
            first[field] = False
    for field in ('NativeCode', 'QTKeyCode'):
        if field in first:
            first[field] = -1
    result['Hotkeys'] = [first]
    # Native files retain unused slots. Clear them instead of copying dial bindings.
    for entry in entries[1:]:
        unused = copy.deepcopy(first)
        unused['VKeyCode'] = -1
        for field in required - {'VKeyCode'}:
            unused[field] = False
        result['Hotkeys'].append(unused)
    result['Coalesce'] = True
    return result
