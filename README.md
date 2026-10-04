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

- Python 3.10+
- Podman installed and running (on macOS, you will be automatically prompted to start the machine if it is stopped)
- `podman` Python package

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/rapidctl.git
cd rapidctl

# Install dependencies
pip install podman

# Optional: Set the Podman socket path manually (auto-detected by default)
# export PODMAN_SOCKET="unix:///run/user/$(id -u)/podman/podman.sock"
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

## 📝 Example: rapidctl-examplectl

A complete reference implementation and template for building your own CLI tool can be found in the [rapidctl-examplectl](https://github.com/dalethestirling/rapidctl-examplectl) repository.

It includes:
- A working CLI wrapper
- A `Dockerfile` for the container environment
- Example command orchestration scripts
- Version management demonstrations

## 🤖 MCP Server Integration

Rapidctl includes a Model Context Protocol (MCP) server that exposes all CLI capabilities as tools for AI agents. This enables deterministic, containerized command execution through standardized tool calls.

### Starting the MCP Server

Add an `mcp` subcommand to your CLI wrapper:

```python
# In your CLI wrapper (e.g., myctl)
if __name__ == '__main__':
    # Handle MCP server subcommand
    if len(sys.argv) > 1 and sys.argv[1] == "mcp":
        sys.argv.pop(1)
        from rapidctl.cli.mcp import run_mcp_server
        run_mcp_server(client)
        sys.exit(0)
    # ... rest of CLI
```

Or run directly:
```bash
./examplectl mcp
```

### Available MCP Tools

The MCP server exposes two categories of tools:

#### Meta-Tools (prefixed with `rapidctl_` by default)

| Tool | Description | Output |
|------|-------------|--------|
| `rapidctl_version` | Get version info & check for local updates | `VersionInfo` |
| `rapidctl_list_commands` | List all available container commands | `List[CommandMetadata]` |
| `rapidctl_help` | Get detailed help for a specific command | `CommandMetadata` |
| `rapidctl_context` | Get execution context for agent orchestration | `ToolsetInfo` |

#### Container Command Tools

Each container subcommand (e.g., `hello-world`, `reflector`) is exposed as a tool with its own parameter schema derived from `commands.json`.

**Example `hello-world` tool:**
```json
{
  "name": "hello-world",
  "description": "Prints a simple greeting.",
  "inputSchema": {"type": "object", "properties": {}, "additionalProperties": false}
}
```

**Example `reflector` tool:**
```json
{
  "name": "reflector",
  "description": "Echoes whatever input is provided.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "input_string": {"type": "string", "description": "The string to reflect back."}
    },
    "required": ["input_string"]
  }
}
```

### Structured Output

All tools return structured `CommandResult` objects:

```python
class CommandResult(BaseModel):
    success: bool
    output: str
    exit_code: int
    command: str
    args: List[str]
```

For meta-tools, typed Pydantic models are returned (`VersionInfo`, `CommandMetadata`, `ToolsetInfo`).

### Configuring in AI Clients

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "examplectl": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/examplectl",
        "run",
        "examplectl",
        "mcp"
      ]
    }
  }
}
```

**Cursor / VS Code** (`.cursor/mcp.json` or `.vscode/mcp.json`):
```json
{
  "mcpServers": {
    "examplectl": {
      "command": "uv",
      "args": ["--directory", "/ABSOLUTE/PATH/TO/examplectl", "run", "examplectl", "mcp"]
    }
  }
}
```

### Execution Modes

The MCP server supports two execution modes via `RAPIDCTL_EXEC_MODE`:

- **`podman`** (default): Local Podman/Docker execution
- **`kubernetes`**: Remote Kubernetes Job execution (for server-side deployments)

```bash
# Kubernetes mode
export RAPIDCTL_EXEC_MODE=kubernetes
./examplectl mcp
```

### Custom Tool Prefix

To avoid naming conflicts when aggregating multiple MCP servers, customize the meta-tool prefix:

```python
run_mcp_server(client, tool_prefix="myctl_")
# Tools: myctl_version, myctl_list_commands, myctl_help, myctl_context
```

### Agent Usage Example

An AI agent can use the tools to execute deterministic workflows:

```python
# 1. Discover available commands
commands = await mcp.call_tool("rapidctl_list_commands", {})

# 2. Get help for a specific command
help_info = await mcp.call_tool("rapidctl_help", {"command": "deploy"})

# 3. Execute container command with structured output
result = await mcp.call_tool("deploy", {"environment": "staging", "version": "v1.2.3"})
if result.success:
    print(f"Deployed successfully: {result.output}")
else:
    print(f"Deployment failed: {result.output}")
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

- **`PODMAN_SOCKET`**: Path to Podman socket (optional)
  - If not set, rapidctl will auto-detect the socket location using platform-specific connectors
  - On macOS, auto-detection checks:
    - `~/.local/share/containers/podman/machine/podman.sock`
    - `/var/run/docker.sock`
    - Machine-specific socket locations
  - Override auto-detection by setting this variable:
    ```bash
    export PODMAN_SOCKET="unix:///path/to/your/podman.sock"
    ```
  - Useful for custom Podman installations or when running multiple Podman instances

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

## 📋 Container Contract

Rapidctl expects container images to conform to a specific contract for command discovery and execution. This enables the ecosystem pattern where **rapidctl-container** (or compatible forks) provide the command hosting environment.

### Required Container Structure

| Path | Purpose | Required |
|------|---------|----------|
| `/opt/rapidctl/cmd/` | Directory containing executable command scripts/binaries | Yes |
| `/opt/rapidctl/commands.json` | Metadata for command discovery, help, and MCP schemas | Yes |

### commands.json Schema

```json
{
  "command-name": {
    "summary": "Brief description for help text",
    "parameters": {
      "type": "object",
      "properties": {
        "param_name": {
          "type": "string|boolean|integer|...",
          "description": "Parameter description",
          "default": "optional default value"
        }
      },
      "required": ["param_name"]
    },
    "argument_mapping": {
      "positional": ["param_name"],
      "flags": {
        "param_name": ["-s", "--long-flag"]
      }
    }
  }
}
```

- **summary**: Used in help tables and MCP tool descriptions
- **parameters**: JSON Schema for MCP tool input validation and CLI argument parsing
- **argument_mapping**: Maps CLI arguments to parameter names
  - `positional`: Ordered positional arguments
  - `flags`: Maps flag names to parameter names (supports short/long forms)

### Command Requirements

- Commands must be **executable files** in `/opt/rapidctl/cmd/`
- Can be any interpreter: bash, python, compiled binaries, etc.
- Shebang (`#!/bin/bash`, `#!/usr/bin/env python3`) required for scripts
- Exit codes: 0 = success, non-zero = failure (surfaced to caller)
- Stdout/stderr streamed directly to caller

### Versioning Expectations

- Images should be tagged with **semantic versions** (`v1.2.3`) or **timestamps** (`1771729391`)
- `latest` tag should always point to the newest stable release
- Breaking changes to `commands.json` schema or command removal require version coordination

### Base Image Reference

The reference implementation is **rapidctl-container**:
- Base: `registry.access.redhat.com/ubi9/ubi` (minimal, no Python)
- Commands: `hello-world`, `reflector` (bash scripts)
- Published: `ghcr.io/dalethestirling/rapidctl-container:<timestamp>` and `latest`
- Extension: Fork → add to `cmd/` → update `commands.json` → add `dnf install` to Containerfile

### Integration with CtlClient

```python
client = CtlClient()
client.container_repo = "ghcr.io/your-org/your-container"  # Your fork
client.baseline_version = "latest"  # or specific tag
client.command_path = "/opt/rapidctl/cmd/"  # Fixed by contract
```

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
│   │   ├── state.py            # State and cache management
│   │   └── connectors/
│   │       ├── __init__.py
│   │       ├── base.py         # BaseConnector interface
│   │       ├── linux.py
│   │       └── osx.py
│   ├── cli/
│   │   ├── __init__.py         # PodmanCLI class
│   │   ├── main.py             # Main entry point
│   │   ├── actions.py          # High-level actions
│   │   ├── mcp.py              # MCP server integration
│   │   └── tasks.py            # Low-level tasks
│   ├── utils/
│   │   └── version.py          # Version utilities
│   └── errors/
│       └── __init__.py         # Custom exceptions
├── tests/
│   ├── test_client.py
│   ├── test_container_validator.py
│   └── ... (comprehensive test suite)
├── examples/
│   └── example_connector_usage.py
├── pyproject.toml           # Packaging configuration
└── README.md
```

## 🛠️ Development Status

**Current Status**: Alpha / In Development

### Known Limitations

- Limited error handling and recovery

### Roadmap

- [x] Complete command execution implementation
- [x] Add comprehensive error handling
- [x] Implement CLI argument parsing
- [x] Implement MCP support
- [x] Add logging framework
- [x] Create packaging configuration (pyproject.toml)
- [x] Expand test coverage
- [x] Add CI/CD pipeline
- [x] Platform-specific socket detection (macOS complete)
- [x] Add Linux connector
- [ ] Add Windows connector

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📄 License

[Add your license here]

## 🙋 Support

For questions or issues, please open an issue on GitHub.

---

**Note**: This project is under active development. APIs may change between versions.
