#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Retry utilities for WiseFlow.

This module provides utilities for retrying operations that may fail with transient errors.
"""

import time
import random
import functools
import asyncio
from typing import Dict, Any, Optional, Callable, Type, Union, List, TypeVar, cast

from core.utils.logging_config import logger, with_context
from core.utils.exceptions import TransientError, ConnectionError, TimeoutError, RateLimitError, ServiceUnavailableError

# Type variable for function return type
T = TypeVar('T')

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retry_on: Optional[List[Type[Exception]]] = None,
    max_delay: Optional[float] = None,
    log_retries: bool = True
) -> Callable:
    """
    Decorator for retrying functions that may fail with transient errors.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts in seconds
        backoff_factor: Factor to increase delay by after each attempt
        jitter: Whether to add random jitter to delay
        retry_on: List of exception types to retry on (defaults to TransientError)
        max_delay: Maximum delay between attempts in seconds
        log_retries: Whether to log retry attempts
        
    Returns:
        Decorator function
    """
    if retry_on is None:
        retry_on = [TransientError, ConnectionError, TimeoutError, RateLimitError, ServiceUnavailableError]
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Determine if function is async
        is_async = asyncio.iscoroutinefunction(func)
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            attempt = 1
            
            while attempt <= max_attempts:
                try:
                    return await func(*args, **kwargs)
                except tuple(retry_on) as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        break
                    
                    # Calculate delay with exponential backoff
                    current_delay = delay * (backoff_factor ** (attempt - 1))
                    
                    # Apply maximum delay if specified
                    if max_delay is not None:
                        current_delay = min(current_delay, max_delay)
                    
                    # Add jitter if requested
                    if jitter:
                        current_delay = current_delay * (0.5 + random.random())
                    
                    # Log retry attempt
                    if log_retries:
                        with_context(
                            attempt=attempt,
                            max_attempts=max_attempts,
                            delay=current_delay,
                            error=str(e),
                            error_type=e.__class__.__name__
                        ).warning(f"Retrying {func.__qualname__} after error: {e}")
                    
                    # Wait before retrying
                    await asyncio.sleep(current_delay)
                    
                    attempt += 1
            
            # If we get here, all retries failed
            if last_exception:
                if log_retries:
                    with_context(
                        max_attempts=max_attempts,
                        error=str(last_exception),
                        error_type=last_exception.__class__.__name__
                    ).error(f"All {max_attempts} retry attempts failed for {func.__qualname__}")
                
                raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            attempt = 1
            
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except tuple(retry_on) as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        break
                    
                    # Calculate delay with exponential backoff
                    current_delay = delay * (backoff_factor ** (attempt - 1))
                    
                    # Apply maximum delay if specified
                    if max_delay is not None:
                        current_delay = min(current_delay, max_delay)
                    
                    # Add jitter if requested
                    if jitter:
                        current_delay = current_delay * (0.5 + random.random())
                    
                    # Log retry attempt
                    if log_retries:
                        with_context(
                            attempt=attempt,
                            max_attempts=max_attempts,
                            delay=current_delay,
                            error=str(e),
                            error_type=e.__class__.__name__
                        ).warning(f"Retrying {func.__qualname__} after error: {e}")
                    
                    # Wait before retrying
                    time.sleep(current_delay)
                    
                    attempt += 1
            
            # If we get here, all retries failed
            if last_exception:
                if log_retries:
                    with_context(
                        max_attempts=max_attempts,
                        error=str(last_exception),
                        error_type=last_exception.__class__.__name__
                    ).error(f"All {max_attempts} retry attempts failed for {func.__qualname__}")
                
                raise last_exception
        
        # Return appropriate wrapper based on function type
        if is_async:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

class RetryContext:
    """Context manager for retrying operations."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retry_on: Optional[List[Type[Exception]]] = None,
        max_delay: Optional[float] = None,
        log_retries: bool = True
    ):
        """
        Initialize the retry context.
        
        Args:
            max_attempts: Maximum number of attempts
            delay: Initial delay between attempts in seconds
            backoff_factor: Factor to increase delay by after each attempt
            jitter: Whether to add random jitter to delay
            retry_on: List of exception types to retry on (defaults to TransientError)
            max_delay: Maximum delay between attempts in seconds
            log_retries: Whether to log retry attempts
        """
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retry_on = retry_on or [TransientError, ConnectionError, TimeoutError, RateLimitError, ServiceUnavailableError]
        self.max_delay = max_delay
        self.log_retries = log_retries
        
        self.attempt = 0
        self.last_exception = None
        self.should_retry = True
    
    def __enter__(self):
        """Enter the retry context."""
        self.attempt += 1
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the retry context.
        
        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
            
        Returns:
            True if the exception was handled and should be retried, False otherwise
        """
        if exc_type is None:
            # No exception, no need to retry
            self.should_retry = False
            return False
        
        # Check if the exception is one we want to retry
        if not any(issubclass(exc_type, error_type) for error_type in self.retry_on):
            # Not a retryable exception
            self.should_retry = False
            return False
        
        # Store the exception
        self.last_exception = exc_val
        
        # Check if we've reached the maximum number of attempts
        if self.attempt >= self.max_attempts:
            # No more retries
            self.should_retry = False
            
            if self.log_retries:
                with_context(
                    max_attempts=self.max_attempts,
                    error=str(exc_val),
                    error_type=exc_type.__name__
                ).error(f"All {self.max_attempts} retry attempts failed")
            
            return False
        
        # Calculate delay with exponential backoff
        current_delay = self.delay * (self.backoff_factor ** (self.attempt - 1))
        
        # Apply maximum delay if specified
        if self.max_delay is not None:
            current_delay = min(current_delay, self.max_delay)
        
        # Add jitter if requested
        if self.jitter:
            current_delay = current_delay * (0.5 + random.random())
        
        # Log retry attempt
        if self.log_retries:
            with_context(
                attempt=self.attempt,
                max_attempts=self.max_attempts,
                delay=current_delay,
                error=str(exc_val),
                error_type=exc_type.__name__
            ).warning(f"Retrying after error: {exc_val}")
        
        # Wait before retrying
        time.sleep(current_delay)
        
        # Indicate that we've handled the exception and should retry
        return True

async def retry_async(
    coro_func: Callable[..., Any],
    *args: Any,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retry_on: Optional[List[Type[Exception]]] = None,
    max_delay: Optional[float] = None,
    log_retries: bool = True,
    **kwargs: Any
) -> Any:
    """
    Retry an async function with exponential backoff.
    
    Args:
        coro_func: Async function to retry
        *args: Positional arguments to pass to the function
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts in seconds
        backoff_factor: Factor to increase delay by after each attempt
        jitter: Whether to add random jitter to delay
        retry_on: List of exception types to retry on (defaults to TransientError)
        max_delay: Maximum delay between attempts in seconds
        log_retries: Whether to log retry attempts
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Result of the function
        
    Raises:
        Exception: If all retry attempts fail
    """
    if retry_on is None:
        retry_on = [TransientError, ConnectionError, TimeoutError, RateLimitError, ServiceUnavailableError]
    
    last_exception = None
    attempt = 1
    
    while attempt <= max_attempts:
        try:
            return await coro_func(*args, **kwargs)
        except tuple(retry_on) as e:
            last_exception = e
            
            if attempt == max_attempts:
                break
            
            # Calculate delay with exponential backoff
            current_delay = delay * (backoff_factor ** (attempt - 1))
            
            # Apply maximum delay if specified
            if max_delay is not None:
                current_delay = min(current_delay, max_delay)
            
            # Add jitter if requested
            if jitter:
                current_delay = current_delay * (0.5 + random.random())
            
            # Log retry attempt
            if log_retries:
                with_context(
                    attempt=attempt,
                    max_attempts=max_attempts,
                    delay=current_delay,
                    error=str(e),
                    error_type=e.__class__.__name__
                ).warning(f"Retrying {coro_func.__qualname__} after error: {e}")
            
            # Wait before retrying
            await asyncio.sleep(current_delay)
            
            attempt += 1
    
    # If we get here, all retries failed
    if last_exception:
        if log_retries:
            with_context(
                max_attempts=max_attempts,
                error=str(last_exception),
                error_type=last_exception.__class__.__name__
            ).error(f"All {max_attempts} retry attempts failed for {coro_func.__qualname__}")
        
        raise last_exception

def retry_sync(
    func: Callable[..., T],
    *args: Any,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retry_on: Optional[List[Type[Exception]]] = None,
    max_delay: Optional[float] = None,
    log_retries: bool = True,
    **kwargs: Any
) -> T:
    """
    Retry a synchronous function with exponential backoff.
    
    Args:
        func: Function to retry
        *args: Positional arguments to pass to the function
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts in seconds
        backoff_factor: Factor to increase delay by after each attempt
        jitter: Whether to add random jitter to delay
        retry_on: List of exception types to retry on (defaults to TransientError)
        max_delay: Maximum delay between attempts in seconds
        log_retries: Whether to log retry attempts
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Result of the function
        
    Raises:
        Exception: If all retry attempts fail
    """
    if retry_on is None:
        retry_on = [TransientError, ConnectionError, TimeoutError, RateLimitError, ServiceUnavailableError]
    
    last_exception = None
    attempt = 1
    
    while attempt <= max_attempts:
        try:
            return func(*args, **kwargs)
        except tuple(retry_on) as e:
            last_exception = e
            
            if attempt == max_attempts:
                break
            
            # Calculate delay with exponential backoff
            current_delay = delay * (backoff_factor ** (attempt - 1))
            
            # Apply maximum delay if specified
            if max_delay is not None:
                current_delay = min(current_delay, max_delay)
            
            # Add jitter if requested
            if jitter:
                current_delay = current_delay * (0.5 + random.random())
            
            # Log retry attempt
            if log_retries:
                with_context(
                    attempt=attempt,
                    max_attempts=max_attempts,
                    delay=current_delay,
                    error=str(e),
                    error_type=e.__class__.__name__
                ).warning(f"Retrying {func.__qualname__} after error: {e}")
            
            # Wait before retrying
            time.sleep(current_delay)
            
            attempt += 1
    
    # If we get here, all retries failed
    if last_exception:
        if log_retries:
            with_context(
                max_attempts=max_attempts,
                error=str(last_exception),
                error_type=last_exception.__class__.__name__
            ).error(f"All {max_attempts} retry attempts failed for {func.__qualname__}")
        
        raise last_exception

