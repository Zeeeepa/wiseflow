"""
Recovery strategies for WiseFlow.

This module provides recovery strategies for handling failures in the WiseFlow system.

Recovery strategies are essential components that enable robust error handling and
fault tolerance throughout the application. This module implements various strategies:

- RetryStrategy: Retries failed operations with configurable backoff
- FallbackStrategy: Provides alternative implementations when primary ones fail
- CacheStrategy: Uses cached results when operations fail
- CompositeStrategy: Combines multiple strategies for comprehensive recovery
- CircuitBreakerStrategy: Prevents cascading failures by temporarily disabling failing operations

The module also provides decorators for easy application of these strategies:
- with_retries: Applies retry logic to functions
- with_fallback: Provides alternative implementations
- with_cache: Uses cached results when available
- with_composite_recovery: Combines multiple strategies

These strategies are used throughout WiseFlow to ensure reliable operation
even in the presence of external service failures, network issues, or other errors.
"""

import asyncio
import logging
import time
import random
from typing import Dict, Any, Optional, Callable, List, Union, Type, TypeVar, cast, Tuple
from functools import wraps
from datetime import datetime, timedelta

from core.utils.error_handling import (
    WiseflowError,
    ConnectionError,
    DataProcessingError,
    log_error,
    save_error_to_file
)
from core.utils.logging_config import logger, with_context

# Type variable for function return type
T = TypeVar('T')

class RecoveryStrategy:
    """
    Base class for recovery strategies.
    
    This abstract class defines the interface for all recovery strategies.
    Concrete implementations should override the execute method to provide
    specific recovery behavior.
    
    Relationships:
    - Extended by specific strategy implementations like RetryStrategy
    - Used by recovery decorators to apply recovery logic to functions
    """
    
    async def execute(self, func, *args, **kwargs):
        """
        Execute a function with recovery strategy.
        
        Args:
            func: The function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            The result of the function
            
        Raises:
            Exception: If recovery fails
        """
        raise NotImplementedError("Subclasses must implement execute method")

class RetryStrategy(RecoveryStrategy):
    """
    Retry strategy for handling transient failures.
    
    This strategy retries the operation with exponential backoff.
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
        Initialize the retry strategy.
        
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
    
    async def execute(self, func, *args, **kwargs):
        """
        Execute a function with retry strategy.
        
        Args:
            func: The function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            The result of the function
            
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
                    jitter_amount = backoff * random.random()
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

class FallbackStrategy(RecoveryStrategy):
    """
    Fallback strategy for handling failures.
    
    This strategy uses a fallback function when the primary function fails.
    """
    
    def __init__(
        self,
        fallback_func: Callable,
        handled_exceptions: Optional[List[Type[Exception]]] = None
    ):
        """
        Initialize the fallback strategy.
        
        Args:
            fallback_func: Fallback function to call when the primary function fails
            handled_exceptions: Exceptions that should trigger the fallback
        """
        self.fallback_func = fallback_func
        self.handled_exceptions = handled_exceptions or [Exception]
    
    async def execute(self, func, *args, **kwargs):
        """
        Execute a function with fallback strategy.
        
        Args:
            func: The function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            The result of the function or fallback
            
        Raises:
            Exception: If both primary and fallback fail
        """
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                # For synchronous functions, run in executor
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, func, *args, **kwargs)
        
        except Exception as e:
            # Check if this exception should trigger the fallback
            if not any(isinstance(e, exc_type) for exc_type in self.handled_exceptions):
                # Not handled by this strategy, re-raise
                raise
            
            logger.info(f"Primary function failed with error: {str(e)}. Using fallback.")
            
            # Call fallback function
            if asyncio.iscoroutinefunction(self.fallback_func):
                return await self.fallback_func(*args, **kwargs)
            else:
                # For synchronous functions, run in executor
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, self.fallback_func, *args, **kwargs)

class CacheStrategy(RecoveryStrategy):
    """
    Cache strategy for handling failures.
    
    This strategy uses cached results when the function fails.
    
    NOTE: This strategy is currently not actively used in the main codebase.
    It's provided as an advanced recovery option for specific use cases where
    returning stale data is preferable to failing completely. Consider using
    a dedicated caching solution for production use cases that require robust caching.
    
    Example use case:
    - When calling external APIs that might be temporarily unavailable
    - When performing expensive computations that can be reused
    
    See the `with_cache` decorator for usage examples.
    """
    
    def __init__(
        self,
        cache: Dict[Tuple, Tuple[Any, datetime]],
        ttl: timedelta = timedelta(minutes=5),
        handled_exceptions: Optional[List[Type[Exception]]] = None
    ):
        """
        Initialize the cache strategy.
        
        Args:
            cache: Cache dictionary mapping (func, args, kwargs) to (result, timestamp)
            ttl: Time-to-live for cached results
            handled_exceptions: Exceptions that should trigger using the cache
        """
        self.cache = cache
        self.ttl = ttl
        self.handled_exceptions = handled_exceptions or [Exception]
    
    async def execute(self, func, *args, **kwargs):
        """
        Execute a function with cache strategy.
        
        Args:
            func: The function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            The result of the function or cached result
            
        Raises:
            Exception: If function fails and no valid cache exists
        """
        # Create a cache key from the function and arguments
        # We need to make sure the key is hashable
        cache_key = (
            func.__qualname__,
            tuple(args),
            tuple(sorted((k, str(v)) for k, v in kwargs.items()))
        )
        
        try:
            # Try to execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                # For synchronous functions, run in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, func, *args, **kwargs)
            
            # Update the cache with the new result
            self.cache[cache_key] = (result, datetime.now())
            
            return result
        
        except Exception as e:
            # Check if this exception should trigger using the cache
            if not any(isinstance(e, exc_type) for exc_type in self.handled_exceptions):
                # Not handled by this strategy, re-raise
                raise
            
            # Check if we have a valid cached result
            if cache_key in self.cache:
                result, timestamp = self.cache[cache_key]
                
                # Check if the cached result is still valid
                if datetime.now() - timestamp <= self.ttl:
                    logger.info(f"Function failed with error: {str(e)}. Using cached result from {timestamp}.")
                    return result
            
            # No valid cache, re-raise the exception
            logger.warning(f"Function failed and no valid cache exists. Error: {str(e)}")
            raise

class CompositeStrategy(RecoveryStrategy):
    """
    Composite strategy for combining multiple recovery strategies.
    
    This strategy applies multiple recovery strategies in sequence.
    
    NOTE: This strategy is currently not actively used in the main codebase.
    It's provided as an advanced recovery option for complex scenarios where
    multiple recovery strategies need to be combined. Consider using simpler
    strategies for most use cases.
    
    Example use case:
    - When you need to apply both retry and fallback strategies
    - When you need to apply both cache and retry strategies
    
    See the `with_composite_recovery` decorator for usage examples.
    """
    
    def __init__(self, strategies: List[RecoveryStrategy]):
        """
        Initialize the composite strategy.
        
        Args:
            strategies: List of recovery strategies to apply
        """
        self.strategies = strategies
    
    async def execute(self, func, *args, **kwargs):
        """
        Execute a function with composite strategy.
        
        Args:
            func: The function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            The result of the function
            
        Raises:
            Exception: If all strategies fail
        """
        # Apply each strategy in sequence
        current_func = func
        
        for strategy in self.strategies:
            # Wrap the current function with the strategy
            wrapped_func = lambda *a, **kw: strategy.execute(current_func, *a, **kw)
            current_func = wrapped_func
        
        # Execute the wrapped function
        return await current_func(*args, **kwargs)

def with_recovery(strategy: RecoveryStrategy):
    """
    Decorator for applying a recovery strategy to a function.
    
    Args:
        strategy: Recovery strategy to apply
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await strategy.execute(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(strategy.execute(func, *args, **kwargs))
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def with_retry(
    max_retries: int = 3,
    initial_backoff: float = 1.0,
    backoff_multiplier: float = 2.0,
    max_backoff: float = 60.0,
    jitter: bool = True,
    retryable_exceptions: Optional[List[Type[Exception]]] = None
):
    """
    Decorator for applying retry strategy to a function.
    
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
    strategy = RetryStrategy(
        max_retries=max_retries,
        initial_backoff=initial_backoff,
        backoff_multiplier=backoff_multiplier,
        max_backoff=max_backoff,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions
    )
    
    return with_recovery(strategy)

def with_fallback(
    fallback_func: Callable,
    handled_exceptions: Optional[List[Type[Exception]]] = None
):
    """
    Decorator for applying fallback strategy to a function.
    
    Args:
        fallback_func: Fallback function to call when the primary function fails
        handled_exceptions: Exceptions that should trigger the fallback
        
    Returns:
        Decorator function
    """
    strategy = FallbackStrategy(
        fallback_func=fallback_func,
        handled_exceptions=handled_exceptions
    )
    
    return with_recovery(strategy)

def with_cache(
    cache: Dict[Tuple, Tuple[Any, datetime]],
    ttl: timedelta = timedelta(minutes=5),
    handled_exceptions: Optional[List[Type[Exception]]] = None
):
    """
    Decorator for applying cache strategy to a function.
    
    NOTE: This decorator is currently not actively used in the main codebase.
    It's provided as an advanced recovery option for specific use cases where
    returning stale data is preferable to failing completely.
    
    Example usage:
    ```python
    # Create a cache dictionary
    my_cache = {}
    
    # Apply the cache decorator to a function
    @with_cache(cache=my_cache, ttl=timedelta(minutes=10))
    async def fetch_external_data(url):
        # Fetch data from external API
        response = await httpx.get(url)
        return response.json()
    ```
    
    Args:
        cache: Cache dictionary mapping (func, args, kwargs) to (result, timestamp)
        ttl: Time-to-live for cached results
        handled_exceptions: Exceptions that should trigger using the cache
        
    Returns:
        Decorator function
    """
    strategy = CacheStrategy(
        cache=cache,
        ttl=ttl,
        handled_exceptions=handled_exceptions
    )
    
    return with_recovery(strategy)

def with_composite_recovery(strategies: List[RecoveryStrategy]):
    """
    Decorator for applying composite recovery strategy to a function.
    
    NOTE: This decorator is currently not actively used in the main codebase.
    It's provided as an advanced recovery option for complex scenarios where
    multiple recovery strategies need to be combined.
    
    Example usage:
    ```python
    # Create a cache dictionary
    my_cache = {}
    
    # Create individual strategies
    retry_strategy = RetryStrategy(max_retries=3)
    cache_strategy = CacheStrategy(cache=my_cache)
    
    # Apply the composite strategy to a function
    @with_composite_recovery(strategies=[retry_strategy, cache_strategy])
    async def fetch_external_data(url):
        # Fetch data from external API
        response = await httpx.get(url)
        return response.json()
    ```
    
    Args:
        strategies: List of recovery strategies to apply
        
    Returns:
        Decorator function
    """
    strategy = CompositeStrategy(strategies=strategies)
    
    return with_recovery(strategy)
