#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example usage of the WiseFlow error handling and logging system.

This file demonstrates how to use the enhanced error handling and logging system in WiseFlow.
"""

import asyncio
import random
import time
import requests
from typing import Dict, List, Any, Optional

# Import logging and error handling utilities
from core.utils.logging_config import logger, get_logger, with_context, LogContext
from core.utils.enhanced_logging import (
    log_api_request, log_task_execution, log_data_processing,
    log_function_call, RequestContext
)
from core.utils.error_handling import (
    WiseflowError,
    handle_exceptions,
    ErrorHandler,
    async_error_handler,
    log_error
)
from core.utils.exceptions import (
    ValidationError,
    DataProcessingError,
    ConnectionError,
    APIError,
    TimeoutError,
    RateLimitError,
    NotFoundError
)
from core.utils.retry import retry, RetryContext, retry_async, retry_sync
from core.utils.circuit_breaker import with_circuit_breaker, CircuitBreakerContext

# Get a module-specific logger
module_logger = get_logger(__name__)

# Example 1: Basic logging
def basic_logging_example():
    """Demonstrate basic logging functionality."""
    module_logger.info("Starting basic logging example")
    
    module_logger.debug("This is a debug message")
    module_logger.info("This is an info message")
    module_logger.success("This is a success message")
    module_logger.warning("This is a warning message")
    module_logger.error("This is an error message")
    module_logger.critical("This is a critical message")
    
    module_logger.info("Finished basic logging example")

# Example 2: Contextual logging
def contextual_logging_example(user_id: str, action: str):
    """
    Demonstrate contextual logging.
    
    Args:
        user_id: User ID for context
        action: Action being performed
    """
    module_logger.info("Starting contextual logging example")
    
    # Add context to logger
    user_logger = with_context(user_id=user_id, action=action)
    
    user_logger.info("User action started")
    
    # Use context manager for temporary context
    with LogContext(request_id="req-123", endpoint="/api/data"):
        logger.info("Processing request")
        logger.debug("Request details: ...")
        logger.success("Request processed successfully")
    
    # Use request context
    with RequestContext(user_id=user_id, request_id="req-456"):
        logger.info("Processing request with request context")
        
        # Nested function calls will inherit the context
        def nested_function():
            logger.info("Inside nested function")
        
        nested_function()
    
    user_logger.success("User action completed")
    
    module_logger.info("Finished contextual logging example")

# Example 3: Error handling with decorator
@handle_exceptions(
    error_types=[ValueError, ValidationError],
    default_message="Error validating user data",
    log_error=True,
    default_return=False
)
def validate_user_data(data: Dict[str, Any]) -> bool:
    """
    Validate user data with error handling.
    
    Args:
        data: User data to validate
        
    Returns:
        True if data is valid, False otherwise
    """
    if not isinstance(data, dict):
        raise TypeError("Data must be a dictionary")
    
    if "name" not in data:
        raise ValidationError("Name is required", field="name")
    
    if "age" in data and not isinstance(data["age"], int):
        raise ValidationError("Age must be an integer", field="age", value=data["age"])
    
    if "email" in data and "@" not in data["email"]:
        raise ValidationError("Invalid email format", field="email", value=data["email"])
    
    return True

# Example 4: Error handling with context manager
def process_payment(payment_id: str, amount: float) -> Dict[str, Any]:
    """
    Process a payment with error handling using context manager.
    
    Args:
        payment_id: Payment ID
        amount: Payment amount
        
    Returns:
        Payment result
    """
    module_logger.info(f"Processing payment {payment_id} for {amount}")
    
    with ErrorHandler(
        error_types=[ConnectionError, ValueError],
        default={"status": "failed", "reason": "Payment processing error"},
        context={"payment_id": payment_id, "amount": amount}
    ) as handler:
        # Simulate payment processing
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if random.random() < 0.3:
            raise ConnectionError("Payment gateway connection failed", {"gateway": "example"})
        
        # Successful payment
        return {
            "status": "success",
            "payment_id": payment_id,
            "amount": amount,
            "timestamp": time.time()
        }
    
    if handler.error_occurred:
        module_logger.warning(f"Payment {payment_id} failed: {handler.error}")
    
    return handler.result

# Example 5: Async error handling
async def fetch_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Fetch a user profile with async error handling.
    
    Args:
        user_id: User ID
        
    Returns:
        User profile data
    """
    module_logger.info(f"Fetching profile for user {user_id}")
    
    # Simulate API call
    async def api_call():
        await asyncio.sleep(0.5)
        if random.random() < 0.3:
            raise ConnectionError("API connection failed", {"endpoint": "/users"})
        return {"id": user_id, "name": "Example User", "email": "user@example.com"}
    
    # Use async error handler
    result = await async_error_handler(
        api_call(),
        error_types=[ConnectionError, TimeoutError],
        default={"id": user_id, "error": "Failed to fetch profile"},
        context={"user_id": user_id, "operation": "fetch_profile"}
    )
    
    return result

# Example 6: Retry mechanism
@retry(
    max_attempts=3,
    delay=1.0,
    backoff_factor=2.0,
    jitter=True,
    retry_on=[ConnectionError, TimeoutError, RateLimitError],
    max_delay=10.0,
    log_retries=True
)
def fetch_data(url: str) -> Dict[str, Any]:
    """
    Fetch data with retry mechanism.
    
    Args:
        url: URL to fetch data from
        
    Returns:
        Fetched data
    """
    module_logger.info(f"Fetching data from {url}")
    
    # Simulate API call
    if random.random() < 0.5:
        if random.random() < 0.5:
            raise ConnectionError("Connection failed", {"url": url})
        else:
            raise TimeoutError("Request timed out", {"url": url, "timeout": 10})
    
    return {"status": "success", "data": "example data"}

# Example 7: Retry context
def fetch_data_with_context(url: str) -> Dict[str, Any]:
    """
    Fetch data with retry context.
    
    Args:
        url: URL to fetch data from
        
    Returns:
        Fetched data
    """
    module_logger.info(f"Fetching data from {url} with retry context")
    
    for attempt in range(3):
        with RetryContext(
            max_attempts=3,
            delay=1.0,
            backoff_factor=2.0,
            jitter=True,
            retry_on=[ConnectionError, TimeoutError, RateLimitError],
            max_delay=10.0,
            log_retries=True
        ) as retry_ctx:
            try:
                # Simulate API call
                if random.random() < 0.5:
                    if random.random() < 0.5:
                        raise ConnectionError("Connection failed", {"url": url})
                    else:
                        raise TimeoutError("Request timed out", {"url": url, "timeout": 10})
                
                return {"status": "success", "data": "example data"}
            except Exception as e:
                if not retry_ctx.should_retry:
                    raise
    
    # If we get here, all retries failed
    raise retry_ctx.last_exception

# Example 8: Circuit breaker
@with_circuit_breaker(
    name="api_service",
    failure_threshold=3,
    recovery_timeout=10.0,
    expected_exceptions=[ConnectionError, TimeoutError, RateLimitError]
)
def call_api_service(endpoint: str) -> Dict[str, Any]:
    """
    Call API service with circuit breaker.
    
    Args:
        endpoint: API endpoint
        
    Returns:
        API response
    """
    module_logger.info(f"Calling API service endpoint {endpoint}")
    
    # Simulate API call
    if random.random() < 0.5:
        if random.random() < 0.5:
            raise ConnectionError("Connection failed", {"endpoint": endpoint})
        else:
            raise TimeoutError("Request timed out", {"endpoint": endpoint, "timeout": 10})
    
    return {"status": "success", "data": "example data"}

# Example 9: Circuit breaker context
def call_api_with_context(endpoint: str) -> Dict[str, Any]:
    """
    Call API service with circuit breaker context.
    
    Args:
        endpoint: API endpoint
        
    Returns:
        API response
    """
    module_logger.info(f"Calling API service endpoint {endpoint} with circuit breaker context")
    
    with CircuitBreakerContext(
        name="api_service",
        failure_threshold=3,
        recovery_timeout=10.0,
        expected_exceptions=[ConnectionError, TimeoutError, RateLimitError]
    ):
        # Simulate API call
        if random.random() < 0.5:
            if random.random() < 0.5:
                raise ConnectionError("Connection failed", {"endpoint": endpoint})
            else:
                raise TimeoutError("Request timed out", {"endpoint": endpoint, "timeout": 10})
        
        return {"status": "success", "data": "example data"}

# Example 10: Standardized logging patterns
def standardized_logging_example():
    """Demonstrate standardized logging patterns."""
    module_logger.info("Starting standardized logging example")
    
    # Log API request
    log_api_request(
        method="GET",
        url="https://api.example.com/data",
        status_code=200,
        elapsed=0.5,
        request_id="req-123",
        user_id="user-456",
        error=None,
        request_data={"param": "value"},
        response_data={"result": "success"}
    )
    
    # Log task execution
    log_task_execution(
        task_id="task-123",
        task_type="data_processing",
        status="completed",
        elapsed=1.5,
        error=None,
        metadata={"items_processed": 100}
    )
    
    # Log data processing
    log_data_processing(
        data_type="user_data",
        operation="validation",
        count=100,
        status="completed",
        elapsed=0.8,
        error=None,
        metadata={"valid": 95, "invalid": 5}
    )
    
    module_logger.info("Finished standardized logging example")

# Example 11: Function call logging
@log_function_call(
    log_args=True,
    log_result=True,
    log_level="DEBUG",
    exclude_args=["password"],
    mask_args={"api_key": "********"}
)
def process_user(user_id: str, password: str, api_key: str) -> Dict[str, Any]:
    """
    Process a user with function call logging.
    
    Args:
        user_id: User ID
        password: User password (will be excluded from logs)
        api_key: API key (will be masked in logs)
        
    Returns:
        Processing result
    """
    # Simulate user processing
    return {
        "status": "success",
        "user_id": user_id,
        "timestamp": time.time()
    }

# Example 12: Specific exception types
def demonstrate_exception_types():
    """Demonstrate specific exception types."""
    module_logger.info("Starting exception types example")
    
    try:
        # Validation error
        raise ValidationError("Invalid input", field="name", value=None)
    except ValidationError as e:
        module_logger.error(f"Caught validation error: {e}")
    
    try:
        # Data processing error
        raise DataProcessingError("Failed to process data", data_type="user_data", operation="transformation")
    except DataProcessingError as e:
        module_logger.error(f"Caught data processing error: {e}")
    
    try:
        # API error
        raise APIError("API request failed", service="example", endpoint="/data", status_code=500)
    except APIError as e:
        module_logger.error(f"Caught API error: {e}")
    
    try:
        # Not found error
        raise NotFoundError("Resource not found", resource_type="user", resource_id="123")
    except NotFoundError as e:
        module_logger.error(f"Caught not found error: {e}")
    
    module_logger.info("Finished exception types example")

# Main function to run all examples
async def main():
    """Run all examples."""
    module_logger.info("Starting error handling and logging examples")
    
    # Example 1: Basic logging
    basic_logging_example()
    
    # Example 2: Contextual logging
    contextual_logging_example("user-123", "login")
    
    # Example 3: Error handling with decorator
    valid_data = {"name": "John", "age": 30, "email": "john@example.com"}
    invalid_data = {"age": "thirty"}
    
    module_logger.info("Validating valid user data")
    result1 = validate_user_data(valid_data)
    module_logger.info(f"Validation result: {result1}")
    
    module_logger.info("Validating invalid user data")
    result2 = validate_user_data(invalid_data)
    module_logger.info(f"Validation result: {result2}")
    
    # Example 4: Error handling with context manager
    module_logger.info("Processing payments")
    payment1 = process_payment("payment-123", 100.0)
    payment2 = process_payment("payment-456", -50.0)
    module_logger.info(f"Payment 1 result: {payment1}")
    module_logger.info(f"Payment 2 result: {payment2}")
    
    # Example 5: Async error handling
    module_logger.info("Fetching user profiles")
    profile1 = await fetch_user_profile("user-123")
    profile2 = await fetch_user_profile("user-456")
    module_logger.info(f"Profile 1: {profile1}")
    module_logger.info(f"Profile 2: {profile2}")
    
    # Example 6: Retry mechanism
    module_logger.info("Fetching data with retry")
    try:
        data1 = fetch_data("https://api.example.com/data")
        module_logger.info(f"Data 1: {data1}")
    except Exception as e:
        module_logger.error(f"Failed to fetch data 1: {e}")
    
    # Example 7: Retry context
    module_logger.info("Fetching data with retry context")
    try:
        data2 = fetch_data_with_context("https://api.example.com/data2")
        module_logger.info(f"Data 2: {data2}")
    except Exception as e:
        module_logger.error(f"Failed to fetch data 2: {e}")
    
    # Example 8: Circuit breaker
    module_logger.info("Calling API service with circuit breaker")
    for i in range(5):
        try:
            result = call_api_service(f"endpoint{i}")
            module_logger.info(f"API call {i} result: {result}")
        except Exception as e:
            module_logger.error(f"API call {i} failed: {e}")
    
    # Example 9: Circuit breaker context
    module_logger.info("Calling API service with circuit breaker context")
    for i in range(5):
        try:
            result = call_api_with_context(f"endpoint{i}")
            module_logger.info(f"API call with context {i} result: {result}")
        except Exception as e:
            module_logger.error(f"API call with context {i} failed: {e}")
    
    # Example 10: Standardized logging patterns
    standardized_logging_example()
    
    # Example 11: Function call logging
    module_logger.info("Processing user with function call logging")
    user_result = process_user("user-123", "password123", "api-key-123")
    module_logger.info(f"User processing result: {user_result}")
    
    # Example 12: Specific exception types
    demonstrate_exception_types()
    
    module_logger.info("Finished error handling and logging examples")

# Run the examples
if __name__ == "__main__":
    asyncio.run(main())

