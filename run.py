import os
from pathlib import Path
import sys

if sys.stdout is None or sys.stderr is None:
    data = Path(os.environ['LOCALAPPDATA']) / 'STREONOR-MCP'
    data.mkdir(parents=True, exist_ok=True)
    log = (data / 'server.log').open('a', encoding='utf-8', buffering=1)
    sys.stdout = sys.stderr = log

from streonor_mcp.server import main
main()
