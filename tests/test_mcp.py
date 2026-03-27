#!/usr/bin/env python
"""Test suite for MCP server integration."""

import sys
import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.cli.mcp import run_mcp_server

class TestMCPServer(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_client.container_version = "ubuntu:latest"
        self.mock_client.container_repo = "docker.io/library/ubuntu"
        self.mock_client.command_path = "/cmd/"
        self.mock_client.cli = MagicMock()
        
        self.mock_context = MagicMock()
        self.mock_client.get_execution_context.return_value = self.mock_context
        
    @patch('rapidctl.cli.mcp.FastMCP')
    def test_run_mcp_server_registers_tools(self, mock_fast_mcp):
        """Test that MCP server registers available container commands as tools."""
        mock_mcp_instance = MagicMock()
        mock_fast_mcp.return_value = mock_mcp_instance
        
        self.mock_context.get_supported_commands.return_value = {
            "build": "Build an image",
            "test": "Run tests"
        }
        
        run_mcp_server(self.mock_client)
        
        mock_fast_mcp.assert_called_once_with("rapidctl-ubuntu")
        
        self.assertEqual(mock_mcp_instance.add_tool.call_count, 2)
        mock_mcp_instance.run.assert_called_once()

    @patch('rapidctl.cli.mcp.FastMCP')
    def test_mcp_handler_executes_command(self, mock_fast_mcp):
        """Test the registered tool handler actually executes and captures stdout."""
        self.mock_context.get_supported_commands.return_value = {"build": "Build an image"}
        mock_mcp_instance = MagicMock()
        mock_fast_mcp.return_value = mock_mcp_instance
        
        registered_func = None
        def mock_add_tool(name, fn, description):
            nonlocal registered_func
            registered_func = fn
            
        mock_mcp_instance.add_tool = mock_add_tool
        
        run_mcp_server(self.mock_client)
        self.assertIsNotNone(registered_func)
        
        # Simulate generator output for run_command
        self.mock_context.run_command.return_value = iter(["Build ", "successful!"])
        
        # Call the registered async function
        result = asyncio.run(registered_func(force=True, tag="v1"))
        
        # Verify kwargs were converted to args properly
        self.mock_context.run_command.assert_called_once_with(
            "build",
            ["--force", "--tag", "v1"]
        )
        
        self.assertEqual(result, "Build successful!")

    @patch('rapidctl.cli.mcp.FastMCP')
    def test_mcp_handler_handles_error(self, mock_fast_mcp):
        """Test the registered tool handler handles exceptions safely."""
        self.mock_context.get_supported_commands.return_value = {"build": "Build an image"}
        mock_mcp_instance = MagicMock()
        mock_fast_mcp.return_value = mock_mcp_instance
        
        self.mock_context.run_command.side_effect = Exception("Container crashed")
        
        registered_func = None
        def mock_add_tool(name, fn, description):
            nonlocal registered_func
            registered_func = fn
            
        mock_mcp_instance.add_tool = mock_add_tool
        run_mcp_server(self.mock_client)
        
        # Call the registered async function
        result = asyncio.run(registered_func())
        
        self.assertEqual(result, "Error: Container crashed")

if __name__ == "__main__":
    unittest.main()
