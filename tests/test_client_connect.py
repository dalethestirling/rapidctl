#!/usr/bin/env python
"""Test suite for CtlClient connection logic."""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.bootstrap.client import CtlClient

class TestClientConnect(unittest.TestCase):
    
    @patch('rapidctl.cli.PodmanCLI')
    def test_connect_creates_podman_cli(self, mock_podman_cli_class):
        """Test that connect creates a PodmanCLI instance and connects it."""
        mock_cli_instance = MagicMock()
        mock_podman_cli_class.return_value = mock_cli_instance
        
        client = CtlClient()
        self.assertIsNone(client.cli)
        
        returned_cli = client.connect()
        
        # Verify PodmanCLI was instantiated
        mock_podman_cli_class.assert_called_once()
        
        # Verify _connect_to_podman was called on the instance
        mock_cli_instance._connect_to_podman.assert_called_once()
        
        # Verify it returned and stored the instance
        self.assertEqual(returned_cli, mock_cli_instance)
        self.assertEqual(client.cli, mock_cli_instance)
        
    @patch('rapidctl.cli.PodmanCLI')
    def test_connect_reuses_existing_cli(self, mock_podman_cli_class):
        """Test that calling connect multiple times reuses the same CLI instance."""
        mock_cli_instance = MagicMock()
        mock_podman_cli_class.return_value = mock_cli_instance
        
        client = CtlClient()
        
        client.cli = mock_cli_instance
        
        returned_cli = client.connect()
        
        # Verify PodmanCLI was NOT instantiated again
        mock_podman_cli_class.assert_not_called()
        self.assertEqual(returned_cli, mock_cli_instance)

    @patch('rapidctl.cli.actions.find_newer_version')
    def test_check_for_updates_connects_if_needed(self, mock_find_newer):
        """Test that check_for_updates ensures connection before searching."""
        mock_find_newer.return_value = "new_version:2.0"
        
        client = CtlClient()
        mock_connect = MagicMock()
        def mock_connect_impl():
            client.cli = "mocked_cli_session"
            return "mocked_cli_session"
            
        mock_connect.side_effect = mock_connect_impl
        client.connect = mock_connect
        
        client.container_repo = "myrepo"
        client.baseline_version = "myrepo:1.0"
        
        result = client.check_for_updates()
        
        # Verify it connected
        mock_connect.assert_called_once()
        
        # Verify it searched using the returned session
        mock_find_newer.assert_called_once_with(
            "mocked_cli_session", "myrepo", "myrepo:1.0"
        )
        self.assertEqual(result, "new_version:2.0")

if __name__ == "__main__":
    unittest.main()
