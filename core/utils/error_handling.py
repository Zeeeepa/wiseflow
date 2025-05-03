"""
Error handling utilities for Wiseflow.

This module provides standardized error handling mechanisms for the Wiseflow system.
"""

import logging
import traceback
import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Type, Union, List

# Configure logging
logger = logging.getLogger(__name__)

class WiseflowError(Exception):
    """Base class for all Wiseflow exceptions."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize a Wiseflow error.
        
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
    """Error raised when there is a configuration issue."""
    pass


class PluginError(WiseflowError):
    """Error raised when there is an issue with a plugin."""
    pass


class LLMError(WiseflowError):
    """Error raised when there is an issue with an LLM."""
    pass


class DatabaseError(WiseflowError):
    """Error raised when there is a database issue."""
    pass


def handle_exceptions(
    error_types: Optional[List[Type[Exception]]] = None,
    default_message: str = "An error occurred",
    log_error: bool = True,
    reraise: bool = False
) -> Callable:
    """
    Decorator for handling exceptions in a standardized way.
    
    Args:
        error_types: List of exception types to catch
        default_message: Default error message
        log_error: Whether to log the error
        reraise: Whether to reraise the exception
        
    Returns:
        Decorated function
    """
    if error_types is None:
        error_types = [Exception]
    
    def decorator(func: Callable) -> Callable:
        """Decorator function."""
        
        async def async_wrapper(*args, **kwargs) -> Any:
            """Wrapper for async functions."""
            try:
                return await func(*args, **kwargs)
            except tuple(error_types) as e:
                if log_error:
                    logger.error(f"Error in {func.__name__}: {str(e)}")
                    logger.error(traceback.format_exc())
                
                if isinstance(e, WiseflowError):
                    error = e
                else:
                    error = WiseflowError(
                        message=str(e) or default_message,
                        details={
                            "function": func.__name__,
                            "args": str(args),
                            "kwargs": str(kwargs),
                            "exception_type": e.__class__.__name__
                        }
                    )
                
                if reraise:
                    raise error
                
                # Return error information
                return {"error": error.to_dict()}
        
        def sync_wrapper(*args, **kwargs) -> Any:
            """Wrapper for synchronous functions."""
            try:
                return func(*args, **kwargs)
            except tuple(error_types) as e:
                if log_error:
                    logger.error(f"Error in {func.__name__}: {str(e)}")
                    logger.error(traceback.format_exc())
                
                if isinstance(e, WiseflowError):
                    error = e
                else:
                    error = WiseflowError(
                        message=str(e) or default_message,
                        details={
                            "function": func.__name__,
                            "args": str(args),
                            "kwargs": str(kwargs),
                            "exception_type": e.__class__.__name__
                        }
                    )
                
                if reraise:
                    raise error
                
                # Return error information
                return {"error": error.to_dict()}
        
        # Choose the appropriate wrapper based on whether the function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def log_error(
    error: Union[Exception, str],
    logger_instance: Optional[logging.Logger] = None,
    level: int = logging.ERROR,
    include_traceback: bool = True,
    additional_info: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an error with standardized formatting.
    
    Args:
        error: Error to log
        logger_instance: Logger instance to use
        level: Logging level
        include_traceback: Whether to include the traceback
        additional_info: Additional information to log
    """
    log = logger_instance or logger
    
    if isinstance(error, Exception):
        message = f"{error.__class__.__name__}: {str(error)}"
    else:
        message = str(error)
    
    log.log(level, message)
    
    if additional_info:
        log.log(level, f"Additional info: {json.dumps(additional_info, indent=2)}")
    
    if include_traceback:
        log.log(level, f"Traceback: {traceback.format_exc()}")


def save_error_to_file(
    error: Union[Exception, str],
    project_dir: str,
    prefix: str = "error",
    additional_info: Optional[Dict[str, Any]] = None
) -> str:
    """
    Save error information to a file.
    
    Args:
        error: Error to save
        project_dir: Directory to save the file in
        prefix: Prefix for the filename
        additional_info: Additional information to save
        
    Returns:
        Path to the saved file
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{prefix}_{timestamp}.json"
    filepath = os.path.join(project_dir, filename)
    
    error_data = {
        "timestamp": datetime.now().isoformat(),
        "error_type": error.__class__.__name__ if isinstance(error, Exception) else "string",
        "error_message": str(error),
        "traceback": traceback.format_exc()
    }
    
    if additional_info:
        error_data["additional_info"] = additional_info
    
    os.makedirs(project_dir, exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(error_data, f, ensure_ascii=False, indent=4)
    
    return filepath


# Import asyncio at the end to avoid circular imports
import asyncio

