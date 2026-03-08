from typing import List, Optional
import json
import os
import re
import logging
from urllib.parse import urlparse
from pathlib import Path
from rapidctl.utils.version import VersionParser

logger = logging.getLogger(__name__)


def local_search(podman_session, container):
    local_images = podman_session.list_images()
    for img in local_images:
        if container in img.tags:
            return img.id
    return None

def cached_local_search(state_manager, podman_session, container) -> Optional[str]:
    """Search for a local image utilizing caching to speed up the process."""
    if state_manager:
        cached = state_manager.get_cache("podman_images")
        if cached:
            for info in cached:
                if container in info.get("tags", []):
                    return info.get("id")
                    
    # Cache miss or no state manager
    image_id = local_search(podman_session, container)
    
    if state_manager and image_id:
        cache_image_list(state_manager, podman_session.list_images())
        
    return image_id

def cache_image_list(state_manager, images, ttl=300) -> None:
    """Cache the list of local images."""
    if not state_manager:
        return
        
    save_data = []
    for img in images:
        save_data.append({
            "id": img.id,
            "short_id": getattr(img, 'short_id', img.id[:12] if img.id else ''),
            "tags": getattr(img, 'tags', [])
        })
    state_manager.set_cache("podman_images", save_data, ttl=ttl)

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

def read_version_state(repo: str, state_manager=None) -> Optional[str]:
    """Task to read the persisted version tag for a repo."""
    if not state_manager:
        from rapidctl.bootstrap.state import StateManager
        state_manager = StateManager()
    return state_manager.get_state(f"version_{repo}")


def write_version_state(repo: str, version: str, state_manager=None) -> None:
    """Task to write the preferred version tag for a repo."""
    if not state_manager:
        from rapidctl.bootstrap.state import StateManager
        state_manager = StateManager()
    state_manager.set_state(f"version_{repo}", version)


def registry_login(podman_session, registry, username, password):
    """Task to authenticate with a registry."""
    return podman_session.login(username=username, password=password, registry=registry)


def run_command_capture(podman_session, image_name: str, command: List[str]) -> List[str]:
    """Task to run a command and capture its output."""
    output = podman_session.run_container(image_name, command, stream=False)
    
    if isinstance(output, bytes):
        output = output.decode('utf-8')
    
    # Split into lines and strip whitespace
    return [line.strip() for line in output.split('\n') if line.strip()]


def extract_registry(image_name: str) -> str:
    """Task to extract the registry hostname from an image name."""
    registry = "docker.io"
    if not image_name:
        return registry
        
    if "/" in image_name:
        parts = image_name.split("/")
        if "." in parts[0] or ":" in parts[0]:
            registry = parts[0]
    return registry


def validate_image_url(image: str) -> Optional[str]:
    """Validate a container image specified as a URL."""
    try:
        parsed = urlparse(image)
        if not parsed.netloc:
            logger.debug(f"Invalid URL netloc in image: {image}")
            return None
    
        path_parts = [part for part in parsed.path.split('/') if part]
        safe_path = '/'.join(re.sub(r'[^a-zA-Z0-9._-]', '', part) for part in path_parts)
    
        return f"{parsed.scheme}://{parsed.netloc}/{safe_path}"
    except Exception as e:
        logger.debug(f"Exception validating URL image {image}: {e}")
        return None


def validate_image_registry(image: str) -> Optional[str]:
    """Validate a container image with registry/repo/image format."""
    parts = image.split('/')
    safe_parts = []
    
    for part in parts:
        if not safe_parts and '.' in part:
            if re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\:\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\:\-]{0,61}[a-zA-Z0-9])?)*$', part):
                safe_parts.append(part)
            else:
                logger.debug(f"Invalid registry format part: {part}")
                return None
        else:
            safe_part = re.sub(r'[^a-zA-Z0-9._:@-]', '', part)
            if safe_part:
                safe_parts.append(safe_part)
                
    if safe_parts:
        return '/'.join(safe_parts)
    return None


def validate_image_simple(image: str) -> Optional[str]:
    """Validate a simple container image name (like ubuntu:latest)."""
    image_parts = image.split(':')
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '', image_parts[0])

    if len(image_parts) > 1:
        safe_tag = re.sub(r'[^a-zA-Z0-9._-]', '', image_parts[1])
        if safe_name and safe_tag:
            return f"{safe_name}:{safe_tag}"

    if safe_name:
        return safe_name

    return None


def sanitize_container_image(container_image: str) -> Optional[str]:
    """Task to sanitize an image name to prevent command injection."""
    if not container_image or not isinstance(container_image, str):
        return None
        
    container_image = container_image.strip()
    
    if '/' in container_image:
        if '://' in container_image:
            return validate_image_url(container_image)
        else:
            return validate_image_registry(container_image)
    else:
        return validate_image_simple(container_image)

def format_command_list(available_cmds: dict) -> str:
    """Task to format the help text for available commands."""
    lines = []
    for cmd, summary in available_cmds.items():
        if summary:
            lines.append(f"  {cmd:<20} - {summary}")
        else:
            lines.append(f"  {cmd}")
    return "\n".join(lines)
