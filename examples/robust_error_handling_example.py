#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example usage of the WiseFlow robust error handling and recovery system.

This file demonstrates how to use the error handling middleware, circuit breakers,
retry mechanisms, and error reporting in WiseFlow.
"""

import asyncio
import random
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.responses import JSONResponse

from core.middleware import (
    ErrorHandlingMiddleware,
    add_error_handling_middleware,
    CircuitBreaker,
    circuit_breaker,
    RetryWithBackoff,
    retry_with_backoff,
    with_error_handling,
    ErrorSeverity,
    ErrorCategory
)
from core.utils.error_handling import (
    WiseflowError,
    ConnectionError,
    DataProcessingError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    log_error
)
from core.utils.recovery_strategies import (
    RetryStrategy,
    FallbackStrategy,
    CacheStrategy,
    CompositeStrategy,
    with_retry,
    with_fallback,
    with_cache,
    with_composite_recovery
)
from core.utils.error_logging import (
    ErrorReport,
    report_error,
    get_error_statistics,
    clear_error_statistics
)
from core.utils.logging_config import logger, with_context

# Example 1: Using error handling middleware with FastAPI
app = FastAPI(title="Error Handling Example")

# Add error handling middleware
add_error_handling_middleware(
    app,
    log_errors=True,
    include_traceback=True,
    save_to_file=True
)

@app.get("/api/example/success")
async def success_endpoint():
    """Example endpoint that succeeds."""
    return {"status": "success", "message": "Operation completed successfully"}

@app.get("/api/example/error")
async def error_endpoint():
    """Example endpoint that raises an error."""
    # Simulate an error
    if random.random() < 0.8:
        raise DataProcessingError(
            "Failed to process data",
            details={"reason": "Simulated error", "timestamp": datetime.now().isoformat()}
        )
    
    return {"status": "success", "message": "Operation completed successfully"}

@app.get("/api/example/validation-error")
async def validation_error_endpoint(value: str = None):
    """Example endpoint that raises a validation error."""
    if not value:
        raise ValidationError(
            "Missing required parameter",
            details={"field": "value", "reason": "Value cannot be empty"}
        )
    
    return {"status": "success", "value": value}

@app.get("/api/example/auth-error")
async def auth_error_endpoint(token: str = None):
    """Example endpoint that raises an authentication error."""
    if not token or token != "valid-token":
        raise AuthenticationError(
            "Invalid authentication token",
            details={"reason": "Token is missing or invalid"}
        )
    
    return {"status": "success", "message": "Authenticated successfully"}

# Example 2: Using circuit breaker pattern
class ExternalService:
    """Example external service that might fail."""
    
    def __init__(self, failure_rate: float = 0.5):
        """
        Initialize the external service.
        
        Args:
            failure_rate: Probability of failure (0.0 to 1.0)
        """
        self.failure_rate = failure_rate
        self.call_count = 0
    
    async def call_api(self, endpoint: str) -> Dict[str, Any]:
        """
        Call an API endpoint.
        
        Args:
            endpoint: API endpoint to call
            
        Returns:
            API response
            
        Raises:
            ConnectionError: If the API call fails
        """
        self.call_count += 1
        
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        # Simulate failure
        if random.random() < self.failure_rate:
            raise ConnectionError(
                f"Failed to call API endpoint: {endpoint}",
                details={"endpoint": endpoint, "attempt": self.call_count}
            )
        
        # Successful response
        return {
            "status": "success",
            "endpoint": endpoint,
            "data": {"value": random.randint(1, 100)},
            "timestamp": datetime.now().isoformat()
        }

# Create an instance of the external service
external_service = ExternalService(failure_rate=0.7)

# Example of using circuit breaker decorator
@circuit_breaker(
    failure_threshold=3,
    recovery_timeout=5.0,
    timeout=1.0,
    fallback=lambda endpoint: {"status": "fallback", "endpoint": endpoint, "timestamp": datetime.now().isoformat()}
)
async def call_external_api_with_circuit_breaker(endpoint: str) -> Dict[str, Any]:
    """
    Call an external API with circuit breaker protection.
    
    Args:
        endpoint: API endpoint to call
        
    Returns:
        API response
    """
    return await external_service.call_api(endpoint)

# Example 3: Using retry with backoff
@retry_with_backoff(
    max_retries=3,
    initial_backoff=0.5,
    backoff_multiplier=2.0,
    max_backoff=5.0,
    jitter=True
)
async def call_external_api_with_retry(endpoint: str) -> Dict[str, Any]:
    """
    Call an external API with retry logic.
    
    Args:
        endpoint: API endpoint to call
        
    Returns:
        API response
    """
    return await external_service.call_api(endpoint)

# Example 4: Using error handling decorator
@with_error_handling(
    error_types=[ConnectionError, TimeoutError],
    severity=ErrorSeverity.ERROR,
    category=ErrorCategory.EXTERNAL_SERVICE,
    include_context=True,
    save_to_file=True,
    reraise=True
)
async def call_external_api_with_error_handling(endpoint: str) -> Dict[str, Any]:
    """
    Call an external API with error handling.
    
    Args:
        endpoint: API endpoint to call
        
    Returns:
        API response
    """
    return await external_service.call_api(endpoint)

# Example 5: Using recovery strategies
async def fallback_function(endpoint: str) -> Dict[str, Any]:
    """
    Fallback function for external API calls.
    
    Args:
        endpoint: API endpoint to call
        
    Returns:
        Fallback response
    """
    return {
        "status": "fallback",
        "endpoint": endpoint,
        "message": "Using fallback response",
        "timestamp": datetime.now().isoformat()
    }

# Create recovery strategies
retry_strategy = RetryStrategy(
    max_retries=3,
    initial_backoff=0.5,
    backoff_multiplier=2.0,
    max_backoff=5.0,
    jitter=True
)

fallback_strategy = FallbackStrategy(
    fallback_func=fallback_function,
    handled_exceptions=[ConnectionError, TimeoutError]
)

# Create a cache for the cache strategy
api_cache = {}

cache_strategy = CacheStrategy(
    cache=api_cache,
    ttl=datetime.timedelta(minutes=5),
    handled_exceptions=[ConnectionError, TimeoutError]
)

# Create a composite strategy
composite_strategy = CompositeStrategy([
    retry_strategy,
    cache_strategy,
    fallback_strategy
])

# Example of using composite recovery strategy
@with_composite_recovery(composite_strategy)
async def call_external_api_with_composite_recovery(endpoint: str) -> Dict[str, Any]:
    """
    Call an external API with composite recovery strategy.
    
    Args:
        endpoint: API endpoint to call
        
    Returns:
        API response
    """
    return await external_service.call_api(endpoint)

# Example 6: Error reporting
def simulate_error_for_reporting():
    """Simulate an error and report it."""
    try:
        # Simulate an error
        if random.random() < 0.5:
            raise ValueError("Simulated error for reporting")
        else:
            raise ConnectionError(
                "Failed to connect to service",
                details={"service": "example", "reason": "Simulated error"}
            )
    except Exception as e:
        # Report the error
        error_context = {
            "function": "simulate_error_for_reporting",
            "timestamp": datetime.now().isoformat()
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.APPLICATION,
            context=error_context,
            save_to_file=True
        )
        
        # Re-raise the error
        raise

# Main function to run all examples
async def main():
    """Run all examples."""
    logger.info("Starting robust error handling examples")
    
    # Example 2: Circuit breaker pattern
    logger.info("Example 2: Circuit breaker pattern")
    
    for i in range(10):
        try:
            result = await call_external_api_with_circuit_breaker(f"/api/endpoint/{i}")
            logger.info(f"Circuit breaker example {i}: {result}")
        except Exception as e:
            logger.error(f"Circuit breaker example {i} failed: {e}")
        
        # Wait a bit between calls
        await asyncio.sleep(0.5)
    
    # Example 3: Retry with backoff
    logger.info("Example 3: Retry with backoff")
    
    for i in range(5):
        try:
            result = await call_external_api_with_retry(f"/api/endpoint/{i}")
            logger.info(f"Retry example {i}: {result}")
        except Exception as e:
            logger.error(f"Retry example {i} failed: {e}")
    
    # Example 4: Error handling decorator
    logger.info("Example 4: Error handling decorator")
    
    for i in range(5):
        try:
            result = await call_external_api_with_error_handling(f"/api/endpoint/{i}")
            logger.info(f"Error handling example {i}: {result}")
        except Exception as e:
            logger.error(f"Error handling example {i} failed: {e}")
    
    # Example 5: Recovery strategies
    logger.info("Example 5: Recovery strategies")
    
    for i in range(5):
        try:
            result = await call_external_api_with_composite_recovery(f"/api/endpoint/{i}")
            logger.info(f"Composite recovery example {i}: {result}")
        except Exception as e:
            logger.error(f"Composite recovery example {i} failed: {e}")
    
    # Example 6: Error reporting
    logger.info("Example 6: Error reporting")
    
    for i in range(5):
        try:
            simulate_error_for_reporting()
            logger.info(f"Error reporting example {i}: success")
        except Exception as e:
            logger.error(f"Error reporting example {i}: {e}")
    
    # Get error statistics
    error_stats = get_error_statistics()
    logger.info(f"Error statistics: {error_stats}")
    
    # Clear error statistics
    clear_error_statistics()
    
    logger.info("Finished robust error handling examples")

# Run the examples
if __name__ == "__main__":
    asyncio.run(main())

