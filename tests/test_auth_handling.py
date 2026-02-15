#!/usr/bin/env python
"""Test suite for registry authentication handling."""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure we can import rapidctl
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.errors import PodmanAuthError, PodmanAPIError
from rapidctl.cli import PodmanCLI
import rapidctl.cli.main as cli_main

class TestAuthHandling(unittest.TestCase):
    def test_pull_image_auth_detection(self):
        cli = PodmanCLI()
        cli.client = MagicMock()
        
        # Mock an unauthorized error from podman-py
        cli.client.images.pull.side_effect = Exception("unauthorized: authentication required")
        
        with self.assertRaises(PodmanAuthError):
            cli.pull_image("private-image")

    @patch('rapidctl.cli.actions.authenticate_to_registry')
    @patch('rapidctl.cli.actions.pull_container')
    @patch('rapidctl.cli.actions.find_container')
    @patch('rapidctl.cli.PodmanCLI._connect_to_podman')
    def test_main_retry_on_auth_fail(self, mock_connect, mock_find, mock_pull, mock_auth):
        client_obj = MagicMock()
        client_obj.container_version = "private:latest"
        
        mock_find.return_value = None
        # First pull fails with AuthError
        mock_pull.side_effect = [PodmanAuthError("Auth required"), MagicMock()]
        # Auth action succeeds
        mock_auth.return_value = True
        
        # Run main (with mocked argv)
        with patch('sys.argv', ['examplectl', 'test']):
            cli_main.main(client_obj)
            
        # Verify it called auth and retried pull
        self.assertEqual(mock_auth.call_count, 1)
        self.assertEqual(mock_pull.call_count, 2)

    @patch('rapidctl.cli.tasks.registry_login')
    @patch('getpass.getpass')
    @patch('builtins.input')
    def test_authenticate_to_registry_action(self, mock_input, mock_getpass, mock_login):
        from rapidctl.cli.actions import authenticate_to_registry
        
        session = MagicMock()
        mock_input.return_value = "user"
        mock_getpass.return_value = "pass"
        
        success = authenticate_to_registry(session, "ghcr.io/repo/img:v1")
        
        self.assertTrue(success)
        mock_login.assert_called_with(session, "ghcr.io", "user", "pass")

if __name__ == "__main__":
    unittest.main()
