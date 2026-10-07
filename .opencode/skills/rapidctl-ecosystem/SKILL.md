---
name: rapidctl-ecosystem
description: Cross-repo knowledge for rapidctl ecosystem development
---

# Rapidctl Ecosystem Knowledge

## Three Repos
| Repo | Path | Purpose |
|------|------|---------|
| rapidctl | `/rapidctl` | Core Python library |
| rapidctl-container | `../rapidctl-container` | Base container image (UBI9) |
| rapidctl-examplectl | `../rapidctl-examplectl` | Reference CLI wrapper |

## Integration Flow
```
rapidctl-container (base image)
    ↓ extends via Dockerfile
rapidctl-examplectl (custom commands)
    ↓ executes via rapidctl library
rapidctl (PodmanCLI → Podman API)
```

## Key Contracts
- **Container path**: `/opt/rapidctl/cmd/` (fixed by rapidctl library)
- **Commands metadata**: `/opt/rapidctl/commands.json`
- **Schema**: `{ "cmd": { "summary", "parameters", "argument_mapping" } }`

## Version Alignment
| Repo | Version | Sync Rule |
|------|---------|-----------|
| rapidctl | hatch-vcs (git tags) | Tag `v*` → PyPI |
| rapidctl-container | timestamp + latest | Push main → GHCR |
| rapidctl-examplectl | baseline_version | Must match container tag |

## Common Cross-Repo Changes
1. **New command**: Add to container cmd/ + commands.json → auto-discovered by examplectl
2. **Schema change**: Update container commands.json + rapidctl parser + examplectl help
3. **Container contract**: Coordinate all three repos + version bump
4. **Library feature**: Implement in rapidctl → test with examplectl → release

## Development Loop
```bash
# Library change
cd rapidctl
# edit code
pip install -e .
cd ../rapidctl-examplectl
./examplectl hello-world

# Container change
cd rapidctl-container
# edit cmd/ or Containerfile
podman build -t rapidctl-test .
cd ../rapidctl-examplectl
container_repo="rapidctl-test" baseline_version="latest" ./examplectl new-command
```