#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Decorators for Wiseflow.

This module provides decorators for common functionality such as input validation,
error handling, logging, and performance monitoring.
"""

import time
import logging
import functools
import traceback
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, get_type_hints

from core.validation import ValidationResult, validate_type, validate_schema

# Set up logging
logger = logging.getLogger(__name__)

# Type variable for function return type
T = TypeVar('T')


def validate_input(
    *,
    arg_types: Optional[Dict[str, Type]] = None,
    schema: Optional[Dict[str, Dict[str, Any]]] = None,
    allow_extra_fields: bool = False
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for validating function inputs.
    
    Args:
        arg_types: Dictionary mapping argument names to expected types
        schema: Schema for validating dictionary arguments
        allow_extra_fields: Whether to allow extra fields in dictionary arguments
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Get type hints from function signature if arg_types not provided
        if arg_types is None:
            hints = get_type_hints(func)
        else:
            hints = arg_types
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get function argument names
            func_args = func.__code__.co_varnames[:func.__code__.co_argcount]
            
            # Combine positional and keyword arguments
            all_args = {}
            for i, arg in enumerate(args):
                if i < len(func_args):
                    all_args[func_args[i]] = arg
            all_args.update(kwargs)
            
            # Validate argument types
            for arg_name, arg_value in all_args.items():
                # Skip 'self' or 'cls' arguments
                if arg_name in ('self', 'cls'):
                    continue
                
                # Check if type hint exists for this argument
                if arg_name in hints:
                    expected_type = hints[arg_name]
                    result = validate_type(arg_value, expected_type)
                    if not result.is_valid:
                        error_msg = f"Invalid type for argument '{arg_name}': {', '.join(result.errors)}"
                        logger.error(error_msg)
                        raise TypeError(error_msg)
            
            # Validate schema for dictionary arguments
            if schema is not None:
                for arg_name, arg_value in all_args.items():
                    # Skip 'self' or 'cls' arguments
                    if arg_name in ('self', 'cls'):
                        continue
                    
                    # Check if argument is a dictionary
                    if isinstance(arg_value, dict):
                        from core.validation import validate_schema
                        result = validate_schema(arg_value, schema, allow_extra_fields)
                        if not result.is_valid:
                            error_msg = f"Invalid schema for argument '{arg_name}': {', '.join(result.errors)}"
                            logger.error(error_msg)
                            raise ValueError(error_msg)
            
            # Call the function if validation passes
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def validate_output(
    expected_type: Optional[Type] = None,
    schema: Optional[Dict[str, Dict[str, Any]]] = None,
    allow_extra_fields: bool = False
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for validating function outputs.
    
    Args:
        expected_type: Expected return type
        schema: Schema for validating dictionary return values
        allow_extra_fields: Whether to allow extra fields in dictionary return values
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Call the function
            result = func(*args, **kwargs)
            
            # Validate return type
            if expected_type is not None:
                type_result = validate_type(result, expected_type)
                if not type_result.is_valid:
                    error_msg = f"Invalid return type: {', '.join(type_result.errors)}"
                    logger.error(error_msg)
                    raise TypeError(error_msg)
            
            # Validate schema for dictionary return values
            if schema is not None and isinstance(result, dict):
                from core.validation import validate_schema
                schema_result = validate_schema(result, schema, allow_extra_fields)
                if not schema_result.is_valid:
                    error_msg = f"Invalid return schema: {', '.join(schema_result.errors)}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            
            return result
        
        return wrapper
    
    return decorator


def handle_exceptions(
    *exception_types: Type[Exception],
    reraise: bool = False,
    default_return: Any = None,
    log_level: int = logging.ERROR
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for handling exceptions.
    
    Args:
        *exception_types: Exception types to catch
        reraise: Whether to reraise the exception after handling
        default_return: Default return value if an exception is caught
        log_level: Logging level for exceptions
        
    Returns:
        Decorated function
    """
    # Default to catching all exceptions if none specified
    if not exception_types:
        exception_types = (Exception,)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception_types as e:
                # Log the exception
                logger.log(log_level, f"Exception in {func.__name__}: {str(e)}")
                logger.log(log_level, traceback.format_exc())
                
                # Reraise or return default value
                if reraise:
                    raise
                return default_return
        
        return wrapper
    
    return decorator


def log_execution(
    log_args: bool = True,
    log_result: bool = True,
    log_level: int = logging.INFO
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for logging function execution.
    
    Args:
        log_args: Whether to log function arguments
        log_result: Whether to log function result
        log_level: Logging level
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Log function call
            if log_args:
                # Format args and kwargs for logging
                args_str = ", ".join([str(arg) for arg in args])
                kwargs_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
                all_args = ", ".join(filter(None, [args_str, kwargs_str]))
                logger.log(log_level, f"Calling {func.__name__}({all_args})")
            else:
                logger.log(log_level, f"Calling {func.__name__}")
            
            # Call the function
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            
            # Log execution time
            execution_time = end_time - start_time
            logger.log(log_level, f"{func.__name__} executed in {execution_time:.4f} seconds")
            
            # Log result
            if log_result:
                logger.log(log_level, f"{func.__name__} returned: {result}")
            
            return result
        
        return wrapper
    
    return decorator


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retrying a function on failure.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts (in seconds)
        backoff_factor: Factor by which the delay increases with each attempt
        exceptions: Exception types to catch and retry
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            current_delay = delay
            
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        logger.error(f"Failed after {attempts} attempts: {str(e)}")
                        raise
                    
                    logger.warning(f"Attempt {attempts} failed: {str(e)}. Retrying in {current_delay:.2f} seconds...")
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
            # This should never be reached, but just in case
            raise RuntimeError(f"Failed after {max_attempts} attempts")
        
        return wrapper
    
    return decorator


def memoize(
    maxsize: Optional[int] = None,
    ttl: Optional[float] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for memoizing function results.
    
    Args:
        maxsize: Maximum cache size (None for unlimited)
        ttl: Time-to-live for cache entries (in seconds, None for no expiration)
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache = {}
        timestamps = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from the function arguments
            key = str(args) + str(sorted(kwargs.items()))
            
            # Check if result is in cache and not expired
            if key in cache:
                if ttl is None or time.time() - timestamps[key] < ttl:
                    return cache[key]
                else:
                    # Remove expired entry
                    del cache[key]
                    del timestamps[key]
            
            # Call the function and cache the result
            result = func(*args, **kwargs)
            cache[key] = result
            timestamps[key] = time.time()
            
            # Limit cache size if maxsize is specified
            if maxsize is not None and len(cache) > maxsize:
                # Remove oldest entry
                oldest_key = min(timestamps, key=timestamps.get)
                del cache[oldest_key]
                del timestamps[oldest_key]
            
            return result
        
        # Add clear_cache method to the wrapper
        def clear_cache():
            cache.clear()
            timestamps.clear()
        
        wrapper.clear_cache = clear_cache
        
        return wrapper
    
    return decorator


def deprecated(
    message: Optional[str] = None,
    alternative: Optional[str] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for marking functions as deprecated.
    
    Args:
        message: Custom deprecation message
        alternative: Alternative function to use
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Create deprecation message
        if message is None:
            if alternative is None:
                warn_msg = f"Function {func.__name__} is deprecated"
            else:
                warn_msg = f"Function {func.__name__} is deprecated, use {alternative} instead"
        else:
            warn_msg = message
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Log deprecation warning
            logger.warning(warn_msg)
            
            # Call the function
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator

