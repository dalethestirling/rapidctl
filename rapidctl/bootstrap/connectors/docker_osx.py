#!/usr/bin/env python3
"""
macOS Connector for Docker

This connector handles macOS-specific requirements for connecting to Docker:
- Detects the Docker socket location using docker.from_env() and fallback paths
- Validates socket accessibility
- Auto-starts Docker Desktop if not running
"""

import os
import shutil
import subprocess
import time
import logging
from pathlib import Path
from typing import Optional

from rapidctl.bootstrap.connectors.base import BaseConnector

logger = logging.getLogger("rapidctl.bootstrap.connectors.docker_osx")


class DockerOSXConnector(BaseConnector):
    """Connector for Docker on macOS systems."""

    def __init__(self):
        super().__init__()

    def detect_socket(self) -> Optional[str]:
        """
        Detect the Docker socket location on macOS.

        Priority order:
        1. DOCKER_HOST environment variable (explicit override)
        2. docker.from_env() with context resolution (docker-py 7.2+)
        3. Active Docker CLI context endpoint
        4. Known Docker Desktop socket paths (~/.docker/run/docker.sock, /var/run/docker.sock)

        Returns:
            str: URI to the Docker socket (e.g., 'unix:///path/to/socket') or None if not found
        """
        # Fast path: return existing valid socket
        if self.socket_path and self._validate_socket(self.socket_path):
            return self.socket_path

        # 1. Check DOCKER_HOST environment variable
        env_socket = os.environ.get("DOCKER_HOST")
        if env_socket:
            if self._validate_socket(env_socket):
                self.socket_path = env_socket
                return env_socket
            logger.debug(f"DOCKER_HOST set but socket not accessible: {env_socket}")

        # 2. Try docker.from_env() which resolves Docker CLI context automatically
        socket_uri = self._try_docker_from_env()
        if socket_uri:
            return socket_uri

        # 3. Try active Docker CLI context via CLI
        socket_uri = self._try_docker_context_cli()
        if socket_uri:
            return socket_uri

        # 4. Fallback to known Docker Desktop socket paths
        socket_candidates = [
            Path.home() / ".docker/run/docker.sock",      # Docker Desktop 4.x+ default
            Path("/var/run/docker.sock"),                  # Legacy symlink (restored in 4.13.1+)
            Path.home() / "Library/Containers/com.docker.docker/Data/docker.raw.sock",  # Raw socket
        ]

        for socket_path in socket_candidates:
            if socket_path.exists():
                socket_uri = f"unix://{socket_path}"
                if self._validate_socket(socket_uri):
                    self.socket_path = socket_uri
                    return socket_uri

        return None

    def _try_docker_from_env(self) -> Optional[str]:
        """Try to get socket via docker.from_env() (uses Docker CLI context)."""
        try:
            import docker
            client = docker.from_env(use_context=True)
            # Get the base_url from the client
            base_url = client.api.base_url
            if base_url and base_url.startswith("unix://"):
                if self._validate_socket(base_url):
                    self.socket_path = base_url
                    return base_url
        except Exception as e:
            logger.debug(f"docker.from_env() failed: {e}")
        return None

    def _try_docker_context_cli(self) -> Optional[str]:
        """Try to get socket from active Docker CLI context."""
        try:
            result = subprocess.run(
                ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                host = result.stdout.strip()
                if host and host.startswith("unix://"):
                    if self._validate_socket(host):
                        self.socket_path = host
                        return host
        except Exception as e:
            logger.debug(f"docker context inspect failed: {e}")
        return None

    def _validate_socket(self, socket_uri: str) -> bool:
        """
        Validate that a socket path exists and is accessible.

        Args:
            socket_uri: Socket URI (e.g., 'unix:///path/to/socket')

        Returns:
            bool: True if socket is valid and accessible
        """
        if super()._validate_socket(socket_uri):
            return True

        # Allow symlinks (common on macOS for /var/run/docker.sock)
        if socket_uri.startswith("unix://"):
            socket_path = socket_uri[7:]
        else:
            socket_path = socket_uri

        path = Path(socket_path)
        if path.exists() and path.is_symlink():
            return os.access(path, os.R_OK | os.W_OK)

        return False

    def ensure_docker_running(self) -> bool:
        """
        Check if Docker Desktop is running, and start it if not.

        Returns:
            bool: True if Docker is running, False otherwise
        """
        # Fast path: If socket is valid and accessible, Docker is effectively running
        if self.socket_path and self._validate_socket(self.socket_path):
            return True

        try:
            # Check if docker command is available and responsive
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return True

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Docker not running - try to start Docker Desktop
        logger.info("Docker Desktop not running. Attempting to start...")
        try:
            # Use 'open -a Docker' to launch Docker Desktop app
            subprocess.run(
                ["open", "-a", "Docker"],
                check=True,
                capture_output=True,
                text=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Failed to start Docker Desktop: {e}")
            return False

        # Wait for Docker Desktop to start and socket to become available
        logger.info("Waiting for Docker Desktop to start (this may take up to 60 seconds)...")
        for i in range(30):  # 30 * 2s = 60s max wait
            time.sleep(2)
            socket = self.detect_socket()
            if socket:
                logger.info("Docker Desktop started successfully")
                return True

        logger.error("Docker Desktop started but socket not detected within timeout")
        return False

    def get_connection_info(self) -> dict:
        """
        Get connection information for Docker on macOS.

        Returns:
            dict: Connection information including socket path
        """
        if not self.socket_path:
            self.detect_socket()

        return {
            "socket_path": self.socket_path,
            "platform": "darwin",
            "connector": "docker_osx"
        }

    def setup(self) -> bool:
        """
        Set up the Docker macOS connector and validate Docker availability.

        This method:
        1. Checks if Docker CLI is installed
        2. Validates Docker Desktop is running and starts it if not
        3. Detects the Docker socket

        Returns:
            bool: True if setup successful, False otherwise
        """
        # 1. Check if docker is installed
        if not self.is_docker_installed():
            logger.error("Docker is not installed. Please install Docker Desktop for Mac.")
            return False

        # 2. Check if Docker is running (with auto-start)
        if not self.ensure_docker_running():
            logger.error("Docker Desktop must be running to use this tool.")
            return False

        # 3. Detect socket
        socket = self.detect_socket()
        if not socket:
            logger.error("Could not detect Docker socket automatically.")
            return False

        return True

    def is_docker_installed(self) -> bool:
        """
        Check if Docker CLI is installed on the system.

        Returns:
            bool: True if Docker executable is found in PATH, False otherwise
        """
        return shutil.which("docker") is not None


def get_connector() -> DockerOSXConnector:
    """
    Factory function to get a Docker macOS connector instance.

    Returns:
        DockerOSXConnector: Configured Docker macOS connector
    """
    connector = DockerOSXConnector()
    return connector