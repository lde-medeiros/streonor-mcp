"""Rasterize bounded, self-contained icon SVGs without external resources."""
import re
import math
import xml.etree.ElementTree as ET
import resvg_py


def render(data):
    if len(data) > 2 * 1024 * 1024 or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('SVG must be self-contained and no larger than 2 MiB')
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise ValueError('Invalid SVG') from error
    if root.tag.split('}')[-1] != 'svg':
        raise ValueError('Not an SVG image')
    for element in root.iter():
        if element.tag.split('}')[-1] in ('script', 'foreignObject', 'image', 'style', 'text'):
            raise ValueError('SVG contains unsupported active or external content')
        for key, value in element.attrib.items():
            if (key.split('}')[-1] == 'href' and not value.startswith('#')) or re.search(r'url\s*\(', value, re.I):
                raise ValueError('SVG resource references are not supported')
    try:
        if 'viewBox' in root.attrib:
            values = [float(x) for x in re.split(r'[ ,]+', root.attrib['viewBox'].strip())]
            if len(values) != 4 or not all(math.isfinite(x) for x in values):
                raise ValueError
            width, height = values[2:]
        else:
            width = float(root.attrib['width'].removesuffix('px'))
            height = float(root.attrib['height'].removesuffix('px'))
        if not math.isfinite(width) or not math.isfinite(height) or width <= 0 or height <= 0:
            raise ValueError
    except (KeyError, ValueError) as error:
        raise ValueError('SVG needs a valid viewBox or numeric width and height') from error
    scale = min(1254 / width, 1254 / height)
    return resvg_py.svg_to_bytes(svg_string=data.decode('utf-8-sig'), width=max(1, int(width * scale)), height=max(1, int(height * scale)), skip_system_fonts=True)
