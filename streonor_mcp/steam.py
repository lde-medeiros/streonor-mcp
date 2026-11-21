"""Find installed Steam titles and artwork without logging into Steam."""
import io
import os
from pathlib import Path
import re
import string
import sys
from functools import lru_cache
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, build_opener

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from .profiles import ICON_SIZE, fingerprint, read_bounded, read_icon


def steam_roots():
    if sys.platform == 'win32':
        import winreg

        roots = [Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Steam']
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam') as key:
                roots.insert(0, Path(winreg.QueryValueEx(key, 'SteamPath')[0]))
        except OSError:
            pass
        return tuple(dict.fromkeys(roots))
    return (Path.home() / '.local/share/Steam', Path.home() / '.steam/steam',
            Path.home() / 'Library/Application Support/Steam')


def installed_games(library_path=''):
    libraries = [Path(library_path).expanduser()] if library_path else list(steam_roots())
    if not library_path and sys.platform == 'win32':
        libraries.extend(Path(f'{drive}:/SteamLibrary') for drive in string.ascii_uppercase)

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


def app_id_from_action(action):
    path = (action.get('Settings') or {}).get('path')
    if not isinstance(path, str):
        return None
    match = re.fullmatch(r'steam://rungameid/([1-9][0-9]{0,9})', path, re.IGNORECASE)
    return match[1] if match and int(match[1]) <= 4294967295 else None


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@lru_cache(maxsize=12)
def _download_artwork(app_id, filename):
    # The app ID and asset name come from the resolver, never a user-supplied URL.
    url = f'https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{app_id}/{filename}'
    limit = 2 * 1024 * 1024
    try:
        with build_opener(_NoRedirect()).open(url, timeout=2) as response:
            if response.headers.get_content_type() not in ('image/png', 'image/jpeg'):
                return None
            data = response.read(limit + 1)
            if len(data) <= limit:
                return data
    except (URLError, OSError):
        pass
    return None


def _open_art(data):
    if data:
        with Image.open(io.BytesIO(data)) as image:
            if image.format in ('JPEG', 'PNG') and image.width * image.height <= 8_000_000:
                return image.convert('RGBA')
    return None


def artwork(app_id):
    """Compose a square from official Steam hero art and its separate logo."""
    if not re.fullmatch(r'[1-9][0-9]{0,9}', app_id) or int(app_id) > 4294967295:
        raise ValueError('Invalid Steam app ID')
    folders = [root / 'appcache' / 'librarycache' / app_id for root in steam_roots()]

    def find(*names):
        for folder in folders:
            for name in names:
                for path in (folder / name, *sorted(folder.glob('*/' + name))):
                    try:
                        if path.is_file() and (image := _open_art(read_icon(path))) is not None:
                            return image, str(path)
                    except (OSError, ValueError, Image.DecompressionBombError):
                        continue
        return None, None

    hero, hero_source = find('library_hero.jpg')
    logo, logo_source = find('logo.png')
    capsule, capsule_source = None, None
    if hero is None or logo is None:
        capsule, capsule_source = find('library_600x900.jpg', 'library_capsule.jpg',
                                       f'{app_id}_library_600x900.jpg')
    if hero is None and capsule is None:
        for name in ('library_hero.jpg', 'logo.png', 'library_600x900.jpg'):
            try:
                image = _open_art(_download_artwork(app_id, name))
            except (OSError, ValueError, Image.DecompressionBombError):
                continue
            if image is None:
                continue
            source = f'https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{app_id}/{name}'
            if name == 'library_hero.jpg':
                hero, hero_source = image, source
            elif name == 'logo.png':
                logo, logo_source = image, source
            else:
                capsule, capsule_source = image, source
            if hero is not None and logo is not None:
                break

    if logo is not None:
        bounds = logo.getchannel('A').getbbox()
        logo = logo.crop(bounds) if bounds else None
    background = hero if hero is not None else capsule
    if background is None and logo is None:
        return None
    resampling = Image.Resampling.LANCZOS
    if background is None:
        canvas = Image.new('RGBA', ICON_SIZE, '#141925')
    else:
        canvas = ImageOps.fit(background, ICON_SIZE, resampling)
        if logo is None and capsule is not None:
            canvas = canvas.filter(ImageFilter.GaussianBlur(38))
        canvas = ImageEnhance.Brightness(canvas).enhance(0.58 if logo is not None else 0.65)
    foreground = logo if logo is not None else capsule
    if foreground is not None:
        safe_area = (1020, 940) if logo is not None else (980, 1120)
        foreground = ImageOps.contain(foreground, safe_area, resampling)
        canvas.alpha_composite(foreground, ((canvas.width - foreground.width) // 2,
                                            (canvas.height - foreground.height) // 2))
    out = io.BytesIO()
    canvas.save(out, format='PNG', optimize=True)
    data = out.getvalue()
    sources = [source for source in (hero_source if hero is not None else capsule_source,
                                      logo_source if logo is not None else capsule_source) if source]
    sources = list(dict.fromkeys(sources))
    return data, {'origin': 'steam_web_artwork' if any(s.startswith('https://') for s in sources) else 'steam_local_artwork',
                  'source_paths': sources, 'sha256': fingerprint(data)}
