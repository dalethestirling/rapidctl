#!/usr/bin/env python3
"""
Linux Connector for Podman

Handles Linux-specific requirements for connecting to Podman:
- Detects the Podman socket location (rootless and rootful)
- Validates socket accessibility
"""

import os
from pathlib import Path
from typing import Optional


class LinuxConnector:
    """Connector for Podman on Linux systems."""
    
    def __init__(self):
        self.socket_path: Optional[str] = None
        
    def is_podman_installed(self) -> bool:
        """Check if Podman is installed on the system."""
        import shutil
        return shutil.which("podman") is not None
        
    def detect_socket(self) -> Optional[str]:
        """
        Detect the Podman socket location on Linux.
        
        Checks:
        1. Environment variable PODMAN_SOCKET
        2. Rootless socket (XDG_RUNTIME_DIR/podman/podman.sock)
        3. Rootful socket (/run/podman/podman.sock)
        4. User-specific socket fallback (/run/user/UID/podman/podman.sock)
        """
        try:
            # Fast path: return existing valid socket
            if self.socket_path and self._validate_socket(self.socket_path):
                return self.socket_path

            # 1. Check environment variable
            env_socket = os.environ.get("PODMAN_SOCKET")
            if env_socket:
                if self._validate_socket(env_socket):
                    self.socket_path = env_socket
                    return env_socket

            # 2. Check XDG_RUNTIME_DIR (Standard for rootless)
            xdg_runtime = os.environ.get("XDG_RUNTIME_DIR")
            if xdg_runtime:
                path = Path(xdg_runtime) / "podman/podman.sock"
                try:
                    if self._validate_socket(f"unix://{path}"):
                        self.socket_path = f"unix://{path}"
                        return self.socket_path
                except PermissionError:
                    pass

            # 3. Check for specific UID-based path as fallback if XDG_RUNTIME_DIR is not set
            try:
                uid = os.getuid()
                uid_path = Path(f"/run/user/{uid}/podman/podman.sock")
                if uid_path.exists():
                    if self._validate_socket(f"unix://{uid_path}"):
                        self.socket_path = f"unix://{uid_path}"
                        return self.socket_path
            except PermissionError:
                pass

            # 4. Check rootful socket (requires permissions)
            try:
                rootful_path = Path("/run/podman/podman.sock")
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
    
    def _validate_socket(self, socket_uri: str) -> bool:
        """Validate that a socket path exists and is accessible."""
        try:
            if socket_uri.startswith("unix://"):
                socket_path = socket_uri[7:]
            else:
                socket_path = socket_uri
                
            path = Path(socket_path)
            if not path.exists():
                return False
                
            # Check if it's a socket and accessible
            return path.is_socket() and os.access(path, os.R_OK | os.W_OK)
        except PermissionError:
            return False
        except Exception:
            return False

    def setup(self) -> bool:
        """Basic setup for Linux."""
        if not self.is_podman_installed():
            return False
            
        return self.detect_socket() is not None


def get_connector() -> LinuxConnector:
    """Factory function."""
    return LinuxConnector()
