import logging
from pathlib import Path
from typing import Optional

def setup_logging(debug: bool = False, log_file: Optional[Path] = None) -> None:
    """
    Sets up the logging configuration for rapidctl.
    
    Args:
        debug: If True, set log level to DEBUG and format with metadata.
        log_file: Optional path to write persistent debug logs.
    """
    level = logging.DEBUG if debug else logging.INFO
    
    # Root logger of rapidctl package
    logger = logging.getLogger("rapidctl")
    logger.setLevel(logging.DEBUG)  # Root logger captures everything; filtering is done at handler level
    
    # Clear existing handlers to prevent duplicate logging
    logger.handlers.clear()
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Simple, clean user-facing format by default; metadata format for debug
    if debug:
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    else:
        formatter = logging.Formatter('%(message)s')
        
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File Handler
    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)  # File logging is always at DEBUG level
            file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s')
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # Fallback to sys.stderr if logging to file fails, but do not crash the CLI
            logger.warning(f"Could not set up log file handler: {e}")
