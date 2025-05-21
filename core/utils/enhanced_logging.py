#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enhanced logging utilities for WiseFlow.

This module extends the base logging system with additional features:
- Standardized logging patterns for common scenarios
- Performance monitoring for logging
- Log sampling for high-volume logs
- Structured logging enhancements
"""

import os
import sys
import json
import time
import random
import inspect
import threading
from pathlib import Path
from functools import wraps
from typing import Dict, Any, Optional, Union, List, Callable, TypeVar, cast

from loguru import logger

# Import config after logger to avoid circular imports
from core.config import config, PROJECT_DIR
from core.utils.logging_config import (
    logger, get_logger, with_context, LogContext, 
    configure_logging, LOG_LEVELS
)

# Type variable for function return type
T = TypeVar('T')

# Thread-local storage for request context
_request_context = threading.local()

def set_request_context(**kwargs) -> None:
    """
    Set context values for the current request/thread.
    
    Args:
        **kwargs: Context key-value pairs
    """
    if not hasattr(_request_context, 'context'):
        _request_context.context = {}
    
    _request_context.context.update(kwargs)

def get_request_context() -> Dict[str, Any]:
    """
    Get the current request context.
    
    Returns:
        Dictionary of context values
    """
    if not hasattr(_request_context, 'context'):
        _request_context.context = {}
    
    return _request_context.context

def clear_request_context() -> None:
    """Clear the current request context."""
    if hasattr(_request_context, 'context'):
        _request_context.context = {}

class RequestContext:
    """Context manager for request context."""
    
    def __init__(self, **kwargs):
        """
        Initialize with context key-value pairs.
        
        Args:
            **kwargs: Context key-value pairs
        """
        self.context = kwargs
        self.previous_context = {}
    
    def __enter__(self):
        """Set context when entering the block."""
        if not hasattr(_request_context, 'context'):
            _request_context.context = {}
        
        self.previous_context = _request_context.context.copy()
        _request_context.context.update(self.context)
        
        return _request_context.context
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore previous context when exiting the block."""
        _request_context.context = self.previous_context

def with_request_context() -> logger:
    """
    Create a logger with the current request context.
    
    Returns:
        Logger with request context
    """
    if not hasattr(_request_context, 'context'):
        _request_context.context = {}
    
    return logger.bind(**_request_context.context)

# Log sampling for high-volume logs
def sample_log(
    sample_rate: float = 0.1,
    min_level: str = "INFO"
) -> Callable:
    """
    Decorator for sampling logs to reduce volume.
    
    Args:
        sample_rate: Fraction of logs to keep (0.0 to 1.0)
        min_level: Minimum log level to apply sampling to
        
    Returns:
        Decorator function
    """
    min_level_no = LOG_LEVELS.get(min_level.upper(), 20)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, message, *args, **kwargs):
            # Get the level number
            level_name = func.__name__.upper()
            level_no = LOG_LEVELS.get(level_name, 0)
            
            # Only sample if level is at or above min_level
            if level_no >= min_level_no:
                # Determine if this log should be sampled
                if random.random() > sample_rate:
                    return None
            
            # Call the original logging function
            return func(self, message, *args, **kwargs)
        
        return wrapper
    
    return decorator

# Performance monitoring for logging
class LogPerformanceMonitor:
    """Monitor and report on logging performance."""
    
    def __init__(self, report_interval: int = 1000):
        """
        Initialize the performance monitor.
        
        Args:
            report_interval: Number of logs between performance reports
        """
        self.report_interval = report_interval
        self.log_count = 0
        self.total_time = 0.0
        self.max_time = 0.0
        self.lock = threading.Lock()
    
    def __call__(self, func: Callable) -> Callable:
        """
        Decorate a logging function to monitor performance.
        
        Args:
            func: Logging function to monitor
            
        Returns:
            Monitored function
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            
            with self.lock:
                self.log_count += 1
                self.total_time += elapsed
                self.max_time = max(self.max_time, elapsed)
                
                if self.log_count % self.report_interval == 0:
                    avg_time = self.total_time / self.log_count
                    
                    # Log performance metrics
                    logger.bind(
                        log_count=self.log_count,
                        avg_time_ms=avg_time * 1000,
                        max_time_ms=self.max_time * 1000
                    ).debug("Logging performance metrics")
                    
                    # Reset metrics
                    self.total_time = 0.0
                    self.max_time = 0.0
            
            return result
        
        return wrapper

# Standardized logging patterns
def log_function_call(
    log_args: bool = True,
    log_result: bool = True,
    log_level: str = "DEBUG",
    exclude_args: Optional[List[str]] = None,
    mask_args: Optional[Dict[str, str]] = None
) -> Callable:
    """
    Decorator for logging function calls.
    
    Args:
        log_args: Whether to log function arguments
        log_result: Whether to log function result
        log_level: Log level to use
        exclude_args: List of argument names to exclude from logging
        mask_args: Dictionary mapping argument names to mask values
        
    Returns:
        Decorator function
    """
    exclude_args = exclude_args or []
    mask_args = mask_args or {}
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Get function signature
        sig = inspect.signature(func)
        
        # Determine if function is async
        is_async = inspect.iscoroutinefunction(func)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Prepare context
            context = _prepare_log_context(func, args, kwargs, sig, exclude_args, mask_args)
            
            # Log function call
            log_func = getattr(with_context(**context), log_level.lower())
            log_func(f"Calling {func.__qualname__}")
            
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Log result if requested
                if log_result:
                    elapsed = time.time() - start_time
                    _log_result(func, result, elapsed, log_level, context)
                
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                
                # Log exception
                with_context(
                    **context,
                    elapsed_ms=elapsed * 1000,
                    error=str(e),
                    error_type=e.__class__.__name__
                ).error(f"Exception in {func.__qualname__}: {e}")
                
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Prepare context
            context = _prepare_log_context(func, args, kwargs, sig, exclude_args, mask_args)
            
            # Log function call
            log_func = getattr(with_context(**context), log_level.lower())
            log_func(f"Calling {func.__qualname__}")
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Log result if requested
                if log_result:
                    elapsed = time.time() - start_time
                    _log_result(func, result, elapsed, log_level, context)
                
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                
                # Log exception
                with_context(
                    **context,
                    elapsed_ms=elapsed * 1000,
                    error=str(e),
                    error_type=e.__class__.__name__
                ).error(f"Exception in {func.__qualname__}: {e}")
                
                raise
        
        # Return appropriate wrapper based on function type
        if is_async:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def _prepare_log_context(
    func: Callable,
    args: tuple,
    kwargs: dict,
    sig: inspect.Signature,
    exclude_args: List[str],
    mask_args: Dict[str, str]
) -> Dict[str, Any]:
    """
    Prepare context for logging function calls.
    
    Args:
        func: Function being called
        args: Positional arguments
        kwargs: Keyword arguments
        sig: Function signature
        exclude_args: Arguments to exclude from logging
        mask_args: Arguments to mask in logs
        
    Returns:
        Context dictionary
    """
    # Get request context
    context = get_request_context().copy()
    
    # Add function info
    context.update({
        "function": func.__qualname__,
        "module": func.__module__
    })
    
    # Add arguments if requested
    if args or kwargs:
        # Bind arguments to signature
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        # Filter and mask arguments
        arg_dict = {}
        for name, value in bound_args.arguments.items():
            if name in exclude_args:
                continue
            
            if name in mask_args:
                arg_dict[name] = mask_args[name]
            else:
                # Truncate large values
                str_value = str(value)
                if len(str_value) > 1000:
                    arg_dict[name] = f"{str_value[:1000]}... (truncated)"
                else:
                    arg_dict[name] = value
        
        context["args"] = arg_dict
    
    return context

def _log_result(
    func: Callable,
    result: Any,
    elapsed: float,
    log_level: str,
    context: Dict[str, Any]
) -> None:
    """
    Log function result.
    
    Args:
        func: Function that was called
        result: Function result
        elapsed: Elapsed time in seconds
        log_level: Log level to use
        context: Logging context
    """
    # Prepare result for logging
    if result is None:
        result_str = "None"
    else:
        # Truncate large results
        result_str = str(result)
        if len(result_str) > 1000:
            result_str = f"{result_str[:1000]}... (truncated)"
    
    # Log result
    log_func = getattr(
        with_context(**context, elapsed_ms=elapsed * 1000),
        log_level.lower()
    )
    log_func(f"{func.__qualname__} completed in {elapsed * 1000:.2f}ms with result: {result_str}")

# Structured logging for specific events
def log_api_request(
    method: str,
    url: str,
    status_code: Optional[int] = None,
    elapsed: Optional[float] = None,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    error: Optional[str] = None,
    request_data: Optional[Dict[str, Any]] = None,
    response_data: Optional[Dict[str, Any]] = None,
    log_level: str = "INFO"
) -> None:
    """
    Log an API request with standardized format.
    
    Args:
        method: HTTP method
        url: Request URL
        status_code: Response status code
        elapsed: Request duration in seconds
        request_id: Request ID
        user_id: User ID
        error: Error message if request failed
        request_data: Request data (will be sanitized)
        response_data: Response data (will be truncated if large)
        log_level: Log level to use
    """
    # Prepare context
    context = {
        "method": method,
        "url": url,
        "event_type": "api_request"
    }
    
    # Add optional fields
    if status_code is not None:
        context["status_code"] = status_code
    
    if elapsed is not None:
        context["elapsed_ms"] = elapsed * 1000
    
    if request_id is not None:
        context["request_id"] = request_id
    
    if user_id is not None:
        context["user_id"] = user_id
    
    if error is not None:
        context["error"] = error
    
    # Sanitize request data
    if request_data is not None:
        sanitized_data = _sanitize_data(request_data)
        context["request_data"] = sanitized_data
    
    # Truncate response data
    if response_data is not None:
        truncated_data = _truncate_data(response_data)
        context["response_data"] = truncated_data
    
    # Determine message based on status
    if error:
        message = f"API request failed: {method} {url}"
        if log_level == "INFO":
            log_level = "ERROR"
    else:
        message = f"API request: {method} {url}"
    
    # Log the request
    log_func = getattr(with_context(**context), log_level.lower())
    log_func(message)

def log_task_execution(
    task_id: str,
    task_type: str,
    status: str,
    elapsed: Optional[float] = None,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    log_level: str = "INFO"
) -> None:
    """
    Log a task execution with standardized format.
    
    Args:
        task_id: Task ID
        task_type: Task type
        status: Task status (started, completed, failed)
        elapsed: Task duration in seconds
        error: Error message if task failed
        metadata: Additional task metadata
        log_level: Log level to use
    """
    # Prepare context
    context = {
        "task_id": task_id,
        "task_type": task_type,
        "status": status,
        "event_type": "task_execution"
    }
    
    # Add optional fields
    if elapsed is not None:
        context["elapsed_ms"] = elapsed * 1000
    
    if error is not None:
        context["error"] = error
    
    if metadata is not None:
        context["metadata"] = metadata
    
    # Determine message and log level based on status
    if status == "started":
        message = f"Task {task_id} ({task_type}) started"
    elif status == "completed":
        message = f"Task {task_id} ({task_type}) completed"
        if elapsed is not None:
            message += f" in {elapsed * 1000:.2f}ms"
    elif status == "failed":
        message = f"Task {task_id} ({task_type}) failed: {error}"
        if log_level == "INFO":
            log_level = "ERROR"
    else:
        message = f"Task {task_id} ({task_type}) {status}"
    
    # Log the task
    log_func = getattr(with_context(**context), log_level.lower())
    log_func(message)

def log_data_processing(
    data_type: str,
    operation: str,
    count: int,
    status: str,
    elapsed: Optional[float] = None,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    log_level: str = "INFO"
) -> None:
    """
    Log a data processing operation with standardized format.
    
    Args:
        data_type: Type of data being processed
        operation: Operation being performed
        count: Number of items processed
        status: Operation status (started, completed, failed)
        elapsed: Operation duration in seconds
        error: Error message if operation failed
        metadata: Additional operation metadata
        log_level: Log level to use
    """
    # Prepare context
    context = {
        "data_type": data_type,
        "operation": operation,
        "count": count,
        "status": status,
        "event_type": "data_processing"
    }
    
    # Add optional fields
    if elapsed is not None:
        context["elapsed_ms"] = elapsed * 1000
    
    if error is not None:
        context["error"] = error
    
    if metadata is not None:
        context["metadata"] = metadata
    
    # Determine message and log level based on status
    if status == "started":
        message = f"Processing {count} {data_type} items with {operation}"
    elif status == "completed":
        message = f"Completed processing {count} {data_type} items with {operation}"
        if elapsed is not None:
            message += f" in {elapsed * 1000:.2f}ms"
    elif status == "failed":
        message = f"Failed processing {data_type} with {operation}: {error}"
        if log_level == "INFO":
            log_level = "ERROR"
    else:
        message = f"{status.capitalize()} processing {count} {data_type} items with {operation}"
    
    # Log the operation
    log_func = getattr(with_context(**context), log_level.lower())
    log_func(message)

# Helper functions
def _sanitize_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize sensitive data for logging.
    
    Args:
        data: Data to sanitize
        
    Returns:
        Sanitized data
    """
    # Define sensitive fields to mask
    sensitive_fields = [
        "password", "token", "secret", "key", "auth", "credential",
        "apikey", "api_key", "access_token", "refresh_token"
    ]
    
    # Create a copy of the data
    sanitized = {}
    
    # Sanitize each field
    for key, value in data.items():
        # Check if field is sensitive
        is_sensitive = any(
            sensitive in key.lower()
            for sensitive in sensitive_fields
        )
        
        if is_sensitive:
            sanitized[key] = "********"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_data(value)
        else:
            sanitized[key] = value
    
    return sanitized

def _truncate_data(data: Any, max_length: int = 1000) -> Any:
    """
    Truncate data for logging.
    
    Args:
        data: Data to truncate
        max_length: Maximum string length
        
    Returns:
        Truncated data
    """
    if isinstance(data, dict):
        return {k: _truncate_data(v, max_length) for k, v in data.items()}
    elif isinstance(data, list):
        if len(data) > 10:
            return [_truncate_data(item, max_length) for item in data[:10]] + ["... (truncated)"]
        return [_truncate_data(item, max_length) for item in data]
    elif isinstance(data, str):
        if len(data) > max_length:
            return data[:max_length] + "... (truncated)"
        return data
    else:
        return data

