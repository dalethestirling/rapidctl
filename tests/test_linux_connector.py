#!/usr/bin/env python
"""Test the Linux connector functionality."""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.bootstrap.connectors.linux import LinuxConnector
import pytest

@pytest.mark.skipif(sys.platform != "linux", reason="Linux connector tests only run on Linux")
@pytest.mark.requires_podman
class TestLinuxConnector(unittest.TestCase):
    def setUp(self):
        self.connector = LinuxConnector()



    @patch('os.environ.get')
    def test_detect_socket_env(self, mock_env_get):
        """Test socket detection via environment variable."""
        mock_env_get.return_value = "unix:///tmp/podman.sock"
        with patch('rapidctl.bootstrap.connectors.linux.LinuxConnector._validate_socket', return_value=True):
            self.assertEqual(self.connector.detect_socket(), "unix:///tmp/podman.sock")

    @patch('pathlib.Path.exists')
    def test_detect_socket_rootless(self, mock_exists):
        """Test rootless socket detection."""
        # Mock env vars
        with patch('os.environ.get') as mock_env:
            mock_env.side_effect = lambda k, d=None: "/run/user/1000" if k == "XDG_RUNTIME_DIR" else None
            mock_exists.return_value = True
            with patch('rapidctl.bootstrap.connectors.linux.LinuxConnector._validate_socket', return_value=True):
                socket = self.connector.detect_socket()
                self.assertEqual(socket, "unix:///run/user/1000/podman/podman.sock")

if __name__ == "__main__":
    unittest.main()
