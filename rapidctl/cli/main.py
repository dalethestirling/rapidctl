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
        print(f"Ready: {client_obj.container_version} (No subcommand provided)")
