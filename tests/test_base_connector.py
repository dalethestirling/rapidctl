#!/usr/bin/env python
"""Test suite for the BaseConnector abstract class."""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Ensure we can import rapidctl
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.bootstrap.connectors.base import BaseConnector

class DummyConnector(BaseConnector):
    """A concrete implementation for testing the base methods."""
    def detect_socket(self):
        return None
        
    def setup(self):
        return True

class TestBaseConnector(unittest.TestCase):
    def setUp(self):
        self.connector = DummyConnector()

    def test_cannot_instantiate_directly(self):
        """Test that BaseConnector cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            BaseConnector()

    @patch('shutil.which')
    def test_is_podman_installed_found(self, mock_which):
        """Test detection of podman executable when present."""
        mock_which.return_value = '/usr/bin/podman'
        self.assertTrue(self.connector.is_podman_installed())

    @patch('shutil.which')
    def test_is_podman_installed_not_found(self, mock_which):
        """Test detection of podman executable when absent."""
        mock_which.return_value = None
        self.assertFalse(self.connector.is_podman_installed())

    @patch('os.access')
    @patch('pathlib.Path.is_socket')
    @patch('pathlib.Path.exists')
    def test_validate_socket_valid(self, mock_exists, mock_is_socket, mock_access):
        """Test that a valid socket returns True."""
        mock_exists.return_value = True
        mock_is_socket.return_value = True
        mock_access.return_value = True
        
        self.assertTrue(self.connector._validate_socket("unix:///tmp/podman.sock"))
        
        # Verify it handled the unix:// prefix correctly
        mock_exists.assert_called_once()
        mock_is_socket.assert_called_once()
        mock_access.assert_called_once_with(Path("/tmp/podman.sock"), os.R_OK | os.W_OK)

    @patch('pathlib.Path.exists')
    def test_validate_socket_missing(self, mock_exists):
        """Test that a missing socket returns False."""
        mock_exists.return_value = False
        self.assertFalse(self.connector._validate_socket("/tmp/missing.sock"))

    @patch('os.access')
    @patch('pathlib.Path.is_socket')
    @patch('pathlib.Path.exists')
    def test_validate_socket_no_perms(self, mock_exists, mock_is_socket, mock_access):
        """Test that a socket without permissions returns False."""
        mock_exists.return_value = True
        mock_is_socket.return_value = True
        mock_access.return_value = False
        
        self.assertFalse(self.connector._validate_socket("/tmp/noperms.sock"))
        
    @patch('pathlib.Path.is_socket')
    @patch('pathlib.Path.exists')
    def test_validate_socket_not_a_socket(self, mock_exists, mock_is_socket):
        """Test that a file that exists but isn't a socket returns False."""
        mock_exists.return_value = True
        mock_is_socket.return_value = False
        
        self.assertFalse(self.connector._validate_socket("/tmp/regular_file.txt"))

if __name__ == "__main__":
    unittest.main()
