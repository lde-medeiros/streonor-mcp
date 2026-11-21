"""Opt-in Windows app lifecycle around guarded profile edits."""
import os
from pathlib import Path
import subprocess
import time
import sys
import logging
from . import profiles


def _request_relaunch(exe):
    # Launch through the desktop shell so the app outlives the MCP process.
    launch = subprocess.Popen(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
         "$ErrorActionPreference = 'Stop'; "
         "$shell = New-Object -ComObject Shell.Application; $handle = 0; "
         "$desktop = $shell.Windows().FindWindowSW(0, 0, 8, [ref]$handle, 1); "
         "if ($null -eq $desktop) { throw 'Missing desktop shell' }; "
         "$exe = $env:STREONOR_RELAUNCH_EXE; "
         "$desktop.Document.Application.ShellExecute($exe, '', (Split-Path -LiteralPath $exe), 'open', 1); "
         "for ($i = 0; $i -lt 30; $i++) { "
         "if (Get-Process Streonor -ErrorAction SilentlyContinue) { exit 0 }; "
         "Start-Sleep -Milliseconds 100 }; throw 'STREONOR did not start'"],
        env={**os.environ, 'STREONOR_RELAUNCH_EXE': str(exe)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if launch.wait(timeout=5) != 0:
        raise OSError('Windows could not start STREONOR')


def edit_with_restart(edit, manage_app=False, force_close=False):
    if force_close and not manage_app:
        raise ValueError('force_close requires manage_app=True')
    if manage_app and sys.platform != 'win32':
        raise RuntimeError('Automatic app restart is only verified on Windows; close the vendor app manually and use manage_app=False')
    if not manage_app or not profiles.vendor_running():
        return edit()
    exe = Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Streonor' / 'Streonor.exe'
    if not exe.is_file():
        raise RuntimeError('Cannot find STREONOR executable to reopen; no edit attempted')
    result = None
    failure = None
    try:
        # Fast restart is opt-in because it can discard changes held only in memory.
        command = ['taskkill', '/IM', 'Streonor.exe']
        if force_close or os.environ.get('STREONOR_FAST_RESTART') == '1':
            command.append('/F')
        subprocess.run(command, capture_output=True, timeout=10,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), check=True)
        for _ in range(20):
            if not profiles.vendor_running():
                break
            time.sleep(0.25)
        else:
            raise RuntimeError('STREONOR did not exit; no edit attempted')
        # The existing hash check catches changes saved by the app during exit.
        result = edit()
        return result
    except Exception as error:
        failure = error
        raise
    finally:
        try:
            if not profiles.vendor_running():
                _request_relaunch(exe)
                if result is not None:
                    result['app_relaunch_requested'] = True
        except (OSError, subprocess.SubprocessError) as error:
            logging.getLogger(__name__).error('Could not relaunch STREONOR: %s', error)
            if result is not None:
                result['app_relaunch_requested'] = False
                result['relaunch_error'] = str(error)
            elif failure is not None:
                failure.add_note(f'Could not relaunch STREONOR: {error}')

