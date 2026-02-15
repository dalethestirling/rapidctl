class PodmanAPIError(Exception):
    """Exception raised when a podman API call fails."""
    pass

class PodmanAuthError(PodmanAPIError):
    """Exception raised when a podman registry authentication fails."""
    pass

class PodmanActionError(Exception):
    """Exception raised when rapidctl action with Podman fail."""
    pass
