#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enhanced error handling utilities for WiseFlow.

This module extends the base error handling system with additional features:
- Retry mechanisms for transient failures
- Circuit breaker pattern for external service calls
- Enhanced error context and correlation
- Standardized error recovery mechanisms
"""

import time
import uuid
import functools
import traceback
import sys
import os
import json
import asyncio
import inspect
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Type, Union, List, TypeVar, cast, Tuple

from core.config import PROJECT_DIR
from core.utils.logging_config import logger, with_context
from core.utils.error_handling import (
    WiseflowError, ConnectionError, DataProcessingError, 
    ConfigurationError, ResourceError, TaskError, PluginError,
    ValidationError, AuthenticationError, AuthorizationError, NotFoundError,
    handle_exceptions, ErrorHandler, async_error_handler, log_error, save_error_to_file
)

# Type variable for function return type
T = TypeVar('T')

# Additional error types
class TransientError(WiseflowError):
    """Error that is likely to be resolved by retrying the operation."""
    pass

class PermanentError(WiseflowError):
    """Error that will not be resolved by retrying the operation."""
    pass

class TimeoutError(TransientError):
    """Error raised when an operation times out."""
    pass

class RateLimitError(TransientError):
    """Error raised when a rate limit is exceeded."""
    pass

class DependencyError(WiseflowError):
    """Error raised when a dependency fails."""
    pass

class StateError(WiseflowError):
    """Error raised when the system is in an invalid state."""
    pass

class ConcurrencyError(WiseflowError):
    """Error raised when there is a concurrency issue."""
    pass

# Error correlation
_ERROR_CORRELATION = {}

def get_correlation_id() -> str:
    """
    Get the current error correlation ID or generate a new one.
    
    Returns:
        Correlation ID string
    """
    thread_id = threading.current_thread().ident
    if thread_id not in _ERROR_CORRELATION:
        _ERROR_CORRELATION[thread_id] = str(uuid.uuid4())
    return _ERROR_CORRELATION[thread_id]

def set_correlation_id(correlation_id: str) -> None:
    """
    Set the error correlation ID for the current thread.
    
    Args:
        correlation_id: Correlation ID to set
    """
    thread_id = threading.current_thread().ident
    _ERROR_CORRELATION[thread_id] = correlation_id

def clear_correlation_id() -> None:
    """Clear the error correlation ID for the current thread."""
    thread_id = threading.current_thread().ident
    if thread_id in _ERROR_CORRELATION:
        del _ERROR_CORRELATION[thread_id]

class ErrorCorrelation:
    """Context manager for error correlation."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        """
        Initialize with an optional correlation ID.
        
        Args:
            correlation_id: Correlation ID to use (generates a new one if None)
        """
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.previous_id = None
    
    def __enter__(self):
        """Set the correlation ID when entering the context."""
        thread_id = threading.current_thread().ident
        self.previous_id = _ERROR_CORRELATION.get(thread_id)
        _ERROR_CORRELATION[thread_id] = self.correlation_id
        return self.correlation_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore the previous correlation ID when exiting the context."""
        thread_id = threading.current_thread().ident
        if self.previous_id:
            _ERROR_CORRELATION[thread_id] = self.previous_id
        else:
            if thread_id in _ERROR_CORRELATION:
                del _ERROR_CORRELATION[thread_id]

# Retry mechanism
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
        retry_on = [TransientError]
    
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
                            error_type=e.__class__.__name__,
                            correlation_id=get_correlation_id()
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
                        error_type=last_exception.__class__.__name__,
                        correlation_id=get_correlation_id()
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
                            error_type=e.__class__.__name__,
                            correlation_id=get_correlation_id()
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
                        error_type=last_exception.__class__.__name__,
                        correlation_id=get_correlation_id()
                    ).error(f"All {max_attempts} retry attempts failed for {func.__qualname__}")
                
                raise last_exception
        
        # Return appropriate wrapper based on function type
        if is_async:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Circuit breaker pattern
class CircuitBreakerState:
    """Circuit breaker state."""
    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"      # Failing, requests are blocked
    HALF_OPEN = "half_open"  # Testing if service is back

class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.
    
    The circuit breaker pattern prevents a failing service from being
    repeatedly called, which can lead to cascading failures.
    """
    
    _instances = {}
    
    @classmethod
    def get_instance(cls, name: str) -> 'CircuitBreaker':
        """
        Get a circuit breaker instance by name.
        
        Args:
            name: Circuit breaker name
            
        Returns:
            Circuit breaker instance
        """
        if name not in cls._instances:
            cls._instances[name] = CircuitBreaker(name)
        return cls._instances[name]
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exceptions: Optional[List[Type[Exception]]] = None
    ):
        """
        Initialize a circuit breaker.
        
        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening the circuit
            recovery_timeout: Time in seconds before attempting recovery
            expected_exceptions: Exceptions that count as failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions or [Exception]
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.last_success_time = time.time()
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorate a function with circuit breaker protection.
        
        Args:
            func: Function to protect
            
        Returns:
            Protected function
        """
        # Determine if function is async
        is_async = asyncio.iscoroutinefunction(func)
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            self._before_call()
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except tuple(self.expected_exceptions) as e:
                self._on_failure(e)
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            self._before_call()
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except tuple(self.expected_exceptions) as e:
                self._on_failure(e)
                raise
        
        # Return appropriate wrapper based on function type
        if is_async:
            return async_wrapper
        else:
            return sync_wrapper
    
    def _before_call(self) -> None:
        """Check circuit state before making a call."""
        if self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has elapsed
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                with_context(circuit=self.name).info(
                    f"Circuit {self.name} transitioning from OPEN to HALF_OPEN"
                )
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit {self.name} is OPEN",
                    {"circuit": self.name, "state": self.state}
                )
    
    def _on_success(self) -> None:
        """Handle successful call."""
        self.last_success_time = time.time()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            with_context(circuit=self.name).info(
                f"Circuit {self.name} transitioning from HALF_OPEN to CLOSED"
            )
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
    
    def _on_failure(self, exception: Exception) -> None:
        """
        Handle failed call.
        
        Args:
            exception: Exception that occurred
        """
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            self.failure_count += 1
            
            if self.failure_count >= self.failure_threshold:
                with_context(
                    circuit=self.name,
                    failure_count=self.failure_count,
                    threshold=self.failure_threshold
                ).warning(f"Circuit {self.name} transitioning from CLOSED to OPEN")
                self.state = CircuitBreakerState.OPEN
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            with_context(circuit=self.name).warning(
                f"Circuit {self.name} transitioning from HALF_OPEN to OPEN"
            )
            self.state = CircuitBreakerState.OPEN

class CircuitBreakerOpenError(WiseflowError):
    """Error raised when a circuit breaker is open."""
    pass

def with_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exceptions: Optional[List[Type[Exception]]] = None
) -> Callable:
    """
    Decorator for applying circuit breaker pattern to a function.
    
    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures before opening the circuit
        recovery_timeout: Time in seconds before attempting recovery
        expected_exceptions: Exceptions that count as failures
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        circuit_breaker = CircuitBreaker.get_instance(name)
        circuit_breaker.failure_threshold = failure_threshold
        circuit_breaker.recovery_timeout = recovery_timeout
        
        if expected_exceptions:
            circuit_breaker.expected_exceptions = expected_exceptions
        
        return circuit_breaker(func)
    
    return decorator

# Enhanced error handling with cleanup
class CleanupHandler:
    """
    Context manager for handling exceptions with cleanup.
    
    Example:
        with CleanupHandler(cleanup_func=lambda: conn.close()) as handler:
            conn = db.connect()
            result = conn.execute(query)
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
        context: Optional[Dict[str, Any]] = None,
        cleanup_func: Optional[Callable[[], None]] = None,
        always_cleanup: bool = True
    ):
        """
        Initialize the cleanup handler.
        
        Args:
            error_types: List of exception types to catch
            default: Default value to return if an exception occurs
            log_error: Whether to log the error
            save_to_file: Whether to save the error to a file
            context: Additional context to include in the error log
            cleanup_func: Function to call for cleanup
            always_cleanup: Whether to always call cleanup_func, even if no error occurs
        """
        self.error_types = error_types or [Exception]
        self.default = default
        self.log_error = log_error
        self.save_to_file = save_to_file
        self.context = context or {}
        self.cleanup_func = cleanup_func
        self.always_cleanup = always_cleanup
        
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
        try:
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
                "module": module_name,
                "correlation_id": get_correlation_id()
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
        finally:
            # Always perform cleanup if requested
            if self.cleanup_func and (self.always_cleanup or self.error_occurred):
                try:
                    self.cleanup_func()
                except Exception as cleanup_error:
                    # Log cleanup error but don't override the original error
                    with_context(
                        function=func_name,
                        module=module_name,
                        correlation_id=get_correlation_id(),
                        original_error=str(self.error) if self.error else None
                    ).error(f"Error during cleanup: {cleanup_error}")

# Import missing modules
import random
import threading

