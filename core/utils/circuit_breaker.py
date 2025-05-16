#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Circuit breaker utilities for WiseFlow.

This module provides a circuit breaker implementation to prevent cascading failures
when external services are unavailable or experiencing issues.
"""

import time
import functools
import asyncio
import threading
from typing import Dict, Any, Optional, Callable, Type, Union, List, TypeVar, cast

from core.utils.logging_config import logger, with_context
from core.utils.exceptions import WiseflowError

# Type variable for function return type
T = TypeVar('T')

class CircuitBreakerOpenError(WiseflowError):
    """Error raised when a circuit breaker is open."""
    
    def __init__(
        self,
        message: str,
        circuit_name: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a circuit breaker open error.
        
        Args:
            message: Error message
            circuit_name: Name of the circuit breaker
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        error_details["circuit_name"] = circuit_name
        
        super().__init__(message, error_details, cause)

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
    _lock = threading.RLock()
    
    @classmethod
    def get_instance(cls, name: str) -> 'CircuitBreaker':
        """
        Get a circuit breaker instance by name.
        
        Args:
            name: Circuit breaker name
            
        Returns:
            Circuit breaker instance
        """
        with cls._lock:
            if name not in cls._instances:
                cls._instances[name] = CircuitBreaker(name)
            return cls._instances[name]
    
    @classmethod
    def reset_all(cls) -> None:
        """Reset all circuit breakers to closed state."""
        with cls._lock:
            for instance in cls._instances.values():
                instance.reset()
    
    @classmethod
    def get_all_states(cls) -> Dict[str, str]:
        """
        Get the state of all circuit breakers.
        
        Returns:
            Dictionary mapping circuit breaker names to states
        """
        with cls._lock:
            return {name: instance.state for name, instance in cls._instances.items()}
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exceptions: Optional[List[Type[Exception]]] = None,
        half_open_max_calls: int = 1
    ):
        """
        Initialize a circuit breaker.
        
        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening the circuit
            recovery_timeout: Time in seconds before attempting recovery
            expected_exceptions: Exceptions that count as failures
            half_open_max_calls: Maximum number of calls allowed in half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions or [Exception]
        self.half_open_max_calls = half_open_max_calls
        
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0
        self._last_success_time = time.time()
        self._half_open_calls = 0
        self._lock = threading.RLock()
    
    @property
    def state(self) -> str:
        """Get the current state of the circuit breaker."""
        with self._lock:
            return self._state
    
    @property
    def failure_count(self) -> int:
        """Get the current failure count."""
        with self._lock:
            return self._failure_count
    
    @property
    def last_failure_time(self) -> float:
        """Get the time of the last failure."""
        with self._lock:
            return self._last_failure_time
    
    @property
    def last_success_time(self) -> float:
        """Get the time of the last success."""
        with self._lock:
            return self._last_success_time
    
    def reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._last_failure_time = 0
            self._last_success_time = time.time()
            self._half_open_calls = 0
            
            with_context(circuit=self.name).info(f"Circuit {self.name} reset to CLOSED state")
    
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
        with self._lock:
            if self._state == CircuitBreakerState.OPEN:
                # Check if recovery timeout has elapsed
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    with_context(circuit=self.name).info(
                        f"Circuit {self.name} transitioning from OPEN to HALF_OPEN"
                    )
                    self._state = CircuitBreakerState.HALF_OPEN
                    self._half_open_calls = 0
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit {self.name} is OPEN",
                        self.name,
                        {"state": self._state, "recovery_timeout": self.recovery_timeout}
                    )
            
            if self._state == CircuitBreakerState.HALF_OPEN:
                # Check if we've reached the maximum number of calls in half-open state
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerOpenError(
                        f"Circuit {self.name} is HALF_OPEN and at maximum calls",
                        self.name,
                        {"state": self._state, "half_open_calls": self._half_open_calls}
                    )
                
                self._half_open_calls += 1
    
    def _on_success(self) -> None:
        """Handle successful call."""
        with self._lock:
            self._last_success_time = time.time()
            
            if self._state == CircuitBreakerState.HALF_OPEN:
                with_context(circuit=self.name).info(
                    f"Circuit {self.name} transitioning from HALF_OPEN to CLOSED"
                )
                self._state = CircuitBreakerState.CLOSED
                self._failure_count = 0
                self._half_open_calls = 0
    
    def _on_failure(self, exception: Exception) -> None:
        """
        Handle failed call.
        
        Args:
            exception: Exception that occurred
        """
        with self._lock:
            self._last_failure_time = time.time()
            
            if self._state == CircuitBreakerState.CLOSED:
                self._failure_count += 1
                
                if self._failure_count >= self.failure_threshold:
                    with_context(
                        circuit=self.name,
                        failure_count=self._failure_count,
                        threshold=self.failure_threshold
                    ).warning(f"Circuit {self.name} transitioning from CLOSED to OPEN")
                    self._state = CircuitBreakerState.OPEN
            
            elif self._state == CircuitBreakerState.HALF_OPEN:
                with_context(circuit=self.name).warning(
                    f"Circuit {self.name} transitioning from HALF_OPEN to OPEN"
                )
                self._state = CircuitBreakerState.OPEN
                self._half_open_calls = 0

def with_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exceptions: Optional[List[Type[Exception]]] = None,
    half_open_max_calls: int = 1
) -> Callable:
    """
    Decorator for applying circuit breaker pattern to a function.
    
    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures before opening the circuit
        recovery_timeout: Time in seconds before attempting recovery
        expected_exceptions: Exceptions that count as failures
        half_open_max_calls: Maximum number of calls allowed in half-open state
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        circuit_breaker = CircuitBreaker.get_instance(name)
        circuit_breaker.failure_threshold = failure_threshold
        circuit_breaker.recovery_timeout = recovery_timeout
        circuit_breaker.half_open_max_calls = half_open_max_calls
        
        if expected_exceptions:
            circuit_breaker.expected_exceptions = expected_exceptions
        
        return circuit_breaker(func)
    
    return decorator

class CircuitBreakerContext:
    """Context manager for circuit breaker."""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exceptions: Optional[List[Type[Exception]]] = None
    ):
        """
        Initialize the circuit breaker context.
        
        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening the circuit
            recovery_timeout: Time in seconds before attempting recovery
            expected_exceptions: Exceptions that count as failures
        """
        self.circuit_breaker = CircuitBreaker.get_instance(name)
        self.circuit_breaker.failure_threshold = failure_threshold
        self.circuit_breaker.recovery_timeout = recovery_timeout
        
        if expected_exceptions:
            self.circuit_breaker.expected_exceptions = expected_exceptions
    
    def __enter__(self):
        """Enter the circuit breaker context."""
        self.circuit_breaker._before_call()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the circuit breaker context.
        
        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
            
        Returns:
            False to propagate the exception
        """
        if exc_type is None:
            # No exception, call was successful
            self.circuit_breaker._on_success()
        elif any(issubclass(exc_type, error_type) for error_type in self.circuit_breaker.expected_exceptions):
            # Exception is one we're monitoring
            self.circuit_breaker._on_failure(exc_val)
        
        # Always propagate the exception
        return False

