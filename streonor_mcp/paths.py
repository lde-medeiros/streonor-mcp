"""Platform paths; overrides support exported profiles and vendor installations."""
import os
from pathlib import Path
import sys


def data_dir():
    if os.environ.get('STREONOR_DATA_DIR'):
        return Path(os.environ['STREONOR_DATA_DIR']).expanduser().resolve()
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
    return base / 'STREONOR-MCP'


def vendor_dir():
    if os.environ.get('STREONOR_PROFILES_DIR'):
        return Path(os.environ['STREONOR_PROFILES_DIR']).expanduser().resolve().parent
    if sys.platform == 'win32':
        return Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / 'HotSpot' / 'StreamDock'
    # Vendor installation layouts outside Windows are not verified.
    return data_dir() / 'vendor'


def profiles_dir():
    return Path(os.environ.get('STREONOR_PROFILES_DIR', vendor_dir() / 'profiles')).expanduser().resolve()


def icons_dir():
    return Path(os.environ.get('STREONOR_ICONS_DIR', vendor_dir() / 'icons')).expanduser().resolve()
