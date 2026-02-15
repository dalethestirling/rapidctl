from typing import List, Optional
import json
import os
from pathlib import Path
from rapidctl.utils.version import VersionParser


def local_search(podman_session, container):
    local_images = podman_session.list_images()

    for image in local_images: 
        if container in image.tags:
            return image.short_id
    
    return None

def parse_version(version_string: str) -> dict:
    """Task to parse a version string using VersionParser."""
    return VersionParser.parse(version_string)


def compare_versions(version1: str, version2: str) -> int:
    """Task to compare two versions using VersionParser."""
    return VersionParser.compare(version1, version2)


def get_local_image_tags(podman_session, repo: str) -> List[str]:
    """Task to get all local tags for a specific repository."""
    local_images = podman_session.list_images()
    tags = []
    
    for image in local_images:
        if image.tags:
            for tag in image.tags:
                # Check if this tag belongs to our repo
                if tag.startswith(repo + ":") or tag == repo:
                    # Extract just the tag part if it's the full repo:tag
                    tag_part = tag.split(':')[-1] if ':' in tag else "latest"
                    if tag_part not in tags:
                        tags.append(tag_part)
                elif ":" not in tag and repo in tag:
                    # Partial match if repo is in tag (like "ubuntu" in "docker.io/library/ubuntu")
                    pass
    
    return tags

def _get_state_file_path() -> Path:
    """Helper to get the path to the rapidctl state file."""
    return Path.home() / ".rapidctl.vstate"


def read_version_state(repo: str) -> Optional[str]:
    """Task to read the persisted version tag for a repo."""
    state_file = _get_state_file_path()
    if not state_file.exists():
        return None
    
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
            return state.get(repo)
    except (json.JSONDecodeError, OSError):
        return None


def write_version_state(repo: str, version: str) -> None:
    """Task to write the preferred version tag for a repo."""
    state_file = _get_state_file_path()
    state = {}
    
    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    
    state[repo] = version
    
    try:
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=4)
    except OSError:
        pass
