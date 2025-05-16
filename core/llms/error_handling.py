"""
Error handling utilities for LLM interactions.

This module provides standardized error handling for LLM API calls,
including retry logic, error classification, and logging.
"""

import asyncio
import time
import logging
import traceback
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, Awaitable

from .config import llm_config

# Define a type variable for the return type of the wrapped function
T = TypeVar('T')

class LLMError(Exception):
    """Base exception class for LLM-related errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """
        Initialize the LLM error.
        
        Args:
            message: Error message
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.original_error = original_error
        self.traceback = traceback.format_exc() if original_error else None

class RateLimitError(LLMError):
    """Exception raised when hitting rate limits."""
    pass

class AuthenticationError(LLMError):
    """Exception raised for authentication issues."""
    pass

class InvalidRequestError(LLMError):
    """Exception raised for invalid requests."""
    pass

class APIConnectionError(LLMError):
    """Exception raised for API connection issues."""
    pass

class ServiceUnavailableError(LLMError):
    """Exception raised when the service is unavailable."""
    pass

class ModelNotFoundError(LLMError):
    """Exception raised when the requested model is not found."""
    pass

class ContextLengthExceededError(LLMError):
    """Exception raised when the context length is exceeded."""
    pass

class ContentFilterError(LLMError):
    """Exception raised when content is filtered by the provider."""
    pass

class QuotaExceededError(LLMError):
    """Exception raised when the API quota is exceeded."""
    pass

class TimeoutError(LLMError):
    """Exception raised when the API request times out."""
    pass

class ServerOverloadedError(LLMError):
    """Exception raised when the server is overloaded."""
    pass

class UnknownLLMError(LLMError):
    """Exception raised for unknown errors."""
    pass

def map_provider_error(provider: str, error: Exception) -> LLMError:
    """
    Map provider-specific errors to our standardized error classes.
    
    Args:
        provider: The LLM provider (e.g., 'openai', 'litellm')
        error: The original error from the provider
        
    Returns:
        A standardized LLMError instance
    """
    error_str = str(error)
    error_type = type(error).__name__
    
    # OpenAI error mapping
    if provider == 'openai':
        if 'rate limit' in error_str.lower() or error_type == 'RateLimitError':
            return RateLimitError(f"Rate limit exceeded: {error_str}", error)
        elif 'authentication' in error_str.lower() or error_type == 'AuthenticationError':
            return AuthenticationError(f"Authentication failed: {error_str}", error)
        elif 'invalid' in error_str.lower() or error_type == 'InvalidRequestError':
            return InvalidRequestError(f"Invalid request: {error_str}", error)
        elif 'connection' in error_str.lower() or error_type == 'APIConnectionError':
            return APIConnectionError(f"API connection error: {error_str}", error)
        elif 'unavailable' in error_str.lower() or error_type == 'ServiceUnavailableError':
            return ServiceUnavailableError(f"Service unavailable: {error_str}", error)
        elif 'not found' in error_str.lower() and 'model' in error_str.lower():
            return ModelNotFoundError(f"Model not found: {error_str}", error)
        elif 'context length' in error_str.lower() or 'token limit' in error_str.lower():
            return ContextLengthExceededError(f"Context length exceeded: {error_str}", error)
        elif 'content filter' in error_str.lower() or 'content policy' in error_str.lower():
            return ContentFilterError(f"Content filtered: {error_str}", error)
        elif 'quota' in error_str.lower() or 'billing' in error_str.lower():
            return QuotaExceededError(f"Quota exceeded: {error_str}", error)
        elif 'timeout' in error_str.lower():
            return TimeoutError(f"Request timed out: {error_str}", error)
        elif 'overloaded' in error_str.lower() or 'capacity' in error_str.lower():
            return ServerOverloadedError(f"Server overloaded: {error_str}", error)
    
    # LiteLLM error mapping
    elif provider == 'litellm':
        if 'rate limit' in error_str.lower():
            return RateLimitError(f"Rate limit exceeded: {error_str}", error)
        elif 'authentication' in error_str.lower() or 'auth' in error_str.lower():
            return AuthenticationError(f"Authentication failed: {error_str}", error)
        elif 'invalid' in error_str.lower():
            return InvalidRequestError(f"Invalid request: {error_str}", error)
        elif 'connection' in error_str.lower() or 'timeout' in error_str.lower():
            return APIConnectionError(f"API connection error: {error_str}", error)
        elif 'unavailable' in error_str.lower() or 'server error' in error_str.lower():
            return ServiceUnavailableError(f"Service unavailable: {error_str}", error)
        elif 'not found' in error_str.lower() and 'model' in error_str.lower():
            return ModelNotFoundError(f"Model not found: {error_str}", error)
        elif 'context length' in error_str.lower() or 'token limit' in error_str.lower():
            return ContextLengthExceededError(f"Context length exceeded: {error_str}", error)
        elif 'content filter' in error_str.lower() or 'content policy' in error_str.lower():
            return ContentFilterError(f"Content filtered: {error_str}", error)
        elif 'quota' in error_str.lower() or 'billing' in error_str.lower():
            return QuotaExceededError(f"Quota exceeded: {error_str}", error)
        elif 'timeout' in error_str.lower():
            return TimeoutError(f"Request timed out: {error_str}", error)
        elif 'overloaded' in error_str.lower() or 'capacity' in error_str.lower():
            return ServerOverloadedError(f"Server overloaded: {error_str}", error)
    
    # Anthropic error mapping
    elif provider == 'anthropic':
        if 'rate' in error_str.lower() and 'limit' in error_str.lower():
            return RateLimitError(f"Rate limit exceeded: {error_str}", error)
        elif 'auth' in error_str.lower() or 'key' in error_str.lower():
            return AuthenticationError(f"Authentication failed: {error_str}", error)
        elif 'invalid' in error_str.lower() or 'bad request' in error_str.lower():
            return InvalidRequestError(f"Invalid request: {error_str}", error)
        elif 'connection' in error_str.lower() or 'network' in error_str.lower():
            return APIConnectionError(f"API connection error: {error_str}", error)
        elif 'unavailable' in error_str.lower() or 'down' in error_str.lower():
            return ServiceUnavailableError(f"Service unavailable: {error_str}", error)
        elif 'not found' in error_str.lower() and 'model' in error_str.lower():
            return ModelNotFoundError(f"Model not found: {error_str}", error)
        elif 'context' in error_str.lower() or 'token' in error_str.lower():
            return ContextLengthExceededError(f"Context length exceeded: {error_str}", error)
        elif 'content' in error_str.lower() and 'policy' in error_str.lower():
            return ContentFilterError(f"Content filtered: {error_str}", error)
    
    # Default to UnknownLLMError for unrecognized errors
    return UnknownLLMError(f"Unknown error ({provider}): {error_str}", error)

async def with_retries(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    max_retries: Optional[int] = None,
    initial_backoff: Optional[float] = None,
    backoff_multiplier: Optional[float] = None,
    max_backoff: Optional[float] = None,
    retryable_errors: Optional[List[type]] = None,
    logger: Optional[logging.Logger] = None,
    **kwargs: Any
) -> T:
    """
    Execute an async function with exponential backoff retry logic.
    
    Args:
        func: The async function to execute
        *args: Positional arguments to pass to the function
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds
        backoff_multiplier: Multiplier for backoff time after each retry
        max_backoff: Maximum backoff time in seconds
        retryable_errors: List of error types that should trigger a retry
        logger: Optional logger for logging retries and errors
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function call
        
    Raises:
        The last exception encountered if all retries fail
    """
    # Get configuration values, with function parameters taking precedence
    config = llm_config.get_all()
    max_retries = max_retries if max_retries is not None else config.get("MAX_RETRIES", 3)
    initial_backoff = initial_backoff if initial_backoff is not None else config.get("INITIAL_BACKOFF", 1.0)
    backoff_multiplier = backoff_multiplier if backoff_multiplier is not None else config.get("BACKOFF_MULTIPLIER", 2.0)
    max_backoff = max_backoff if max_backoff is not None else config.get("MAX_BACKOFF", 60.0)
    
    if retryable_errors is None:
        retryable_errors = [
            RateLimitError,
            APIConnectionError,
            ServiceUnavailableError,
            TimeoutError,
            ServerOverloadedError
        ]
    
    backoff = initial_backoff
    last_exception = None
    
    for retry in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            
            # Map to our standardized error types if it's not already one
            if not isinstance(e, LLMError):
                # Try to determine the provider from the function name or module
                provider = 'unknown'
                func_name = func.__name__ if hasattr(func, '__name__') else str(func)
                if 'openai' in func_name.lower():
                    provider = 'openai'
                elif 'litellm' in func_name.lower():
                    provider = 'litellm'
                elif 'anthropic' in func_name.lower():
                    provider = 'anthropic'
                
                mapped_error = map_provider_error(provider, e)
                last_exception = mapped_error
            
            # Check if this error type is retryable
            if not any(isinstance(last_exception, error_type) for error_type in retryable_errors):
                if logger:
                    logger.error(f"Non-retryable error: {last_exception}")
                    if hasattr(last_exception, 'traceback') and last_exception.traceback:
                        logger.debug(f"Error traceback: {last_exception.traceback}")
                raise last_exception
            
            # If we've exhausted our retries, raise the last exception
            if retry >= max_retries:
                if logger:
                    logger.error(f"Maximum retries ({max_retries}) reached. Last error: {last_exception}")
                    if hasattr(last_exception, 'traceback') and last_exception.traceback:
                        logger.debug(f"Error traceback: {last_exception.traceback}")
                raise last_exception
            
            # Log the retry
            if logger:
                logger.warning(f"Retry {retry+1}/{max_retries} after error: {last_exception}")
            
            # Wait before retrying with exponential backoff
            await asyncio.sleep(backoff)
            
            # Increase backoff for next retry, but don't exceed max_backoff
            backoff = min(backoff * backoff_multiplier, max_backoff)
    
    # This should never be reached due to the raise in the loop, but just in case
    raise last_exception if last_exception else RuntimeError("Unexpected error in retry logic")

def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error should be retried.
    
    Args:
        error: The error to check
        
    Returns:
        True if the error is retryable, False otherwise
    """
    retryable_errors = [
        RateLimitError,
        APIConnectionError,
        ServiceUnavailableError,
        TimeoutError,
        ServerOverloadedError
    ]
    
    return any(isinstance(error, error_type) for error_type in retryable_errors)

def get_error_context(error: Exception) -> Dict[str, Any]:
    """
    Get context information for an error.
    
    Args:
        error: The error to get context for
        
    Returns:
        Dictionary with error context information
    """
    context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "timestamp": time.time()
    }
    
    # Add original error information if available
    if isinstance(error, LLMError) and error.original_error:
        context["original_error_type"] = type(error.original_error).__name__
        context["original_error_message"] = str(error.original_error)
    
    # Add traceback if available
    if isinstance(error, LLMError) and error.traceback:
        context["traceback"] = error.traceback
    
    return context

class ErrorHandler:
    """
    Handler for LLM-related errors.
    
    This class provides methods for handling LLM-related errors,
    including error mapping, retry logic, and error reporting.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the error handler.
        
        Args:
            logger: Optional logger for logging errors
        """
        self.logger = logger
        self.error_counts: Dict[str, int] = {}
    
    def handle_error(self, error: Exception, provider: str = "unknown") -> LLMError:
        """
        Handle an LLM-related error.
        
        Args:
            error: The error to handle
            provider: The LLM provider
            
        Returns:
            A standardized LLMError instance
        """
        # Map to standardized error type
        if not isinstance(error, LLMError):
            mapped_error = map_provider_error(provider, error)
        else:
            mapped_error = error
        
        # Log the error
        if self.logger:
            self.logger.error(f"LLM error ({provider}): {mapped_error}")
            if hasattr(mapped_error, 'traceback') and mapped_error.traceback:
                self.logger.debug(f"Error traceback: {mapped_error.traceback}")
        
        # Track error counts
        error_type = type(mapped_error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        return mapped_error
    
    def get_error_stats(self) -> Dict[str, int]:
        """
        Get error statistics.
        
        Returns:
            Dictionary with error counts by type
        """
        return self.error_counts.copy()
    
    def reset_error_stats(self) -> None:
        """
        Reset error statistics.
        """
        self.error_counts.clear()

# Create a singleton instance
error_handler = ErrorHandler()
