import rapidctl.cli.tasks
from typing import List, Optional
from functools import cmp_to_key

def find_container(podman_session, container):
    image = rapidctl.cli.tasks.local_search(podman_session, container)

    return image 

def pull_container(podman_session, container):
    print(container)
    image = podman_session.pull_image(container)

    return image

def list_local_versions(podman_session, repo: str) -> List[str]:
    """Action to list all local versions for a repo, sorted from newest to oldest."""
    tags = rapidctl.cli.tasks.get_local_image_tags(podman_session, repo)
    
    # Sort tags using the VersionParser via task compare_versions
    sorted_tags = sorted(
        tags, 
        key=cmp_to_key(rapidctl.cli.tasks.compare_versions),
        reverse=True
    )
    
    return sorted_tags


def find_newer_version(podman_session, repo: str, current_version: str) -> Optional[str]:
    """Action to find the newest available local version that is newer than current."""
    all_versions = list_local_versions(podman_session, repo)
    
    if not all_versions:
        return None
        
    newest = all_versions[0]
    
    # Compare with current
    if rapidctl.cli.tasks.compare_versions(newest, current_version) > 0:
        return newest
        
    return None


def ensure_version(podman_session, repo: str, version: str):
    """Action to ensure a specific version exists locally, pulling if necessary."""
    full_image_ref = f"{repo}:{version}"
    
    image_id = find_container(podman_session, full_image_ref)
    
    if not image_id:
        print(f"Version {version} not found locally. Pulling...")
        image = pull_container(podman_session, full_image_ref)
        if isinstance(image, dict):
            return image.get("Id")
        return image.short_id if hasattr(image, "short_id") else None
        
    return image_id


def apply_latest_available(podman_session, repo: str, current_version: str) -> str:
    """
    Action to find the latest local version, update baseline_version,
    and persist the choice to disk.
    
    Returns the version that was applied.
    """
    newer = find_newer_version(podman_session, repo, current_version)
    
    if newer:
        # Persist the choice to disk so it's sticky across executions
        rapidctl.cli.tasks.write_version_state(repo, newer)
        return newer
        
    return current_version
    return current_version


def authenticate_to_registry(podman_session, image_name: str):
    """
    Action to prompt user for credentials and log in to the registry.
    Extracts registry from image name if possible.
    """
    import getpass
    from urllib.parse import urlparse
    
    # Simple extraction of registry from image name (e.g., ghcr.io/repo/img)
    registry = "docker.io" # Default
    if "/" in image_name:
        parts = image_name.split("/")
        if "." in parts[0] or ":" in parts[0]:
            registry = parts[0]
            
    print(f"\n--- Registry Authentication Required for {registry} ---")
    username = input(f"Username: ")
    password = getpass.getpass(f"Password: ")
    
    try:
        rapidctl.cli.tasks.registry_login(podman_session, registry, username, password)
        print("✓ Login successful\n")
        return True
    except Exception as e:
        print(f"✗ Login failed: {e}\n")
        return False
