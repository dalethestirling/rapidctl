#!/usr/bin/env python
"""Test the OSX connector functionality."""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.bootstrap.connectors.osx import OSXConnector

import pytest

@pytest.mark.requires_podman
class TestOSXConnector(unittest.TestCase):
    def setUp(self):
        self.connector = OSXConnector()

    @patch('shutil.which')
    def test_is_podman_installed(self, mock_which):
        """Test detection of podman executable."""
        mock_which.return_value = '/usr/local/bin/podman'
        self.assertTrue(self.connector.is_podman_installed())

        mock_which.return_value = None
        self.assertFalse(self.connector.is_podman_installed())

    @patch('rapidctl.bootstrap.connectors.osx.OSXConnector.is_podman_installed')
    def test_setup_not_installed(self, mock_installed):
        """Test setup fails when podman is not installed."""
        mock_installed.return_value = False
        self.assertFalse(self.connector.setup())

    @patch('rapidctl.bootstrap.connectors.osx.OSXConnector.detect_socket')
    @patch('rapidctl.bootstrap.connectors.osx.OSXConnector.ensure_podman_running')
    @patch('rapidctl.bootstrap.connectors.osx.OSXConnector.is_podman_installed')
    def test_setup_already_running(self, mock_installed, mock_running, mock_detect):
        """Test setup succeeds immediately if podman is installed and running."""
        mock_installed.return_value = True
        mock_running.return_value = True
        mock_detect.return_value = '/fake/socket'
        
        self.assertTrue(self.connector.setup())
        mock_detect.assert_called_once()
        mock_running.assert_called_once()

    @patch('builtins.input')
    @patch('subprocess.run')
    @patch('time.sleep')
    @patch('rapidctl.bootstrap.connectors.osx.OSXConnector.detect_socket')
    @patch('rapidctl.bootstrap.connectors.osx.OSXConnector.ensure_podman_running')
    @patch('rapidctl.bootstrap.connectors.osx.OSXConnector.is_podman_installed')
    def test_setup_start_machine_yes(self, mock_installed, mock_running, mock_detect, mock_sleep, mock_run, mock_input):
        """Test setup prompts and starts podman machine successfully."""
        mock_installed.return_value = True
        # First check is False (not running), second check is True (running after start)
        mock_running.side_effect = [False, True]
        mock_input.return_value = 'y'
        mock_detect.return_value = '/fake/socket'
        
        self.assertTrue(self.connector.setup())
        
        mock_input.assert_called_once()
        mock_run.assert_called_once_with(
            ["podman", "machine", "start"],
            check=True,
            capture_output=True,
            text=True
        )
        self.assertEqual(mock_running.call_count, 2)
        mock_detect.assert_called_once()

    @patch('builtins.input')
    @patch('rapidctl.bootstrap.connectors.osx.OSXConnector.ensure_podman_running')
    @patch('rapidctl.bootstrap.connectors.osx.OSXConnector.is_podman_installed')
    def test_setup_start_machine_no(self, mock_installed, mock_running, mock_input):
        """Test setup fails and aborts if user declines to start machine."""
        mock_installed.return_value = True
        mock_running.return_value = False
        mock_input.return_value = 'n'
        
        self.assertFalse(self.connector.setup())
        mock_input.assert_called_once()

    @patch('builtins.input')
    @patch('subprocess.run')
    @patch('time.sleep')
    @patch('rapidctl.bootstrap.connectors.osx.OSXConnector.ensure_podman_running')
    @patch('rapidctl.bootstrap.connectors.osx.OSXConnector.is_podman_installed')
    def test_setup_start_machine_fails(self, mock_installed, mock_running, mock_sleep, mock_run, mock_input):
        """Test setup fails if starting podman machine throws an error."""
        import subprocess
        mock_installed.return_value = True
        mock_running.return_value = False
        mock_input.return_value = 'y'
        mock_run.side_effect = subprocess.CalledProcessError(1, ["podman", "machine", "start"], stderr="error")
        
        self.assertFalse(self.connector.setup())
        mock_input.assert_called_once()
        mock_run.assert_called_once()

if __name__ == "__main__":
    unittest.main()
