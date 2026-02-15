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
        except PodmanAuthError:
            # Trigger authentication action
            if rapidctl.cli.actions.authenticate_to_registry(cli, client_obj.container_version):
                # Retry once if authentication was successful
                print(f"Retrying pull for {client_obj.container_version}...")
                new_image = rapidctl.cli.actions.pull_container(cli, client_obj.container_version)
                print("✓ Pull successful")
            else:
                print("✗ Authentication failed. Cannot proceed.")
                sys.exit(1)
        except Exception as e:
            print(f"✗ Failed to obtain container: {e}")
            sys.exit(1)
