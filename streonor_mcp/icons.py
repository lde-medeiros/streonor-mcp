"""Local icon matching and a deterministic fallback with no network requests."""
import io
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
    words = re.findall(r'[A-Za-z0-9]+', query) or ['Key']
    text = (''.join(w[0] for w in words[:3]) if len(words) > 1 else words[0][:3]).upper()
    image = Image.new('RGBA', (1254, 1254), '#000000')
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=360)
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((1254-box[2]+box[0])//2, (1254-box[3]+box[1])//2-box[1]), text, font=font, fill='white')
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    data = buffer.getvalue()
    return data, {'origin': 'generated_label', 'query': query, 'sha256': profiles.fingerprint(data)}


def for_action(action, folder, query='', image_path=''):
    if image_path:
        data, info = resolve(query or label_for_action(action), image_path)
        info['origin'] = 'provided'
        return data, info
    states = action.get('States') or [{}]
    current = states[0].get('Image', '')
    if not query and current and not current.startswith('Images/btn_'):
        return None, {'origin': 'preserved', 'image': current}
    settings = action.get('Settings', {})
    apps = settings.get('applications', [])
    index = settings.get('appId')
    preferred = ''
    if type(index) is int and 0 <= index < len(apps):
        candidate = apps[index].get('image', '')
        if candidate and Path(candidate).is_file():
            preferred = candidate
    return resolve(query or label_for_action(action), preferred)
