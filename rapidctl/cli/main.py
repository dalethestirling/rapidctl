import sys
import os
import logging
from pathlib import Path
from rapidctl.cli import PodmanCLI
import rapidctl.cli.actions as actions
from rapidctl.utils.logging import setup_logging
from rapidctl.errors import PodmanConnectionError, PodmanCommandError

logger = logging.getLogger("rapidctl.cli.main")

def _check_and_notify_updates(client_obj) -> None:
    newer = client_obj.check_for_updates()
    if newer:
        logger.info(f"--- Newer container version found: {newer} (Current: {client_obj.baseline_version}) ---")
        logger.info(f"--- You can pin this version to your environment by running apply-update ---")

def _handle_reserved_commands(client_obj, cli, sub_command) -> bool:
    if not sub_command:
        return False
        
    cmd = sub_command[0]
    if cmd == "apply-update":
        logger.info(f"Applying update to latest version...")
        new_v = actions.apply_latest_available(cli, client_obj.container_repo, client_obj.baseline_version)
        if new_v != client_obj.baseline_version:
            logger.info(f"✓ Version {new_v} is now pinned as your default.")
        else:
            logger.info("No newer local version found to apply.")
        return True
        
    if cmd == "mcp":
        from rapidctl.cli.mcp import run_mcp_server
        run_mcp_server(client_obj)
        return True
        
    return False

def _ensure_container_image(client_obj, cli):
    from rapidctl.errors import PodmanAuthError
    
    container_image = actions.find_container(cli, client_obj.container_version)
    
    if not container_image:
        try:
            logger.info(f"Container {client_obj.container_version} not found locally. Pulling...")
            new_image = actions.pull_container(cli, client_obj.container_version)
            logger.info("✓ Pull successful")
            return new_image
        except PodmanAuthError:
            if actions.authenticate_to_registry(cli, client_obj.container_version):
                logger.info(f"Retrying pull for {client_obj.container_version}...")
                new_image = actions.pull_container(cli, client_obj.container_version)
                logger.info("✓ Pull successful")
                return new_image
            else:
                logger.error("✗ Authentication failed. Cannot proceed.")
                raise  # Handled in main
        except Exception as e:
            logger.error(f"✗ Failed to obtain container: {e}")
            raise

    return container_image

def _dispatch_subcommand(client_obj, cli, sub_command) -> None:
    if not sub_command:
        actions.display_available_commands(
            cli, 
            client_obj.container_version, 
            client_obj.command_path,
            f"Ready: {client_obj.container_version} (No subcommand provided)\nAvailable commands:"
        )
        return

    requested_cmd = sub_command[0]
    
    if requested_cmd in ('--help', '-h'):
        actions.display_available_commands(
            cli, 
            client_obj.container_version, 
            client_obj.command_path,
            f"Available commands for {client_obj.container_version}:"
        )
        sys.exit(0)
        
    available_cmds = actions.get_container_subcommands(
        cli, 
        client_obj.container_version, 
        client_obj.command_path
    )
        
    if len(sub_command) == 2 and sub_command[1] in ('--help', '-h') and requested_cmd in available_cmds:
        summary = available_cmds.get(requested_cmd)
        logger.info(f"Command: {requested_cmd}")
        logger.info(f"  {summary if summary else 'No description available.'}")
        sys.exit(0)
        
    if available_cmds and requested_cmd not in available_cmds:
        import difflib
        logger.error(f"✗ Error: '{requested_cmd}' is not a valid subcommand.")
        suggestions = difflib.get_close_matches(requested_cmd, available_cmds.keys(), n=3, cutoff=0.5)
        if suggestions:
            logger.error(f"Did you mean: {', '.join(suggestions)}?")
            
        logger.error("\nAvailable commands:")
        from rapidctl.cli.tasks import format_command_list
        logger.error(format_command_list(available_cmds))
        sys.exit(1)
        
    try:
        actions.run_container_command(
            cli, 
            client_obj.container_version, 
            client_obj.command_path, 
            sub_command
        )
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        raise

def main(client_obj):
    """Main entry point for the CLI tool."""
    debug_mode = False
    if os.environ.get("RAPIDCTL_DEBUG") in ("1", "true", "TRUE") or os.environ.get("RAPIDCTL_LOG_LEVEL", "").upper() == "DEBUG":
        debug_mode = True
        
    for flag in ("--debug", "-d", "--verbose"):
        if flag in sys.argv:
            debug_mode = True
            while flag in sys.argv:
                sys.argv.remove(flag)

    setup_logging(debug=debug_mode, log_file=Path.home() / ".rapidctl" / "rapidctl.log")

    try:
        cli = client_obj.cli
        if cli is None:
            cli = client_obj.connect()

        sub_command = sys.argv[1:]

        _check_and_notify_updates(client_obj)

        if _handle_reserved_commands(client_obj, cli, sub_command):
            sys.exit(0)

        _ensure_container_image(client_obj, cli)
        _dispatch_subcommand(client_obj, cli, sub_command)
    except SystemExit:
        raise
    except PodmanCommandError as e:
        logger.error(f"Command failed: {e}")
        sys.exit(e.exit_code)
    except PodmanConnectionError as e:
        logger.error(f"Connection Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"CRITICAL ERROR: {e}")
        if debug_mode:
            import traceback
            traceback.print_exc()
        sys.exit(1)
