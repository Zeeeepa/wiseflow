"""
Error handling utilities for LLM interactions.

This module provides standardized error handling for LLM API calls,
including retry logic, error classification, and logging.
"""

import asyncio
import time
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, Awaitable

# Define a type variable for the return type of the wrapped function
T = TypeVar('T')

class LLMError(Exception):
    """Base exception class for LLM-related errors."""
    pass

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
            return RateLimitError(f"Rate limit exceeded: {error_str}")
        elif 'authentication' in error_str.lower() or error_type == 'AuthenticationError':
            return AuthenticationError(f"Authentication failed: {error_str}")
        elif 'invalid' in error_str.lower() or error_type == 'InvalidRequestError':
            return InvalidRequestError(f"Invalid request: {error_str}")
        elif 'connection' in error_str.lower() or error_type == 'APIConnectionError':
            return APIConnectionError(f"API connection error: {error_str}")
        elif 'unavailable' in error_str.lower() or error_type == 'ServiceUnavailableError':
            return ServiceUnavailableError(f"Service unavailable: {error_str}")
        elif 'not found' in error_str.lower() and 'model' in error_str.lower():
            return ModelNotFoundError(f"Model not found: {error_str}")
        elif 'context length' in error_str.lower() or 'token limit' in error_str.lower():
            return ContextLengthExceededError(f"Context length exceeded: {error_str}")
        elif 'content filter' in error_str.lower() or 'content policy' in error_str.lower():
            return ContentFilterError(f"Content filtered: {error_str}")
    
    # LiteLLM error mapping
    elif provider == 'litellm':
        if 'rate limit' in error_str.lower():
            return RateLimitError(f"Rate limit exceeded: {error_str}")
        elif 'authentication' in error_str.lower() or 'auth' in error_str.lower():
            return AuthenticationError(f"Authentication failed: {error_str}")
        elif 'invalid' in error_str.lower():
            return InvalidRequestError(f"Invalid request: {error_str}")
        elif 'connection' in error_str.lower() or 'timeout' in error_str.lower():
            return APIConnectionError(f"API connection error: {error_str}")
        elif 'unavailable' in error_str.lower() or 'server error' in error_str.lower():
            return ServiceUnavailableError(f"Service unavailable: {error_str}")
        elif 'not found' in error_str.lower() and 'model' in error_str.lower():
            return ModelNotFoundError(f"Model not found: {error_str}")
        elif 'context length' in error_str.lower() or 'token limit' in error_str.lower():
            return ContextLengthExceededError(f"Context length exceeded: {error_str}")
        elif 'content filter' in error_str.lower() or 'content policy' in error_str.lower():
            return ContentFilterError(f"Content filtered: {error_str}")
    
    # Default to UnknownLLMError for unrecognized errors
    return UnknownLLMError(f"Unknown error ({provider}): {error_str}")

async def with_retries(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    max_retries: int = 3,
    initial_backoff: float = 1.0,
    backoff_multiplier: float = 2.0,
    max_backoff: float = 60.0,
    retryable_errors: List[type] = None,
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
    if retryable_errors is None:
        retryable_errors = [
            RateLimitError,
            APIConnectionError,
            ServiceUnavailableError
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
                
                mapped_error = map_provider_error(provider, e)
                last_exception = mapped_error
            
            # Check if this error type is retryable
            if not any(isinstance(last_exception, error_type) for error_type in retryable_errors):
                if logger:
                    logger.error(f"Non-retryable error: {last_exception}")
                raise last_exception
            
            # If we've exhausted our retries, raise the last exception
            if retry >= max_retries:
                if logger:
                    logger.error(f"Maximum retries ({max_retries}) reached. Last error: {last_exception}")
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
        ServiceUnavailableError
    ]
    
    return any(isinstance(error, error_type) for error_type in retryable_errors)

