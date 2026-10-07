"""
Connectors module for platform-specific container runtime connections.

This module provides platform-specific connectors for different operating systems
to detect and connect to container runtimes like Podman and Docker.
"""

import os
import platform
from typing import Optional


def get_connector(runtime: str = "podman"):
    """
    Get the appropriate connector for the current platform and runtime.

    Args:
        runtime: Container runtime to use ("podman" or "docker")

    Returns:
        Connector instance for the current platform and runtime

    Raises:
        NotImplementedError: If the current platform or runtime is not supported
    """
    system = platform.system()
    runtime = runtime.lower()

    if system == "Darwin":
        if runtime == "docker":
            from rapidctl.bootstrap.connectors.docker_osx import get_connector as get_docker_osx_connector
            return get_docker_osx_connector()
        elif runtime == "podman":
            from rapidctl.bootstrap.connectors.osx import get_connector as get_osx_connector
            return get_osx_connector()
        else:
            raise NotImplementedError(f"Unsupported runtime '{runtime}' on macOS")
    elif system == "Linux":
        if runtime == "docker":
            from rapidctl.bootstrap.connectors.docker_linux import get_connector as get_docker_linux_connector
            return get_docker_linux_connector()
        elif runtime == "podman":
            from rapidctl.bootstrap.connectors.linux import get_connector as get_linux_connector
            return get_linux_connector()
        else:
            raise NotImplementedError(f"Unsupported runtime '{runtime}' on Linux")
    elif system == "Windows":
        # TODO: Implement Windows connector
        raise NotImplementedError(f"Windows connector not yet implemented")
    else:
        raise NotImplementedError(f"Unsupported platform: {system}")


def detect_socket(runtime: str = "podman") -> Optional[str]:
    """
    Detect the container runtime socket for the current platform.

    Args:
        runtime: Container runtime to use ("podman" or "docker")

    Returns:
        str: Socket URI or None if not found
    """
    connector = get_connector(runtime)
    return connector.detect_socket()