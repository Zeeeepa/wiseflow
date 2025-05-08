"""
Error handling module for LLM API integrations.

This module provides comprehensive error handling for LLM API integrations,
including error classification, logging, and recovery strategies.
"""

import logging
import time
import traceback
from typing import Dict, Any, Optional, Callable, Tuple, Union, Type
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)

# Error categories
class ErrorCategory:
    """Error categories for LLM API errors."""
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    INVALID_REQUEST = "invalid_request"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    NETWORK = "network"
    UNKNOWN = "unknown"

class LLMError(Exception):
    """Base class for LLM API errors."""
    
    def __init__(self, message: str, category: str = ErrorCategory.UNKNOWN, original_error: Optional[Exception] = None):
        """
        Initialize the error.
        
        Args:
            message: Error message
            category: Error category
            original_error: Original exception that caused this error
        """
        self.message = message
        self.category = category
        self.original_error = original_error
        super().__init__(message)

class AuthenticationError(LLMError):
    """Error raised for authentication failures."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """Initialize the error."""
        super().__init__(message, ErrorCategory.AUTHENTICATION, original_error)

class RateLimitError(LLMError):
    """Error raised for rate limit exceeded."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """Initialize the error."""
        super().__init__(message, ErrorCategory.RATE_LIMIT, original_error)

class InvalidRequestError(LLMError):
    """Error raised for invalid requests."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """Initialize the error."""
        super().__init__(message, ErrorCategory.INVALID_REQUEST, original_error)

class ServerError(LLMError):
    """Error raised for server errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """Initialize the error."""
        super().__init__(message, ErrorCategory.SERVER_ERROR, original_error)

class TimeoutError(LLMError):
    """Error raised for timeouts."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """Initialize the error."""
        super().__init__(message, ErrorCategory.TIMEOUT, original_error)

class NetworkError(LLMError):
    """Error raised for network errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """Initialize the error."""
        super().__init__(message, ErrorCategory.NETWORK, original_error)

def classify_error(error: Exception) -> LLMError:
    """
    Classify an error into one of the error categories.
    
    Args:
        error: Original exception
        
    Returns:
        Classified error
    """
    error_str = str(error)
    error_type = type(error).__name__
    
    # Check for authentication errors
    if any(keyword in error_str.lower() for keyword in ["authentication", "auth", "unauthorized", "api key", "apikey", "401"]):
        return AuthenticationError(f"Authentication error: {error_str}", error)
    
    # Check for rate limit errors
    if any(keyword in error_str.lower() for keyword in ["rate limit", "ratelimit", "too many requests", "429"]):
        return RateLimitError(f"Rate limit exceeded: {error_str}", error)
    
    # Check for invalid request errors
    if any(keyword in error_str.lower() for keyword in ["invalid request", "bad request", "validation", "400"]):
        return InvalidRequestError(f"Invalid request: {error_str}", error)
    
    # Check for server errors
    if any(keyword in error_str.lower() for keyword in ["server error", "internal server", "500", "502", "503", "504"]):
        return ServerError(f"Server error: {error_str}", error)
    
    # Check for timeout errors
    if any(keyword in error_str.lower() for keyword in ["timeout", "timed out"]):
        return TimeoutError(f"Request timed out: {error_str}", error)
    
    # Check for network errors
    if any(keyword in error_str.lower() for keyword in ["network", "connection", "unreachable", "dns", "socket"]):
        return NetworkError(f"Network error: {error_str}", error)
    
    # Default to unknown error
    return LLMError(f"Unknown error ({error_type}): {error_str}", ErrorCategory.UNKNOWN, error)

def log_error(error: LLMError, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an error with context.
    
    Args:
        error: Classified error
        context: Additional context for the error
    """
    context = context or {}
    
    # Format context as string
    context_str = ", ".join(f"{k}={v}" for k, v in context.items())
    
    # Log error with appropriate level based on category
    if error.category in [ErrorCategory.AUTHENTICATION, ErrorCategory.INVALID_REQUEST]:
        logger.error(f"{error.message} [{context_str}]")
    elif error.category in [ErrorCategory.RATE_LIMIT, ErrorCategory.SERVER_ERROR, ErrorCategory.NETWORK]:
        logger.warning(f"{error.message} [{context_str}]")
    else:
        logger.info(f"{error.message} [{context_str}]")
    
    # Log traceback for unknown errors
    if error.category == ErrorCategory.UNKNOWN and error.original_error:
        logger.debug(f"Traceback: {traceback.format_exc()}")

def with_error_handling(func):
    """
    Decorator to add error handling to a function.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Classify and log the error
            error = classify_error(e)
            log_error(error, {"function": func.__name__})
            
            # Re-raise the classified error
            raise error
    
    return wrapper

async def with_async_error_handling(func):
    """
    Decorator to add error handling to an async function.
    
    Args:
        func: Async function to decorate
        
    Returns:
        Decorated async function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Classify and log the error
            error = classify_error(e)
            log_error(error, {"function": func.__name__})
            
            # Re-raise the classified error
            raise error
    
    return wrapper

async def with_retry(
    func,
    max_retries: int = 3,
    initial_wait: float = 1.0,
    backoff_factor: float = 2.0,
    retry_on: Optional[List[Type[Exception]]] = None,
    *args,
    **kwargs
):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        initial_wait: Initial wait time in seconds
        backoff_factor: Factor to multiply wait time by after each retry
        retry_on: List of exception types to retry on
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Result of the function
        
    Raises:
        Exception: If all retries fail
    """
    retry_on = retry_on or [RateLimitError, ServerError, NetworkError, TimeoutError]
    
    wait_time = initial_wait
    last_error = None
    
    for retry in range(max_retries):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except tuple(retry_on) as e:
            last_error = e
            logger.warning(f"Retry {retry+1}/{max_retries} after error: {str(e)}")
            
            if retry < max_retries - 1:
                # Wait with exponential backoff
                if asyncio.iscoroutinefunction(func):
                    await asyncio.sleep(wait_time)
                else:
                    time.sleep(wait_time)
                
                # Increase wait time for next retry
                wait_time *= backoff_factor
        except Exception as e:
            # Don't retry on other exceptions
            raise classify_error(e)
    
    # If all retries fail, raise the last error
    if last_error:
        raise classify_error(last_error)
    else:
        raise LLMError("All retries failed with unknown error")

