class PodmanAPIError(Exception):
    """Exception raised when a podman API call fails."""
    pass

class PodmanAuthError(PodmanAPIError):
    """Exception raised when a podman registry authentication fails."""
    pass

class PodmanActionError(Exception):
    """Exception raised when rapidctl action with Podman fail."""
    pass

class PodmanConnectionError(PodmanAPIError):
    """Exception raised when connection to Podman service fails."""
    pass

class PodmanCommandError(PodmanAPIError):
    """Exception raised when a command executed inside a container fails."""
    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code

