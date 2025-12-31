"""
Centralized logging configuration for SwingFinder.
Replaces print statements with proper logging.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Import config if available, otherwise use defaults
try:
    from config import LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT
except ImportError:
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[Path] = None
) -> logging.Logger:
    """
    Set up a logger with consistent formatting.
    
    Args:
        name: Logger name (usually __name__ from calling module)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set level
    log_level = level or LOG_LEVEL
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT
    )
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Create default logger for the app
app_logger = setup_logger("swingfinder")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        name: Module name (use __name__)
        
    Returns:
        Logger instance
    """
    return setup_logger(name)


# Convenience functions for quick logging
def debug(msg: str, *args, **kwargs):
    """Log debug message."""
    app_logger.debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """Log info message."""
    app_logger.info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """Log warning message."""
    app_logger.warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """Log error message."""
    app_logger.error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    """Log critical message."""
    app_logger.critical(msg, *args, **kwargs)


# Example usage in other modules:
# from utils.logger import get_logger
# logger = get_logger(__name__)
# logger.info("This is an info message")
# logger.error("This is an error message")

