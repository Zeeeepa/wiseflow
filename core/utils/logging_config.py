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
import socket
import platform
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Callable
from datetime import datetime
from functools import wraps
import asyncio

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

# Enhanced log format with more context
ENHANCED_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<magenta>{process.name}[{process.id}]</magenta>:<yellow>{thread.name}</yellow> | "
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
    "process_name": record["process"].name,
    "thread_id": record["thread"].id,
    "thread_name": record["thread"].name,
    "hostname": socket.gethostname(),
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
    log_format: str = None,
    enhanced_format: bool = False,
    include_system_info: bool = True
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
        enhanced_format: Whether to use enhanced format with more context
        include_system_info: Whether to include system information in logs
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
        if structured_logging:
            log_format = JSON_FORMAT
        elif enhanced_format:
            log_format = ENHANCED_FORMAT
        else:
            log_format = DEFAULT_FORMAT
    
    # Add system info to logger context if requested
    if include_system_info:
        system_info = {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "app_name": app_name
        }
        logger = logger.bind(**system_info)
    
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
        
        # Add separate log file for each level if configured
        if config.get("SEPARATE_LOG_FILES_BY_LEVEL", False):
            for level in ["DEBUG", "INFO", "WARNING"]:
                level_log_file = os.path.join(log_dir, f"{app_name}_{level.lower()}.log")
                logger.add(
                    level_log_file,
                    format=log_format,
                    level=level,
                    rotation=rotation,
                    retention=retention,
                    compression="zip",
                    filter=lambda record, level=level: record["level"].name == level
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

def log_execution(log_args: bool = True, log_result: bool = False, level: str = "DEBUG"):
    """
    Decorator to log function execution with arguments and result.
    
    Args:
        log_args: Whether to log function arguments
        log_result: Whether to log function result
        level: Log level to use
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__qualname__
            module_name = func.__module__
            
            # Create context
            context = {
                "function": func_name,
                "module": module_name
            }
            
            # Log function call with arguments if requested
            if log_args:
                # Safely convert args and kwargs to strings to avoid serialization issues
                args_str = ", ".join([str(arg) for arg in args])
                kwargs_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
                params_str = f"{args_str}{', ' if args_str and kwargs_str else ''}{kwargs_str}"
                
                with_context(**context).log(level, f"Executing {func_name}({params_str})")
            else:
                with_context(**context).log(level, f"Executing {func_name}")
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Log result if requested
            if log_result:
                with_context(**context).log(level, f"{func_name} returned: {result}")
            else:
                with_context(**context).log(level, f"{func_name} completed")
            
            return result
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = func.__qualname__
            module_name = func.__module__
            
            # Create context
            context = {
                "function": func_name,
                "module": module_name
            }
            
            # Log function call with arguments if requested
            if log_args:
                # Safely convert args and kwargs to strings to avoid serialization issues
                args_str = ", ".join([str(arg) for arg in args])
                kwargs_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
                params_str = f"{args_str}{', ' if args_str and kwargs_str else ''}{kwargs_str}"
                
                with_context(**context).log(level, f"Executing async {func_name}({params_str})")
            else:
                with_context(**context).log(level, f"Executing async {func_name}")
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Log result if requested
            if log_result:
                with_context(**context).log(level, f"Async {func_name} returned: {result}")
            else:
                with_context(**context).log(level, f"Async {func_name} completed")
            
            return result
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator

def log_method_calls(cls=None, *, exclude=None, level="DEBUG"):
    """
    Class decorator to log all method calls.
    
    Args:
        cls: Class to decorate
        exclude: List of method names to exclude from logging
        level: Log level to use
        
    Returns:
        Decorated class
    """
    exclude = exclude or []
    
    def decorator(cls):
        for name, method in cls.__dict__.items():
            if callable(method) and name not in exclude and not name.startswith("__"):
                setattr(cls, name, log_execution(level=level)(method))
        return cls
    
    if cls is None:
        return decorator
    return decorator(cls)

# Configure logging on module import
configure_logging(
    log_level=config.get("LOG_LEVEL", "INFO"),
    log_to_console=True,
    log_to_file=True,
    structured_logging=config.get("STRUCTURED_LOGGING", False),
    enhanced_format=config.get("ENHANCED_LOG_FORMAT", False),
    include_system_info=config.get("INCLUDE_SYSTEM_INFO", True)
)

# Export commonly used functions and classes
__all__ = [
    "logger", "get_logger", "with_context", "LogContext", "configure_logging",
    "log_execution", "log_method_calls"
]
