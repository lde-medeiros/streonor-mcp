"""Edit a running scene through the Windows app's own property inspector."""
import io
import os
from pathlib import Path
import sys
import tempfile
import time

from PIL import Image

from . import live, profiles


def _one(items, description):
    matches = list(items)
    if len(matches) != 1:
        raise RuntimeError(f'Expected one {description} in STREONOR, found {len(matches)}')
    return matches[0]


def _wait_for(find, description):
    for _ in range(30):
        result = find()
        if result:
            return result
        time.sleep(0.2)
    raise RuntimeError(f'STREONOR did not show {description}')


def _matches_icon(folder, filename, expected):
    if not filename:
        return False
    images = folder / 'Images'
    try:
        asset = (images / Path(filename).name).resolve(strict=True)
        if asset.parent != images.resolve() or asset.suffix.lower() != '.png':
            return False
        with Image.open(io.BytesIO(profiles.read_bounded(asset, 16 * 1024 * 1024))) as saved:
            return saved.size == (1254, 1254) and saved.convert('RGBA').tobytes() == expected
    except (OSError, ValueError, Image.DecompressionBombError):
        return False


def _only_icon_changed(before, after, coordinate, filename):
    action = before['Actions'][coordinate]
    edited = after['Actions'].get(coordinate, {})
    # STREONOR serializes this native dial's inferred controller as an empty string.
    controller = edited.get('Controller')
    if controller not in (action.get('Controller'), ''):
        return False
    expected = {**before, 'Actions': {**before['Actions'], coordinate: {
        **action, 'Controller': controller, 'States': [{**action['States'][0], 'Image': filename}]
    }}}
    return after == expected


def edit_icon(profile, page, coordinate, expected_sha256, image_path, expected_image_sha256, state_index, operation):
    if sys.platform != 'win32':
        raise RuntimeError('In-place live editing requires the Windows STREONOR desktop')
    try:
        from pywinauto import Application, Desktop
        import win32con
        import win32gui
        import win32process
    except ImportError as error:
        raise RuntimeError('Install streonor-mcp[live] to use in-place live editing on Windows') from error

    root = profiles.ROOT
    if root.resolve() != (Path(os.environ['APPDATA']) / 'HotSpot' / 'StreamDock' / 'profiles').resolve():
        raise ValueError('In-place live editing requires the default STREONOR profile directory')
    doc, digest = profiles.read_manifest(profile)
    action = doc['Actions'].get(coordinate, {})
    if digest != expected_sha256:
        raise ValueError('Scene changed since preview')
    if (doc.get('DeviceUUID') != 'StreonorS6' or page not in ('', profile)
            or doc.get('Pages') != {'Current': profile, 'Pages': [profile]}
            or coordinate != '4,1' or state_index != 0
            or action.get('UUID') != 'com.hotspot.streamdock.profile.rotate'
            or action.get('Name') != 'Scene Shift' or action.get('Controller') not in ('Knob', '')
            or len(action.get('States', [])) != 1):
        raise ValueError('In-place icon editing currently supports Scene Shift at 4,1 on a single-page S6 Mini scene')
    if sum(p['name'] == doc['Name'] for p in profiles.list_profiles()) != 1:
        raise ValueError('Scene name must uniquely identify the target in STREONOR')
    restore_default = operation == 'clear_icon'
    pid = live._vendor_pid()
    if not pid:
        raise RuntimeError('Open STREONOR before requesting live editing')
    pid = int(pid)
    source_path = profiles.profile_path(profile)
    old_image = action['States'][0].get('Image')
    if restore_default:
        already_applied = old_image == ''
    else:
        image = profiles.read_icon(image_path)
        if profiles.fingerprint(image) != expected_image_sha256:
            raise ValueError('Image changed since preview')
        normalized = profiles.normalize_icon(image)
        with Image.open(io.BytesIO(normalized)) as prepared:
            expected_pixels = prepared.convert('RGBA').tobytes()
        already_applied = _matches_icon(source_path.parent, old_image, expected_pixels)
    if already_applied:
        return {'updated': False, 'profile': profile, 'name': doc['Name'], 'coordinate': coordinate,
                'new_sha256': digest, 'icon': old_image, 'app_restarted': False}
    app = Application(backend='uia').connect(process=pid, timeout=3)
    window = _one((w for w in app.windows(visible_only=True)
                   if w.element_info.class_name == 'StreamDock'
                   and w.window_text().startswith('Stream Controller')), 'main window')
    if not window.is_enabled() or window.is_minimized():
        raise RuntimeError('Show the STREONOR main window and dismiss any open dialogs')
    scene = _one((s for s in window.descendants(control_type='RadioButton', class_name='SDRadioButton')
                  if s.is_visible() and s.window_text() == doc['Name']), 'scene selector')
    if scene.get_toggle_state() != 1:
        raise RuntimeError(f'Select {doc["Name"]} in STREONOR before editing it live')
    canvas = _one((c for c in window.descendants(class_name='SDActionCanvasWidget') if c.is_visible()),
                  'visible control grid')
    knobs = [k for k in canvas.descendants(class_name='SDKnobBackground') if k.is_visible()]
    if len(knobs) != 3:
        raise RuntimeError('The visible S6 Mini dial layout does not match the verified layout')
    target = max(knobs, key=lambda k: k.rectangle().left)
    label = _one(target.descendants(class_name='SDActionCanvasLabel'), 'control at 4,1')
    window.set_focus()
    if win32gui.GetForegroundWindow() != window.handle:
        raise RuntimeError('Could not focus the STREONOR window')
    label.click_input()
    inspector = _one((i for i in window.descendants(class_name='SDPropertyInspectorWidget') if i.is_visible()),
                     'property inspector')
    _one((t for t in inspector.descendants(control_type='Text')
          if t.is_visible() and t.window_text() == 'Scene Shift'), 'Scene Shift property inspector')
    icon = _one((i for i in inspector.descendants(class_name='SDActionPropertyInspectorLabel')
                 if i.is_visible()), 'action icon')
    _one(icon.children(control_type='Button'), 'icon menu button').invoke()
    menu = _wait_for(lambda: [w for w in app.windows(visible_only=True)
                              if w.element_info.class_name == 'QMenu'], 'the icon menu')
    command = 'Reset to default' if restore_default else 'Select Local File'
    item = _one((i for i in _one(menu, 'icon menu').descendants(control_type='MenuItem')
                 if i.window_text() == command and i.is_enabled()), command)

    backup = profiles.BACKUPS / f'{profile}--{profile}--{time.time_ns()}.json'
    original = profiles.read_bounded(source_path, profiles.MAX_MANIFEST_BYTES)
    if profiles.fingerprint(original) != expected_sha256 or scene.get_toggle_state() != 1:
        raise ValueError('Scene changed before applying the icon edit')
    profiles.write_new_file(backup, original)
    if restore_default:
        item.click_input()
    else:
        _choose_icon_file(item, normalized, pid, Desktop, win32gui, win32con, win32process)

    def read_saved():
        try:
            updated, new_digest = profiles.read_manifest(profile)
        except (FileNotFoundError, ValueError):
            return None
        if new_digest != expected_sha256:
            return updated, new_digest
        return None

    updated, new_digest = _wait_for(read_saved, 'a saved icon change')
    after = updated['Actions'].get(coordinate, {})
    new_image = (after.get('States') or [{}])[0].get('Image')
    saved_as_requested = (new_image == '' if restore_default
                          else _matches_icon(source_path.parent, new_image, expected_pixels))
    if (not saved_as_requested or new_image == old_image
            or not _only_icon_changed(doc, updated, coordinate, new_image)
            or live._vendor_pid() != str(pid)):
        raise RuntimeError(f'STREONOR saved changes, but the icon edit could not be fully verified. Backup: {backup}')
    return {'updated': True, 'profile': profile, 'name': doc['Name'], 'coordinate': coordinate,
            'new_sha256': new_digest, 'icon': new_image, 'backup': str(backup), 'app_restarted': False}


def _choose_icon_file(item, normalized, pid, Desktop, win32gui, win32con, win32process):
    with tempfile.TemporaryDirectory(prefix='streonor-live-icon-') as temp:
        icon_file = Path(temp) / 'icon.png'
        icon_file.write_bytes(normalized)

        def dialogs(title, class_name):
            matches = []
            def inspect(hwnd, _):
                if (win32process.GetWindowThreadProcessId(hwnd)[1] == pid
                        and win32gui.IsWindowVisible(hwnd)
                        and win32gui.GetClassName(hwnd) == class_name
                        and win32gui.GetWindowText(hwnd) == title):
                    matches.append(hwnd)
                return True
            win32gui.EnumWindows(inspect, None)
            return matches

        def picker():
            return dialogs('Select file', '#32770')

        if picker():
            raise RuntimeError('A STREONOR file picker is already open')
        item.click_input()
        dialog = _one(_wait_for(picker, 'the native icon file picker'), 'native icon file picker')
        edits = []
        def find_edit(hwnd, _):
            if win32gui.GetClassName(hwnd) == 'Edit' and win32gui.GetDlgCtrlID(hwnd) == 1148:
                edits.append(hwnd)
            return True
        try:
            win32gui.EnumChildWindows(dialog, find_edit, None)
            field = _one(edits, 'native File name field')
            win32gui.SendMessage(field, win32con.WM_SETTEXT, 0, str(icon_file))
            open_button = win32gui.GetDlgItem(dialog, win32con.IDOK)
            if not open_button or not win32gui.IsWindowEnabled(open_button):
                raise RuntimeError('The native icon picker Open button is unavailable')
            win32gui.PostMessage(dialog, win32con.WM_COMMAND, win32con.IDOK, open_button)
            _wait_for(lambda: not win32gui.IsWindow(dialog), 'the icon picker to close')
        finally:
            if win32gui.IsWindow(dialog):
                win32gui.PostMessage(dialog, win32con.WM_COMMAND, win32con.IDCANCEL, 0)

        def cropping():
            return dialogs('Image cropping', 'Qt5152QWindowIcon')

        crop = _one(_wait_for(cropping, 'the image cropping window'), 'image cropping window')
        try:
            crop_window = Desktop(backend='uia').window(handle=crop).wrapper_object()
            original_button = _one((b for b in crop_window.descendants(control_type='Button')
                                    if b.window_text() == 'Original image' and b.is_enabled()),
                                   'Original image button')
            if win32gui.GetForegroundWindow() != crop:
                raise RuntimeError('The image cropping window must be in the foreground')
            original_button.click_input()
            time.sleep(0.25)
            if win32gui.IsWindow(crop):
                ok = _one((b for b in crop_window.descendants(control_type='Button')
                           if b.window_text() == 'Ok' and b.is_enabled()), 'crop confirmation button')
                if win32gui.GetForegroundWindow() != crop:
                    raise RuntimeError('The image cropping window lost focus')
                ok.click_input()
                _wait_for(lambda: not win32gui.IsWindow(crop), 'the crop dialog to close')
        finally:
            if win32gui.IsWindow(crop):
                win32gui.PostMessage(crop, win32con.WM_CLOSE, 0, 0)
