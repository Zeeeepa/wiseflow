"""
Error handling utilities for Wiseflow.

This module provides utilities for handling errors, retries, and recovery
in data processing and connector operations.
"""

import asyncio
import logging
import time
import functools
import traceback
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable, TypeVar, Generic, Type

logger = logging.getLogger(__name__)

T = TypeVar('T')
F = TypeVar('F', bound=Callable)


def retry(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception,
    logger_name: Optional[str] = None
):
    """
    Decorator for retrying functions on failure.
    
    Args:
        max_retries: Maximum number of retries
        retry_delay: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        exceptions: Exception types to catch and retry on
        logger_name: Optional logger name to use
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            local_logger = logging.getLogger(logger_name or func.__module__)
            
            attempt = 0
            while attempt < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= max_retries:
                        local_logger.error(
                            f"Function {func.__name__} failed after {max_retries} attempts: {e}"
                        )
                        raise
                    
                    delay = retry_delay * (backoff_factor ** (attempt - 1))
                    local_logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt}/{max_retries}): {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    time.sleep(delay)
        
        return wrapper  # type: ignore
    
    return decorator


async def async_retry(
    coro: Callable[..., Awaitable[T]],
    *args,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception,
    logger_name: Optional[str] = None,
    **kwargs
) -> T:
    """
    Retry an async coroutine on failure.
    
    Args:
        coro: Coroutine function to retry
        *args: Arguments to pass to the coroutine
        max_retries: Maximum number of retries
        retry_delay: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        exceptions: Exception types to catch and retry on
        logger_name: Optional logger name to use
        **kwargs: Keyword arguments to pass to the coroutine
        
    Returns:
        T: Result of the coroutine
        
    Raises:
        Exception: If all retries fail
    """
    local_logger = logging.getLogger(logger_name or coro.__module__)
    
    attempt = 0
    while attempt < max_retries:
        try:
            return await coro(*args, **kwargs)
        except exceptions as e:
            attempt += 1
            if attempt >= max_retries:
                local_logger.error(
                    f"Function {coro.__name__} failed after {max_retries} attempts: {e}"
                )
                raise
            
            delay = retry_delay * (backoff_factor ** (attempt - 1))
            local_logger.warning(
                f"Function {coro.__name__} failed (attempt {attempt}/{max_retries}): {e}. "
                f"Retrying in {delay:.2f} seconds..."
            )
            await asyncio.sleep(delay)
    
    # This should never be reached, but just in case
    raise RuntimeError(f"Unexpected error in async_retry for {coro.__name__}")


def async_retry_decorator(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception,
    logger_name: Optional[str] = None
):
    """
    Decorator for retrying async functions on failure.
    
    Args:
        max_retries: Maximum number of retries
        retry_delay: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        exceptions: Exception types to catch and retry on
        logger_name: Optional logger name to use
        
    Returns:
        Callable: Decorated function
    """
    def decorator(coro: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(coro)
        async def wrapper(*args, **kwargs) -> T:
            return await async_retry(
                coro,
                *args,
                max_retries=max_retries,
                retry_delay=retry_delay,
                backoff_factor=backoff_factor,
                exceptions=exceptions,
                logger_name=logger_name,
                **kwargs
            )
        
        return wrapper
    
    return decorator


class ErrorHandler:
    """
    Error handler for capturing and processing errors.
    
    This class provides utilities for capturing, logging, and recovering from errors.
    """
    
    def __init__(self, logger_name: Optional[str] = None):
        """
        Initialize the error handler.
        
        Args:
            logger_name: Optional logger name to use
        """
        self.logger = logging.getLogger(logger_name or __name__)
        self.errors: List[Dict[str, Any]] = []
        self.max_errors = 100  # Maximum number of errors to store
    
    def capture(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        log_level: int = logging.ERROR
    ) -> Dict[str, Any]:
        """
        Capture and log an error.
        
        Args:
            error: Exception to capture
            context: Optional context information
            log_level: Logging level to use
            
        Returns:
            Dict[str, Any]: Error information
        """
        error_info = {
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": time.time(),
            "context": context or {},
            "traceback": traceback.format_exc()
        }
        
        # Log the error
        self.logger.log(
            log_level,
            f"Error: {error_info['error_type']}: {error_info['error']}",
            exc_info=True
        )
        
        # Store the error
        self.errors.append(error_info)
        
        # Trim the error list if needed
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
        
        return error_info
    
    def get_errors(
        self,
        error_type: Optional[Type[Exception]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get captured errors.
        
        Args:
            error_type: Optional error type to filter by
            limit: Optional limit on the number of errors to return
            
        Returns:
            List[Dict[str, Any]]: List of error information
        """
        if error_type is None:
            errors = self.errors
        else:
            errors = [e for e in self.errors if e["error_type"] == error_type.__name__]
        
        if limit is not None:
            errors = errors[-limit:]
        
        return errors
    
    def clear_errors(self) -> None:
        """Clear all captured errors."""
        self.errors = []
    
    def has_errors(self) -> bool:
        """
        Check if any errors have been captured.
        
        Returns:
            bool: True if errors have been captured, False otherwise
        """
        return len(self.errors) > 0
    
    def get_error_count(self) -> int:
        """
        Get the number of captured errors.
        
        Returns:
            int: Number of captured errors
        """
        return len(self.errors)


# Create a global error handler instance
error_handler = ErrorHandler()


def safe_execute(
    func: Callable[..., T],
    *args,
    default_value: Optional[T] = None,
    log_error: bool = True,
    error_handler: Optional[ErrorHandler] = None,
    **kwargs
) -> T:
    """
    Safely execute a function, catching any exceptions.
    
    Args:
        func: Function to execute
        *args: Arguments to pass to the function
        default_value: Default value to return if an exception occurs
        log_error: Whether to log the error
        error_handler: Optional error handler to use
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        T: Result of the function or default value if an exception occurs
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger.error(f"Error executing {func.__name__}: {e}", exc_info=True)
        
        if error_handler is not None:
            error_handler.capture(
                e,
                context={
                    "function": func.__name__,
                    "args": args,
                    "kwargs": kwargs
                }
            )
        
        return default_value  # type: ignore


async def safe_execute_async(
    coro: Callable[..., Awaitable[T]],
    *args,
    default_value: Optional[T] = None,
    log_error: bool = True,
    error_handler: Optional[ErrorHandler] = None,
    **kwargs
) -> T:
    """
    Safely execute an async coroutine, catching any exceptions.
    
    Args:
        coro: Coroutine function to execute
        *args: Arguments to pass to the coroutine
        default_value: Default value to return if an exception occurs
        log_error: Whether to log the error
        error_handler: Optional error handler to use
        **kwargs: Keyword arguments to pass to the coroutine
        
    Returns:
        T: Result of the coroutine or default value if an exception occurs
    """
    try:
        return await coro(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger.error(f"Error executing {coro.__name__}: {e}", exc_info=True)
        
        if error_handler is not None:
            error_handler.capture(
                e,
                context={
                    "function": coro.__name__,
                    "args": args,
                    "kwargs": kwargs
                }
            )
        
        return default_value  # type: ignore


def handle_exceptions(
    error_types: Union[Type[Exception], List[Type[Exception]]] = Exception,
    default_message: str = "An error occurred",
    log_error: bool = True,
    reraise: bool = True
):
    """
    Decorator for handling exceptions.
    
    Args:
        error_types: Exception types to catch
        default_message: Default error message
        log_error: Whether to log the error
        reraise: Whether to reraise the exception
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except error_types as e:
                if log_error:
                    logger.error(
                        f"{default_message}: {e} in {func.__name__}",
                        exc_info=True
                    )
                
                if reraise:
                    raise
                
                return None
        
        return wrapper  # type: ignore
    
    return decorator


def async_handle_exceptions(
    error_types: Union[Type[Exception], List[Type[Exception]]] = Exception,
    default_message: str = "An error occurred",
    log_error: bool = True,
    reraise: bool = True
):
    """
    Decorator for handling exceptions in async functions.
    
    Args:
        error_types: Exception types to catch
        default_message: Default error message
        log_error: Whether to log the error
        reraise: Whether to reraise the exception
        
    Returns:
        Callable: Decorated function
    """
    def decorator(coro: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(coro)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await coro(*args, **kwargs)
            except error_types as e:
                if log_error:
                    logger.error(
                        f"{default_message}: {e} in {coro.__name__}",
                        exc_info=True
                    )
                
                if reraise:
                    raise
                
                return None  # type: ignore
        
        return wrapper
    
    return decorator

