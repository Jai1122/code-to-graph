"""Logging configuration for CodeToGraph."""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from .config import settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[Path] = None,
    enable_console: bool = True,
) -> None:
    """Set up logging configuration.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (default: logs/code_to_graph.log)
        enable_console: Whether to enable console logging
    """
    # Remove default logger
    logger.remove()
    
    # Use provided values or fall back to settings
    log_level = log_level or settings.log_level
    log_file = log_file or settings.logs_dir / "code_to_graph.log"
    
    # Console handler
    if enable_console:
        logger.add(
            sys.stderr,
            level=log_level,
            format=settings.log_format,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
    
    # File handler
    logger.add(
        log_file,
        level=log_level,
        format=settings.log_format,
        rotation="10 MB",
        retention="1 week",
        compression="gz",
        backtrace=True,
        diagnose=True,
    )
    
    logger.info(f"Logging initialized - Level: {log_level}, File: {log_file}")


# Set up default logging
setup_logging()