import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.cli import PodmanCLI, main
from rapidctl.errors import PodmanAPIError, PodmanCommandError, PodmanConnectionError
from rapidctl.bootstrap.client import CtlClient

class TestErrorHandling(unittest.TestCase):
    
    @patch('podman.client.PodmanClient')
    def test_run_container_raises_command_error_on_nonzero_exit(self, mock_podman_client_class):
        """Test that run_container raises PodmanCommandError when container exits with non-zero code."""
        # Setup mock container
        mock_container = MagicMock()
        mock_container.logs.return_value = [b"line1\n", b"line2\n"]
        mock_container.wait.return_value = {"StatusCode": 42}
        
        # Setup mock Podman client
        mock_client_instance = MagicMock()
        mock_client_instance.containers.run.return_value = mock_container
        mock_podman_client_class.return_value = mock_client_instance
        
        cli = PodmanCLI()
        cli.client = mock_client_instance
        
        # Verify for stream=True
        generator = cli.run_container("fake_image", ["fake", "command"], stream=True)
        
        # Iterate to trigger execution and status check
        with self.assertRaises(PodmanCommandError) as context:
            list(generator)
            
        self.assertEqual(context.exception.exit_code, 42)
        mock_container.remove.assert_called_once()

    @patch('podman.client.PodmanClient')
    def test_run_container_no_stream_raises_command_error(self, mock_podman_client_class):
        """Test non-streaming run_container raises PodmanCommandError on non-zero exit."""
        mock_container = MagicMock()
        mock_container.logs.return_value = b"error output"
        mock_container.wait.return_value = {"StatusCode": 99}
        
        mock_client_instance = MagicMock()
        mock_client_instance.containers.run.return_value = mock_container
        mock_podman_client_class.return_value = mock_client_instance
        
        cli = PodmanCLI()
        cli.client = mock_client_instance
        
        with self.assertRaises(PodmanCommandError) as context:
            cli.run_container("fake_image", ["fake", "command"], stream=False)
            
        self.assertEqual(context.exception.exit_code, 99)
        mock_container.remove.assert_called_once()

    @patch('rapidctl.cli.main.setup_logging')
    @patch('rapidctl.cli.main.logger')
    @patch('sys.exit')
    def test_main_propagates_command_error_exit_code(self, mock_exit, mock_logger, mock_setup_logging):
        """Test that main entry point catches PodmanCommandError and exits with its code."""
        client_obj = MagicMock()
        
        # Mock connect to throw PodmanCommandError when main calls ensure_container_image/dispatch_subcommand
        client_obj.cli = MagicMock()
        client_obj.connect.return_value = client_obj.cli
        
        with patch('rapidctl.cli.main._ensure_container_image') as mock_ensure:
            mock_ensure.side_effect = PodmanCommandError("Command failed inside container", exit_code=7)
            
            # Run main, should catch the error and exit
            main.main(client_obj)
            
            mock_logger.error.assert_any_call("Command failed: Command failed inside container")
            mock_exit.assert_called_once_with(7)

    @patch('rapidctl.cli.main.setup_logging')
    @patch('rapidctl.cli.main.logger')
    @patch('sys.exit')
    def test_main_handles_connection_error(self, mock_exit, mock_logger, mock_setup_logging):
        """Test that main entry point catches PodmanConnectionError and exits with 1."""
        client_obj = MagicMock()
        client_obj.connect.side_effect = PodmanConnectionError("Cannot connect to socket")
        client_obj.cli = None
        
        main.main(client_obj)
        
        mock_logger.error.assert_any_call("Connection Error: Cannot connect to socket")
        mock_exit.assert_called_once_with(1)

if __name__ == '__main__':
    unittest.main()
