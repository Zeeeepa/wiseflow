"""
Error handling module for the Code Search Connector.

This module provides custom exceptions and error handling utilities for the Code Search Connector.
"""

import logging
import time
import functools
import asyncio
from typing import Dict, Any, Optional, Union, Callable, Type, List, Tuple
import traceback

logger = logging.getLogger(__name__)

class CodeSearchError(Exception):
    """Base exception for all code search errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the exception to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the exception
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details
        }


class ServiceError(CodeSearchError):
    """Exception for service-specific errors."""
    
    def __init__(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            service: Service name
            message: Error message
            details: Additional error details
        """
        super().__init__(message, details)
        self.service = service
        self.details["service"] = service


class AuthenticationError(ServiceError):
    """Exception for authentication errors."""
    pass


class RateLimitError(ServiceError):
    """Exception for rate limit errors."""
    
    def __init__(self, service: str, message: str, retry_after: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            service: Service name
            message: Error message
            retry_after: Seconds to wait before retrying
            details: Additional error details
        """
        super().__init__(service, message, details)
        self.retry_after = retry_after
        if retry_after is not None:
            self.details["retry_after"] = retry_after


class ResourceNotFoundError(ServiceError):
    """Exception for resource not found errors."""
    pass


class InvalidRequestError(ServiceError):
    """Exception for invalid request errors."""
    pass


class NetworkError(CodeSearchError):
    """Exception for network errors."""
    pass


class TimeoutError(NetworkError):
    """Exception for timeout errors."""
    pass


class ServerError(ServiceError):
    """Exception for server errors."""
    pass


class CacheError(CodeSearchError):
    """Exception for cache errors."""
    pass


class ConfigurationError(CodeSearchError):
    """Exception for configuration errors."""
    pass


def handle_service_errors(func: Callable) -> Callable:
    """
    Decorator for handling service errors.
    
    Args:
        func: Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except CodeSearchError:
            # Re-raise CodeSearchError exceptions
            raise
        except Exception as e:
            # Convert other exceptions to CodeSearchError
            logger.error(f"Error in {func.__name__}: {e}")
            logger.debug(traceback.format_exc())
            raise CodeSearchError(f"Unexpected error in {func.__name__}: {str(e)}", {
                "original_error": str(e),
                "traceback": traceback.format_exc()
            })
    return wrapper


def async_handle_service_errors(func: Callable) -> Callable:
    """
    Decorator for handling service errors in async functions.
    
    Args:
        func: Async function to decorate
        
    Returns:
        Callable: Decorated async function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except CodeSearchError:
            # Re-raise CodeSearchError exceptions
            raise
        except Exception as e:
            # Convert other exceptions to CodeSearchError
            logger.error(f"Error in {func.__name__}: {e}")
            logger.debug(traceback.format_exc())
            raise CodeSearchError(f"Unexpected error in {func.__name__}: {str(e)}", {
                "original_error": str(e),
                "traceback": traceback.format_exc()
            })
    return wrapper


def retry_on_error(
    max_retries: int = 3,
    retry_delay: int = 5,
    retry_on: Optional[List[Type[Exception]]] = None,
    backoff_factor: float = 2.0
) -> Callable:
    """
    Decorator for retrying on specific errors.
    
    Args:
        max_retries: Maximum number of retries
        retry_delay: Base delay between retries in seconds
        retry_on: List of exception types to retry on
        backoff_factor: Factor to multiply delay by after each retry
        
    Returns:
        Callable: Decorator function
    """
    if retry_on is None:
        retry_on = [RateLimitError, NetworkError, TimeoutError, ServerError]
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            last_error = None
            
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except tuple(retry_on) as e:
                    retries += 1
                    last_error = e
                    
                    if retries > max_retries:
                        logger.warning(f"Max retries ({max_retries}) exceeded for {func.__name__}")
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = retry_delay * (backoff_factor ** (retries - 1))
                    
                    # Use retry_after from RateLimitError if available
                    if isinstance(e, RateLimitError) and e.retry_after is not None:
                        delay = max(delay, e.retry_after)
                    
                    logger.info(f"Retrying {func.__name__} in {delay:.2f} seconds (attempt {retries}/{max_retries})")
                    time.sleep(delay)
                except Exception as e:
                    # Don't retry on other exceptions
                    raise
            
            # If we get here, all retries failed
            if last_error:
                raise last_error
            
            # This should never happen, but just in case
            raise CodeSearchError(f"Failed to execute {func.__name__} after {max_retries} retries")
        
        return wrapper
    
    return decorator


def async_retry_on_error(
    max_retries: int = 3,
    retry_delay: int = 5,
    retry_on: Optional[List[Type[Exception]]] = None,
    backoff_factor: float = 2.0
) -> Callable:
    """
    Decorator for retrying on specific errors in async functions.
    
    Args:
        max_retries: Maximum number of retries
        retry_delay: Base delay between retries in seconds
        retry_on: List of exception types to retry on
        backoff_factor: Factor to multiply delay by after each retry
        
    Returns:
        Callable: Decorator function
    """
    if retry_on is None:
        retry_on = [RateLimitError, NetworkError, TimeoutError, ServerError]
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            last_error = None
            
            while retries <= max_retries:
                try:
                    return await func(*args, **kwargs)
                except tuple(retry_on) as e:
                    retries += 1
                    last_error = e
                    
                    if retries > max_retries:
                        logger.warning(f"Max retries ({max_retries}) exceeded for {func.__name__}")
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = retry_delay * (backoff_factor ** (retries - 1))
                    
                    # Use retry_after from RateLimitError if available
                    if isinstance(e, RateLimitError) and e.retry_after is not None:
                        delay = max(delay, e.retry_after)
                    
                    logger.info(f"Retrying {func.__name__} in {delay:.2f} seconds (attempt {retries}/{max_retries})")
                    await asyncio.sleep(delay)
                except Exception as e:
                    # Don't retry on other exceptions
                    raise
            
            # If we get here, all retries failed
            if last_error:
                raise last_error
            
            # This should never happen, but just in case
            raise CodeSearchError(f"Failed to execute {func.__name__} after {max_retries} retries")
        
        return wrapper
    
    return decorator


def parse_service_error(service: str, status_code: int, response_text: str) -> ServiceError:
    """
    Parse a service error from a response.
    
    Args:
        service: Service name
        status_code: HTTP status code
        response_text: Response text
        
    Returns:
        ServiceError: Appropriate service error exception
    """
    error_message = f"{service} API error: {status_code} - {response_text}"
    details = {
        "status_code": status_code,
        "response_text": response_text
    }
    
    if status_code == 401 or status_code == 403:
        return AuthenticationError(service, error_message, details)
    elif status_code == 404:
        return ResourceNotFoundError(service, error_message, details)
    elif status_code == 429:
        # Try to extract retry-after header
        retry_after = None
        if "retry after" in response_text.lower():
            try:
                # Extract number from "retry after X seconds"
                import re
                match = re.search(r"retry after (\d+)", response_text.lower())
                if match:
                    retry_after = int(match.group(1))
            except (ValueError, IndexError):
                pass
        
        return RateLimitError(service, error_message, retry_after, details)
    elif status_code >= 400 and status_code < 500:
        return InvalidRequestError(service, error_message, details)
    elif status_code >= 500:
        return ServerError(service, error_message, details)
    else:
        return ServiceError(service, error_message, details)
"""

