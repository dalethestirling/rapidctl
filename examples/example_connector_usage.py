#!/usr/bin/env python
"""
Example showing how to use the OSX connector with the CLI.

This demonstrates how the connector should be integrated into the main CLI flow.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.bootstrap.connectors import get_connector, detect_socket
from rapidctl.cli import PodmanCLI


def example_with_auto_detection():
    """Example: Auto-detect socket and connect to Podman."""
    
    print("Example 1: Auto-detect socket")
    print("-" * 40)
    
    # Detect socket automatically
    socket_path = detect_socket()
    print(f"Detected socket: {socket_path}")
    
    # Connect to Podman using detected socket
    if socket_path:
        os.environ["PODMAN_SOCKET"] = socket_path
        cli = PodmanCLI()
        cli._connect_to_podman()
        print("✓ Connected to Podman")
        
        # List images as a test
        images = cli.list_images()
        print(f"Found {len(images)} images")
        for img in images[:3]:  # Show first 3
            tags = img.tags if img.tags else ["<none>"]
            print(f"  - {tags[0]}")
    else:
        print("✗ Could not detect socket")


def example_with_connector_info():
    """Example: Get detailed connector information."""
    
    print("\nExample 2: Get connector information")
    print("-" * 40)
    
    # Get platform-specific connector
    connector = get_connector()
    
    # Set up connector
    if connector.setup():
        print("✓ Connector setup successful")
        
        # Get connection info
        info = connector.get_connection_info()
        print("\nConnection Info:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    else:
        print("✗ Connector setup failed")


def example_integration_pattern():
    """Example: Recommended integration pattern for main CLI."""
    
    print("\nExample 3: Recommended integration pattern")
    print("-" * 40)
    
    # Step 1: Get connector for current platform
    connector = get_connector()
    
    # Step 2: Setup connector (detects socket, validates Podman)
    if not connector.setup():
        print("ERROR: Could not set up connector")
        print("Please ensure Podman is installed and running")
        return False
    
    # Step 3: Get socket path
    socket_path = connector.socket_path
    print(f"Using socket: {socket_path}")
    
    # Step 4: Set environment variable for PodmanCLI
    os.environ["PODMAN_SOCKET"] = socket_path
    
    # Step 5: Connect to Podman
    cli = PodmanCLI()
    try:
        cli._connect_to_podman()
        print("✓ Connected to Podman successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return False


if __name__ == "__main__":
    example_with_auto_detection()
    example_with_connector_info()
    example_integration_pattern()
