# AGENTS.md - Rapidctl Development Guide

## Project Overview
Rapidctl is a Python framework for creating custom CLI tools that execute commands inside containerized environments using Podman. The main package is `rapidctl/` with entry points in `rapidctl/cli/main.py`.

## Related Repositories
These three repos form a complete ecosystem - changes often span multiple:

| Repo | Path | Purpose |
|------|------|---------|
| **rapidctl** (this repo) | `/rapidctl` | Core library: Bootstrap (CtlClient), CLI layer (PodmanCLI), actions/tasks, connectors |
| **rapidctl-container** | `../rapidctl-container` | Base container image (UBI9) with built-in commands (`hello-world`, `reflector`) at `/opt/rapidctl/cmd/`. Published to `ghcr.io/dalethestirling/rapidctl-container` with timestamp versions |
| **rapidctl-examplectl** | `../rapidctl-examplectl` | Reference CLI wrapper using rapidctl. Points to `ghcr.io/dalethestirling/rapidctl-container`. Contains `examplectl` entrypoint and custom `Dockerfile` for extending the container |

**Integration flow**: `rapidctl-container` (base image) ← `rapidctl-examplectl` (custom Dockerfile extends it) ← `rapidctl` (library executes commands inside container)

## rapidctl-container (../rapidctl-container)
- **Base image**: UBI9 (`registry.access.redhat.com/ubi9/ubi`)
- **Commands location**: `/opt/rapidctl/cmd/` (copied from local `cmd/` directory)
- **Command metadata**: `commands.json` defines summaries, parameters, argument mappings for help text
- **Built-in commands**: `hello-world`, `reflector`
- **To extend**: Add scripts to `cmd/`, update `commands.json`, add `dnf install` to Containerfile if needed
- **CI**: Builds multi-platform (amd64/arm64) on push to main, publishes to GHCR with timestamp version (`date +%s`)
- **Image tag**: `ghcr.io/dalethestirling/rapidctl-container:<timestamp>` and `latest`

## rapidctl-examplectl (../rapidctl-examplectl)
- **Entry point**: `examplectl` script instantiates `CtlClient` and calls `main(client)`
- **Container repo**: `ghcr.io/dalethestirling/rapidctl-container` (points to rapidctl-container)
- **Baseline version**: Hardcoded timestamp (e.g., `1771729391`) - must match published container version
- **Custom Dockerfile**: Extends `python:3.11-slim`, sets workdir to `/opt/rapidctl/cmd/`, entrypoint `python`
- **Usage**: `python3 examplectl <command>` - runs command inside container via rapidctl
- **Test**: `python3 -m pytest tests`

## Key Commands

### Testing
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_client.py
pytest tests/test_container_validator.py

# Run tests requiring Podman (marked with @pytest.mark.requires_podman)
pytest tests/ -m requires_podman
```

### Development
```bash
# Install in editable mode
pip install -e .

# Run linting/typecheck (if configured)
# No explicit lint config found in pyproject.toml
```

### Building/Publishing
```bash
# Build package (uses hatch-vcs for versioning)
python -m build

# Publish to PyPI (via CI on tag push)
# Tags must match v* pattern
```

## Architecture Notes
- **Entry point**: `rapidctl.cli.main.main(client_obj)` - called by user's CLI wrapper
- **Core layers**: Bootstrap (CtlClient) → CLI (PodmanCLI) → Podman API
- **Connectors**: Platform-specific socket detection (`rapidctl.bootstrap.connectors`)
- **Actions/Tasks**: High-level operations in `rapidctl/cli/actions.py` and `tasks.py`

## Test Configuration
- Tests auto-skip if Podman socket unavailable (`conftest.py` detects via `detect_socket()`)
- Mark tests requiring Podman with `@pytest.mark.requires_podman`
- CI runs on Ubuntu with Podman service started manually

## Environment Variables
- `PODMAN_SOCKET`: Override auto-detected socket path
- `RAPIDCTL_DEBUG` / `RAPIDCTL_LOG_LEVEL=DEBUG`: Enable debug logging
- `--debug`, `-d`, `--verbose`: CLI flags for debug mode

## CI Workflows
- **python-test.yml**: Runs on push/PR to main, tests Python 3.10-3.12 with Podman
- **python-publish.yml**: Builds and publishes to PyPI on release/tag push (v*)

## Versioning
- Dynamic version from VCS via `hatch-vcs` (git tags)
- No manual version bumping needed

## Common Gotchas
- Tests require running Podman socket; CI sets this up explicitly
- macOS auto-detects socket at `~/.local/share/containers/podman/machine/podman.sock`
- User CLI wrappers must instantiate `CtlClient` and pass to `main()`