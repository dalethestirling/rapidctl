import pytest
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.bootstrap.connectors import detect_socket

@pytest.fixture(scope="session")
def podman_available():
    """Detect if Podman socket is available for tests."""
    socket = detect_socket()
    return socket is not None

@pytest.fixture(autouse=True)
def skip_if_no_podman(request, podman_available):
    """Automatically skip tests that require podman if it's not available."""
    if request.node.get_closest_marker("requires_podman"):
        if not podman_available:
            pytest.skip("Podman socket not available")
