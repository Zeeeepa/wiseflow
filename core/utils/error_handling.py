"""
Error handling utilities for WiseFlow.

This module provides standardized error handling mechanisms for the WiseFlow system.
"""

import traceback
import sys
import os
import json
import asyncio
import inspect
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Type, Union, List, TypeVar, cast

from core.config import PROJECT_DIR
from core.utils.logging_config import logger, with_context

# Type variable for function return type
T = TypeVar('T')

class WiseflowError(Exception):
    """Base class for all WiseFlow exceptions."""
    
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a WiseFlow error.
        
        Args:
            message: Error message
            details: Additional error details
            cause: Original exception that caused this error
        """
        self.message = message
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.now().isoformat()
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the error to a dictionary.
        
        Returns:
            Dictionary representation of the error
        """
        error_dict = {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "timestamp": self.timestamp,
            "details": self.details
        }
        
        if self.cause:
            error_dict["cause"] = {
                "error_type": self.cause.__class__.__name__,
                "message": str(self.cause)
            }
            
        return error_dict
    
    def log(self, log_level: str = "error") -> None:
        """
        Log the error with structured context.
        
        Args:
            log_level: Log level to use (default: error)
        """
        error_dict = self.to_dict()
        
        # Create a logger with error context
        log_func = getattr(with_context(**error_dict), log_level)
        
        # Log the error
        log_func(f"{self.__class__.__name__}: {self.message}")
        
        # Log traceback for debugging
        if log_level in ["error", "critical"]:
            with_context(**error_dict).debug(f"Traceback:\n{traceback.format_exc()}")

# System Errors

class SystemError(WiseflowError):
    """Base class for system-level errors."""
    pass

class ConfigurationError(SystemError):
    """Error raised when there is a configuration error."""
    pass

class StartupError(SystemError):
    """Error raised during system startup."""
    pass

class ShutdownError(SystemError):
    """Error raised during system shutdown."""
    pass

class ResourceError(SystemError):
    """Error raised when there is a resource error."""
    pass

class MemoryError(ResourceError):
    """Error raised when there is insufficient memory."""
    pass

class DiskSpaceError(ResourceError):
    """Error raised when there is insufficient disk space."""
    pass

class CPUError(ResourceError):
    """Error raised when there is a CPU-related error."""
    pass

# Network Errors

class NetworkError(WiseflowError):
    """Base class for network-related errors."""
    pass

class ConnectionError(NetworkError):
    """Error raised when a connection fails."""
    pass

class TimeoutError(NetworkError):
    """Error raised when a network operation times out."""
    pass

class APIError(NetworkError):
    """Error raised when an API call fails."""
    pass

class DNSError(NetworkError):
    """Error raised when DNS resolution fails."""
    pass

# Data Errors

class DataError(WiseflowError):
    """Base class for data-related errors."""
    pass

class DataProcessingError(DataError):
    """Error raised when data processing fails."""
    pass

class DataValidationError(DataError):
    """Error raised when data validation fails."""
    pass

class DataCorruptionError(DataError):
    """Error raised when data is corrupted."""
    pass

class DataNotFoundError(DataError):
    """Error raised when data is not found."""
    pass

class DataConversionError(DataError):
    """Error raised when data conversion fails."""
    pass

# Task Errors

class TaskError(WiseflowError):
    """Base class for task-related errors."""
    pass

class TaskExecutionError(TaskError):
    """Error raised when task execution fails."""
    pass

class TaskTimeoutError(TaskError):
    """Error raised when a task times out."""
    pass

class TaskCancellationError(TaskError):
    """Error raised when a task is cancelled."""
    pass

class TaskDependencyError(TaskError):
    """Error raised when a task dependency fails."""
    pass

class TaskNotFoundError(TaskError):
    """Error raised when a task is not found."""
    pass

# Plugin Errors

class PluginError(WiseflowError):
    """Base class for plugin-related errors."""
    pass

class PluginLoadError(PluginError):
    """Error raised when a plugin fails to load."""
    pass

class PluginExecutionError(PluginError):
    """Error raised when a plugin execution fails."""
    pass

class PluginNotFoundError(PluginError):
    """Error raised when a plugin is not found."""
    pass

class PluginConfigurationError(PluginError):
    """Error raised when a plugin configuration is invalid."""
    pass

# Authentication and Authorization Errors

class SecurityError(WiseflowError):
    """Base class for security-related errors."""
    pass

class AuthenticationError(SecurityError):
    """Error raised when authentication fails."""
    pass

class AuthorizationError(SecurityError):
    """Error raised when authorization fails."""
    pass

class TokenError(SecurityError):
    """Error raised when there is a token-related error."""
    pass

class PermissionError(SecurityError):
    """Error raised when a permission check fails."""
    pass

# Resource Errors

class NotFoundError(WiseflowError):
    """Error raised when a resource is not found."""
    pass

class AlreadyExistsError(WiseflowError):
    """Error raised when a resource already exists."""
    pass

class ValidationError(WiseflowError):
    """Error raised when validation fails."""
    pass

# Parallel Processing Errors

class ParallelError(WiseflowError):
    """Base class for parallel processing errors."""
    pass

class ParallelExecutionError(ParallelError):
    """Error raised when parallel execution fails."""
    pass

class ParallelTimeoutError(ParallelError):
    """Error raised when parallel execution times out."""
    pass

class ParallelResourceError(ParallelError):
    """Error raised when parallel execution runs out of resources."""
    pass

class ParallelCancellationError(ParallelError):
    """Error raised when parallel execution is cancelled."""
    pass

# Recovery-related errors

class RecoveryError(WiseflowError):
    """Base class for recovery-related errors."""
    pass

class RecoveryTimeoutError(RecoveryError):
    """Error raised when recovery times out."""
    pass

class RecoveryFailedError(RecoveryError):
    """Error raised when recovery fails."""
    pass

class MaxRetriesExceededError(RecoveryError):
    """Error raised when maximum retries are exceeded."""
    pass

# External Service Errors

class ExternalServiceError(WiseflowError):
    """Base class for external service errors."""
    pass

class DatabaseError(ExternalServiceError):
    """Error raised when a database operation fails."""
    pass

class CacheError(ExternalServiceError):
    """Error raised when a cache operation fails."""
    pass

class QueueError(ExternalServiceError):
    """Error raised when a queue operation fails."""
    pass

class StorageError(ExternalServiceError):
    """Error raised when a storage operation fails."""
    pass

def handle_exceptions(
    error_types: Optional[List[Type[Exception]]] = None,
    default_message: str = "An error occurred",
    log_error: bool = True,
    reraise: bool = False,
    save_to_file: bool = False,
    default_return: Any = None,
    error_transformer: Optional[Callable[[Exception], Exception]] = None
) -> Callable:
    """
    Decorator for handling exceptions.
    
    Args:
        error_types: List of exception types to catch
        default_message: Default error message
        log_error: Whether to log the error
        reraise: Whether to re-raise the exception
        save_to_file: Whether to save the error to a file
        default_return: Default return value if an exception occurs
        error_transformer: Function to transform the caught exception
        
    Returns:
        Decorator function
    """
    if error_types is None:
        error_types = [Exception]
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Get function signature for better error context
        func_signature = inspect.signature(func)
        func_name = func.__qualname__
        module_name = func.__module__
        
        # Determine if function is async
        is_async = asyncio.iscoroutinefunction(func)
        
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await func(*args, **kwargs)
            except tuple(error_types) as e:
                return _handle_error(e, args, kwargs)
        
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except tuple(error_types) as e:
                return _handle_error(e, args, kwargs)
        
        def _handle_error(e: Exception, args: Any, kwargs: Any) -> T:
            # Create error context
            error_context = {
                "function": func_name,
                "module": module_name,
                "args": str(args),
                "kwargs": str(kwargs)
            }
            
            # Get error message
            error_message = str(e) or default_message
            
            # Transform error if needed
            if error_transformer is not None:
                e = error_transformer(e)
            
            # Log the error
            if log_error:
                if isinstance(e, WiseflowError):
                    e.log()
                else:
                    with_context(**error_context).error(f"Error in {func_name}: {error_message}")
                    with_context(**error_context).debug(f"Traceback:\n{traceback.format_exc()}")
            
            # Save error to file if requested
            if save_to_file:
                save_error_to_file(func_name, error_message, traceback.format_exc())
            
            # Re-raise the exception if requested
            if reraise:
                raise
            
            # Return default value based on function's return annotation or provided default
            if default_return is not None:
                return cast(T, default_return)
            
            # Try to determine appropriate default return value
            return_annotation = func_signature.return_annotation
            
            if return_annotation is inspect.Signature.empty:
                return cast(T, None)
            elif return_annotation is type(None):
                return cast(T, None)
            elif return_annotation is bool:
                return cast(T, False)
            elif return_annotation is int:
                return cast(T, 0)
            elif return_annotation is str:
                return cast(T, "")
            elif return_annotation is list or getattr(return_annotation, "__origin__", None) is list:
                return cast(T, [])
            elif return_annotation is dict or getattr(return_annotation, "__origin__", None) is dict:
                return cast(T, {})
            else:
                return cast(T, None)
        
        # Return appropriate wrapper based on function type
        if is_async:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_error(
    error: Exception, 
    log_level: str = "error",
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an error with context.
    
    Args:
        error: Exception to log
        log_level: Log level to use
        context: Additional context to include in the log
    """
    ctx = context or {}
    
    if isinstance(error, WiseflowError):
        # Use the error's built-in logging with context
        error_with_context = type(error)(
            error.message,
            {**error.details, **ctx},
            error.cause
        )
        error_with_context.log(log_level)
    else:
        # Log the error with context
        log_func = getattr(with_context(**ctx), log_level)
        log_func(f"{type(error).__name__}: {str(error)}")
        
        # Log traceback for debugging
        if log_level in ["error", "critical"]:
            with_context(**ctx).debug(f"Traceback:\n{traceback.format_exc()}")


def save_error_to_file(
    function_name: str,
    error_message: str,
    traceback_str: str,
    directory: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Save an error to a file.
    
    Args:
        function_name: Name of the function where the error occurred
        error_message: Error message
        traceback_str: Traceback string
        directory: Directory to save the file to
        context: Additional context to include in the error file
        
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
        
        if context:
            f.write("\nContext:\n")
            f.write(json.dumps(context, indent=2))
        
        f.write("\nTraceback:\n")
        f.write(traceback_str)
    
    logger.info(f"Error saved to {filepath}")
    return filepath


class ErrorHandler:
    """
    Context manager for handling exceptions.
    
    Example:
        with ErrorHandler(default="default value") as handler:
            result = risky_operation()
            return result
        
        if handler.error_occurred:
            # Handle error
            print(f"Error: {handler.error}")
        
        return handler.result
    """
    
    def __init__(
        self,
        error_types: Optional[List[Type[Exception]]] = None,
        default: Any = None,
        log_error: bool = True,
        save_to_file: bool = False,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the error handler.
        
        Args:
            error_types: List of exception types to catch
            default: Default value to return if an exception occurs
            log_error: Whether to log the error
            save_to_file: Whether to save the error to a file
            context: Additional context to include in the error log
        """
        self.error_types = error_types or [Exception]
        self.default = default
        self.log_error = log_error
        self.save_to_file = save_to_file
        self.context = context or {}
        
        self.error = None
        self.error_occurred = False
        self.result = default
    
    def __enter__(self):
        """Enter the context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context manager.
        
        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
            
        Returns:
            True if the exception was handled, False otherwise
        """
        if exc_type is None:
            return False
        
        # Check if the exception is one we want to catch
        if not any(issubclass(exc_type, error_type) for error_type in self.error_types):
            return False
        
        # Store the error
        self.error = exc_val
        self.error_occurred = True
        
        # Get the calling function name for context
        frame = sys._getframe(1)
        func_name = frame.f_code.co_name
        module_name = frame.f_globals.get('__name__', 'unknown')
        
        # Add function context
        error_context = {
            **self.context,
            "function": func_name,
            "module": module_name
        }
        
        # Log the error
        if self.log_error:
            log_error(exc_val, context=error_context)
        
        # Save the error to a file
        if self.save_to_file:
            save_error_to_file(
                func_name,
                str(exc_val),
                traceback.format_exc(),
                context=error_context
            )
        
        # Return the default value
        self.result = self.default
        
        # Indicate that we've handled the exception
        return True


async def async_error_handler(
    coro,
    error_types: Optional[List[Type[Exception]]] = None,
    default: Any = None,
    log_error: bool = True,
    save_to_file: bool = False,
    context: Optional[Dict[str, Any]] = None
):
    """
    Async utility function for handling exceptions in async code.
    
    Args:
        coro: Coroutine to execute
        error_types: List of exception types to catch
        default: Default value to return if an exception occurs
        log_error: Whether to log the error
        save_to_file: Whether to save the error to a file
        context: Additional context to include in the error log
        
    Returns:
        Result of the coroutine or default value if an exception occurs
    """
    error_types = error_types or [Exception]
    context = context or {}
    
    try:
        return await coro
    except tuple(error_types) as e:
        # Get the calling function name for context
        frame = sys._getframe(1)
        func_name = frame.f_code.co_name
        module_name = frame.f_globals.get('__name__', 'unknown')
        
        # Add function context
        error_context = {
            **context,
            "function": func_name,
            "module": module_name
        }
        
        # Log the error
        if log_error:
            log_error(e, context=error_context)
        
        # Save the error to a file
        if save_to_file:
            save_error_to_file(
                func_name,
                str(e),
                traceback.format_exc(),
                context=error_context
            )
        
        # Return the default value
        return default
