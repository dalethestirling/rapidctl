from mcp.server.fastmcp import FastMCP
from pydantic import create_model, Field, BaseModel
from typing import List, Optional, Dict, Any
import sys

class CommandResult(BaseModel):
    """Standard result for container command execution."""
    success: bool
    output: str
    exit_code: int
    command: str
    args: List[str]

class CommandMetadata(BaseModel):
    """Metadata for a single command."""
    name: str
    summary: str
    parameters: Optional[Dict[str, Any]] = None
    argument_mapping: Optional[Dict[str, Any]] = None

class VersionInfo(BaseModel):
    """Version information for the toolset."""
    container_repo: str
    baseline_version: str
    client_version: str
    available_versions: List[str]
    latest_local_version: Optional[str] = None
    has_update: bool = False

class ToolsetInfo(BaseModel):
    """Complete toolset context for agents."""
    name: str
    version: str
    container_repo: str
    command_path: str
    execution_mode: str
    commands: List[CommandMetadata]

class HelpArgs(BaseModel):
    command: str = Field(description="Name of the command to get help for")

def run_mcp_server(client_obj, tool_prefix: str = "rapidctl_"):
    """
    Starts an MCP server that exposes container subcommands as tools.
    
    Args:
        client_obj: The CtlClient instance with configuration
        tool_prefix: Prefix for meta-tool names (default: "rapidctl_")
    """
    # Create the MCP server
    server_name = f"rapidctl-{client_obj.container_repo.split('/')[-1]}"
    mcp = FastMCP(server_name)

    # Set up the execution context
    context = client_obj.get_execution_context()
    
    # Ensure readiness via the execution context - raise on failure
    context.ensure_readiness(client_obj.baseline_version)

    # Discover available subcommands
    try:
        available_cmds = context.get_supported_commands()
    except Exception as e:
        print(f"Failed to discover commands: {e}", file=sys.stderr)
        available_cmds = {}

    # Build command metadata list for meta-tools
    command_metadata_list = []
    for cmd, metadata in available_cmds.items():
        if not isinstance(metadata, dict):
            metadata = {"summary": str(metadata)}
        command_metadata_list.append(CommandMetadata(
            name=cmd,
            summary=metadata.get("summary", f"Execute {cmd} in the container environment."),
            parameters=metadata.get("parameters"),
            argument_mapping=metadata.get("argument_mapping")
        ))

    # ========== META-TOOLS ==========
    
    # Tool: rapidctl_version - Get version info
    async def version_tool() -> VersionInfo:
        """Get version information and check for available updates."""
        # Get available local versions (only in Podman mode)
        from rapidctl.cli.actions import list_local_versions
        import os
        exec_mode = os.environ.get("RAPIDCTL_EXEC_MODE", "podman")
        
        available_versions = []
        latest_local = None
        has_update = False
        
        if exec_mode == "podman":
            try:
                cli = client_obj.cli or client_obj.connect()
                available_versions = list_local_versions(cli, client_obj.container_repo)
                if available_versions:
                    latest_local = available_versions[0]
                    has_update = latest_local != client_obj.baseline_version
            except Exception:
                pass  # In Kubernetes mode or if Podman unavailable, skip local version check
        
        return VersionInfo(
            container_repo=client_obj.container_repo,
            baseline_version=client_obj.baseline_version,
            client_version=client_obj.client_version,
            available_versions=available_versions,
            latest_local_version=latest_local,
            has_update=has_update
        )

    mcp.add_tool(
        name=f"{tool_prefix}version",
        fn=version_tool,
        description="Get version information and check for available updates."
    )

    # Tool: rapidctl_list_commands - List all available commands
    async def list_commands_tool() -> List[CommandMetadata]:
        """List all available container commands with their metadata."""
        return command_metadata_list

    mcp.add_tool(
        name=f"{tool_prefix}list_commands",
        fn=list_commands_tool,
        description="List all available container commands with their metadata."
    )

    # Tool: rapidctl_help - Get detailed help for a specific command
    async def help_tool(args: HelpArgs) -> CommandMetadata:
        """Get detailed help for a specific command."""
        for cmd_meta in command_metadata_list:
            if cmd_meta.name == args.command:
                return cmd_meta
        # Return empty metadata if not found (structured output)
        return CommandMetadata(
            name=args.command,
            summary="Command not found",
            parameters=None,
            argument_mapping=None
        )

    mcp.add_tool(
        name=f"{tool_prefix}help",
        fn=help_tool,
        description="Get detailed help for a specific command."
    )

    # Tool: rapidctl_context - Get execution context for agents
    async def context_tool() -> ToolsetInfo:
        """Get execution context information for agent orchestration."""
        # Detect execution mode
        import os
        exec_mode = os.environ.get("RAPIDCTL_EXEC_MODE", "podman")
        
        return ToolsetInfo(
            name=server_name,
            version=client_obj.client_version,
            container_repo=client_obj.container_repo,
            command_path=client_obj.command_path,
            execution_mode=exec_mode,
            commands=command_metadata_list
        )

    mcp.add_tool(
        name=f"{tool_prefix}context",
        fn=context_tool,
        description="Get execution context information for agent orchestration."
    )

    # ========== CONTAINER COMMAND TOOLS ==========
    
    # Register each subcommand as a tool
    for cmd, metadata in available_cmds.items():
        if not isinstance(metadata, dict):
            # Fallback for old format
            metadata = {"summary": str(metadata)}
            
        description = metadata.get("summary", f"Execute {cmd} in the container environment.")
        parameters = metadata.get("parameters", {})
        argument_mapping = metadata.get("argument_mapping", {})
        
        # 1. Dynamically create a Pydantic model representing the tool schema
        fields = {}
        required_fields = parameters.get("required", [])
        for prop_name, prop_info in parameters.get("properties", {}).items():
            prop_type = str
            ptype_str = prop_info.get("type", "string")
            if ptype_str == "boolean":
                prop_type = bool
            elif ptype_str == "integer":
                prop_type = int
                
            default = ... if prop_name in required_fields else None
            fields[prop_name] = (prop_type, Field(default=default, description=prop_info.get("description", "")))
            
        ArgsModel = create_model(f"{cmd}_args", **fields)

        # 2. Define the handler utilizing the dynamic model
        # Capture ArgsModel in default argument to fix closure bug
        def make_handler(command_name, arg_mapping, ArgsModel=ArgsModel):
            async def handler(args: ArgsModel) -> CommandResult:
                cli_args = []
                args_dict = args.model_dump(exclude_none=True)
                
                # Map positional args
                for pos_arg in arg_mapping.get("positional", []):
                    if pos_arg in args_dict:
                        cli_args.append(str(args_dict[pos_arg]))
                        
                # Map flag args
                flags_mapping = arg_mapping.get("flags", {})
                for k, v in args_dict.items():
                    if k in arg_mapping.get("positional", []):
                        continue
                        
                    flag_name = flags_mapping.get(k, f"--{k}")
                    if isinstance(v, bool):
                        if v:
                            cli_args.append(flag_name)
                    else:
                        cli_args.append(flag_name)
                        cli_args.append(str(v))
                        
                try:
                    output = ""
                    exit_code = 0
                    for chunk in context.run_command(command_name, cli_args):
                        output += chunk
                    return CommandResult(
                        success=True,
                        output=output,
                        exit_code=exit_code,
                        command=command_name,
                        args=cli_args
                    )
                except Exception as e:
                    return CommandResult(
                        success=False,
                        output=f"Error: {e}",
                        exit_code=1,
                        command=command_name,
                        args=cli_args
                    )
            return handler

        mcp.add_tool(
            name=cmd,
            fn=make_handler(cmd, argument_mapping),
            description=description
        )

    # Run the server via stdio
    mcp.run()
