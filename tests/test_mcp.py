#!/usr/bin/env python
"""Test suite for MCP server integration."""

import sys
import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.cli.mcp import run_mcp_server, CommandResult

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
            "build": {"summary": "Build an image"},
            "test": {"summary": "Run tests"}
        }
        
        run_mcp_server(self.mock_client)
        
        mock_fast_mcp.assert_called_once_with("rapidctl-ubuntu")
        
        self.assertEqual(mock_mcp_instance.add_tool.call_count, 2)
        mock_mcp_instance.run.assert_called_once()

    @patch('rapidctl.cli.mcp.FastMCP')
    def test_mcp_handler_executes_command(self, mock_fast_mcp):
        """Test the registered tool handler actually executes and captures stdout."""
        # Provide metadata with parameters and argument_mapping for proper handler creation
        self.mock_context.get_supported_commands.return_value = {
            "build": {
                "summary": "Build an image",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "force": {"type": "boolean", "description": "Force rebuild"},
                        "tag": {"type": "string", "description": "Tag for the image"}
                    }
                },
                "argument_mapping": {
                    "flags": {
                        "force": "--force",
                        "tag": "--tag"
                    }
                }
            }
        }
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
        
        # Get the ArgsModel from the handler's closure and create an instance
        # The handler expects a Pydantic model, not kwargs
        import inspect
        handler_sig = inspect.signature(registered_func)
        args_param = list(handler_sig.parameters.values())[0]
        ArgsModel = args_param.annotation
        
        # Call the registered async function with model instance
        result = asyncio.run(registered_func(ArgsModel(force=True, tag="v1")))
        
        # Verify kwargs were converted to args properly
        self.mock_context.run_command.assert_called_once_with(
            "build",
            ["--force", "--tag", "v1"]
        )
        
        # Verify structured output
        self.assertIsInstance(result, CommandResult)
        self.assertTrue(result.success)
        self.assertEqual(result.output, "Build successful!")
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.command, "build")
        self.assertEqual(result.args, ["--force", "--tag", "v1"])

    @patch('rapidctl.cli.mcp.FastMCP')
    def test_mcp_handler_handles_error(self, mock_fast_mcp):
        """Test the registered tool handler handles exceptions safely."""
        self.mock_context.get_supported_commands.return_value = {
            "build": {
                "summary": "Build an image",
                "parameters": {"type": "object", "properties": {}},
                "argument_mapping": {}
            }
        }
        mock_mcp_instance = MagicMock()
        mock_fast_mcp.return_value = mock_mcp_instance
        
        self.mock_context.run_command.side_effect = Exception("Container crashed")
        
        registered_func = None
        def mock_add_tool(name, fn, description):
            nonlocal registered_func
            registered_func = fn
            
        mock_mcp_instance.add_tool = mock_add_tool
        run_mcp_server(self.mock_client)
        
        # Get the ArgsModel from the handler's closure
        import inspect
        handler_sig = inspect.signature(registered_func)
        args_param = list(handler_sig.parameters.values())[0]
        ArgsModel = args_param.annotation
        
        # Call the registered async function with empty model instance
        result = asyncio.run(registered_func(ArgsModel()))
        
        # Verify structured error output
        self.assertIsInstance(result, CommandResult)
        self.assertFalse(result.success)
        self.assertEqual(result.output, "Error: Container crashed")
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.command, "build")
        self.assertEqual(result.args, [])

    @patch('rapidctl.cli.mcp.FastMCP')
    def test_mcp_handler_closure_bug_fixed(self, mock_fast_mcp):
        """Test that each command gets its own ArgsModel (closure bug fix)."""
        self.mock_context.get_supported_commands.return_value = {
            "cmd_a": {
                "summary": "Command A",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "arg_a": {"type": "string", "description": "Arg for A"}
                    }
                },
                "argument_mapping": {"positional": ["arg_a"]}
            },
            "cmd_b": {
                "summary": "Command B",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "arg_b": {"type": "integer", "description": "Arg for B"}
                    }
                },
                "argument_mapping": {"positional": ["arg_b"]}
            }
        }
        mock_mcp_instance = MagicMock()
        mock_fast_mcp.return_value = mock_mcp_instance
        
        registered_handlers = {}
        def mock_add_tool(name, fn, description):
            registered_handlers[name] = fn
            
        mock_mcp_instance.add_tool = mock_add_tool
        
        run_mcp_server(self.mock_client)
        
        # Verify each handler has its own ArgsModel with correct fields
        import inspect
        for cmd_name, handler in registered_handlers.items():
            handler_sig = inspect.signature(handler)
            args_param = list(handler_sig.parameters.values())[0]
            ArgsModel = args_param.annotation
            
            if cmd_name == "cmd_a":
                # Should have arg_a field
                model_instance = ArgsModel(arg_a="test")
                self.assertEqual(model_instance.arg_a, "test")
            elif cmd_name == "cmd_b":
                # Should have arg_b field
                model_instance = ArgsModel(arg_b=42)
                self.assertEqual(model_instance.arg_b, 42)

if __name__ == "__main__":
    unittest.main()
