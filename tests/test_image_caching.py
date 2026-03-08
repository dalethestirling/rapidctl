#!/usr/bin/env python
"""Test suite for image caching functions."""

import sys
import os
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.cli.tasks import cached_local_search, cache_image_list
from rapidctl.bootstrap.state import StateManager

class TestImageCaching(unittest.TestCase):
    def setUp(self):
        self.state_manager = MagicMock(spec=StateManager)
        self.podman_session = MagicMock()
        
    def test_cached_search_hit(self):
        """Test that a cache hit returns the ID immediately without calling Podman."""
        self.state_manager.get_cache.return_value = [
            {"id": "sha256:123456", "short_id": "123456", "tags": ["ubuntu:latest"]}
        ]
        
        result = cached_local_search(self.state_manager, self.podman_session, "ubuntu:latest")
        
        self.assertEqual(result, "sha256:123456")
        self.podman_session.list_images.assert_not_called()
        self.state_manager.get_cache.assert_called_with("podman_images")

    def test_cached_search_miss(self):
        """Test that a cache miss calls Podman and updates the cache."""
        self.state_manager.get_cache.return_value = None
        
        # Mock what Podman CLI would return
        mock_image = MagicMock()
        mock_image.id = "sha256:789012"
        mock_image.short_id = "789012"
        mock_image.tags = ["alpine:latest"]
        self.podman_session.list_images.return_value = [mock_image]
        
        result = cached_local_search(self.state_manager, self.podman_session, "alpine:latest")
        
        self.assertEqual(result, "sha256:789012")
        self.assertEqual(self.podman_session.list_images.call_count, 2) # Once for local_search, once to rebuild cache
        self.state_manager.set_cache.assert_called_once()
        
    def test_cache_image_list_roundtrip(self):
        """Test that caching the image list formats the data correctly."""
        mock_image = MagicMock()
        mock_image.id = "sha256:abcdef"
        mock_image.short_id = "abcdef"
        mock_image.tags = ["nginx:latest"]
        
        cache_image_list(self.state_manager, [mock_image], ttl=600)
        
        self.state_manager.set_cache.assert_called_once()
        args, kwargs = self.state_manager.set_cache.call_args
        self.assertEqual(args[0], "podman_images")
        
        cached_data = args[1]
        self.assertEqual(len(cached_data), 1)
        self.assertEqual(cached_data[0]["id"], "sha256:abcdef")
        self.assertEqual(cached_data[0]["tags"], ["nginx:latest"])
        self.assertEqual(kwargs["ttl"], 600)

if __name__ == "__main__":
    unittest.main()
