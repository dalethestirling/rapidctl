#!/usr/bin/env python3
"""
OSX Connector for Podman

This connector handles macOS-specific requirements for connecting to Podman:
- Detects the Podman socket location
- Validates socket accessibility
- Sets up any OS-specific requirements
"""

import os
import subprocess
from pathlib import Path
from typing import Optional


class OSXConnector:
    """Connector for Podman on macOS systems."""
    
    def __init__(self):
        self.socket_path: Optional[str] = None
        self.podman_machine_name: Optional[str] = None
        
    def detect_socket(self) -> Optional[str]:
        """
        Detect the Podman socket location on macOS.
        
        Checks multiple common locations in order of preference:
        1. Environment variable PODMAN_SOCKET
        2. User's podman machine socket (~/.local/share/containers/podman/machine/podman.sock)
        3. System docker.sock (often symlinked to podman on macOS)
        4. Podman machine-specific sockets
        
        Returns:
            str: URI to the Podman socket (e.g., 'unix:///path/to/socket') or None if not found
        """
        # Check environment variable first
        env_socket = os.environ.get("PODMAN_SOCKET")
        if env_socket:
            if self._validate_socket(env_socket):
                self.socket_path = env_socket
                return env_socket
        
        # Common socket locations on macOS
        socket_candidates = [
            # Podman machine default socket (symlink)
            Path.home() / ".local/share/containers/podman/machine/podman.sock",
            # System docker.sock (may be symlinked to podman)
            Path("/var/run/docker.sock"),
            # Podman Desktop socket
            Path.home() / ".local/share/containers/podman/podman.sock",
        ]
        
        # Check each candidate
        for socket_path in socket_candidates:
            if socket_path.exists():
                socket_uri = f"unix://{socket_path}"
                if self._validate_socket(socket_uri):
                    self.socket_path = socket_uri
                    return socket_uri
        
        # Try to find machine-specific sockets
        machine_dir = Path.home() / ".local/share/containers/podman/machine"
        if machine_dir.exists():
            for machine_path in machine_dir.iterdir():
                if machine_path.is_dir():
                    socket_path = machine_path / "podman.sock"
                    if socket_path.exists():
                        socket_uri = f"unix://{socket_path}"
                        if self._validate_socket(socket_uri):
                            self.podman_machine_name = machine_path.name
                            self.socket_path = socket_uri
                            return socket_uri
        
        return None
    
    def _validate_socket(self, socket_uri: str) -> bool:
        """
        Validate that a socket path exists and is accessible.
        
        Args:
            socket_uri: Socket URI (e.g., 'unix:///path/to/socket')
            
        Returns:
            bool: True if socket is valid and accessible
        """
        # Extract path from URI
        if socket_uri.startswith("unix://"):
            socket_path = socket_uri[7:]
        else:
            socket_path = socket_uri
            
        path = Path(socket_path)
        
        # Check if path exists and is a socket
        if not path.exists():
            return False
            
        # On macOS, check if it's a socket or symlink to a socket
        if path.is_socket() or path.is_symlink():
            # Check read/write permissions
            return os.access(path, os.R_OK | os.W_OK)
            
        return False
    
    def ensure_podman_running(self) -> bool:
        """
        Check if Podman machine is running, and provide guidance if not.
        
        Returns:
            bool: True if Podman is running, False otherwise
        """
        try:
            # Check if podman command is available
            result = subprocess.run(
                ["podman", "machine", "list", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse output to check if any machine is running
                import json
                machines = json.loads(result.stdout)
                running_machines = [m for m in machines if m.get("Running", False)]
                
                if running_machines:
                    self.podman_machine_name = running_machines[0].get("Name")
                    return True
                    
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass
            
        return False
    
    def get_connection_info(self) -> dict:
        """
        Get connection information for Podman on macOS.
        
        Returns:
            dict: Connection information including socket path and machine name
        """
        if not self.socket_path:
            self.detect_socket()
            
        return {
            "socket_path": self.socket_path,
            "machine_name": self.podman_machine_name,
            "platform": "darwin",
            "connector": "osx"
        }
    
    def setup(self) -> bool:
        """
        Set up the OSX connector and validate Podman availability.
        
        This method:
        1. Detects the Podman socket
        2. Validates Podman is running
        3. Sets up any OS-specific requirements
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        # Detect socket
        socket = self.detect_socket()
        if not socket:
            return False
            
        # Check if Podman is running
        if not self.ensure_podman_running():
            # Socket exists but Podman might not be running
            # This is not necessarily an error - socket might still work
            pass
            
        return True


def get_connector() -> OSXConnector:
    """
    Factory function to get an OSX connector instance.
    
    Returns:
        OSXConnector: Configured OSX connector
    """
    connector = OSXConnector()
    return connector
