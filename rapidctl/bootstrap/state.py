import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

class StateManager:
    """
    Manages persistent state and cache data for rapidctl.
    Pluggable by design: defaults to ~/.rapidctl/state.json, but can be
    overridden for testing or multiple profiles.
    """

    def __init__(self, state_file: Optional[Path] = None):
        """
        Initialize the state manager.
        
        Args:
            state_file: Path to the JSON state file. Defaults to ~/.rapidctl/state.json
        """
        self.state_file: Path = state_file or Path.home() / ".rapidctl" / "state.json"

    def get_state(self, key: str) -> Any:
        """
        Get a value from the state file.
        
        Args:
            key: The state key
            
        Returns:
            Any: The stored value, or None if not found or on error
        """
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                return state.get(key)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read state from {self.state_file}: {e}")
            return None

    def set_state(self, key: str, value: Any) -> None:
        """
        Set a value in the state file.
        
        Args:
            key: The state key
            value: The data to store (must be JSON serializable)
        """
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        state = {}
        
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load existing state file, overwriting: {e}")
                # We intentionally don't fail here and just overwrite with empty state dict
                pass
        
        state[key] = value
        
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=4)
        except OSError as e:
            logger.warning(f"Failed to write state to {self.state_file}: {e}")

    def get_cache(self, key: str) -> Any:
        """
        Get a cached value if it has not expired.
        
        Args:
            key: The cache key
            
        Returns:
            Any: The cached data, or None if missing or expired
        """
        cache_data = self.get_state(f"cache_{key}")
        if cache_data and isinstance(cache_data, dict):
            timestamp = cache_data.get("timestamp", 0)
            ttl = cache_data.get("ttl", 300) # Default 5 mins
            
            if time.time() - timestamp < ttl:
                return cache_data.get("data")
        return None

    def set_cache(self, key: str, data: Any, ttl: int = 300) -> None:
        """
        Set a cached value with a time-to-live.
        
        Args:
            key: The cache key
            data: The data to cache
            ttl: Time to live in seconds (default: 300)
        """
        cache_data = {
            "timestamp": time.time(),
            "ttl": ttl,
            "data": data
        }
        self.set_state(f"cache_{key}", cache_data)
