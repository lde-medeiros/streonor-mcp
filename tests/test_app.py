import subprocess
import unittest
from unittest.mock import patch, Mock
from streonor_mcp.app import edit_with_restart


@patch('streonor_mcp.app.sys.platform', 'win32')
class AppTests(unittest.TestCase):
    def test_relaunch_failure_reports_committed_edit(self):
        with patch('streonor_mcp.app.profiles.vendor_running', side_effect=[True, False, False, False]), patch('streonor_mcp.app.Path.is_file', return_value=True), patch('streonor_mcp.app.subprocess.run'), patch('streonor_mcp.app.subprocess.Popen', side_effect=OSError('launch denied')):
            result = edit_with_restart(lambda: {'updated': True}, True)
            self.assertTrue(result['updated'])
            self.assertFalse(result['app_relaunch_requested'])
            self.assertIn('launch denied', result['relaunch_error'])

    def test_force_close_and_relaunch(self):
        with patch('streonor_mcp.app.profiles.vendor_running', side_effect=[True, False, False, False]), patch('streonor_mcp.app.Path.is_file', return_value=True), patch('streonor_mcp.app.subprocess.run') as run, patch('streonor_mcp.app.subprocess.Popen') as launch:
            launch.return_value.wait.return_value = 0
            result = edit_with_restart(lambda: {'updated': True}, True, True)
            self.assertIn('/F', run.call_args.args[0])
            self.assertTrue(result['app_relaunch_requested'])
            launch.assert_called_once()

    @patch.dict('streonor_mcp.app.os.environ', {'STREONOR_FAST_RESTART': '1'})
    def test_fast_restart_preference_for_managed_edits(self):
        with patch('streonor_mcp.app.profiles.vendor_running', side_effect=[True, False, False]), patch('streonor_mcp.app.Path.is_file', return_value=True), patch('streonor_mcp.app.subprocess.run') as run, patch('streonor_mcp.app.subprocess.Popen') as launch:
            launch.return_value.wait.return_value = 0
            edit_with_restart(lambda: {'updated': True}, manage_app=True)
        self.assertIn('/F', run.call_args.args[0])

    def test_opt_out_does_not_touch_app(self):
        with patch('streonor_mcp.app.subprocess.run') as run:
            self.assertEqual(edit_with_restart(lambda: {'updated': True}), {'updated': True})
            run.assert_not_called()

    def test_restart_after_failed_edit(self):
        with patch('streonor_mcp.app.profiles.vendor_running', side_effect=[True, False, False, False]), patch('streonor_mcp.app.Path.is_file', return_value=True), patch('streonor_mcp.app.subprocess.run'), patch('streonor_mcp.app.subprocess.Popen') as launch:
            launch.return_value.wait.return_value = 0
            with self.assertRaises(ValueError):
                edit_with_restart(Mock(side_effect=ValueError('changed hash')), True)
            launch.assert_called_once()

    def test_close_failure_prevents_edit(self):
        edit = Mock()
        with patch('streonor_mcp.app.profiles.vendor_running', return_value=True), patch('streonor_mcp.app.Path.is_file', return_value=True), patch('streonor_mcp.app.subprocess.run', side_effect=subprocess.CalledProcessError(1, 'taskkill')):
            with self.assertRaises(subprocess.CalledProcessError):
                edit_with_restart(edit, True)
        edit.assert_not_called()
