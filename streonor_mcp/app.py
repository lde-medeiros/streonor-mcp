"""Opt-in Windows app lifecycle around guarded profile edits."""
import os
from pathlib import Path
import subprocess
import time
import sys
from . import profiles


def edit_with_restart(edit, manage_app=False, force_close=False):
    if manage_app and sys.platform != 'win32':
        raise RuntimeError('Automatic app restart is only verified on Windows; close the vendor app manually and use manage_app=False')
    if not manage_app or not profiles.vendor_running():
        return edit()
    exe = Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Streonor' / 'Streonor.exe'
    if not exe.is_file():
        raise RuntimeError('Cannot find STREONOR executable to reopen; no edit attempted')
    result = None
    try:
        # Force is opt-in because it can discard changes held only in memory.
        command = ['taskkill', '/IM', 'Streonor.exe']
        if force_close:
            command.append('/F')
        subprocess.run(command, capture_output=True, timeout=10,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), check=True)
        for _ in range(20):
            if not profiles.vendor_running():
                break
            time.sleep(0.25)
        if profiles.vendor_running():
            raise RuntimeError('STREONOR did not exit; no edit attempted')
        # The existing hash check catches changes saved by the app during exit.
        result = edit()
        return result
    finally:
        if not profiles.vendor_running():
            try:
                # Keep the app alive when a stdio MCP client ends its process job.
                flags = getattr(subprocess, 'DETACHED_PROCESS', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0) | getattr(subprocess, 'CREATE_BREAKAWAY_FROM_JOB', 0)
                subprocess.Popen([str(exe)], cwd=str(exe.parent), creationflags=flags)
                if result is not None:
                    result['app_relaunch_requested'] = True
            except OSError as error:
                if result is not None:
                    result['app_relaunch_requested'] = False
                    result['relaunch_error'] = str(error)

