# Rapidctl

**Rapidctl** is a Python framework for creating custom CLI tools that execute commands inside containerized environments using Podman. It allows you to package and distribute CLI utilities where all dependencies and runtime environments are containerized, ensuring consistency across different systems.

## 🎯 Purpose

Rapidctl solves the problem of distributing CLI tools with complex dependencies. Instead of requiring users to install specific versions of languages, libraries, or system packages, you package everything in a container and provide a lightweight Python wrapper that handles container orchestration transparently.

## 🏗️ Architecture

Rapidctl consists of three main layers:

```
┌─────────────────────────────────────┐
│   Your Custom CLI (e.g. examplectl) │  ← User-facing entry point
├─────────────────────────────────────┤
│   Bootstrap Layer (CtlClient)       │  ← Configuration & validation
├─────────────────────────────────────┤
│   CLI Layer (PodmanCLI)             │  ← Container orchestration
├─────────────────────────────────────┤
│   Podman API                         │  ← Container runtime
└─────────────────────────────────────┘
```

### Components

- **Bootstrap Layer** (`rapidctl.bootstrap.client`)
  - `CtlClient`: Defines container configuration and validates container image names
  - Prevents command injection through input sanitization

- **Connectors** (`rapidctl.bootstrap.connectors`)
  - Connectors are used to connect to the container runtime
  - Connectors are platform specific
  - Connectors are used by the CLI Layer to interact with the container runtime
  - Connectors are plugins for different ecosystems (Window, OSX, Linux, etc)
  
- **CLI Layer** (`rapidctl.cli`)
  - `PodmanCLI`: Interfaces with Podman API for container operations
  - Handles image pulling, container management, and command execution
  
- **Actions** (`rapidctl.cli.actions`)
  - Actions are an operation to achieve an outcome 
  - Actions orchestrate and use one or more tasks to achieve their outcome

- **Tasks** (`rapidctl.cli.tasks`)
  - Tasks perform a single operation 
  - Tasks are the building blocks of actions

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- Podman installed and running
- `podman` Python package

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/rapidctl.git
cd rapidctl

# Install dependencies
pip install podman

# Set the Podman socket path (if not default)
export PODMAN_SOCKET="unix:///run/user/$(id -u)/podman/podman.sock"
```

### Creating Your Custom CLI Tool

1. **Create your CLI wrapper** (e.g., `myctl`):

```python
#!/usr/bin/env python

import re
import sys
from rapidctl.cli.main import main
from rapidctl.bootstrap import client

# Create and configure the client
client = client.CtlClient()
client.container_repo = "docker.io/myorg/mytool-container"
client.baseline_version = "1.0.0"
client.client_version = "0.0.1"

# Run the CLI
if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
    sys.exit(main(client))
```

2. **Make it executable**:

```bash
chmod +x myctl
```

3. **Use your CLI**:

```bash
./myctl <command> <args>
```

The tool will automatically:
- Check if the container image exists locally
- Pull the image if needed
- Execute your command inside the container

## 📝 Example: examplectl

The repository includes `examplectl` as a reference implementation:

```python
#!/usr/bin/env python

import re
import sys
from rapidctl.cli.main import main
from rapidctl.bootstrap import client

client = client.CtlClient()
client.container_repo = "ghcr.io/dalethestirling/rapidctl-container"
client.baseline_version = "1746190043"
client.client_version = "0.0.1"

if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
    sys.exit(main(client))
```

## 🔧 Configuration

### CtlClient Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `container_repo` | `str` | `None` | Container registry path (e.g., `docker.io/user/image`) |
| `baseline_version` | `str` | `"1.0.0"` | Container image tag/version |
| `client_version` | `str` | `"0.0.1"` | Your CLI tool version |
| `image_id` | `str` | `None` | Specific image ID (optional) |
| `command_path` | `str` | `"/opt/rapidctl/cmd/"` | Path inside container where commands are located |

### Environment Variables

- `PODMAN_SOCKET`: Path to Podman socket (default: `unix:///var/run/docker.sock`)

## 🔒 Security

Rapidctl includes container image name validation to prevent command injection attacks:

- Sanitizes registry URLs and image names
- Validates domain names and repository paths
- Removes dangerous characters (`;`, `|`, `&`, etc.)
- Supports standard Docker/Podman image formats

Example validated formats:
- `ubuntu:20.04`
- `docker.io/library/ubuntu:latest`
- `registry.example.com/myproject/myimage:v1.2.3`
- `localhost:5000/my-image`

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_client.py
pytest tests/test_container_validator.py
```

## 📦 Project Structure

```
rapidctl/
├── rapidctl/
│   ├── __init__.py
│   ├── bootstrap/
│   │   ├── __init__.py
│   │   ├── client.py           # CtlClient configuration
│   │   └── connectors/
│   │       ├── __init__.py
│   │       └── osx.py
│   ├── cli/
│   │   ├── __init__.py         # PodmanCLI class
│   │   ├── main.py             # Main entry point
│   │   ├── actions.py          # High-level actions
│   │   └── tasks.py            # Low-level tasks
│   └── errors/
│       └── __init__.py         # Custom exceptions
├── tests/
│   ├── test_client.py
│   └── test_container_validator.py
├── examplectl                  # Example CLI tool
└── README.md
```

## 🛠️ Development Status

**Current Status**: Alpha / In Development

### Known Limitations

- Command execution not yet fully implemented
- Limited error handling and recovery
- No CLI argument parsing (--help, --version, etc.)
- Platform-specific connectors incomplete

### Roadmap

- [ ] Complete command execution implementation
- [ ] Add comprehensive error handling
- [ ] Implement CLI argument parsing
- [ ] Add logging framework
- [ ] Create packaging configuration (pyproject.toml)
- [ ] Expand test coverage
- [ ] Add CI/CD pipeline
- [ ] Platform-specific socket detection

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📄 License

[Add your license here]

## 🙋 Support

For questions or issues, please open an issue on GitHub.

---

**Note**: This project is under active development. APIs may change between versions.
