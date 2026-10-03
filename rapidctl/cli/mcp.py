from mcp.server.fastmcp import FastMCP
from pydantic import create_model, Field
import sys

def run_mcp_server(client_obj):
    """
    Starts an MCP server that exposes container subcommands as tools.
    """
    # Create the MCP server
    mcp = FastMCP(f"rapidctl-{client_obj.container_repo.split('/')[-1]}")

    # Set up the execution context
    context = client_obj.get_execution_context()
    
    # Ensure readiness via the execution context 
    try:
        context.ensure_readiness(client_obj.baseline_version)
    except Exception as e:
        print(f"Failed to ensure readiness: {e}")

    # Discover available subcommands
    try:
        available_cmds = context.get_supported_commands()
    except Exception as e:
        print(f"Failed to discover commands: {e}")
        available_cmds = {}

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
        def make_handler(command_name, arg_mapping):
            async def handler(args: ArgsModel) -> str:
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
                    for chunk in context.run_command(command_name, cli_args):
                        output += chunk
                    return output
                except Exception as e:
                    return f"Error: {e}"
            return handler

        mcp.add_tool(
            name=cmd,
            fn=make_handler(cmd, argument_mapping),
            description=description
        )

    # Run the server via stdio
    mcp.run()
