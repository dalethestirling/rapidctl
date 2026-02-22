import sys
from rapidctl.cli import PodmanCLI
import rapidctl.cli.actions

def main(client_obj):
    """Main entry point for the CLI tool."""
    from rapidctl.errors import PodmanAuthError

    # Use the connection from client_obj, connecting if not already connected
    cli = client_obj.cli
    if cli is None:
        cli = client_obj.connect()

    sub_command = sys.argv[1:]

    # check for updates
    newer = client_obj.check_for_updates()
    if newer:
        print(f"--- Newer container version found: {newer} (Current: {client_obj.baseline_version}) ---")
        print(f"--- You can pin this version to your environment by running apply-update ---")

    # Handle reserved local commands
    if sub_command and sub_command[0] == "apply-update":
        from rapidctl.cli.actions import apply_latest_available
        print(f"Applying update to latest version...")
        new_v = apply_latest_available(cli, client_obj.container_repo, client_obj.baseline_version)
        if new_v != client_obj.baseline_version:
            print(f"✓ Version {new_v} is now pinned as your default.")
        else:
            print("No newer local version found to apply.")
        sys.exit(0)

    def get_container():
        return rapidctl.cli.actions.find_container(cli, client_obj.container_version)

    container_image = get_container()

    if not container_image:
        try:
            print(f"Container {client_obj.container_version} not found locally. Pulling...")
            new_image = rapidctl.cli.actions.pull_container(cli, client_obj.container_version)
            print("✓ Pull successful")
            container_image = new_image  # Update container_image after pull
        except PodmanAuthError:
            # Trigger authentication action
            if rapidctl.cli.actions.authenticate_to_registry(cli, client_obj.container_version):
                # Retry once if authentication was successful
                print(f"Retrying pull for {client_obj.container_version}...")
                new_image = rapidctl.cli.actions.pull_container(cli, client_obj.container_version)
                print("✓ Pull successful")
                container_image = new_image
            else:
                print("✗ Authentication failed. Cannot proceed.")
                sys.exit(1)
        except Exception as e:
            print(f"✗ Failed to obtain container: {e}")
            sys.exit(1)

    # Now that we have the container, run the command if provided
    if sub_command:
        # 1. Discover available subcommands
        available_cmds = rapidctl.cli.actions.get_container_subcommands(
            cli, 
            client_obj.container_version, 
            client_obj.command_path
        )
        
        # 2. Validate requested subcommand
        requested_cmd = sub_command[0]
        if available_cmds and requested_cmd not in available_cmds:
            import difflib
            print(f"✗ Error: '{requested_cmd}' is not a valid subcommand.")
            
            # Find closest matches
            suggestions = difflib.get_close_matches(requested_cmd, available_cmds, n=3, cutoff=0.5)
            if suggestions:
                print(f"Did you mean: {', '.join(suggestions)}?")
            
            print("\nAvailable commands:")
            for cmd in available_cmds:
                print(f"  - {cmd}")
            sys.exit(1)
            
        # 3. Execute
        try:
            rapidctl.cli.actions.run_container_command(
                cli, 
                client_obj.container_version, 
                client_obj.command_path, 
                sub_command
            )
        except Exception as e:
            print(f"Error executing command: {e}")
            sys.exit(1)
    else:
        # If no subcommand, maybe show available ones anyway
        available_cmds = rapidctl.cli.actions.get_container_subcommands(
            cli, 
            client_obj.container_version, 
            client_obj.command_path
        )
        if available_cmds:
            print(f"Available commands for {client_obj.container_version}:")
            for cmd in available_cmds:
                print(f"  - {cmd}")
        else:
            print(f"Ready: {client_obj.container_version} (No subcommand provided)")
