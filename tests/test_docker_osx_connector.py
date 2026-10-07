#!/usr/bin/env python
"""Test the Docker macOS connector functionality."""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.bootstrap.connectors.docker_osx import DockerOSXConnector

import pytest

@pytest.mark.skipif(sys.platform != "darwin", reason="Docker macOS connector tests only run on macOS")
@pytest.mark.requires_docker
class TestDockerOSXConnector(unittest.TestCase):
    def setUp(self):
        self.connector = DockerOSXConnector()

    @patch('rapidctl.bootstrap.connectors.docker_osx.DockerOSXConnector.is_docker_installed')
    def test_setup_not_installed(self, mock_installed):
        """Test setup fails when docker is not installed."""
        mock_installed.return_value = False
        self.assertFalse(self.connector.setup())

    @patch('rapidctl.bootstrap.connectors.docker_osx.DockerOSXConnector.detect_socket')
    @patch('rapidctl.bootstrap.connectors.docker_osx.DockerOSXConnector.ensure_docker_running')
    @patch('rapidctl.bootstrap.connectors.docker_osx.DockerOSXConnector.is_docker_installed')
    def test_setup_already_running(self, mock_installed, mock_running, mock_detect):
        """Test setup succeeds immediately if docker is installed and running."""
        mock_installed.return_value = True
        mock_running.return_value = True
        mock_detect.return_value = '/fake/socket'
        
        self.assertTrue(self.connector.setup())
        mock_detect.assert_called_once()
        mock_running.assert_called_once()

    @patch('subprocess.run')
    @patch('rapidctl.bootstrap.connectors.docker_osx.DockerOSXConnector.detect_socket')
    @patch('rapidctl.bootstrap.connectors.docker_osx.DockerOSXConnector.ensure_docker_running')
    @patch('rapidctl.bootstrap.connectors.docker_osx.DockerOSXConnector.is_docker_installed')
    def test_setup_already_running(self, mock_installed, mock_running, mock_detect, mock_run):
        """Test setup succeeds immediately if Docker is installed and running."""
        mock_installed.return_value = True
        mock_running.return_value = True
        mock_detect.return_value = 'unix:///fake/socket'
        
        with patch.object(self.connector, '_validate_socket', return_value=True):
            self.assertTrue(self.connector.setup())
        
        mock_running.assert_called_once()
        mock_detect.assert_called_once()
        # Docker already running, so open -a Docker should NOT be called
        mock_run.assert_not_called()

    @patch('rapidctl.bootstrap.connectors.docker_osx.DockerOSXConnector.ensure_docker_running')
    @patch('rapidctl.bootstrap.connectors.docker_osx.DockerOSXConnector.is_docker_installed')
    def test_setup_start_docker_fails(self, mock_installed, mock_running):
        """Test setup fails if starting Docker Desktop throws an error."""
        import subprocess
        mock_installed.return_value = True
        mock_running.return_value = False
        
        with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, ["open", "-a", "Docker"], stderr="error")):
            self.assertFalse(self.connector.setup())

    @patch('rapidctl.bootstrap.connectors.docker_osx.DockerOSXConnector._try_docker_from_env')
    @patch('rapidctl.bootstrap.connectors.docker_osx.DockerOSXConnector._try_docker_context_cli')
    @patch('rapidctl.bootstrap.connectors.docker_osx.os.environ.get')
    def test_detect_socket_env_var(self, mock_environ, mock_context, mock_from_env):
        """Test detect_socket uses DOCKER_HOST env var first."""
        mock_environ.return_value = "unix:///custom/docker.sock"
        mock_from_env.return_value = None
        mock_context.return_value = None
        
        with patch.object(self.connector, '_validate_socket', return_value=True):
            result = self.connector.detect_socket()
            self.assertEqual(result, "unix:///custom/docker.sock")

    @patch('rapidctl.bootstrap.connectors.docker_osx.DockerOSXConnector._try_docker_from_env')
    @patch('rapidctl.bootstrap.connectors.docker_osx.DockerOSXConnector._try_docker_context_cli')
    @patch('rapidctl.bootstrap.connectors.docker_osx.os.environ.get')
    def test_detect_socket_from_env(self, mock_environ, mock_context, mock_from_env):
        """Test detect_socket falls back to docker.from_env()."""
        mock_environ.return_value = None
        mock_from_env.return_value = "unix:///from/env/docker.sock"
        mock_context.return_value = None
        
        with patch.object(self.connector, '_validate_socket', return_value=True):
            result = self.connector.detect_socket()
            self.assertEqual(result, "unix:///from/env/docker.sock")

    @patch('rapidctl.bootstrap.connectors.docker_osx.DockerOSXConnector._try_docker_from_env')
    @patch('rapidctl.bootstrap.connectors.docker_osx.DockerOSXConnector._try_docker_context_cli')
    @patch('rapidctl.bootstrap.connectors.docker_osx.os.environ.get')
    def test_detect_socket_context_cli(self, mock_environ, mock_context, mock_from_env):
        """Test detect_socket falls back to docker context inspect."""
        mock_environ.return_value = None
        mock_from_env.return_value = None
        mock_context.return_value = "unix:///context/docker.sock"
        
        with patch.object(self.connector, '_validate_socket', return_value=True):
            result = self.connector.detect_socket()
            self.assertEqual(result, "unix:///context/docker.sock")

if __name__ == "__main__":
    unittest.main()