#!/usr/bin/env python
"""Test the DockerCLI wrapper."""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

@pytest.mark.requires_docker
class TestDockerCLI(unittest.TestCase):
    @patch('rapidctl.cli.docker_cli.docker')
    def test_connect_to_docker_with_env(self, mock_docker):
        """Test _connect_to_docker uses DOCKER_SOCKET env var."""
        from rapidctl.cli.docker_cli import DockerCLI
        
        mock_client = MagicMock()
        mock_docker.DockerClient.return_value = mock_client
        
        with patch.dict('os.environ', {'DOCKER_SOCKET': 'unix:///custom.sock'}):
            cli = DockerCLI()
            cli._connect_to_docker()
            
            mock_docker.DockerClient.assert_called_once_with(base_url='unix:///custom.sock')
            self.assertEqual(cli.client, mock_client)

    @patch('rapidctl.cli.docker_cli.docker')
    def test_connect_to_docker_from_env(self, mock_docker):
        """Test _connect_to_docker uses docker.from_env()."""
        from rapidctl.cli.docker_cli import DockerCLI
        
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        
        # Ensure DOCKER_SOCKET is not set
        with patch.dict('os.environ', {}, clear=True):
            cli = DockerCLI()
            cli._connect_to_docker()
            
            mock_docker.from_env.assert_called_once_with(use_context=True)
            self.assertEqual(cli.client, mock_client)

    @patch('rapidctl.cli.docker_cli.docker', None)
    def test_connect_to_docker_import_error(self):
        """Test _connect_to_docker raises error when docker SDK not installed."""
        from rapidctl.cli.docker_cli import DockerCLI
        from rapidctl.errors import PodmanConnectionError
        
        cli = DockerCLI()
        with self.assertRaises(PodmanConnectionError) as cm:
            cli._connect_to_docker()
        self.assertIn("Docker Python SDK not installed", str(cm.exception))

    @patch('rapidctl.cli.docker_cli.docker')
    def test_list_images(self, mock_docker):
        """Test list_images returns wrapped image objects."""
        from rapidctl.cli.docker_cli import DockerCLI, DockerImageWrapper
        
        mock_client = MagicMock()
        mock_img1 = MagicMock()
        mock_img1.attrs = {"Id": "sha256:abc123", "RepoTags": ["nginx:latest"]}
        mock_img2 = MagicMock()
        mock_img2.attrs = {"Id": "sha256:def456", "RepoTags": ["alpine:3.18"]}
        mock_client.images.list.return_value = [mock_img1, mock_img2]
        
        cli = DockerCLI()
        cli.client = mock_client
        
        images = cli.list_images()
        
        self.assertEqual(len(images), 2)
        self.assertIsInstance(images[0], DockerImageWrapper)
        self.assertEqual(images[0].id, "sha256:abc123")
        self.assertEqual(images[0].tags, ["nginx:latest"])
        self.assertEqual(images[1].id, "sha256:def456")
        self.assertEqual(images[1].tags, ["alpine:3.18"])

    @patch('rapidctl.cli.docker_cli.docker')
    def test_pull_image_success(self, mock_docker):
        """Test pull_image returns expected dict."""
        from rapidctl.cli.docker_cli import DockerCLI
        
        mock_client = MagicMock()
        mock_image = MagicMock()
        mock_image.id = "sha256:abc123"
        mock_image.tags = ["nginx:latest"]
        mock_image.attrs = {"Size": 123456}
        mock_client.images.get.return_value = mock_image
        mock_client.images.pull.return_value = iter([
            {"status": "Pulling from library/nginx"},
            {"status": "Downloaded", "progress": "10MB/10MB"},
            {"status": "Download complete"}
        ])
        
        cli = DockerCLI()
        cli.client = mock_client
        
        result = cli.pull_image("nginx:latest")
        
        self.assertEqual(result["Id"], "sha256:abc123")
        self.assertEqual(result["RepoTags"], ["nginx:latest"])
        self.assertEqual(result["Size"], 123456)
        self.assertEqual(len(result["PullLogs"]), 3)

    @patch('rapidctl.cli.docker_cli.docker')
    def test_login(self, mock_docker):
        """Test login caches credentials."""
        from rapidctl.cli.docker_cli import DockerCLI
        
        mock_client = MagicMock()
        mock_client.login.return_value = {"Status": "Login Succeeded"}
        
        cli = DockerCLI()
        cli.client = mock_client
        
        result = cli.login("user", "pass", "docker.io")
        
        self.assertEqual(result, {"Status": "Login Succeeded"})
        self.assertIn("docker.io", cli.auth_configs)
        self.assertEqual(cli.auth_configs["docker.io"]["username"], "user")
        self.assertEqual(cli.auth_configs["docker.io"]["password"], "pass")
        self.assertEqual(cli.auth_configs["docker.io"]["registry"], "docker.io")

    @patch('rapidctl.cli.docker_cli.docker')
    def test_run_container_stream(self, mock_docker):
        """Test run_container with stream=True returns generator."""
        from rapidctl.cli.docker_cli import DockerCLI
        
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.logs.return_value = iter([b"line1\n", b"line2\n"])
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_client.containers.run.return_value = mock_container
        
        cli = DockerCLI()
        cli.client = mock_client
        
        result = cli.run_container("nginx", ["echo", "hello"], stream=True)
        
        lines = list(result)
        self.assertEqual(lines, [b"line1\n", b"line2\n"])
        mock_container.remove.assert_called_once()

    @patch('rapidctl.cli.docker_cli.docker')
    def test_run_container_no_stream(self, mock_docker):
        """Test run_container with stream=False returns bytes."""
        from rapidctl.cli.docker_cli import DockerCLI
        
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.logs.return_value = b"output\n"
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_client.containers.run.return_value = mock_container
        
        cli = DockerCLI()
        cli.client = mock_client
        
        result = cli.run_container("nginx", ["echo", "hello"], stream=False)
        
        self.assertEqual(result, b"output\n")
        mock_container.remove.assert_called_once()

    @patch('rapidctl.cli.docker_cli.docker')
    def test_run_container_error(self, mock_docker):
        """Test run_container raises PodmanCommandError on non-zero exit."""
        from rapidctl.cli.docker_cli import DockerCLI
        from rapidctl.errors import PodmanCommandError
        
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.logs.return_value = iter([b"error\n"])
        mock_container.wait.return_value = {"StatusCode": 1}
        mock_client.containers.run.return_value = mock_container
        
        cli = DockerCLI()
        cli.client = mock_client
        
        with self.assertRaises(PodmanCommandError) as cm:
            list(cli.run_container("nginx", ["false"], stream=True))
        
        self.assertIn("exit code 1", str(cm.exception))

    @patch('rapidctl.cli.docker_cli.docker')
    def test_run_container_command_not_found(self, mock_docker):
        """Test run_container raises PodmanAPIError for command not found."""
        from rapidctl.cli.docker_cli import DockerCLI
        from rapidctl.errors import PodmanAPIError
        
        mock_client = MagicMock()
        mock_client.containers.run.side_effect = Exception("executable file `missing_cmd` not found in $PATH")
        
        cli = DockerCLI()
        cli.client = mock_client
        
        with self.assertRaises(PodmanAPIError) as cm:
            cli.run_container("nginx", ["missing_cmd"], stream=True)
        
        self.assertIn("Command not found inside container: missing_cmd", str(cm.exception))

    @patch('rapidctl.cli.docker_cli.docker')
    def test_list_containers(self, mock_docker):
        """Test list_containers returns expected format."""
        from rapidctl.cli.docker_cli import DockerCLI
        
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.name = "test_container"
        mock_container.image.tags = ["nginx:latest"]
        mock_container.image.id = "sha256:def456"
        mock_container.status = "running"
        mock_container.attrs = {"Created": "2024-01-01T00:00:00Z"}
        mock_container.ports = {"80/tcp": [{"HostPort": "8080"}]}
        mock_client.containers.list.return_value = [mock_container]
        
        cli = DockerCLI()
        cli.client = mock_client
        
        containers = cli.list_containers(all_containers=True)
        
        self.assertEqual(len(containers), 1)
        self.assertEqual(containers[0]["Id"], "abc123")
        self.assertEqual(containers[0]["Names"], "test_container")
        self.assertEqual(containers[0]["Image"], "nginx:latest")

    @patch('rapidctl.cli.docker_cli.docker')
    def test_exec_container(self, mock_docker):
        """Test exec_container returns output."""
        from rapidctl.cli.docker_cli import DockerCLI
        
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.exec_run.return_value = (0, b"output\n")
        mock_client.containers.get.return_value = mock_container
        
        cli = DockerCLI()
        cli.client = mock_client
        
        result = cli.exec_container("abc123", ["ls", "-la"])
        
        self.assertEqual(result, "output\n")

    @patch('rapidctl.cli.docker_cli.docker')
    def test_show_logs(self, mock_docker):
        """Test show_logs returns logs."""
        from rapidctl.cli.docker_cli import DockerCLI
        
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.logs.return_value = b"log line 1\nlog line 2\n"
        mock_client.containers.get.return_value = mock_container
        
        cli = DockerCLI()
        cli.client = mock_client
        
        result = cli.show_logs("abc123", follow=False, tail=10)
        
        self.assertEqual(result, "log line 1\nlog line 2\n")

    @patch('rapidctl.cli.docker_cli.docker')
    def test_inspect_container(self, mock_docker):
        """Test inspect_container returns attrs."""
        from rapidctl.cli.docker_cli import DockerCLI
        
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.attrs = {"Id": "abc123", "State": {"Running": True}}
        mock_client.containers.get.return_value = mock_container
        
        cli = DockerCLI()
        cli.client = mock_client
        
        result = cli.inspect_container("abc123")
        
        self.assertEqual(result["Id"], "abc123")
        self.assertTrue(result["State"]["Running"])

    @patch('rapidctl.cli.docker_cli.docker')
    def test_start_container(self, mock_docker):
        """Test start_container calls start."""
        from rapidctl.cli.docker_cli import DockerCLI
        
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.get.return_value = mock_container
        
        cli = DockerCLI()
        cli.client = mock_client
        
        cli.start_container("abc123")
        
        mock_container.start.assert_called_once()

    @patch('rapidctl.cli.docker_cli.docker')
    def test_stop_container(self, mock_docker):
        """Test stop_container calls stop."""
        from rapidctl.cli.docker_cli import DockerCLI
        
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.get.return_value = mock_container
        
        cli = DockerCLI()
        cli.client = mock_client
        
        cli.stop_container("abc123")
        
        mock_container.stop.assert_called_once()

if __name__ == "__main__":
    unittest.main()