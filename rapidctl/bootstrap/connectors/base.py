import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BaseConnector(ABC):
    """
    Abstract base class for platform-specific Podman connectors.
    Defines the standard interface and common functionality shared
    across the operating systems.
    """

    def __init__(self):
        self.socket_path: Optional[str] = None

    @abstractmethod
    def detect_socket(self) -> Optional[str]:
        """
        Detect the Podman socket location for the current platform.
        
        Returns:
            str: URI to the Podman socket or None if not found
        """
        pass

    @abstractmethod
    def setup(self) -> bool:
        """
        Platform-specific setup routine, checking requirements and
        providing guidance or auto-starting Podman if needed.
        
        Returns:
            bool: True if Podman is ready and socket is found, False otherwise
        """
        pass

    def is_podman_installed(self) -> bool:
        """
        Check if Podman is installed on the system.
        
        Returns:
            bool: True if Podman executable is found in PATH, False otherwise
        """
        return shutil.which("podman") is not None

    def _validate_socket(self, socket_uri: str) -> bool:
        """
        Validate that a socket path exists and is accessible.
        
        Args:
            socket_uri: Socket URI (e.g., 'unix:///path/to/socket')
            
        Returns:
            bool: True if socket is valid and accessible
        """
        if socket_uri.startswith("unix://"):
            socket_path = socket_uri[7:]
        else:
            socket_path = socket_uri
            
        path = Path(socket_path)
        
        if not path.exists():
            return False
            
        # Standard check: must be a socket and accessible
        if path.is_socket():
            return os.access(path, os.R_OK | os.W_OK)
            
        return False
