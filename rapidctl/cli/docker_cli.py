#!/usr/bin/env python3

from rapidctl.errors import PodmanAPIError, PodmanAuthError, PodmanConnectionError, PodmanCommandError
import sys
import json
import os
from typing import List, Optional, Dict, Any
import re

# Import docker at module level for easier testing
try:
    import docker
except ImportError:
    docker = None


class DockerImageWrapper:
    """Wrapper to make Docker image objects compatible with PodmanCLI interface."""
    
    def __init__(self, img_dict: Dict[str, Any]):
        self.id = img_dict.get("Id", "")
        self.tags = img_dict.get("RepoTags", [])
        self.attrs = img_dict
    
    @property
    def short_id(self) -> str:
        return self.id[:12] if self.id else ""


class DockerCLI:
    """A CLI tool for interacting with Docker containers using the API."""
    
    def __init__(self):
        self.client = None
        self.auth_configs = {}
    
    def _connect_to_docker(self) -> None:
        """Connect to the Docker socket using docker.from_env() with context resolution."""
        # Try to get socket from environment first
        socket_path = os.environ.get("DOCKER_SOCKET")
        
        if docker is None:
            raise PodmanConnectionError("Docker Python SDK not installed. Install with: pip install docker")
        
        try:
            if socket_path:
                # Explicit socket provided
                self.client = docker.DockerClient(base_url=socket_path)
            else:
                # Use docker.from_env() which auto-resolves Docker CLI context
                # use_context=True (default) falls back to active Docker CLI context
                self.client = docker.from_env(use_context=True)
        except Exception as e:
            raise PodmanConnectionError(f"Failed to connect to Docker API: {str(e)}")
    
    def list_images(self):
        """List container images - returns objects compatible with PodmanCLI (with .tags, .id)"""
        try:
            images = self.client.images.list()
            return [DockerImageWrapper(img.attrs) for img in images]
        except Exception as e:
            raise PodmanAPIError(f"Failed to list images: {str(e)}")
    
    def pull_image(self, image_name: str) -> Dict[str, Any]:
        """Pull an image from a registry."""
        try:
            # Extract registry for auth checking
            from rapidctl.cli.tasks import extract_registry
            registry = extract_registry(image_name)
            
            # Use cached credentials if available
            auth_config = self.auth_configs.get(registry)
            if auth_config:
                print(f"Using cached credentials for {registry} (User: {auth_config.get('username')})")
            
            # Docker SDK auth config format
            docker_auth = None
            if auth_config:
                docker_auth = {
                    "username": auth_config.get("username"),
                    "password": auth_config.get("password"),
                    "registry": registry
                }
            
            # Pull with streaming for progress
            pull_logs = []
            # decode=True returns dicts instead of raw JSON strings
            for line in self.client.images.pull(image_name, stream=True, decode=True, auth_config=docker_auth):
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
            if any(key in error_msg for key in ["unauthorized", "auth token", "401", "authentication required", "denied"]):
                raise PodmanAuthError(f"Authentication required for {image_name}: {str(e)}")
            raise PodmanAPIError(f"Failed to pull image: {str(e)}")
    
    def login(self, username, password, registry):
        """Authenticate with a registry."""
        try:
            # Docker SDK uses different auth config format
            auth_config = {
                "username": username,
                "password": password,
                "registry": registry
            }
            result = self.client.login(username=username, password=password, registry=registry)
            # Cache credentials for pull operations
            self.auth_configs[registry] = auth_config
            return result
        except Exception as e:
            raise PodmanAPIError(f"Failed to login to {registry}: {str(e)}")
    
    def run_container(self, image_name: str, command: List[str], stream: bool = True) -> Any:
        """Run a command in a new container."""
        try:
            container = self.client.containers.run(
                image_name,
                command=command,
                detach=True
            )
        except Exception as e:
            error_msg = str(e)
            # Detect command not found errors
            if "executable file not found" in error_msg or "not found in $PATH" in error_msg or "OCI runtime attempted to invoke a command that was not found" in error_msg:
                import re
                cmd_search = re.search(r'executable file `([^`]+)`', error_msg)
                missing_cmd = cmd_search.group(1) if cmd_search else command[0]
                raise PodmanAPIError(
                    f"Command not found inside container: {missing_cmd}\n"
                    "Please verify the command exists at the expected path within the container image."
                )
            raise PodmanAPIError(f"Failed to run command in container: {error_msg}")
        
        if not stream:
            try:
                # Get all logs
                logs = container.logs(stream=False)
                if isinstance(logs, (bytes, str)):
                    pass
                else:
                    logs = b"".join(logs)
                # Wait for the container to exit
                exit_code = container.wait()
                if exit_code.get("StatusCode", 0) != 0:
                    raise PodmanCommandError(
                        f"Container command failed with exit code {exit_code.get('StatusCode')}",
                        exit_code=exit_code.get("StatusCode", 1)
                    )
                return logs
            finally:
                try:
                    container.remove()
                except Exception:
                    pass
        else:
            def log_generator():
                try:
                    # Stream container logs
                    for line in container.logs(stream=True):
                        yield line
                    
                    # Wait for container completion and get exit status
                    exit_code = container.wait()
                    if exit_code.get("StatusCode", 0) != 0:
                        raise PodmanCommandError(
                            f"Container command failed with exit code {exit_code.get('StatusCode')}",
                            exit_code=exit_code.get("StatusCode", 1)
                        )
                finally:
                    try:
                        container.remove()
                    except Exception:
                        pass
            return log_generator()
    
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
            # docker-py returns tuple (exit_code, output)
            if isinstance(exec_result, tuple) and len(exec_result) == 2:
                output = exec_result[1]
            else:
                output = getattr(exec_result, 'output', exec_result)
            return output.decode('utf-8') if isinstance(output, bytes) else str(output)
        except Exception as e:
            raise PodmanAPIError(f"Failed to execute command in container: {str(e)}")
    
    def show_logs(self, container_id: str, follow: bool = False, tail: Optional[int] = None) -> str:
        """Show container logs."""
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(stream=follow, follow=follow, tail=tail)
            if isinstance(logs, bytes):
                return logs.decode('utf-8')
            elif hasattr(logs, '__iter__'):
                return b"".join(logs).decode('utf-8')
            return str(logs)
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