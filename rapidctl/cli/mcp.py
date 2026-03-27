from mcp.server.fastmcp import FastMCP
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
    for cmd, summary in available_cmds.items():
        description = summary or f"Execute {cmd} in the container environment."
        
        # Define a tool handler for this command
        # Use a closure to capture cmd and other context
        def make_handler(command_name):
            async def handler(**kwargs) -> str:
                # Prepare arguments for the command
                args = []
                for k, v in kwargs.items():
                    if isinstance(v, bool):
                        if v:
                            args.append(f"--{k}")
                    else:
                        args.append(f"--{k}")
                        args.append(str(v))
                
                try:
                    output = ""
                    # Context handles execution and streams back text chunks
                    for chunk in context.run_command(command_name, args):
                        output += chunk
                    return output
                except Exception as e:
                    return f"Error: {e}"

            return handler

        mcp.add_tool(
            name=cmd,
            fn=make_handler(cmd),
            description=description
        )

    # Run the server via stdio
    mcp.run()
