#!/usr/bin/env python
"""Test suite for the StateManager class."""

import json
import sys
import os
import time
import unittest
from pathlib import Path

# Ensure we can import rapidctl
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.bootstrap.state import StateManager


class TestStateManager(unittest.TestCase):
    def setUp(self):
        # We don't want to use pytest fixtures here because it's a unittest.TestCase
        # For simplicity we'll create a temp directory and path manually
        import tempfile
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_file = Path(self.temp_dir.name) / "test_state.json"
        self.manager = StateManager(state_file=self.state_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_get_set_state(self):
        """Test round-trip of setting and getting state."""
        self.manager.set_state("my_key", "my_value")
        self.assertEqual(self.manager.get_state("my_key"), "my_value")

    def test_get_state_missing_key(self):
        """Test getting a non-existent key."""
        # Ensure file exists first
        self.manager.set_state("other_key", "val")
        self.assertIsNone(self.manager.get_state("missing_key"))

    def test_get_state_no_file(self):
        """Test getting state when file doesn't exist at all."""
        self.assertFalse(self.state_file.exists())
        self.assertIsNone(self.manager.get_state("my_key"))

    def test_cache_within_ttl(self):
        """Test cache data is returned if within TTL."""
        self.manager.set_cache("my_cache", {"data": 123}, ttl=60)
        self.assertEqual(self.manager.get_cache("my_cache"), {"data": 123})

    def test_cache_expired(self):
        """Test cache data is ignored if TTL is exceeded."""
        self.manager.set_cache("my_cache", "expired_data", ttl=1)
        # Manually manipulate the saved timestamp to simulate expiration
        with open(self.state_file, 'r') as f:
            data = json.load(f)
        
        data["cache_my_cache"]["timestamp"] = time.time() - 10
        
        with open(self.state_file, 'w') as f:
            json.dump(data, f)
            
        self.assertIsNone(self.manager.get_cache("my_cache"))

    def test_custom_state_file(self):
        """Test pluggable state file capability."""
        custom_path = Path(self.temp_dir.name) / "custom" / "path.json"
        mgr = StateManager(state_file=custom_path)
        mgr.set_state("custom", "val")
        
        self.assertTrue(custom_path.exists())
        self.assertEqual(mgr.get_state("custom"), "val")

    def test_file_corruption_handling(self):
        """Test state manager handles JSON corruption gracefully."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            f.write("not valid json {")
            
        # Should catch JSONDecodeError and return None instead of crashing
        self.assertIsNone(self.manager.get_state("my_key"))
        
        # Should overwrite bad file instead of crashing
        self.manager.set_state("new_key", "val")
        self.assertEqual(self.manager.get_state("new_key"), "val")

if __name__ == "__main__":
    unittest.main()
