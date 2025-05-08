"""
Logging configuration for WiseFlow.

This module provides functions to configure logging for the WiseFlow system.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional, Dict, Any, Union


def configure_logging(
    log_file: Optional[str] = None,
    log_level: int = logging.INFO,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    max_bytes: int = 10485760,  # 10 MB
    backup_count: int = 5,
    console: bool = True,
    logger_name: str = "wiseflow"
) -> logging.Logger:
    """
    Configure logging for the application.
    
    Args:
        log_file: Path to the log file (if None, only console logging is enabled)
        log_level: Logging level (default: INFO)
        log_format: Format string for log messages
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
        console: Whether to enable console logging
        logger_name: Name of the logger
        
    Returns:
        logging.Logger: Configured logger
    """
    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Add console handler if enabled
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Add file handler if log_file is specified
    if log_file:
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Create rotating file handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def configure_daily_logging(
    log_file: str,
    log_level: int = logging.INFO,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    backup_count: int = 30,
    console: bool = True,
    logger_name: str = "wiseflow"
) -> logging.Logger:
    """
    Configure daily rotating logging for the application.
    
    Args:
        log_file: Path to the log file
        log_level: Logging level (default: INFO)
        log_format: Format string for log messages
        backup_count: Number of backup log files to keep
        console: Whether to enable console logging
        logger_name: Name of the logger
        
    Returns:
        logging.Logger: Configured logger
    """
    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Add console handler if enabled
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Create directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create timed rotating file handler
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=backup_count
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d"
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str, config: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """
    Get a logger with the specified name and configuration.
    
    Args:
        name: Name of the logger
        config: Logger configuration
        
    Returns:
        logging.Logger: Configured logger
    """
    if config is None:
        # Use default configuration
        return logging.getLogger(name)
    
    # Extract configuration parameters
    log_file = config.get("file")
    log_level_name = config.get("level", "INFO")
    log_format = config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    max_bytes = config.get("max_bytes", 10485760)  # 10 MB
    backup_count = config.get("backup_count", 5)
    console = config.get("console", True)
    rotation = config.get("rotation", "size")  # "size" or "daily"
    
    # Convert log level name to integer
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    
    # Configure logging based on rotation type
    if rotation == "daily" and log_file:
        return configure_daily_logging(
            log_file=log_file,
            log_level=log_level,
            log_format=log_format,
            backup_count=backup_count,
            console=console,
            logger_name=name
        )
    else:
        return configure_logging(
            log_file=log_file,
            log_level=log_level,
            log_format=log_format,
            max_bytes=max_bytes,
            backup_count=backup_count,
            console=console,
            logger_name=name
        )


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds context information to log messages.
    """
    
    def __init__(self, logger: logging.Logger, extra: Optional[Dict[str, Any]] = None):
        """
        Initialize a LoggerAdapter.
        
        Args:
            logger: The logger to adapt
            extra: Extra context information
        """
        super().__init__(logger, extra or {})
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """
        Process the log message by adding context information.
        
        Args:
            msg: The log message
            kwargs: Keyword arguments for the log method
            
        Returns:
            tuple: Processed message and kwargs
        """
        # Add context information to the message
        context_str = " ".join(f"{k}={v}" for k, v in self.extra.items())
        if context_str:
            msg = f"{msg} [{context_str}]"
        
        return msg, kwargs
    
    def update_context(self, **kwargs: Any) -> None:
        """
        Update the context information.
        
        Args:
            **kwargs: Context information to update
        """
        self.extra.update(kwargs)


def get_logger_with_context(name: str, context: Optional[Dict[str, Any]] = None,
                          config: Optional[Dict[str, Any]] = None) -> LoggerAdapter:
    """
    Get a logger adapter with context information.
    
    Args:
        name: Name of the logger
        context: Context information
        config: Logger configuration
        
    Returns:
        LoggerAdapter: Logger adapter with context
    """
    logger = get_logger(name, config)
    return LoggerAdapter(logger, context)

