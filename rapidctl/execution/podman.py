import os
import json
from typing import List, Iterator, Dict

from rapidctl.execution.base import ExecutionContext
import rapidctl.cli.actions as actions
import rapidctl.cli.tasks as tasks

class PodmanExecutionContext(ExecutionContext):
    """
    ExecutionContext implementation for local Podman/Docker execution.
    It encapsulates the existing logic found in actions.py.
    """
    
    def __init__(self, podman_session, repo: str, command_path: str):
        """
        Initialize the context.
        
        Args:
            podman_session: Authenticated PodmanCLI instance.
            repo (str): The repository name (e.g., ghcr.io/namespace/tool).
            command_path (str): Path inside the container where scripts are located.
        """
        self.podman_session = podman_session
        self.repo = repo
        self.command_path = command_path
        self.resolved_image = None

    def ensure_readiness(self, version: str) -> None:
        """
        Ensures the requested image version is pulled locally.
        Re-uses actions.ensure_version().
        """
        actions.ensure_version(self.podman_session, self.repo, version)
        self.resolved_image = f"{self.repo}:{version}"

    def run_command(self, sub_command: str, args: List[str]) -> Iterator[str]:
        """
        Execute a command in the Podman container.
        """        
        if not self.resolved_image:
            raise RuntimeError("Execution context not ready. Call ensure_readiness() first.")
            
        full_command_path = os.path.join(self.command_path, sub_command)
        full_command = [full_command_path] + args
        
        output_stream = self.podman_session.run_container(
            self.resolved_image, 
            full_command, 
            stream=True
        )
        
        for line in output_stream:
            if isinstance(line, bytes):
                yield line.decode('utf-8')
            else:
                yield str(line)

    def get_supported_commands(self) -> Dict[str, Dict]:
        """
        Discover subcommands by reading the commands manifest or listing files inside the container.
        """
        if not self.resolved_image:
            raise RuntimeError("Execution context not ready. Call ensure_readiness() first.")
            
        base_path = os.path.dirname(self.command_path.rstrip('/'))
        json_path = os.path.join(base_path, "commands.json")
        
        try:
            output = tasks.run_command_capture(
                self.podman_session,
                self.resolved_image,
                ["cat", json_path]
            )
            if output:
                metadata = json.loads("\n".join(output))
                return metadata

        except Exception:
            pass # Fallback to ls -1
            
        try:
            commands = tasks.run_command_capture(
                self.podman_session, 
                self.resolved_image, 
                ["ls", "-1", self.command_path]
            )
            return {cmd: {"summary": ""} for cmd in sorted(commands) if cmd}
        except Exception as e:
            return {}
