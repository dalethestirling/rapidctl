from abc import ABC, abstractmethod
from typing import List, Iterator, Dict

class ExecutionContext(ABC):
    """
    Abstract base class defining the contract for executing workloads 
    and discovering tools in different environments (e.g., Local Podman, Kubernetes Sidecar).
    """

    @abstractmethod
    def run_command(self, sub_command: str, args: List[str]) -> Iterator[str]:
        """
        Execute a command within the execution environment and stream the output.
        
        Args:
            sub_command (str): The name of the subcommand to execute.
            args (List[str]): Additional arguments for the subcommand.
            
        Yields:
            Iterator[str]: Chunks of output from the command execution.
        """
        pass

    @abstractmethod
    def get_supported_commands(self) -> Dict[str, Dict]:
        """
        Discover and return a manifest of available subcommands.
        
        Returns:
            Dict[str, Dict]: A dictionary mapping command names to their full metadata.
        """
        pass

    @abstractmethod
    def ensure_readiness(self, version: str) -> None:
        """
        Ensure the execution environment is ready for the specified version.
        
        Note:
            In local environments, this might involve pulling an image.
            In remote environments, it might involve checking the connectivity of a sidecar.
            
        Args:
            version (str): The version of the toolset required.
        """
        pass
