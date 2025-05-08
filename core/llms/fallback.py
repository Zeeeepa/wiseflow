"""
Fallback mechanism for LLM API calls.

This module provides a fallback mechanism for LLM API calls, allowing the system
to switch to alternative providers when the primary provider is unavailable.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Callable, Tuple, Union
import time
import functools

from core.llms.auth import get_auth_manager

logger = logging.getLogger(__name__)
auth_manager = get_auth_manager()

class CircuitBreaker:
    """
    Circuit breaker pattern implementation for API calls.
    
    This class implements the circuit breaker pattern to prevent cascading failures
    when an API service is unavailable. It tracks failures and temporarily disables
    calls to the service when a threshold is reached.
    """
    
    def __init__(self, name: str, failure_threshold: int = 5, reset_timeout: int = 60):
        """
        Initialize the circuit breaker.
        
        Args:
            name: Name of the service
            failure_threshold: Number of failures before opening the circuit
            reset_timeout: Time in seconds before attempting to close the circuit
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.state = "closed"  # closed, open, half-open
        self.last_failure_time = 0
    
    def record_failure(self):
        """Record a failure and update the circuit state."""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker for {self.name} is now OPEN")
    
    def record_success(self):
        """Record a success and reset the circuit."""
        self.failures = 0
        self.state = "closed"
    
    def can_execute(self) -> bool:
        """
        Check if the circuit allows execution.
        
        Returns:
            True if the circuit is closed or half-open, False if open
        """
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # Check if enough time has passed to try again
            if time.time() - self.last_failure_time >= self.reset_timeout:
                self.state = "half-open"
                logger.info(f"Circuit breaker for {self.name} is now HALF-OPEN")
                return True
            return False
        
        # Half-open state allows one request through
        return True

# Dictionary to store circuit breakers for different providers
circuit_breakers = {}

def get_circuit_breaker(provider: str) -> CircuitBreaker:
    """
    Get or create a circuit breaker for a provider.
    
    Args:
        provider: Provider name
        
    Returns:
        Circuit breaker instance
    """
    if provider not in circuit_breakers:
        circuit_breakers[provider] = CircuitBreaker(provider)
    return circuit_breakers[provider]

async def with_fallback(
    primary_func: Callable,
    fallback_funcs: List[Callable],
    *args,
    **kwargs
) -> Tuple[Any, str]:
    """
    Execute a function with fallbacks if it fails.
    
    Args:
        primary_func: Primary function to execute
        fallback_funcs: List of fallback functions to try if primary fails
        *args: Arguments to pass to the functions
        **kwargs: Keyword arguments to pass to the functions
        
    Returns:
        Tuple of (result, provider_used)
    """
    # Try primary function
    try:
        result = await primary_func(*args, **kwargs)
        return result, "primary"
    except Exception as e:
        logger.warning(f"Primary function failed: {str(e)}")
        
        # Try fallback functions in order
        for i, fallback_func in enumerate(fallback_funcs):
            try:
                result = await fallback_func(*args, **kwargs)
                logger.info(f"Used fallback {i+1}")
                return result, f"fallback_{i+1}"
            except Exception as e:
                logger.warning(f"Fallback {i+1} failed: {str(e)}")
        
        # If all fallbacks fail, re-raise the original exception
        logger.error("All fallbacks failed")
        raise

def with_circuit_breaker(provider: str):
    """
    Decorator to apply circuit breaker pattern to a function.
    
    Args:
        provider: Provider name
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            circuit_breaker = get_circuit_breaker(provider)
            
            if not circuit_breaker.can_execute():
                # Circuit is open, try to use fallback
                fallback_provider = auth_manager.get_fallback_provider(provider)
                if fallback_provider:
                    logger.info(f"Circuit open for {provider}, using fallback: {fallback_provider}")
                    # This would need to be implemented to actually use the fallback
                    # For now, we'll just raise an exception
                    raise Exception(f"Service {provider} is unavailable (circuit open)")
                else:
                    raise Exception(f"Service {provider} is unavailable (circuit open) and no fallback is available")
            
            try:
                result = await func(*args, **kwargs)
                
                # If we're in half-open state and the call succeeded, close the circuit
                if circuit_breaker.state == "half-open":
                    circuit_breaker.record_success()
                
                return result
            except Exception as e:
                circuit_breaker.record_failure()
                raise
        
        return wrapper
    
    return decorator

