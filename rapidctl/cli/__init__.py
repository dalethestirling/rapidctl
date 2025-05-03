#!/usr/bin/env python3

from rapidctl.errors import PodmanAPIError
import sys
import json
import os
from typing import List, Optional, Dict, Any
import podman


class PodmanCLI:
    """A CLI tool for interacting with Podman containers using the API."""

    def __init__(self):
        self.client = None

    def _connect_to_podman(self) -> None:
        """Connect to the podman socket."""
        socket_path = os.environ.get("PODMAN_SOCKET", "unix:///var/run/docker.sock")
        try:
            self.client = podman.client.PodmanClient(base_url=socket_path)
        except Exception as e:
            raise PodmanAPIError(f"Failed to connect to Podman API: {str(e)}")

    def list_images(self):
        """List container images"""
        try:
            images = self.client.images.list()
            return images
        except Exception as e:
            raise PodmanApiError(f"Failed to list images: {str(e)}")

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

