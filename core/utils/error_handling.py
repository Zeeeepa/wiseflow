"""
Error handling utilities for WiseFlow.

This module provides standardized error handling mechanisms for the WiseFlow system.
"""

import logging
import traceback
import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Type, Union, List

from core.config import PROJECT_DIR

# Configure logging
logger = logging.getLogger(__name__)

class WiseflowError(Exception):
    """Base class for all WiseFlow exceptions."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize a WiseFlow error.
        
        Args:
            message: Error message
            details: Additional error details
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the error to a dictionary.
        
        Returns:
            Dictionary representation of the error
        """
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details
        }
    
    def log(self, logger_instance: Optional[logging.Logger] = None) -> None:
        """
        Log the error.
        
        Args:
            logger_instance: Logger instance to use
        """
        log = logger_instance or logger
        log.error(f"{self.__class__.__name__}: {self.message}")
        if self.details:
            log.error(f"Details: {json.dumps(self.details, indent=2)}")


class ConnectionError(WiseflowError):
    """Error raised when a connection fails."""
    pass


class DataProcessingError(WiseflowError):
    """Error raised when data processing fails."""
    pass


class ConfigurationError(WiseflowError):
    """Error raised when there is a configuration error."""
    pass


class ResourceError(WiseflowError):
    """Error raised when there is a resource error."""
    pass


class TaskError(WiseflowError):
    """Error raised when there is a task error."""
    pass


class PluginError(WiseflowError):
    """Error raised when there is a plugin error."""
    pass


def handle_exceptions(
    error_types: Optional[List[Type[Exception]]] = None,
    default_message: str = "An error occurred",
    log_error: bool = True,
    reraise: bool = False,
    save_to_file: bool = False
) -> Callable:
    """
    Decorator for handling exceptions.
    
    Args:
        error_types: List of exception types to catch
        default_message: Default error message
        log_error: Whether to log the error
        reraise: Whether to re-raise the exception
        save_to_file: Whether to save the error to a file
        
    Returns:
        Decorator function
    """
    if error_types is None:
        error_types = [Exception]
    
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except tuple(error_types) as e:
                error_message = str(e) or default_message
                if log_error:
                    logger.error(f"Error in {func.__name__}: {error_message}")
                    logger.error(traceback.format_exc())
                
                if save_to_file:
                    save_error_to_file(func.__name__, error_message, traceback.format_exc())
                
                if reraise:
                    raise
                
                # Return a default value based on the function's return annotation
                return_annotation = func.__annotations__.get('return')
                if return_annotation is None:
                    return None
                elif return_annotation is bool:
                    return False
                elif return_annotation is int:
                    return 0
                elif return_annotation is str:
                    return ""
                elif return_annotation is list or return_annotation is List:
                    return []
                elif return_annotation is dict or return_annotation is Dict:
                    return {}
                else:
                    return None
        
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except tuple(error_types) as e:
                error_message = str(e) or default_message
                if log_error:
                    logger.error(f"Error in {func.__name__}: {error_message}")
                    logger.error(traceback.format_exc())
                
                if save_to_file:
                    save_error_to_file(func.__name__, error_message, traceback.format_exc())
                
                if reraise:
                    raise
                
                # Return a default value based on the function's return annotation
                return_annotation = func.__annotations__.get('return')
                if return_annotation is None:
                    return None
                elif return_annotation is bool:
                    return False
                elif return_annotation is int:
                    return 0
                elif return_annotation is str:
                    return ""
                elif return_annotation is list or return_annotation is List:
                    return []
                elif return_annotation is dict or return_annotation is Dict:
                    return {}
                else:
                    return None
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_error(error: Exception, logger_instance: Optional[logging.Logger] = None) -> None:
    """
    Log an error.
    
    Args:
        error: Exception to log
        logger_instance: Logger instance to use
    """
    log = logger_instance or logger
    if isinstance(error, WiseflowError):
        error.log(log)
    else:
        log.error(f"{type(error).__name__}: {str(error)}")
        log.error(traceback.format_exc())


def save_error_to_file(
    function_name: str,
    error_message: str,
    traceback_str: str,
    directory: Optional[str] = None
) -> str:
    """
    Save an error to a file.
    
    Args:
        function_name: Name of the function where the error occurred
        error_message: Error message
        traceback_str: Traceback string
        directory: Directory to save the file to
        
    Returns:
        Path to the error file
    """
    if directory is None:
        directory = os.path.join(PROJECT_DIR, "errors")
    
    os.makedirs(directory, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"error_{function_name}_{timestamp}.log"
    filepath = os.path.join(directory, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Error in {function_name} at {datetime.now().isoformat()}\n")
        f.write(f"Error message: {error_message}\n")
        f.write("\nTraceback:\n")
        f.write(traceback_str)
    
    logger.info(f"Error saved to {filepath}")
    return filepath


# Import asyncio at the end to avoid circular imports
import asyncio

