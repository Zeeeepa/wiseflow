#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Centralized logging configuration for WiseFlow.

This module provides a standardized way to configure and use logging throughout the application.
It uses loguru for all logging needs and provides consistent formatting and configuration.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

from loguru import logger

# Import config after logger to avoid circular imports
from core.config import config, PROJECT_DIR

# Define log levels with their corresponding integer values
LOG_LEVELS = {
    "TRACE": 5,
    "DEBUG": 10,
    "INFO": 20,
    "SUCCESS": 25,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50
}

# Default log format
DEFAULT_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level> | "
    "{extra}"
)

# JSON log format for structured logging
JSON_FORMAT = lambda record: json.dumps({
    "timestamp": record["time"].strftime("%Y-%m-%d %H:%M:%S.%f"),
    "level": record["level"].name,
    "message": record["message"],
    "module": record["name"],
    "function": record["function"],
    "line": record["line"],
    "process_id": record["process"].id,
    "thread_id": record["thread"].id,
    "extra": record["extra"]
})

def configure_logging(
    log_level: str = None,
    log_to_console: bool = True,
    log_to_file: bool = True,
    log_dir: str = None,
    app_name: str = "wiseflow",
    structured_logging: bool = False,
    rotation: str = "50 MB",
    retention: str = "10 days",
    log_format: str = None
) -> None:
    """
    Configure the logging system.
    
    Args:
        log_level: Minimum log level to capture (default: from config or INFO)
        log_to_console: Whether to log to console
        log_to_file: Whether to log to file
        log_dir: Directory to store log files (default: PROJECT_DIR/logs)
        app_name: Application name for log file naming
        structured_logging: Whether to use structured (JSON) logging
        rotation: When to rotate log files (default: 50 MB)
        retention: How long to keep log files (default: 10 days)
        log_format: Custom log format string
    """
    # Remove default handlers
    logger.remove()
    
    # Determine log level
    if log_level is None:
        log_level = config.get("LOG_LEVEL", "INFO")
    
    # Normalize log level
    log_level = log_level.upper()
    if log_level not in LOG_LEVELS:
        log_level = "INFO"
    
    # Determine log format
    if log_format is None:
        log_format = JSON_FORMAT if structured_logging else DEFAULT_FORMAT
    
    # Add console handler if requested
    if log_to_console:
        logger.add(
            sys.stderr,
            format=log_format,
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=True
        )
    
    # Add file handler if requested
    if log_to_file:
        if log_dir is None:
            log_dir = os.path.join(PROJECT_DIR, "logs")
        
        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Determine log file path
        log_file = os.path.join(log_dir, f"{app_name}.log")
        
        # Add file handler
        logger.add(
            log_file,
            format=log_format,
            level=log_level,
            rotation=rotation,
            retention=retention,
            compression="zip",
            backtrace=True,
            diagnose=True
        )
        
        # Add error-specific log file
        error_log_file = os.path.join(log_dir, f"{app_name}_error.log")
        logger.add(
            error_log_file,
            format=log_format,
            level="ERROR",
            rotation=rotation,
            retention=retention,
            compression="zip",
            backtrace=True,
            diagnose=True,
            filter=lambda record: record["level"].no >= LOG_LEVELS["ERROR"]
        )

def get_logger(name: str) -> logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (usually module name)
        
    Returns:
        Configured logger instance
    """
    return logger.bind(name=name)

def with_context(**kwargs) -> logger:
    """
    Create a logger with additional context.
    
    Args:
        **kwargs: Context key-value pairs
        
    Returns:
        Logger with context
    """
    return logger.bind(**kwargs)

class LogContext:
    """Context manager for adding context to logs within a block."""
    
    def __init__(self, **kwargs):
        """
        Initialize with context key-value pairs.
        
        Args:
            **kwargs: Context key-value pairs
        """
        self.context = kwargs
        self.token = None
    
    def __enter__(self):
        """Add context when entering the block."""
        self.token = logger.configure(extra=self.context)
        return logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Remove context when exiting the block."""
        logger.remove(self.token)

# Configure logging on module import
configure_logging(
    log_level=config.get("LOG_LEVEL", "INFO"),
    log_to_console=True,
    log_to_file=True,
    structured_logging=config.get("STRUCTURED_LOGGING", False)
)

# Export commonly used functions and classes
__all__ = [
    "logger", "get_logger", "with_context", "LogContext", "configure_logging"
]
