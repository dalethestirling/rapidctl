#!/usr/bin/env python
"""Test the OSX connector functionality."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.bootstrap.connectors.osx import OSXConnector, get_connector


def test_osx_connector():
    """Test OSX connector socket detection and setup."""
    
    print("=" * 60)
    print("Testing OSX Connector")
    print("=" * 60)
    
    # Get connector instance
    connector = get_connector()
    print(f"\n✓ Created connector instance: {connector}")
    
    # Test socket detection
    print("\n--- Socket Detection ---")
    socket_path = connector.detect_socket()
    if socket_path:
        print(f"✓ Socket detected: {socket_path}")
    else:
        print("✗ No socket found")
        return False
    
    # Test Podman running status
    print("\n--- Podman Status ---")
    is_running = connector.ensure_podman_running()
    if is_running:
        print(f"✓ Podman is running")
        if connector.podman_machine_name:
            print(f"  Machine name: {connector.podman_machine_name}")
    else:
        print("⚠ Podman machine status could not be determined")
        print("  (This is OK if Podman is running manually)")
    
    # Test full setup
    print("\n--- Full Setup ---")
    setup_success = connector.setup()
    if setup_success:
        print("✓ Connector setup successful")
    else:
        print("✗ Connector setup failed")
        return False
    
    # Get connection info
    print("\n--- Connection Info ---")
    info = connector.get_connection_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = test_osx_connector()
    sys.exit(0 if success else 1)
