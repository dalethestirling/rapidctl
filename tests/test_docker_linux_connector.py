#!/usr/bin/env python
"""Test the Docker Linux connector functionality."""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.bootstrap.connectors.docker_linux import DockerLinuxConnector

import pytest

@pytest.mark.skipif(sys.platform != "linux", reason="Docker Linux connector tests only run on Linux")
@pytest.mark.requires_docker
class TestDockerLinuxConnector(unittest.TestCase):
    def setUp(self):
        self.connector = DockerLinuxConnector()

    @patch('rapidctl.bootstrap.connectors.docker_linux.DockerLinuxConnector.is_docker_installed')
    def test_setup_not_installed(self, mock_installed):
        """Test setup fails when docker is not installed."""
        mock_installed.return_value = False
        self.assertFalse(self.connector.setup())

    @patch('rapidctl.bootstrap.connectors.docker_linux.DockerLinuxConnector.detect_socket')
    @patch('rapidctl.bootstrap.connectors.docker_linux.DockerLinuxConnector.is_docker_installed')
    def test_setup_success(self, mock_installed, mock_detect):
        """Test setup succeeds if docker is installed and socket detected."""
        mock_installed.return_value = True
        mock_detect.return_value = 'unix:///run/docker.sock'
        
        self.assertTrue(self.connector.setup())
        mock_detect.assert_called_once()

    @patch('rapidctl.bootstrap.connectors.docker_linux.DockerLinuxConnector._try_docker_from_env')
    @patch('rapidctl.bootstrap.connectors.docker_linux.DockerLinuxConnector._try_docker_context_cli')
    @patch('rapidctl.bootstrap.connectors.docker_linux.os.environ.get')
    def test_detect_socket_env_var(self, mock_environ, mock_context, mock_from_env):
        """Test detect_socket uses DOCKER_HOST env var first."""
        mock_environ.return_value = "unix:///custom/docker.sock"
        mock_from_env.return_value = None
        mock_context.return_value = None
        
        with patch.object(self.connector, '_validate_socket', return_value=True):
            result = self.connector.detect_socket()
            self.assertEqual(result, "unix:///custom/docker.sock")

    @patch('rapidctl.bootstrap.connectors.docker_linux.DockerLinuxConnector._try_docker_from_env')
    @patch('rapidctl.bootstrap.connectors.docker_linux.DockerLinuxConnector._try_docker_context_cli')
    @patch('rapidctl.bootstrap.connectors.docker_linux.os.environ.get')
    def test_detect_socket_from_env(self, mock_environ, mock_context, mock_from_env):
        """Test detect_socket falls back to docker.from_env()."""
        mock_environ.return_value = None
        mock_from_env.return_value = "unix:///from/env/docker.sock"
        mock_context.return_value = None
        
        with patch.object(self.connector, '_validate_socket', return_value=True):
            result = self.connector.detect_socket()
            self.assertEqual(result, "unix:///from/env/docker.sock")

    @patch('rapidctl.bootstrap.connectors.docker_linux.DockerLinuxConnector._try_docker_from_env')
    @patch('rapidctl.bootstrap.connectors.docker_linux.DockerLinuxConnector._try_docker_context_cli')
    @patch('rapidctl.bootstrap.connectors.docker_linux.os.environ.get')
    def test_detect_socket_context_cli(self, mock_environ, mock_context, mock_from_env):
        """Test detect_socket falls back to docker context inspect."""
        mock_environ.return_value = None
        mock_from_env.return_value = None
        mock_context.return_value = "unix:///context/docker.sock"
        
        with patch.object(self.connector, '_validate_socket', return_value=True):
            result = self.connector.detect_socket()
            self.assertEqual(result, "unix:///context/docker.sock")

    @patch('rapidctl.bootstrap.connectors.docker_linux.os.getuid')
    @patch('rapidctl.bootstrap.connectors.docker_linux.Path.exists')
    @patch('rapidctl.bootstrap.connectors.docker_linux.DockerLinuxConnector._validate_socket')
    def test_detect_socket_xdg_runtime(self, mock_validate, mock_exists, mock_getuid):
        """Test detect_socket uses XDG_RUNTIME_DIR for rootless docker."""
        mock_getuid.return_value = 1000
        mock_validate.return_value = True
        
        with patch.dict('os.environ', {'XDG_RUNTIME_DIR': '/run/user/1000'}):
            mock_exists.return_value = True
            result = self.connector.detect_socket()
            self.assertEqual(result, "unix:///run/user/1000/docker.sock")

if __name__ == "__main__":
    unittest.main()