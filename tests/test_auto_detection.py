#!/usr/bin/env python
"""Test that _connect_to_podman uses connector auto-detection."""

import sys
import os
import pytest

# Remove PODMAN_SOCKET from environment to test auto-detection
if "PODMAN_SOCKET" in os.environ:
    del os.environ["PODMAN_SOCKET"]

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.cli import PodmanCLI


@pytest.mark.requires_podman
def test_auto_detection():
    """Test that PodmanCLI auto-detects socket without environment variable."""
    
    print(f"Testing auto-detection in _connect_to_podman on {sys.platform}")
    print("=" * 60)
    
    # Platform-specific gating or notes
    if sys.platform not in ("darwin", "linux"):
        pytest.skip(f"Auto-detection tests not yet implemented for {sys.platform}")
    
    # Ensure PODMAN_SOCKET is not set
    assert "PODMAN_SOCKET" not in os.environ, "PODMAN_SOCKET should not be set for this test"
    print("✓ PODMAN_SOCKET environment variable not set")
    
    # Create CLI instance
    cli = PodmanCLI()
    print("✓ Created PodmanCLI instance")
    
    # Connect - should auto-detect socket
    cli._connect_to_podman()
    print("✓ Connected to Podman using auto-detection")
    
    # Verify connection works by listing images
    images = cli.list_images()
    print(f"✓ Successfully listed {len(images)} images")
    
    print("=" * 60)
    print("✓ Auto-detection test passed!")
