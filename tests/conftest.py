import pytest
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.bootstrap.connectors import detect_socket


@pytest.fixture(scope="session")
def podman_available():
    """Detect if Podman socket is available for tests."""
    socket = detect_socket("podman")
    return socket is not None


@pytest.fixture(scope="session")
def docker_available():
    """Detect if Docker daemon is available for tests."""
    try:
        import docker
        client = docker.from_env(use_context=True)
        client.ping()
        return True
    except Exception:
        return False


@pytest.fixture(autouse=True)
def skip_if_no_podman(request, podman_available):
    """Automatically skip tests that require podman if it's not available."""
    if request.node.get_closest_marker("requires_podman"):
        if not podman_available:
            pytest.skip("Podman socket not available")


@pytest.fixture(autouse=True)
def skip_if_no_docker(request, docker_available):
    """Automatically skip tests that require docker if it's not available."""
    if request.node.get_closest_marker("requires_docker"):
        if not docker_available:
            pytest.skip("Docker daemon not available")