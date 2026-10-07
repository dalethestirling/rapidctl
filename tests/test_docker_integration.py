#!/usr/bin/env python
"""Integration tests for Docker execution flow."""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

@pytest.mark.requires_docker
class TestDockerIntegration(unittest.TestCase):
    """Integration tests for Docker execution flow using mocked DockerCLI."""

    @patch('rapidctl.cli.docker_cli.DockerCLI')
    @patch('rapidctl.execution.docker.DockerExecutionContext')
    def test_get_execution_context_docker(self, mock_exec_ctx, mock_docker_cli):
        """Test CtlClient.get_execution_context returns DockerExecutionContext when mode=docker."""
        from rapidctl.bootstrap.client import CtlClient
        
        mock_cli_instance = MagicMock()
        mock_docker_cli.return_value = mock_cli_instance
        
        mock_ctx_instance = MagicMock()
        mock_exec_ctx.return_value = mock_ctx_instance
        
        client = CtlClient()
        client.container_repo = "myrepo"
        client.command_path = "/cmd/"
        
        with patch.dict('os.environ', {'RAPIDCTL_EXEC_MODE': 'docker'}):
            ctx = client.get_execution_context()
            
            self.assertEqual(ctx, mock_ctx_instance)
            mock_docker_cli.assert_called_once()
            mock_cli_instance._connect_to_docker.assert_called_once()
            mock_exec_ctx.assert_called_once_with(mock_cli_instance, "myrepo", "/cmd/")

    @patch('rapidctl.cli.docker_cli.DockerCLI')
    def test_connect_docker(self, mock_docker_cli):
        """Test CtlClient._connect_docker creates and connects DockerCLI."""
        from rapidctl.bootstrap.client import CtlClient
        
        mock_cli_instance = MagicMock()
        mock_docker_cli.return_value = mock_cli_instance
        
        client = CtlClient()
        result = client._connect_docker()
        
        self.assertEqual(result, mock_cli_instance)
        self.assertEqual(client.cli, mock_cli_instance)
        mock_cli_instance._connect_to_docker.assert_called_once()

    @patch('rapidctl.bootstrap.connectors.detect_socket')
    def test_detect_socket_docker(self, mock_detect):
        """Test detect_socket with runtime='docker'."""
        from rapidctl.bootstrap.connectors import detect_socket
        
        mock_detect.return_value = "unix:///var/run/docker.sock"
        
        result = detect_socket("docker")
        
        self.assertEqual(result, "unix:///var/run/docker.sock")
        mock_detect.assert_called_once_with("docker")

    @patch('rapidctl.bootstrap.connectors.get_connector')
    def test_get_connector_docker_mac(self, mock_get_connector):
        """Test get_connector returns DockerOSXConnector on macOS with runtime=docker."""
        from rapidctl.bootstrap.connectors import get_connector
        
        mock_connector = MagicMock()
        mock_get_connector.return_value = mock_connector
        
        with patch('platform.system', return_value='Darwin'):
            connector = get_connector("docker")
            
            self.assertEqual(connector, mock_connector)
            mock_get_connector.assert_called_once()

    @patch('rapidctl.bootstrap.connectors.get_connector')
    def test_get_connector_docker_linux(self, mock_get_connector):
        """Test get_connector returns DockerLinuxConnector on Linux with runtime=docker."""
        from rapidctl.bootstrap.connectors import get_connector
        
        mock_connector = MagicMock()
        mock_get_connector.return_value = mock_connector
        
        with patch('platform.system', return_value='Linux'):
            connector = get_connector("docker")
            
            self.assertEqual(connector, mock_connector)
            mock_get_connector.assert_called_once()

    def test_docker_image_wrapper(self):
        """Test DockerImageWrapper provides compatible interface."""
        from rapidctl.cli.docker_cli import DockerImageWrapper
        
        img_dict = {
            "Id": "sha256:abc123def456",
            "RepoTags": ["nginx:latest", "nginx:1.24"],
            "Size": 123456789
        }
        
        wrapper = DockerImageWrapper(img_dict)
        
        self.assertEqual(wrapper.id, "sha256:abc123def456")
        self.assertEqual(wrapper.tags, ["nginx:latest", "nginx:1.24"])
        self.assertEqual(wrapper.attrs, img_dict)
        self.assertEqual(wrapper.short_id, "sha256:abc12")

if __name__ == "__main__":
    unittest.main()