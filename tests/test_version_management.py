#!/usr/bin/env python
"""Test suite for container version management functionality."""

import sys
import os
import unittest
from unittest.mock import MagicMock

# Ensure we can import rapidctl
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.utils.version import VersionParser
import rapidctl.cli.tasks as tasks
import rapidctl.cli.actions as actions
from rapidctl.bootstrap.client import CtlClient
import json
import tempfile
from pathlib import Path


class TestVersionParser(unittest.TestCase):
    def test_semver_detection(self):
        self.assertTrue(VersionParser.is_semver("1.2.3"))
        self.assertTrue(VersionParser.is_semver("v1.2.3"))
        self.assertFalse(VersionParser.is_semver("1746190043"))
        self.assertFalse(VersionParser.is_semver("latest"))

    def test_timestamp_detection(self):
        self.assertTrue(VersionParser.is_timestamp("1746190043"))
        self.assertFalse(VersionParser.is_timestamp("1.2.3"))
        self.assertFalse(VersionParser.is_timestamp("v1.2.3"))

    def test_compare_semver(self):
        self.assertEqual(VersionParser.compare("1.2.3", "1.2.4"), -1)
        self.assertEqual(VersionParser.compare("2.0.0", "1.9.9"), 1)
        self.assertEqual(VersionParser.compare("1.2.3", "1.2.3"), 0)
        self.assertEqual(VersionParser.compare("v1.2.3", "1.2.3"), 0)

    def test_compare_timestamps(self):
        self.assertEqual(VersionParser.compare("1000", "2000"), -1)
        self.assertEqual(VersionParser.compare("2000", "1000"), 1)
        self.assertEqual(VersionParser.compare("1000", "1000"), 0)

    def test_compare_latest(self):
        self.assertEqual(VersionParser.compare("1.2.3", "latest"), -1)
        self.assertEqual(VersionParser.compare("latest", "1.2.3"), 1)
        self.assertEqual(VersionParser.compare("latest", "latest"), 0)

    def test_compare_mixed(self):
        # We decided timestamp is newer than semver for this specific project pattern
        self.assertEqual(VersionParser.compare("1.0.0", "1746190043"), -1)
        self.assertEqual(VersionParser.compare("1746190043", "1.0.0"), 1)


class TestVersionTasks(unittest.TestCase):
    def test_get_local_image_tags(self):
        mock_podman = MagicMock()
        mock_img1 = MagicMock()
        mock_img1.tags = ["repo:1.0.0", "repo:v1.0.0"]
        mock_img2 = MagicMock()
        mock_img2.tags = ["repo:1.1.0"]
        mock_img3 = MagicMock()
        mock_img3.tags = ["other:2.0.0"]
        
        mock_podman.list_images.return_value = [mock_img1, mock_img2, mock_img3]
        
        tags = tasks.get_local_image_tags(mock_podman, "repo")
        self.assertIn("1.0.0", tags)
        self.assertIn("v1.0.0", tags)
        self.assertIn("1.1.0", tags)
        self.assertNotIn("2.0.0", tags)


class TestVersionActions(unittest.TestCase):
    def test_list_local_versions(self):
        mock_podman = MagicMock()
        mock_img = MagicMock()
        mock_img.tags = ["repo:1.0.0", "repo:1.2.0", "repo:1.1.0"]
        mock_podman.list_images.return_value = [mock_img]
        
        versions = actions.list_local_versions(mock_podman, "repo")
        self.assertEqual(versions, ["1.2.0", "1.1.0", "1.0.0"])

    def test_find_newer_version(self):
        mock_podman = MagicMock()
        mock_img = MagicMock()
        mock_img.tags = ["repo:1.0.0", "repo:1.2.0", "repo:1.1.0"]
        mock_podman.list_images.return_value = [mock_img]
        
        newer = actions.find_newer_version(mock_podman, "repo", "1.1.0")
        self.assertEqual(newer, "1.2.0")
        
        no_newer = actions.find_newer_version(mock_podman, "repo", "1.2.0")
        self.assertIsNone(no_newer)

    def test_find_newer_version(self):
        mock_podman = MagicMock()
        mock_img = MagicMock()
        mock_img.tags = ["repo:1.0.0", "repo:1.2.0", "repo:1.1.0"]
        mock_podman.list_images.return_value = [mock_img]
        
        no_newer = actions.find_newer_version(mock_podman, "repo", "1.2.0")
        self.assertIsNone(no_newer)


class TestVersionPersistence(unittest.TestCase):
    def setUp(self):
        # Mock the state file path to a temporary one
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_path = Path(self.temp_file.name)
        tasks._get_state_file_path = lambda: self.temp_path

    def tearDown(self):
        if self.temp_path.exists():
            os.unlink(self.temp_path)

    def test_read_write_state(self):
        repo = "test-repo"
        version = "2.0.0"
        
        # Write state
        tasks.write_version_state(repo, version)
        
        # Read state back
        read_version = tasks.read_version_state(repo)
        self.assertEqual(read_version, version)

    def test_client_persistence_integration(self):
        repo = "persistent-repo"
        version = "3.1.4"
        
        # Manually write state
        tasks.write_version_state(repo, version)
        
        # Create client - should load version automatically
        client = CtlClient()
        client.container_repo = repo
        client._load_persisted_version() # Trigger reload since repo wasn't set in __init__
        
        self.assertEqual(client.baseline_version, version)
        self.assertEqual(client.get_version(), version)


if __name__ == "__main__":
    unittest.main()
