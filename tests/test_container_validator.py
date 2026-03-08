#!/usr/bin/env python
import sys
import unittest

sys.path.insert(0, '../')

from rapidctl.bootstrap.client import CtlClient
from rapidctl.cli.tasks import extract_registry

class TestContainerValidationAndRegistryExtraction(unittest.TestCase):
    def setUp(self):
        self.client = CtlClient()

    def test_container_validator(self):
        test_images = [
            ["ubuntu", "ubuntu"],
            ["ubuntu:20.04", "ubuntu:20.04"],
            ["docker.io/library/ubuntu:latest", "docker.io/library/ubuntu:latest"],
            ["registry.example.com/myproject/myimage:v1.2.3", "registry.example.com/myproject/myimage:v1.2.3"],
            ["http://evil.com/;rm -rf /", "http://evil.com/rm-rf"],
            ["ubuntu; rm -rf /", "ubunturm-rf"],
            ["localhost:5000/my-image", "localhost:5000/my-image"],
            [" malicious;  commands", "maliciouscommands"],
            ["docker.io/valid_repo/valid_image@sha256:abc123", "docker.io/valid_repo/valid_image@sha256:abc123"],
            ["192.168.1.100:8080/test-image", "192.168.1.100:8080/test-image"],
            ["custom-registry:12345/namespace/image:tag", "custom-registry:12345/namespace/image:tag"]
        ]

        for img, ansr in test_images:
            sanitized = self.client._container_validator(img)
            self.assertEqual(sanitized, ansr, f"Failed for image: {img}")

        self.assertIsNone(self.client._container_validator(None))
        self.assertIsNone(self.client._container_validator(""))
        self.assertIsNone(self.client._container_validator("   "))

    def test_extract_registry(self):
        self.assertEqual(extract_registry("ubuntu:latest"), "docker.io")
        self.assertEqual(extract_registry("library/ubuntu:latest"), "docker.io")
        self.assertEqual(extract_registry("ghcr.io/repo/image:tag"), "ghcr.io")
        self.assertEqual(extract_registry("localhost:5000/image:tag"), "localhost:5000")
        self.assertEqual(extract_registry("myregistry.local:8080/project/app:v1"), "myregistry.local:8080")

if __name__ == "__main__":
    unittest.main()
