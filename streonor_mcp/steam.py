"""Read local Steam app manifests without logging into Steam."""
import os
from pathlib import Path
import re
import string
import sys

from .profiles import read_bounded


def installed_games(library_path=''):
    if library_path:
        libraries = [Path(library_path).expanduser()]
    elif sys.platform == 'win32':
        import winreg

        libraries = [Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Steam']
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam') as key:
                libraries.append(Path(winreg.QueryValueEx(key, 'SteamPath')[0]))
        except OSError:
            pass
        libraries.extend(Path(f'{drive}:/SteamLibrary') for drive in string.ascii_uppercase)
    else:
        libraries = [Path.home() / '.local/share/Steam', Path.home() / '.steam/steam',
                     Path.home() / 'Library/Application Support/Steam']

    app_dirs = set()
    for library in libraries:
        apps = library if library.name.casefold() == 'steamapps' else library / 'steamapps'
        if not apps.is_dir():
            continue
        app_dirs.add(apps.resolve())
        try:
            config = read_bounded(apps / 'libraryfolders.vdf', 2 * 1024 * 1024).decode('utf-8-sig')
            for path in re.findall(r'^\s*"path"\s+"([^"\r\n]+)"', config, re.MULTILINE):
                candidate = Path(path.replace('\\\\', '\\')) / 'steamapps'
                if candidate.is_absolute() and candidate.is_dir():
                    app_dirs.add(candidate.resolve())
        except (OSError, ValueError):
            continue
    games = {}
    for apps in sorted(app_dirs):
        for manifest in apps.glob('appmanifest_*.acf'):
            app_id = manifest.stem.removeprefix('appmanifest_')
            if not re.fullmatch(r'[1-9][0-9]{0,9}', app_id) or app_id == '228980':
                continue
            try:
                raw = read_bounded(manifest, 128 * 1024).decode('utf-8-sig')
            except (OSError, ValueError):
                continue
            fields = dict(re.findall(r'^\s*"(appid|name|StateFlags|LastPlayed)"\s+"((?:\\.|[^"\\\r\n])*)"', raw, re.MULTILINE))
            if fields.get('appid') != app_id or not fields.get('name'):
                continue
            flags = fields.get('StateFlags', '')
            if not flags.isdecimal() or not int(flags) & 4:
                continue
            name = fields['name'].replace(r'\"', '"').replace('\\\\', '\\')
            last_played = fields.get('LastPlayed', '')
            game = {'app_id': app_id, 'name': name, 'launch_uri': f'steam://rungameid/{app_id}',
                    'last_played': int(last_played) if last_played.isdecimal() else 0}
            if app_id not in games or games[app_id]['last_played'] < game['last_played']:
                games[app_id] = game
    return sorted(games.values(), key=lambda game: (-game['last_played'], game['name'].casefold(), game['app_id']))
