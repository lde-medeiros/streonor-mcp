"""Prefer supplied and real artwork before falling back to a legible label."""
import io
import itertools
from pathlib import Path
import re
from urllib.parse import urlsplit
from PIL import Image, ImageDraw, ImageFont


def label_for_action(action):
    settings = action.get('Settings', {})
    if action.get('Name') == 'Multi Action':
        return action.get('States', [{}])[0].get('Title') or 'Flow'
    apps = settings.get('applications', [])
    index = settings.get('appId')
    if type(index) is int and 0 <= index < len(apps):
        return apps[index].get('name') or action.get('Name', 'Key')
    value = settings.get('path', '')
    if isinstance(value, str) and value:
        host = urlsplit(value).hostname
        if host:
            return host.removeprefix('www.').split('.')[0]
        return Path(value).stem or 'Key'
    return action.get('States', [{}])[0].get('Title') or action.get('Name', 'Key')



def _app_icon(key):
    """Find a matching app image from the vendor's own icon cache."""
    from . import profiles
    cache = (profiles.vendor_dir() / 'images' / 'appsImage').resolve()
    if not cache.is_dir():
        return None
    for manifest in itertools.islice(profiles.ROOT.glob('*.sdProfile/manifest.json'), 64):
        try:
            path = profiles.profile_path(manifest.parent.name, root=profiles.ROOT)
            doc = profiles.parse_manifest(profiles.read_bounded(path, 2 * 1024 * 1024))
        except (OSError, ValueError):
            continue
        for action in doc['Actions'].values():
            settings = action.get('Settings') if isinstance(action, dict) else None
            apps = settings.get('applications') if isinstance(settings, dict) else None
            if not isinstance(apps, list):
                continue
            for app in apps:
                if not isinstance(app, dict):
                    continue
                name, image = app.get('name'), app.get('image')
                if not isinstance(name, str) or not isinstance(image, str):
                    continue
                if re.sub(r'[^a-z0-9]', '', name.casefold()) != key:
                    continue
                try:
                    icon = Path(image).resolve(strict=True)
                    if icon.is_relative_to(cache) and icon.is_file():
                        return str(icon)
                except (OSError, ValueError):
                    continue
    return None

def resolve(query, preferred_path=''):
    from . import profiles
    if not isinstance(query, str) or not query.strip() or len(query) > 100:
        raise ValueError('Icon query must be 1 to 100 characters')
    key = re.sub(r'[^a-z0-9]', '', query.casefold())
    if not key and not any(c.isalnum() for c in query):
        raise ValueError('Icon query must include letters or numbers')
    aliases = {'visualstudiocode': 'visualstudiocode', 'vscode': 'visualstudiocode', 'windows terminal': 'windowsterminal'}
    key = aliases.get(query.casefold(), key) or 'key'
    matches = profiles.find_icons(key, 100)
    matches.sort(key=lambda x: (re.sub(r'[^a-z0-9]', '', x['name'].casefold()) != key, str(x['path']).casefold()))
    candidates = ([{'path': preferred_path, 'name': query}] if preferred_path else []) + [m for m in matches if re.sub(r'[^a-z0-9]', '', m['name'].casefold()) == key]
    for match in candidates:
        try:
            data = profiles.normalize_icon(profiles.read_icon(match['path']), '#000000')
            # Dark monochrome SVG marks need contrast on a black key background.
            if Path(match['path']).suffix.lower() == '.svg':
                with Image.open(io.BytesIO(data)) as image:
                    rgb = image.convert('RGB')
                    if max(rgb.getextrema()[i][1] for i in range(3)) < 96:
                        source = profiles.read_icon(match['path'])
                        with Image.open(io.BytesIO(source)) as transparent:
                            mark = Image.new('RGBA', transparent.size, 'white')
                            mark.putalpha(transparent.convert('RGBA').getchannel('A'))
                            buffer = io.BytesIO()
                            mark.save(buffer, format='PNG')
                        data = profiles.normalize_icon(buffer.getvalue(), '#000000')
            return data, {'origin': 'installed', 'query': query, 'source_path': match['path'], 'sha256': profiles.fingerprint(data)}
        except (OSError, ValueError, Image.DecompressionBombError):
            if preferred_path and match['path'] == preferred_path:
                raise
    if app_icon := _app_icon(key):
        try:
            data = profiles.normalize_icon(profiles.read_icon(app_icon), '#000000')
            return data, {'origin': 'installed_app', 'query': query, 'source_path': app_icon,
                          'sha256': profiles.fingerprint(data)}
        except (OSError, ValueError, Image.DecompressionBombError):
            pass
    words = re.findall(r'[A-Za-z0-9]+', query) or ['Key']
    text = (''.join(w[0] for w in words[:3]) if len(words) > 1 else words[0][:3]).upper()
    palette = ('#18365A', '#283566', '#155548', '#562D52', '#704527')
    background = palette[int(profiles.fingerprint(query.casefold().encode())[:8], 16) % len(palette)]
    image = Image.new('RGBA', profiles.ICON_SIZE, background)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((76, 76, 1178, 1178), radius=205, outline='#ADB6C7', width=20)
    font = ImageFont.load_default(size=420)
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((1254-box[2]+box[0])//2, (1254-box[3]+box[1])//2-box[1]), text, font=font, fill='white')
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    data = buffer.getvalue()
    return data, {'origin': 'generated_label', 'needs_artwork': True, 'query': query, 'sha256': profiles.fingerprint(data)}


def for_action(action, folder, query='', image_path='', *, refresh=False):
    if image_path:
        data, info = resolve(query or label_for_action(action), image_path)
        info['origin'] = 'provided'
        return data, info
    states = action.get('States') or [{}]
    current = states[0].get('Image', '')
    from .steam import app_id_from_action, artwork
    steam_id = app_id_from_action(action)
    if not query and current and not current.startswith('Images/btn_') and not (refresh and steam_id):
        return None, {'origin': 'preserved', 'image': current}
    if steam_id and (art := artwork(steam_id)) is not None:
        return art
    settings = action.get('Settings', {})
    apps = settings.get('applications', [])
    index = settings.get('appId')
    preferred = ''
    if type(index) is int and 0 <= index < len(apps):
        candidate = apps[index].get('image', '')
        if candidate and Path(candidate).is_file():
            preferred = candidate
    return resolve(query or label_for_action(action), preferred)
