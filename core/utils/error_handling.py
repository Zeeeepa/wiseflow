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


class ResourceError(WiseflowError):
    """Error raised when there is a resource issue."""
    pass


class PluginError(WiseflowError):
    """Error raised when there is a plugin issue."""
    pass


class LLMError(WiseflowError):
    """Error raised when there is an LLM issue."""
    pass


def handle_exceptions(func=None, *, error_type=WiseflowError, reraise=False, log_level=logging.ERROR):
    """
    Decorator to handle exceptions in a standardized way.
    
    Args:
        func: Function to decorate
        error_type: Type of error to raise
        reraise: Whether to reraise the exception
        log_level: Logging level for the error
        
    Returns:
        Decorated function
    """
    def decorator(f):
        def sync_wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                log_error(e, log_level=log_level)
                if reraise:
                    raise
                if isinstance(e, WiseflowError):
                    return None
                raise error_type(str(e), {"original_error": str(e), "traceback": traceback.format_exc()})
        
        async def async_wrapper(*args, **kwargs):
            try:
                return await f(*args, **kwargs)
            except Exception as e:
                log_error(e, log_level=log_level)
                if reraise:
                    raise
                if isinstance(e, WiseflowError):
                    return None
                raise error_type(str(e), {"original_error": str(e), "traceback": traceback.format_exc()})
        
        import inspect
        if inspect.iscoroutinefunction(f):
            return async_wrapper
        return sync_wrapper
    
    if func is None:
        return decorator
    return decorator(func)


def log_error(error: Exception, log_level=logging.ERROR, logger_instance=None):
    """
    Log an error with traceback.
    
    Args:
        error: Exception to log
        log_level: Logging level
        logger_instance: Logger instance to use
    """
    log = logger_instance or logger
    
    if isinstance(error, WiseflowError):
        error.log(log)
    else:
        log.log(log_level, f"Error: {error}")
        log.log(log_level, f"Traceback: {traceback.format_exc()}")


def save_error_to_file(error: Exception, filepath: Optional[str] = None) -> str:
    """
    Save an error to a file.
    
    Args:
        error: Exception to save
        filepath: Path to save the error to
        
    Returns:
        Path to the saved error file
    """
    if filepath is None:
        # Generate a default filepath
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = os.environ.get("PROJECT_DIR", "")
        if project_dir:
            error_dir = os.path.join(project_dir, "errors")
            os.makedirs(error_dir, exist_ok=True)
            filepath = os.path.join(error_dir, f"error_{timestamp}.json")
        else:
            filepath = f"error_{timestamp}.json"
    
    # Create the error data
    error_data = {
        "timestamp": datetime.now().isoformat(),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc()
    }
    
    # Add additional details for WiseflowError
    if isinstance(error, WiseflowError):
        error_data.update(error.to_dict())
    
    # Save to file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(error_data, f, indent=2)
        logger.info(f"Error saved to {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Failed to save error to file: {e}")
        return ""

