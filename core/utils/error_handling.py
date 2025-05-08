"""
Error handling utilities for WiseFlow.

This module provides error handling functions and classes for the WiseFlow system.
"""

import time
import json
import logging
import functools
import traceback
import jsonschema
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable, TypeVar, Union, Type

# Type variables for generic functions
T = TypeVar('T')
R = TypeVar('R')


class ErrorCode(Enum):
    """Error codes for WiseFlow errors."""
    
    UNKNOWN_ERROR = auto()
    VALIDATION_ERROR = auto()
    API_ERROR = auto()
    DATABASE_ERROR = auto()
    CONNECTOR_ERROR = auto()
    PLUGIN_ERROR = auto()
    AUTHENTICATION_ERROR = auto()
    AUTHORIZATION_ERROR = auto()
    RESOURCE_NOT_FOUND = auto()
    RESOURCE_ALREADY_EXISTS = auto()
    RATE_LIMIT_EXCEEDED = auto()
    TIMEOUT_ERROR = auto()
    NETWORK_ERROR = auto()
    PARSING_ERROR = auto()
    CONFIGURATION_ERROR = auto()
    LLM_ERROR = auto()
    TASK_ERROR = auto()
    SYSTEM_ERROR = auto()


class WiseflowError(Exception):
    """Base class for WiseFlow errors."""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR, 
                details: Optional[Dict[str, Any]] = None):
        """
        Initialize a WiseflowError.
        
        Args:
            message: Error message
            error_code: Error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self) -> str:
        """Return string representation of the error."""
        return self.message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the error to a dictionary."""
        return {
            "error": f"{self.__class__.__name__}: {self.message}",
            "error_code": self.error_code.name,
            "details": self.details
        }


class ValidationError(WiseflowError):
    """Error raised when input validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize a ValidationError.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, ErrorCode.VALIDATION_ERROR, details)


class APIError(WiseflowError):
    """Error raised when an API request fails."""
    
    def __init__(self, message: str, status_code: int = 500, 
                details: Optional[Dict[str, Any]] = None):
        """
        Initialize an APIError.
        
        Args:
            message: Error message
            status_code: HTTP status code
            details: Additional error details
        """
        super().__init__(message, ErrorCode.API_ERROR, details)
        self.status_code = status_code


class DatabaseError(WiseflowError):
    """Error raised when a database operation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize a DatabaseError.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, ErrorCode.DATABASE_ERROR, details)


class ConnectorError(WiseflowError):
    """Error raised when a connector operation fails."""
    
    def __init__(self, message: str, connector_name: str, 
                details: Optional[Dict[str, Any]] = None):
        """
        Initialize a ConnectorError.
        
        Args:
            message: Error message
            connector_name: Name of the connector
            details: Additional error details
        """
        details = details or {}
        details["connector_name"] = connector_name
        super().__init__(message, ErrorCode.CONNECTOR_ERROR, details)


class PluginError(WiseflowError):
    """Error raised when a plugin operation fails."""
    
    def __init__(self, message: str, plugin_name: str, 
                details: Optional[Dict[str, Any]] = None):
        """
        Initialize a PluginError.
        
        Args:
            message: Error message
            plugin_name: Name of the plugin
            details: Additional error details
        """
        details = details or {}
        details["plugin_name"] = plugin_name
        super().__init__(message, ErrorCode.PLUGIN_ERROR, details)


class LLMError(WiseflowError):
    """Error raised when an LLM operation fails."""
    
    def __init__(self, message: str, model_name: str, 
                details: Optional[Dict[str, Any]] = None):
        """
        Initialize an LLMError.
        
        Args:
            message: Error message
            model_name: Name of the LLM model
            details: Additional error details
        """
        details = details or {}
        details["model_name"] = model_name
        super().__init__(message, ErrorCode.LLM_ERROR, details)


class TaskError(WiseflowError):
    """Error raised when a task operation fails."""
    
    def __init__(self, message: str, task_id: str, 
                details: Optional[Dict[str, Any]] = None):
        """
        Initialize a TaskError.
        
        Args:
            message: Error message
            task_id: ID of the task
            details: Additional error details
        """
        details = details or {}
        details["task_id"] = task_id
        super().__init__(message, ErrorCode.TASK_ERROR, details)


def handle_exception(exception: Exception, logger: Optional[logging.Logger] = None) -> Dict[str, Any]:
    """
    Handle an exception and return a standardized error response.
    
    Args:
        exception: The exception to handle
        logger: Logger to use for logging the error
        
    Returns:
        Dict: Standardized error response
    """
    # Log the error
    log_error(exception, logger=logger)
    
    # Create the error response
    response = {
        "success": False,
        "error": f"{exception.__class__.__name__}: {str(exception)}"
    }
    
    # Add additional information for WiseflowError
    if isinstance(exception, WiseflowError):
        response["error_code"] = exception.error_code.name
        response["details"] = exception.details
    
    return response


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None, 
             logger: Optional[logging.Logger] = None) -> None:
    """
    Log an error with context information.
    
    Args:
        error: The error to log
        context: Additional context information
        logger: Logger to use for logging the error
    """
    # Get the logger
    if logger is None:
        logger = logging.getLogger("wiseflow")
    
    # Create the error message
    error_message = f"{error.__class__.__name__}: {str(error)}"
    
    # Add traceback information
    tb_str = traceback.format_exc()
    
    # Add context information
    context_str = ""
    if context:
        context_str = f"Context: {json.dumps(context)}"
    
    # Log the error
    logger.error(f"{error_message}\n{context_str}\n{tb_str}")


def retry(max_retries: int = 3, retry_delay: float = 1.0, 
         retry_exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception,
         logger: Optional[logging.Logger] = None) -> Callable[[Callable[..., R]], Callable[..., R]]:
    """
    Decorator to retry a function on failure.
    
    Args:
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds
        retry_exceptions: Exception types to retry on
        logger: Logger to use for logging retries
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: Callable[..., R]) -> Callable[..., R]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> R:
            # Get the logger
            nonlocal logger
            if logger is None:
                logger = logging.getLogger("wiseflow")
            
            # Initialize retry count
            retries = 0
            
            while True:
                try:
                    return func(*args, **kwargs)
                except retry_exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {str(e)}")
                        raise
                    
                    logger.warning(f"Retry {retries}/{max_retries} for {func.__name__} after error: {str(e)}")
                    time.sleep(retry_delay)
        
        return wrapper
    
    return decorator


def validate_input(data: Any, schema: Dict[str, Any]) -> bool:
    """
    Validate input data against a JSON schema.
    
    Args:
        data: The data to validate
        schema: The JSON schema to validate against
        
    Returns:
        bool: True if validation succeeds
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        jsonschema.validate(instance=data, schema=schema)
        return True
    except jsonschema.exceptions.ValidationError as e:
        raise ValidationError(
            message=f"Validation error: {str(e)}",
            details={"schema_path": list(e.path), "instance_path": list(e.path)}
        )


def safe_execute(func: Callable[..., T], *args: Any, **kwargs: Any) -> Union[T, Dict[str, Any]]:
    """
    Safely execute a function and handle any exceptions.
    
    Args:
        func: The function to execute
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Union[T, Dict[str, Any]]: Function result or error response
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        return handle_exception(e)


async def safe_execute_async(func: Callable[..., T], *args: Any, **kwargs: Any) -> Union[T, Dict[str, Any]]:
    """
    Safely execute an async function and handle any exceptions.
    
    Args:
        func: The async function to execute
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Union[T, Dict[str, Any]]: Function result or error response
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        return handle_exception(e)

