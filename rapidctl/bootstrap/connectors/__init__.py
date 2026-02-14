"""
Connectors module for platform-specific container runtime connections.

This module provides platform-specific connectors for different operating systems
to detect and connect to container runtimes like Podman.
"""

import os
import platform
from typing import Optional


def get_connector():
    """
    Get the appropriate connector for the current platform.
    
    Returns:
        Connector instance for the current platform
        
    Raises:
        NotImplementedError: If the current platform is not supported
    """
    system = platform.system()
    
    if system == "Darwin":
        from rapidctl.bootstrap.connectors.osx import get_connector as get_osx_connector
        return get_osx_connector()
    elif system == "Linux":
        # TODO: Implement Linux connector
        raise NotImplementedError(f"Linux connector not yet implemented")
    elif system == "Windows":
        # TODO: Implement Windows connector
        raise NotImplementedError(f"Windows connector not yet implemented")
    else:
        raise NotImplementedError(f"Unsupported platform: {system}")


def detect_socket() -> Optional[str]:
    """
    Detect the container runtime socket for the current platform.
    
    Returns:
        str: Socket URI or None if not found
    """
    connector = get_connector()
    return connector.detect_socket()
