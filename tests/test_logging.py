import os
import sys
import logging
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rapidctl.utils.logging import setup_logging

class TestLogging(unittest.TestCase):
    def setUp(self):
        # Backup handlers
        self.logger = logging.getLogger("rapidctl")
        self.original_handlers = list(self.logger.handlers)
        self.original_level = self.logger.level

    def tearDown(self):
        # Restore handlers
        self.logger.handlers = self.original_handlers
        self.logger.setLevel(self.original_level)
        # Cleanup temporary files
        temp_log = Path(__file__).parent / "temp_test_rapidctl.log"
        if temp_log.exists():
            try:
                temp_log.unlink()
            except Exception:
                pass

    def test_setup_logging_default(self):
        """Test default setup sets level to INFO for console handler."""
        setup_logging(debug=False)
        
        self.assertEqual(self.logger.level, logging.DEBUG)
        
        # Verify console handler is configured with INFO
        console_handlers = [h for h in self.logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
        self.assertEqual(len(console_handlers), 1)
        self.assertEqual(console_handlers[0].level, logging.INFO)

    def test_setup_logging_debug(self):
        """Test debug setup sets level to DEBUG for console handler."""
        setup_logging(debug=True)
        
        console_handlers = [h for h in self.logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
        self.assertEqual(len(console_handlers), 1)
        self.assertEqual(console_handlers[0].level, logging.DEBUG)

    def test_setup_logging_file(self):
        """Test logging to file setup."""
        temp_log = Path(__file__).parent / "temp_test_rapidctl.log"
        setup_logging(debug=False, log_file=temp_log)
        
        # Check if file handler is added
        file_handlers = [h for h in self.logger.handlers if isinstance(h, logging.FileHandler)]
        self.assertEqual(len(file_handlers), 1)
        self.assertEqual(file_handlers[0].level, logging.DEBUG)
        
        # Write a message and verify it is written to the file
        logger = logging.getLogger("rapidctl.test")
        logger.warning("Test warning message")
        
        # Force flush and close file handler
        file_handlers[0].close()
        
        self.assertTrue(temp_log.exists())
        with open(temp_log, "r") as f:
            content = f.read()
        self.assertIn("Test warning message", content)
        self.assertIn("WARNING", content)

if __name__ == '__main__':
    unittest.main()
