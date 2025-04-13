import sys
from rapidctl.cli import PodmanCLI()

def main():
    """Main entry point for the CLI tool."""
    cli = PodmanCLI()
    sys.exit(cli.run())
