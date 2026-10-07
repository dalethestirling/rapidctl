---
description: Run local E2E test with examplectl
agent: build
---

Run end-to-end test using rapidctl-examplectl against a local or published container.

## Quick Test (published container)
```bash
cd rapidctl
pip install -e .
cd ../rapidctl-examplectl
./examplectl hello-world
```

## Test with Local Container Build
```bash
cd rapidctl-container
podman build -t rapidctl-test .
cd ../rapidctl-examplectl
container_repo="rapidctl-test" baseline_version="latest" ./examplectl hello-world
container_repo="rapidctl-test" baseline_version="latest" ./examplectl reflector --help
```

## Full Matrix
```bash
# Podman (default)
./examplectl hello-world
./examplectl mcp

# Docker
RAPIDCTL_EXEC_MODE=docker ./examplectl hello-world
RAPIDCTL_EXEC_MODE=docker ./examplectl mcp
```