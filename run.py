import os
from pathlib import Path
import sys

if sys.stdout is None or sys.stderr is None:
    from streonor_mcp.paths import data_dir
    data = data_dir()
    data.mkdir(parents=True, exist_ok=True)
    log = (data / 'server.log').open('a', encoding='utf-8', buffering=1)
    sys.stdout = sys.stderr = log

from streonor_mcp.server import main
main()
