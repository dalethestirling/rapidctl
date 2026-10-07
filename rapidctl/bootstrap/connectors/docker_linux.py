#!/usr/bin/env python3
"""
Linux Connector for Docker

Handles Linux-specific requirements for connecting to Docker:
- Detects the Docker socket location (rootless and rootful)
- Validates socket accessibility
"""

import os
import subprocess
from pathlib import Path
from typing import Optional

from rapidctl.bootstrap.connectors.base import BaseConnector


class DockerLinuxConnector(BaseConnector):
    """Connector for Docker on Linux systems."""

    def __init__(self):
        super().__init__()

    def detect_socket(self) -> Optional[str]:
        """
        Detect the Docker socket location on Linux.

        Priority order:
        1. DOCKER_HOST environment variable
        2. docker.from_env() with context resolution (docker-py 7.2+)
        3. Active Docker CLI context endpoint
        4. Rootless socket (XDG_RUNTIME_DIR/docker.sock)
        5. Rootful socket (/run/docker.sock)
        6. User-specific socket fallback (/run/user/UID/docker.sock)
        """
        try:
            # Fast path: return existing valid socket
            if self.socket_path and self._validate_socket(self.socket_path):
                return self.socket_path

            # 1. Check DOCKER_HOST environment variable
            env_socket = os.environ.get("DOCKER_HOST")
            if env_socket:
                if self._validate_socket(env_socket):
                    self.socket_path = env_socket
                    return env_socket

            # 2. Try docker.from_env() which resolves Docker CLI context automatically
            socket_uri = self._try_docker_from_env()
            if socket_uri:
                return socket_uri

            # 3. Try active Docker CLI context via CLI
            socket_uri = self._try_docker_context_cli()
            if socket_uri:
                return socket_uri

            # 4. Check XDG_RUNTIME_DIR (Standard for rootless Docker)
            xdg_runtime = os.environ.get("XDG_RUNTIME_DIR")
            if xdg_runtime:
                path = Path(xdg_runtime) / "docker.sock"
                try:
                    if self._validate_socket(f"unix://{path}"):
                        self.socket_path = f"unix://{path}"
                        return self.socket_path
                except PermissionError:
                    pass

            # 5. Check for specific UID-based path as fallback if XDG_RUNTIME_DIR is not set
            try:
                uid = os.getuid()
                uid_path = Path(f"/run/user/{uid}/docker.sock")
                if uid_path.exists():
                    if self._validate_socket(f"unix://{uid_path}"):
                        self.socket_path = f"unix://{uid_path}"
                        return self.socket_path
            except PermissionError:
                pass

            # 6. Check rootful socket (requires permissions)
            try:
                rootful_path = Path("/run/docker.sock")
                if rootful_path.exists():
                    if self._validate_socket(f"unix://{rootful_path}"):
                        self.socket_path = f"unix://{rootful_path}"
                        return self.socket_path
            except PermissionError:
                pass

        except Exception:
            # Catch-all for any other unexpected issues during detection
            pass

        return None

    def _try_docker_from_env(self) -> Optional[str]:
        """Try to get socket via docker.from_env() (uses Docker CLI context)."""
        try:
            import docker
            client = docker.from_env(use_context=True)
            base_url = client.api.base_url
            if base_url and base_url.startswith("unix://"):
                if self._validate_socket(base_url):
                    self.socket_path = base_url
                    return base_url
        except Exception:
            pass
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
        except Exception:
            pass
        return None

    def _validate_socket(self, socket_uri: str) -> bool:
        """Validate that a socket path exists and is accessible."""
        return super()._validate_socket(socket_uri)

    def setup(self) -> bool:
        """Basic setup for Linux Docker."""
        if not self.is_docker_installed():
            return False

        return self.detect_socket() is not None

    def is_docker_installed(self) -> bool:
        """
        Check if Docker CLI is installed on the system.

        Returns:
            bool: True if Docker executable is found in PATH, False otherwise
        """
        import shutil
        return shutil.which("docker") is not None


def get_connector() -> DockerLinuxConnector:
    """Factory function."""
    return DockerLinuxConnector()