import os
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from streonor_mcp import paths, profiles
from streonor_mcp.app import edit_with_restart


class PlatformTests(unittest.TestCase):
    def test_paths_do_not_depend_on_working_directory(self):
        home = Path.home()
        for platform in ('win32', 'darwin', 'linux'):
            with self.subTest(platform=platform), patch.dict(os.environ, {}, clear=True), patch('streonor_mcp.paths.sys.platform', platform), patch('streonor_mcp.paths.Path.home', return_value=home):
                self.assertTrue(paths.profiles_dir().is_absolute())
                self.assertTrue(paths.icons_dir().is_absolute())
                self.assertTrue(paths.data_dir().is_absolute())

    def test_explicit_paths(self):
        with patch.dict(os.environ, {'STREONOR_PROFILES_DIR': str(Path.home() / 'exported-profiles'), 'STREONOR_DATA_DIR': str(Path.home() / 'mcp-data')}):
            self.assertEqual(paths.profiles_dir(), Path.home() / 'exported-profiles')
            self.assertEqual(paths.data_dir(), Path.home() / 'mcp-data')

    def test_unix_process_check_and_fail_closed(self):
        with patch('streonor_mcp.profiles.sys.platform', 'linux'), patch('streonor_mcp.profiles.subprocess.run', return_value=Mock(stdout='/opt/Streonor\n')):
            self.assertTrue(profiles.vendor_running())
        with patch('streonor_mcp.profiles.sys.platform', 'darwin'), patch('streonor_mcp.profiles.subprocess.run', side_effect=OSError('ps unavailable')):
            with self.assertRaises(OSError):
                profiles.vendor_running()

    def test_non_windows_restart_refuses_before_edit(self):
        edit = Mock()
        with patch('streonor_mcp.app.sys.platform', 'darwin'):
            with self.assertRaises(RuntimeError):
                edit_with_restart(edit, True)
        edit.assert_not_called()
