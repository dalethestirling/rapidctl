#!/usr/bin/env python
"""Test that _connect_to_podman uses connector auto-detection."""

import sys
import os

# Remove PODMAN_SOCKET from environment to test auto-detection
if "PODMAN_SOCKET" in os.environ:
    del os.environ["PODMAN_SOCKET"]

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.cli import PodmanCLI


def test_auto_detection():
    """Test that PodmanCLI auto-detects socket without environment variable."""
    
    print("Testing auto-detection in _connect_to_podman")
    print("=" * 60)
    
    # Ensure PODMAN_SOCKET is not set
    assert "PODMAN_SOCKET" not in os.environ, "PODMAN_SOCKET should not be set for this test"
    print("✓ PODMAN_SOCKET environment variable not set")
    
    # Create CLI instance
    cli = PodmanCLI()
    print("✓ Created PodmanCLI instance")
    
    # Connect - should auto-detect socket
    try:
        cli._connect_to_podman()
        print("✓ Connected to Podman using auto-detection")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return False
    
    # Verify connection works by listing images
    try:
        images = cli.list_images()
        print(f"✓ Successfully listed {len(images)} images")
    except Exception as e:
        print(f"✗ Failed to list images: {e}")
        return False
    
    print("=" * 60)
    print("✓ Auto-detection test passed!")
    return True


if __name__ == "__main__":
    success = test_auto_detection()
    sys.exit(0 if success else 1)
