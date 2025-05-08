"""
Utility functions for LLM integration.

This module provides utility functions for LLM integration, including
retry logic, rate limiting, and error handling.
"""

import time
import asyncio
import logging
from typing import TypeVar, Callable, Any, Dict, Optional, List, Union, Awaitable
import random
from functools import wraps
from datetime import datetime, timedelta

from .exceptions import (
    LLMException, NetworkException, AuthenticationException, RateLimitException,
    TimeoutException, ContentFilterException, ContextLengthException,
    InvalidRequestException, ServiceUnavailableException, QuotaExceededException,
    UnknownException
)

logger = logging.getLogger(__name__)

# Type variable for generic function
T = TypeVar('T')


class RateLimiter:
    """
    Rate limiter for LLM API calls.
    
    This class implements a token bucket algorithm for rate limiting.
    """
    
    def __init__(self, tokens_per_second: float, max_tokens: int):
        """
        Initialize the rate limiter.
        
        Args:
            tokens_per_second: Rate at which tokens are added to the bucket
            max_tokens: Maximum number of tokens the bucket can hold
        """
        self.tokens_per_second = tokens_per_second
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.last_update = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            float: Time to wait before the requested tokens are available
            
        Raises:
            ValueError: If requested tokens exceed max_tokens
        """
        if tokens > self.max_tokens:
            raise ValueError(f"Requested tokens ({tokens}) exceed maximum ({self.max_tokens})")
        
        async with self.lock:
            # Update tokens based on elapsed time
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.max_tokens, self.tokens + elapsed * self.tokens_per_second)
            self.last_update = now
            
            # Calculate wait time if not enough tokens
            if tokens > self.tokens:
                wait_time = (tokens - self.tokens) / self.tokens_per_second
                return wait_time
            
            # Consume tokens
            self.tokens -= tokens
            return 0
    
    async def wait(self, tokens: int = 1) -> None:
        """
        Wait until the requested tokens are available.
        
        Args:
            tokens: Number of tokens to acquire
        """
        wait_time = await self.acquire(tokens)
        if wait_time > 0:
            await asyncio.sleep(wait_time)


def map_exception(exception: Exception) -> LLMException:
    """
    Map a provider-specific exception to a custom LLM exception.
    
    Args:
        exception: The original exception
        
    Returns:
        LLMException: The mapped exception
    """
    error_msg = str(exception)
    error_type = type(exception).__name__
    details = {"original_exception": error_type}
    
    # Check for network errors
    if any(term in error_msg.lower() for term in ["connection", "network", "socket", "connection reset", "eof"]):
        return NetworkException("Network error occurred", details)
    
    # Check for authentication errors
    if any(term in error_msg.lower() for term in ["authentication", "auth", "key", "unauthorized", "permission", "401"]):
        return AuthenticationException("Authentication error", details)
    
    # Check for rate limit errors
    if any(term in error_msg.lower() for term in ["rate limit", "ratelimit", "too many requests", "429"]):
        retry_after = None
        if hasattr(exception, "retry_after"):
            retry_after = exception.retry_after
        return RateLimitException("Rate limit exceeded", details, retry_after)
    
    # Check for timeout errors
    if any(term in error_msg.lower() for term in ["timeout", "timed out"]):
        return TimeoutException("Request timed out", details)
    
    # Check for content filter errors
    if any(term in error_msg.lower() for term in ["content", "policy", "filter", "moderation"]):
        return ContentFilterException("Content filter triggered", details)
    
    # Check for context length errors
    if any(term in error_msg.lower() for term in ["context", "length", "token", "too long"]):
        return ContextLengthException("Context length exceeded", details)
    
    # Check for invalid request errors
    if any(term in error_msg.lower() for term in ["invalid", "malformed", "bad request", "400"]):
        return InvalidRequestException("Invalid request", details)
    
    # Check for service unavailable errors
    if any(term in error_msg.lower() for term in ["unavailable", "server", "down", "503", "502"]):
        return ServiceUnavailableException("Service unavailable", details)
    
    # Check for quota exceeded errors
    if any(term in error_msg.lower() for term in ["quota", "limit", "exceeded", "usage"]):
        return QuotaExceededException("Quota exceeded", details)
    
    # Default to unknown exception
    return UnknownException(f"Unknown error: {error_msg}", details)


def is_transient_error(exception: LLMException) -> bool:
    """
    Determine if an exception is transient and should be retried.
    
    Args:
        exception: The exception to check
        
    Returns:
        bool: True if the exception is transient, False otherwise
    """
    # These error types are considered transient and should be retried
    transient_types = (
        NetworkException,
        RateLimitException,
        TimeoutException,
        ServiceUnavailableException
    )
    
    return isinstance(exception, transient_types)


async def with_retry(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    logger: Optional[logging.Logger] = None,
    **kwargs: Any
) -> T:
    """
    Execute a function with retry logic.
    
    Args:
        func: The function to execute
        *args: Positional arguments to pass to the function
        max_retries: Maximum number of retries
        base_delay: Base delay between retries (in seconds)
        max_delay: Maximum delay between retries (in seconds)
        jitter: Whether to add jitter to the delay
        logger: Logger for logging retry attempts
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function
        
    Raises:
        LLMException: If all retries fail
    """
    logger = logger or logging.getLogger(__name__)
    
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Map the exception to a custom LLM exception
            llm_exception = e if isinstance(e, LLMException) else map_exception(e)
            
            # Check if we should retry
            if attempt < max_retries and is_transient_error(llm_exception):
                # Calculate delay with exponential backoff
                delay = min(base_delay * (2 ** attempt), max_delay)
                
                # Add jitter if enabled
                if jitter:
                    delay = delay * (0.5 + random.random())
                
                # If it's a rate limit exception with retry_after, use that instead
                if isinstance(llm_exception, RateLimitException) and llm_exception.retry_after:
                    delay = llm_exception.retry_after
                
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed with error: {llm_exception}. "
                    f"Retrying in {delay:.2f} seconds..."
                )
                
                await asyncio.sleep(delay)
            else:
                # If we've exhausted retries or it's not a transient error, raise the exception
                if attempt == max_retries:
                    logger.error(f"All {max_retries + 1} attempts failed. Last error: {llm_exception}")
                else:
                    logger.error(f"Non-transient error occurred: {llm_exception}. Not retrying.")
                
                raise llm_exception
    
    # This should never be reached due to the raise in the loop
    raise UnknownException("Unexpected error in retry logic")


def with_timeout(timeout: float):
    """
    Decorator to add timeout to an async function.
    
    Args:
        timeout: Timeout in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            except asyncio.TimeoutError:
                raise TimeoutException(f"Operation timed out after {timeout} seconds")
        return wrapper
    return decorator

