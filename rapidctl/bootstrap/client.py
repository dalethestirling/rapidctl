from typing import Optional, Dict, Any
import re
from urllib.parse import urlparse
import os.path
import rapidctl.cli.tasks
from pathlib import Path
import json
import time

from rapidctl.bootstrap.state import StateManager

class CtlClient:
    """
    Class that defines and validates the required data that requires definition
    on the CTL client side of the stack.

    Once actions using this class are complete the CTL client should be ready
    to connect to the container layer and start command provisioning.
    """
    def __init__(self, state_manager: Optional[StateManager] = None):
        self.container_repo: Optional[str] = None
        self.baseline_version: str = "1.0.0"
        self.client_version: str = "0.0.1"
        self.image_id: Optional[str] = None
        self.command_path: str = "/opt/rapidctl/cmd/"
        self.cli: Optional[Any] = None
        
        # Pluggable state manager
        self.state_manager = state_manager or StateManager()
        
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



    def _load_persisted_version(self) -> None:
        """Attempt to load a pinned version from disk."""
        if self.container_repo:
            pinned = self.state_manager.get_state(f"version_{self.container_repo}")
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
            self.state_manager.set_state(f"version_{self.container_repo}", self.baseline_version)

    def connect(self):
        """
        Connect to Podman and return the active session.
        """
        if self.cli is None:
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
        import rapidctl.cli.tasks as tasks
        return tasks.sanitize_container_image(container_image)

