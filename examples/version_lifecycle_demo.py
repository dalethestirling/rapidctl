#!/usr/bin/env python
"""
Demonstration of container version management lifecycle.
This script shows how to:
1. Identify current version
2. List all local versions
3. Find newer versions
4. Seamlessly update the utilized version
"""

import sys
import os

# Ensure we can import rapidctl
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.bootstrap.client import CtlClient
from rapidctl.cli import PodmanCLI
import rapidctl.cli.actions as actions

def version_lifecycle_demo():
    print("=== Rapidctl Version Lifecycle Management Demo ===")
    
    # 1. Setup Client
    client = CtlClient()
    client.container_repo = "ghcr.io/dalethestirling/rapidctl-container"
    client.baseline_version = "1746190043" # An older version
    
    print(f"Initial preferred version: {client.get_version()}")
    
    # 2. Connect to Podman
    cli = PodmanCLI()
    try:
        cli._connect_to_podman()
    except Exception as e:
        print(f"Error connecting to Podman: {e}")
        return

    # 3. List all local versions
    print("\nScanning for local versions...")
    all_versions = actions.list_local_versions(cli, client.container_repo)
    if all_versions:
        print(f"Found local versions: {', '.join(all_versions)}")
    else:
        print("No local versions found for this repo.")

    # 4. Identify if a newer version is available locally
    print("\nChecking for newer versions...")
    newer = actions.find_newer_version(cli, client.container_repo, client.get_version())
    
    if newer:
        print(f"★ NEW VERSION IDENTIFIED: {newer}")
        
        # 5. Update the utilized version
        print(f"Updating application to use version {newer}...")
        client.set_version(newer)
        print(f"✓ Current preferred version updated to: {client.get_version()}")
    else:
        print("You are using the latest local version.")

    # 6. Ensure the container exists (pull if necessary)
    # Since we use local versions in this demo, let's just show the ensure_version action
    print(f"\nEnsuring container {client.container_version} is ready for execution...")
    # This would normally pull if the tag wasn't local
    image_id = actions.find_container(cli, client.container_version)
    if image_id:
        print(f"✓ Container ready (ID: {image_id})")
    else:
        print("Container not found locally. (ensure_version would normally pull it here)")

    print("\n=== Demo Complete ===")

if __name__ == "__main__":
    version_lifecycle_demo()
