#!/usr/bin/env python3

from rapidctl.errors import PodmanAPIError, PodmanAuthError
import sys
import json
import os
from typing import List, Optional, Dict, Any
import podman


class PodmanCLI:
    """A CLI tool for interacting with Podman containers using the API."""

    def __init__(self):
        self.client = None
        self.auth_configs = {}

    def _connect_to_podman(self) -> None:
        """Connect to the podman socket using platform-specific connector."""
        # Try to get socket from environment first
        socket_path = os.environ.get("PODMAN_SOCKET")
        
        # If not set, use connector to auto-detect
        if not socket_path:
            try:
                from rapidctl.bootstrap.connectors import detect_socket
                socket_path = detect_socket()
                if not socket_path:
                    raise PodmanAPIError(
                        "Could not detect Podman socket. "
                        "Please ensure Podman is installed and running, "
                        "or set the PODMAN_SOCKET environment variable."
                    )
            except ImportError as e:
                raise PodmanAPIError(f"Failed to import connector: {str(e)}")
        
        try:
            self.client = podman.client.PodmanClient(base_url=socket_path)
        except Exception as e:
            raise PodmanAPIError(f"Failed to connect to Podman API at {socket_path}: {str(e)}")

    def list_images(self):
        """List container images"""
        try:
            images = self.client.images.list()
            return images
        except Exception as e:
            raise PodmanAPIError(f"Failed to list images: {str(e)}")

    def pull_image(self, image_name: str) -> Dict[str, Any]:
        """Pull an image from a registry."""
        try:
            # Extract registry for auth lookup
            registry = "docker.io"
            if "/" in image_name:
                parts = image_name.split("/")
                # If first part looks like a registry (has . or :)
                if "." in parts[0] or ":" in parts[0]:
                    registry = parts[0]
            
            # Use cached credentials if available
            auth_config = self.auth_configs.get(registry)
            if auth_config:
                print(f"Using cached credentials for {registry} (User: {auth_config.get('username')})")
            
            # The stream=True parameter provides progress information
            pull_logs = []
            for line in self.client.images.pull(image_name, stream=True, auth_config=auth_config):
                # Handle both bytes and str (some environments yield bytes)
                if isinstance(line, bytes):
                    try:
                        line = json.loads(line.decode('utf-8'))
                    except Exception:
                        # If not JSON, just decode it
                        line = {"status": line.decode('utf-8')}
                elif isinstance(line, str):
                    try:
                        line = json.loads(line)
                    except Exception:
                        line = {"status": line}

                if isinstance(line, dict) and 'status' in line:
                    status = line['status']
                    if 'progress' in line:
                        progress = line['progress']
                        print(f"{status}: {progress}", end='\r')
                    else:
                        print(f"{status}")
                pull_logs.append(line)
        
            # Get the pulled image
            image = self.client.images.get(image_name)
        
            return {
                "Id": image.id,
                "RepoTags": image.tags,
                "Size": image.attrs.get("Size"),
                "PullLogs": pull_logs
            }
        except Exception as e:
            error_msg = str(e).lower()
            if any(key in error_msg for key in ["unauthorized", "auth token", "401", "authentication required"]):
                raise PodmanAuthError(f"Authentication required for {image_name}: {str(e)}")
            raise PodmanAPIError(f"Failed to pull image: {str(e)}")

    def login(self, username, password, registry):
        """Authenticate with a registry."""
        try:
            result = self.client.login(username=username, password=password, registry=registry)
            # Cache credentials for pull operations
            self.auth_configs[registry] = {
                "username": username,
                "password": password,
                "serveraddress": registry
            }
            return result
        except Exception as e:
            raise PodmanAPIError(f"Failed to login to {registry}: {str(e)}")

    def list_containers(self, all_containers: bool = False) -> List[Dict[str, Any]]:
        """List containers."""
        try:
            containers = self.client.containers.list(all=all_containers)
            container_list = []
            for container in containers:
                container_list.append({
                    "Id": container.id,
                    "Names": container.name,
                    "Image": container.image.tags[0] if container.image.tags else container.image.id,
                    "Status": container.status,
                    "Created": container.attrs.get("Created"),
                    "Ports": container.ports
                })
            return container_list
        except Exception as e:
            raise PodmanAPIError(f"Failed to list containers: {str(e)}")

    def exec_container(self, container_id: str, cmd: List[str]) -> str:
        """Execute a command in a container."""
        try:
            container = self.client.containers.get(container_id)
            exec_result = container.exec_run(cmd)
            return exec_result.output.decode('utf-8')
        except Exception as e:
            raise PodmanAPIError(f"Failed to execute command in container: {str(e)}")

    def show_logs(self, container_id: str, follow: bool = False, tail: Optional[int] = None) -> str:
        """Show container logs."""
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(stream=follow, follow=follow, tail=tail).decode('utf-8')
            return logs
        except Exception as e:
            raise PodmanAPIError(f"Failed to get container logs: {str(e)}")

    def inspect_container(self, container_id: str) -> Dict[str, Any]:
        """Display detailed information about a container."""
        try:
            container = self.client.containers.get(container_id)
            return container.attrs
        except Exception as e:
            raise PodmanAPIError(f"Failed to inspect container: {str(e)}")

    def start_container(self, container_id: str) -> None:
        """Start a container."""
        try:
            container = self.client.containers.get(container_id)
            container.start()
        except Exception as e:
            raise PodmanAPIError(f"Failed to start container: {str(e)}")

    def stop_container(self, container_id: str) -> None:
        """Stop a container."""
        try:
            container = self.client.containers.get(container_id)
            container.stop()
        except Exception as e:
            raise PodmanAPIError(f"Failed to stop container: {str(e)}")

