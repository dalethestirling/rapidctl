#!/usr/bin/env python
from rapidctl.bootstrap.client import CtlClient

client = CtlClient()

if __name__ == "__main__":
    test_images = [
        "ubuntu",
        "ubuntu:20.04",
        "docker.io/library/ubuntu:latest",
        "registry.example.com/myproject/myimage:v1.2.3",
        "http://evil.com/;rm -rf /",
        "ubuntu; rm -rf /",
        "localhost:5000/my-image",
        " malicious;  commands",
        "docker.io/valid_repo/valid_image@sha256:abc123",
        "192.168.1.100:8080/test-image",
        "custom-registry:12345/namespace/image:tag"
    ]

    for img in test_images:
        sanitized = client._container_validator(img)
        print(f"Original: {img}")
        print(f"Sanitized: {sanitized}")
        print("-" * 50)
