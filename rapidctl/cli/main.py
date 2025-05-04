import sys
from rapidctl.cli import PodmanCLI
import rapidctl.cli.actions

def main(client_obj):
    """Main entry point for the CLI tool."""
    cli = PodmanCLI()
    cli._connect_to_podman()

    sub_command = sys.argv[1:]

    container_image = rapidctl.cli.actions.find_container(cli, client_obj.container_version)

    if not container_image:
        new_image = rapidctl.cli.actions.pull_container(cli, client_obj.container_version)
        print("Pulling container")
        print(new_image)
