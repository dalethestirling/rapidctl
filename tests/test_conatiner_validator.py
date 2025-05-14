#!/usr/bin/env python
import sys
sys.path.insert(0, '../')

from rapidctl.bootstrap.client import CtlClient


def test_container_validator():

    client = CtlClient()

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

    for img, ansr  in test_images:
        sanitized = client._container_validator(img)
        print("Original: %s" % img)
        print("Sanitized: %s" % sanitized)
        print("--------------------------------------------------")
        assert sanitized == ansr

if __name__ == "__main__":
    test_container_validator()
