from typing import Optional, Dict, Any
import re
from urllib.parse import urlparse
import os.path
import rapidctl.cli.tasks
from pathlib import Path
import json
import time

class CtlClient:
    """
    Class that defines and validates the required data that requires definition
    on the CTL client side of the stack.

    Once actions using this class are complete the CTL client should be ready
    to connect to the container layer and start command provisioning.
    """
    def __init__(self):
        self.container_repo: Optional[str] = None
        self.baseline_version: str = "1.0.0"
        self.client_version: str = "0.0.1"
        self.image_id: Optional[str] = None
        self.command_path: str = "/opt/rapidctl/cmd/"
        self.cli: Optional[Any] = None
        
        # Load persisted version state if available
        self._load_persisted_version()
    
    def check_for_updates(self) -> Optional[str]:
        """Check if a newer container version exists locally."""
        import rapidctl.cli.actions as actions
        
        if not self.cli:
            self.connect()
            
        try:
            newer = actions.find_newer_version(self.cli, self.container_repo, self.baseline_version)
            return newer
        except Exception:
            return None

    def _get_state_file_path(self) -> Path:
        """Helper to get the path to the rapidctl state file."""
        return Path.home() / ".rapidctl" / "state.json"

    def get_state(self, key: str) -> Any:
        """Get a value from the state file."""
        state_file = self._get_state_file_path()
        if not state_file.exists():
            return None
        
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
                return state.get(key)
        except (json.JSONDecodeError, OSError):
            return None

    def set_state(self, key: str, value: Any) -> None:
        """Set a value in the state file."""
        state_file = self._get_state_file_path()
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state = {}
        
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        
        state[key] = value
        
        try:
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=4)
        except OSError:
            pass

    def get_cache(self, key: str) -> Any:
        """Get a cached value if it has not expired."""
        cache_data = self.get_state(f"cache_{key}")
        if cache_data and isinstance(cache_data, dict):
            timestamp = cache_data.get("timestamp", 0)
            ttl = cache_data.get("ttl", 300) # Default 5 mins
            
            if time.time() - timestamp < ttl:
                return cache_data.get("data")
        return None

    def set_cache(self, key: str, data: Any, ttl: int = 300) -> None:
        """Set a cached value with a time-to-live seconds."""
        cache_data = {
            "timestamp": time.time(),
            "ttl": ttl,
            "data": data
        }
        self.set_state(f"cache_{key}", cache_data)

    def _load_persisted_version(self) -> None:
        """Attempt to load a pinned version from disk."""
        if self.container_repo:
            pinned = self.get_state(f"version_{self.container_repo}")
            if pinned:
                self.baseline_version = pinned
    
    @property
    def container_version(self):
        """
         Function to provide an view of the container image tag

         Returns:
            str: Aggregrated version of the container repo path and version
        """
        return self._container_validator("%s:%s" % (self.container_repo, self.baseline_version))

    def set_version(self, version: str) -> None:
        """Update the baseline version with validation."""
        # Validate that the version string is safe
        safe_version = re.sub(r'[^a-zA-Z0-9._-]', '', version)
        if safe_version:
            self.baseline_version = safe_version

    def get_version(self) -> str:
        """Return the current baseline version."""
        return self.baseline_version

    def persist_version(self) -> None:
        """Persist the current baseline version to disk."""
        if self.container_repo:
            self.set_state(f"version_{self.container_repo}", self.baseline_version)

    def connect(self):
        """
        Initialize the Podman CLI connection and store it in self.cli.
        
        Returns:
            PodmanCLI: The connected CLI instance
        """
        from rapidctl.cli import PodmanCLI
        self.cli = PodmanCLI()
        self.cli._connect_to_podman()
        return self.cli

    def _container_validator(self, container_image):
        """
         Sanitize a container image URL/name to prevent command injection and ensure valid format.
    
        Args:
            container_image (str): The container image URL or name to sanitize
        
        Returns:
            str: Sanitized container image string or None if invalid
        """
        # Return None if input is None or empty
        if not container_image or not isinstance(container_image, str):
            return None
    
        # Strip whitespace
        container_image = container_image.strip()
    
        # Check if the image contains a URL/registry part
        if '/' in container_image:
            # Parse as URL if it contains protocol
            if '://' in container_image:
                try:
                    parsed = urlparse(container_image)
                    # Validate the hostname
                    if not parsed.netloc:
                        return None
                
                    # Reconstruct the path part safely
                    path_parts = [part for part in parsed.path.split('/') if part]
                    safe_path = '/'.join(re.sub(r'[^a-zA-Z0-9._-]', '', part) for part in path_parts)
                
                    # Reconstruct the URL with sanitized components
                    return f"{parsed.scheme}://{parsed.netloc}/{safe_path}"
                except Exception:
                    return None
            else:
                # Handle registry/repo/image format (like docker.io/library/ubuntu)
                parts = container_image.split('/')
                safe_parts = []
            
                for part in parts:
                    # First part might be a domain name (registry)
                    if not safe_parts and '.' in part:
                    # Basic domain validation
                        if re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\:\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\:\-]{0,61}[a-zA-Z0-9])?)*$', part):
                            safe_parts.append(part)
                        else:
                            return None
                    else:
                        # Repository and image name validation
                        safe_part = re.sub(r'[^a-zA-Z0-9._:@-]', '', part)
                        if safe_part:
                            safe_parts.append(safe_part)
            
                if safe_parts:
                    return '/'.join(safe_parts)
                return None
        else:
            # Simple image name (like "ubuntu" or "ubuntu:latest")
            image_parts = container_image.split(':')
        
            # Sanitize the image name
            safe_name = re.sub(r'[^a-zA-Z0-9._-]', '', image_parts[0])
        
            # Handle tag if present
            if len(image_parts) > 1:
                safe_tag = re.sub(r'[^a-zA-Z0-9._-]', '', image_parts[1])
                if safe_name and safe_tag:
                    return f"{safe_name}:{safe_tag}"
        
            if safe_name:
                return safe_name
        
            return None

