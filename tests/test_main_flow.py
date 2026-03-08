#!/usr/bin/env python
"""Test suite for the refactored main.py orchestrator."""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.cli import main

class TestMainFlow(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_client.cli = MagicMock()
        self.mock_client.container_version = "ubuntu:latest"
        self.mock_client.container_repo = "ubuntu"
        self.mock_client.baseline_version = "ubuntu:1.0"
        self.mock_client.command_path = "/cmd/"

    @patch('builtins.print')
    def test_update_notification_shown(self, mock_print):
        """Test updates notification is shown if newer exists."""
        self.mock_client.check_for_updates.return_value = "ubuntu:2.0"
        
        main._check_and_notify_updates(self.mock_client)
        
        mock_print.assert_any_call("--- Newer container version found: ubuntu:2.0 (Current: ubuntu:1.0) ---")

    @patch('builtins.print')
    @patch('sys.exit')
    @patch('rapidctl.cli.actions.display_available_commands')
    def test_help_flag_shows_commands(self, mock_display, mock_exit, mock_print):
        """Test that --help correctly dispatches."""
        main._dispatch_subcommand(self.mock_client, self.mock_client.cli, ['--help'])
        
        mock_display.assert_called_once()
        mock_exit.assert_called_with(0)

    @patch('rapidctl.cli.actions.get_container_subcommands')
    @patch('builtins.print')
    @patch('sys.exit')
    def test_invalid_subcommand_shows_suggestions(self, mock_exit, mock_print, mock_get_cmds):
        """Test that invalid command raises SystemExit and shows Did you mean."""
        mock_get_cmds.return_value = {"build": "build image", "run": "run image"}
        
        main._dispatch_subcommand(self.mock_client, self.mock_client.cli, ['built'])
        
        # Verify it printed the suggestions correctly
        mock_print.assert_any_call("✗ Error: 'built' is not a valid subcommand.")
        mock_print.assert_any_call("Did you mean: build?")
        mock_exit.assert_called_with(1)

    def test_format_command_list_output(self):
        """Test task level formatting function."""
        from rapidctl.cli.tasks import format_command_list
        cmds = {"build": "builds things", "run": None}
        out = format_command_list(cmds)
        
        self.assertIn("build                - builds things", out)
        self.assertIn("run", out)

if __name__ == "__main__":
    unittest.main()
