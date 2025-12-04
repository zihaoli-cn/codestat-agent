"""
Logging configuration for the application.
"""
import logging
import sys
from .config import settings


def setup_logging():
    """Configure application logging."""
    
    # Create logger
    logger = logging.getLogger("codestat")
    
    # Set level based on debug mode
    level = logging.DEBUG if settings.debug else logging.INFO
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger


# Global logger instance
logger = setup_logging()
