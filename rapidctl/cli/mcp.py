from mcp.server.fastmcp import FastMCP
import rapidctl.cli.actions
import sys
import io

def run_mcp_server(client_obj):
    """
    Starts an MCP server that exposes container subcommands as tools.
    """
    # Use the connection from client_obj, connecting if not already connected
    cli = client_obj.cli
    if cli is None:
        cli = client_obj.connect()

    # Create the MCP server
    mcp = FastMCP(f"rapidctl-{client_obj.container_repo.split('/')[-1]}")

    # Discover available subcommands
    available_cmds = rapidctl.cli.actions.get_container_subcommands(
        cli, 
        client_obj.container_version, 
        client_obj.command_path
    )

    # Register each subcommand as a tool
    for cmd, summary in available_cmds.items():
        description = summary or f"Execute {cmd} in the container environment."
        
        # Define a tool handler for this command
        # Use a closure to capture cmd and other context
        def make_handler(command_name):
            async def handler(**kwargs) -> str:
                # Prepare arguments for the command
                # For now, we converts all kwargs into a list of --key value
                args = [command_name]
                for k, v in kwargs.items():
                    if isinstance(v, bool):
                        if v:
                            args.append(f"--{k}")
                    else:
                        args.append(f"--{k}")
                        args.append(str(v))

                # Capture stdout
                output_capture = io.StringIO()
                original_stdout = sys.stdout
                sys.stdout = output_capture
                
                try:
                    rapidctl.cli.actions.run_container_command(
                        cli, 
                        client_obj.container_version, 
                        client_obj.command_path, 
                        args
                    )
                    return output_capture.getvalue()
                except Exception as e:
                    return f"Error: {e}"
                finally:
                    sys.stdout = original_stdout

            return handler

        # Register the tool
        # Note: In a real implementation, we might want to parse the subcommand's 
        # own --help to generate more specific tool arguments.
        # For now, we expose it with generic *args or similar if FastMCP supports it.
        # FastMCP dynamic registration might be simpler if we use add_tool directly.
        mcp.add_tool(
            name=cmd,
            fn=make_handler(cmd),
            description=description
        )

    # Run the server via stdio
    mcp.run()
