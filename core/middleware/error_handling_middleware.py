"""
Error handling middleware for WiseFlow.

This module provides middleware components for consistent error handling across the application.
"""

import logging
import traceback
import time
import asyncio
from typing import Dict, Any, Optional, Callable, List, Union, Type, TypeVar, cast
from functools import wraps
from datetime import datetime

from fastapi import Request, Response, FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.utils.error_handling import (
    WiseflowError,
    ConnectionError,
    DataProcessingError,
    ConfigurationError,
    ResourceError,
    TaskError,
    PluginError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    log_error,
    save_error_to_file
)
from core.utils.logging_config import logger, with_context
from core.task_management.exceptions import (
    TaskDependencyError,
    TaskCancellationError,
    TaskTimeoutError,
    TaskExecutionError,
    TaskNotFoundError,
    InvalidTaskStateError
)

# Type variable for function return type
T = TypeVar('T')

# Severity levels for error logging
class ErrorSeverity:
    """Error severity levels for structured logging."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ErrorCategory:
    """Error categories for classification."""
    SYSTEM = "system"
    APPLICATION = "application"
    NETWORK = "network"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    RESOURCE = "resource"
    TASK = "task"
    PLUGIN = "plugin"
    EXTERNAL_SERVICE = "external_service"
    UNKNOWN = "unknown"

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling exceptions in FastAPI applications.
    
    This middleware catches exceptions, logs them, and returns appropriate responses.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        log_errors: bool = True,
        include_traceback: bool = False,
        save_to_file: bool = False,
        error_handlers: Optional[Dict[Type[Exception], Callable]] = None
    ):
        """
        Initialize the error handling middleware.
        
        Args:
            app: The ASGI application
            log_errors: Whether to log errors
            include_traceback: Whether to include traceback in the response (for development)
            save_to_file: Whether to save errors to a file
            error_handlers: Custom error handlers for specific exception types
        """
        super().__init__(app)
        self.log_errors = log_errors
        self.include_traceback = include_traceback
        self.save_to_file = save_to_file
        self.error_handlers = error_handlers or {}
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Dispatch the request and handle exceptions.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            Response: The response
        """
        try:
            return await call_next(request)
        except Exception as exc:
            # Get request information for context
            request_info = {
                "method": request.method,
                "url": str(request.url),
                "client_host": request.client.host if request.client else None,
                "headers": dict(request.headers),
                "path_params": request.path_params,
                "query_params": dict(request.query_params),
            }
            
            # Check if we have a custom handler for this exception type
            for exc_type, handler in self.error_handlers.items():
                if isinstance(exc, exc_type):
                    return await handler(request, exc)
            
            # Handle WiseflowError
            if isinstance(exc, WiseflowError):
                if self.log_errors:
                    exc.log()
                
                if self.save_to_file:
                    save_error_to_file(
                        f"{request.method}_{request.url.path.replace('/', '_')}",
                        str(exc),
                        traceback.format_exc(),
                        context=request_info
                    )
                
                status_code = self._get_status_code_for_error(exc)
                
                return JSONResponse(
                    status_code=status_code,
                    content={
                        "detail": str(exc),
                        "error_type": exc.__class__.__name__,
                        "timestamp": datetime.now().isoformat(),
                        "traceback": traceback.format_exc() if self.include_traceback else None,
                        **exc.details
                    }
                )
            
            # Handle TaskError
            elif isinstance(exc, TaskError):
                if self.log_errors:
                    log_error(exc, context=request_info)
                
                if self.save_to_file:
                    save_error_to_file(
                        f"{request.method}_{request.url.path.replace('/', '_')}",
                        str(exc),
                        traceback.format_exc(),
                        context=request_info
                    )
                
                status_code = self._get_status_code_for_task_error(exc)
                
                return JSONResponse(
                    status_code=status_code,
                    content={
                        "detail": str(exc),
                        "error_type": exc.__class__.__name__,
                        "task_id": exc.task_id,
                        "timestamp": datetime.now().isoformat(),
                        "traceback": traceback.format_exc() if self.include_traceback else None,
                        **exc.details
                    }
                )
            
            # Handle other exceptions
            else:
                if self.log_errors:
                    logger.error(f"Unhandled exception: {str(exc)}")
                    logger.debug(f"Traceback: {traceback.format_exc()}")
                
                if self.save_to_file:
                    save_error_to_file(
                        f"{request.method}_{request.url.path.replace('/', '_')}",
                        str(exc),
                        traceback.format_exc(),
                        context=request_info
                    )
                
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": f"Internal server error: {str(exc)}",
                        "error_type": exc.__class__.__name__,
                        "timestamp": datetime.now().isoformat(),
                        "traceback": traceback.format_exc() if self.include_traceback else None
                    }
                )
    
    def _get_status_code_for_error(self, error: WiseflowError) -> int:
        """
        Get the appropriate HTTP status code for a WiseflowError.
        
        Args:
            error: The error
            
        Returns:
            int: The HTTP status code
        """
        if isinstance(error, ValidationError):
            return 400
        elif isinstance(error, AuthenticationError):
            return 401
        elif isinstance(error, AuthorizationError):
            return 403
        elif isinstance(error, NotFoundError):
            return 404
        elif isinstance(error, ConnectionError):
            return 503
        elif isinstance(error, ResourceError):
            return 503
        elif isinstance(error, ConfigurationError):
            return 500
        elif isinstance(error, DataProcessingError):
            return 500
        elif isinstance(error, PluginError):
            return 500
        else:
            return 500
    
    def _get_status_code_for_task_error(self, error: TaskError) -> int:
        """
        Get the appropriate HTTP status code for a TaskError.
        
        Args:
            error: The error
            
        Returns:
            int: The HTTP status code
        """
        if isinstance(error, TaskNotFoundError):
            return 404
        elif isinstance(error, TaskDependencyError):
            return 400
        elif isinstance(error, InvalidTaskStateError):
            return 400
        elif isinstance(error, TaskTimeoutError):
            return 408
        elif isinstance(error, TaskCancellationError):
            return 500
        elif isinstance(error, TaskExecutionError):
            return 500
        else:
            return 500

def add_error_handling_middleware(
    app: FastAPI,
    log_errors: bool = True,
    include_traceback: bool = False,
    save_to_file: bool = False,
    error_handlers: Optional[Dict[Type[Exception], Callable]] = None
) -> None:
    """
    Add error handling middleware to a FastAPI application.
    
    Args:
        app: The FastAPI application
        log_errors: Whether to log errors
        include_traceback: Whether to include traceback in the response (for development)
        save_to_file: Whether to save errors to a file
        error_handlers: Custom error handlers for specific exception types
    """
    app.add_middleware(
        ErrorHandlingMiddleware,
        log_errors=log_errors,
        include_traceback=include_traceback,
        save_to_file=save_to_file,
        error_handlers=error_handlers
    )

class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    
    This class implements the circuit breaker pattern to prevent cascading failures
    when an external service is unavailable.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        timeout: Optional[float] = None,
        fallback: Optional[Callable] = None,
        excluded_exceptions: Optional[List[Type[Exception]]] = None
    ):
        """
        Initialize the circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening the circuit
            recovery_timeout: Time in seconds before attempting to close the circuit
            timeout: Timeout for the wrapped function
            fallback: Fallback function to call when the circuit is open
            excluded_exceptions: Exceptions that should not count as failures
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.timeout = timeout
        self.fallback = fallback
        self.excluded_exceptions = excluded_exceptions or []
        
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = asyncio.Lock()
    
    async def __call__(self, func, *args, **kwargs):
        """
        Call the wrapped function with circuit breaker protection.
        
        Args:
            func: The function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            The result of the function call
            
        Raises:
            Exception: If the circuit is open and no fallback is provided
        """
        async with self._lock:
            # Check if the circuit is open
            if self.state == "OPEN":
                # Check if recovery timeout has elapsed
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    # Move to half-open state
                    self.state = "HALF_OPEN"
                    logger.info(f"Circuit breaker moved to HALF_OPEN state after {self.recovery_timeout}s")
                else:
                    # Circuit is still open, use fallback or raise exception
                    if self.fallback:
                        logger.info(f"Circuit is OPEN, using fallback function")
                        return await self.fallback(*args, **kwargs)
                    else:
                        logger.warning(f"Circuit is OPEN, no fallback provided")
                        raise ConnectionError(
                            "Service unavailable (circuit open)",
                            {"recovery_time": self.last_failure_time + self.recovery_timeout - time.time()}
                        )
        
        try:
            # Call the function with timeout if specified
            if self.timeout and asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.timeout)
            elif self.timeout:
                # For synchronous functions, run in executor with timeout
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, func, *args, **kwargs),
                    timeout=self.timeout
                )
            elif asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                # For synchronous functions, run in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, func, *args, **kwargs)
            
            # Success, reset failure count if in half-open state
            async with self._lock:
                if self.state == "HALF_OPEN":
                    self.state = "CLOSED"
                    self.failure_count = 0
                    logger.info("Circuit breaker moved to CLOSED state after successful call")
            
            return result
        
        except Exception as e:
            # Check if this exception should be excluded
            if any(isinstance(e, exc_type) for exc_type in self.excluded_exceptions):
                # Don't count this as a failure
                raise
            
            # Increment failure count
            async with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                # Check if we should open the circuit
                if self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"
                    logger.warning(f"Circuit breaker moved to OPEN state after {self.failure_count} failures")
                elif self.state == "HALF_OPEN":
                    self.state = "OPEN"
                    logger.warning("Circuit breaker moved back to OPEN state after failure in HALF_OPEN state")
            
            # Use fallback or re-raise the exception
            if self.fallback:
                logger.info(f"Using fallback function after failure: {str(e)}")
                return await self.fallback(*args, **kwargs)
            else:
                raise

def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    timeout: Optional[float] = None,
    fallback: Optional[Callable] = None,
    excluded_exceptions: Optional[List[Type[Exception]]] = None
):
    """
    Decorator for applying circuit breaker pattern to a function.
    
    Args:
        failure_threshold: Number of failures before opening the circuit
        recovery_timeout: Time in seconds before attempting to close the circuit
        timeout: Timeout for the wrapped function
        fallback: Fallback function to call when the circuit is open
        excluded_exceptions: Exceptions that should not count as failures
        
    Returns:
        Decorator function
    """
    breaker = CircuitBreaker(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        timeout=timeout,
        fallback=fallback,
        excluded_exceptions=excluded_exceptions
    )
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(breaker(func, *args, **kwargs))
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

class RetryWithBackoff:
    """
    Retry mechanism with exponential backoff.
    
    This class implements a retry mechanism with exponential backoff for handling
    transient failures in external service calls.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        backoff_multiplier: float = 2.0,
        max_backoff: float = 60.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None
    ):
        """
        Initialize the retry mechanism.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_backoff: Initial backoff time in seconds
            backoff_multiplier: Multiplier for backoff time after each retry
            max_backoff: Maximum backoff time in seconds
            jitter: Whether to add jitter to backoff times
            retryable_exceptions: Exceptions that should trigger a retry
        """
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.backoff_multiplier = backoff_multiplier
        self.max_backoff = max_backoff
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError
        ]
    
    async def __call__(self, func, *args, **kwargs):
        """
        Call the wrapped function with retry logic.
        
        Args:
            func: The function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            The result of the function call
            
        Raises:
            Exception: If all retries fail
        """
        last_exception = None
        backoff = self.initial_backoff
        
        for retry in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    # For synchronous functions, run in executor
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, func, *args, **kwargs)
            
            except Exception as e:
                last_exception = e
                
                # Check if this exception is retryable
                if not any(isinstance(e, exc_type) for exc_type in self.retryable_exceptions):
                    # Non-retryable exception, re-raise immediately
                    raise
                
                # If we've exhausted our retries, re-raise the exception
                if retry >= self.max_retries:
                    logger.warning(f"Maximum retries ({self.max_retries}) reached. Last error: {last_exception}")
                    raise
                
                # Calculate backoff time with optional jitter
                if self.jitter:
                    # Add random jitter between 0-100% of the backoff time
                    jitter_amount = backoff * (0.5 + (0.5 * (time.time() % 1)))
                    sleep_time = min(backoff + jitter_amount, self.max_backoff)
                else:
                    sleep_time = min(backoff, self.max_backoff)
                
                logger.info(f"Retry {retry+1}/{self.max_retries} after error: {str(e)}. Waiting {sleep_time:.2f}s")
                
                # Wait before retrying
                await asyncio.sleep(sleep_time)
                
                # Increase backoff for next retry
                backoff = min(backoff * self.backoff_multiplier, self.max_backoff)
        
        # This should never be reached due to the raise in the loop, but just in case
        raise last_exception if last_exception else RuntimeError("Unexpected error in retry logic")

def retry_with_backoff(
    max_retries: int = 3,
    initial_backoff: float = 1.0,
    backoff_multiplier: float = 2.0,
    max_backoff: float = 60.0,
    jitter: bool = True,
    retryable_exceptions: Optional[List[Type[Exception]]] = None
):
    """
    Decorator for applying retry with exponential backoff to a function.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds
        backoff_multiplier: Multiplier for backoff time after each retry
        max_backoff: Maximum backoff time in seconds
        jitter: Whether to add jitter to backoff times
        retryable_exceptions: Exceptions that should trigger a retry
        
    Returns:
        Decorator function
    """
    retry_mechanism = RetryWithBackoff(
        max_retries=max_retries,
        initial_backoff=initial_backoff,
        backoff_multiplier=backoff_multiplier,
        max_backoff=max_backoff,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions
    )
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await retry_mechanism(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(retry_mechanism(func, *args, **kwargs))
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def with_error_handling(
    error_types: Optional[List[Type[Exception]]] = None,
    severity: str = ErrorSeverity.ERROR,
    category: str = ErrorCategory.APPLICATION,
    include_context: bool = True,
    save_to_file: bool = False,
    reraise: bool = True,
    transform_error: Optional[Callable[[Exception], Exception]] = None
):
    """
    Decorator for handling exceptions with structured logging.
    
    Args:
        error_types: List of exception types to catch
        severity: Error severity level for logging
        category: Error category for classification
        include_context: Whether to include function context in logs
        save_to_file: Whether to save errors to a file
        reraise: Whether to re-raise the exception
        transform_error: Function to transform the caught exception
        
    Returns:
        Decorator function
    """
    if error_types is None:
        error_types = [Exception]
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except tuple(error_types) as e:
                _handle_error(e, func, args, kwargs)
                if reraise:
                    raise
                return None
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except tuple(error_types) as e:
                _handle_error(e, func, args, kwargs)
                if reraise:
                    raise
                return None
        
        def _handle_error(e, func, args, kwargs):
            # Create error context
            context = {}
            if include_context:
                context = {
                    "function": func.__qualname__,
                    "module": func.__module__,
                    "args": str(args),
                    "kwargs": str(kwargs),
                    "error_category": category,
                    "error_severity": severity
                }
            
            # Transform error if needed
            if transform_error is not None:
                e = transform_error(e)
            
            # Log the error
            if isinstance(e, WiseflowError):
                # Add context to the error
                error_with_context = type(e)(
                    e.message,
                    {**e.details, **context},
                    e.cause
                )
                error_with_context.log(severity)
            else:
                # Log the error with context
                log_error(e, log_level=severity, context=context)
            
            # Save error to file if requested
            if save_to_file:
                save_error_to_file(
                    func.__qualname__,
                    str(e),
                    traceback.format_exc(),
                    context=context
                )
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

