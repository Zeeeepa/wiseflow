# WiseFlow Error Handling and Recovery System

This document provides an overview of the robust error handling and recovery system implemented in WiseFlow.

## Table of Contents

1. [Introduction](#introduction)
2. [Error Handling Middleware](#error-handling-middleware)
3. [Circuit Breaker Pattern](#circuit-breaker-pattern)
4. [Retry Mechanisms](#retry-mechanisms)
5. [Recovery Strategies](#recovery-strategies)
6. [Error Reporting and Visualization](#error-reporting-and-visualization)
7. [Best Practices](#best-practices)
8. [Examples](#examples)

## Introduction

The WiseFlow error handling and recovery system provides a comprehensive approach to handling errors and recovering from failures throughout the application. The system includes:

- **Error Handling Middleware**: Consistent error handling for FastAPI applications
- **Circuit Breaker Pattern**: Prevent cascading failures when external services are unavailable
- **Retry Mechanisms**: Automatically retry operations that fail due to transient issues
- **Recovery Strategies**: Apply different recovery strategies based on the type of failure
- **Error Reporting and Visualization**: Track and visualize errors for monitoring and debugging

## Error Handling Middleware

The error handling middleware provides a consistent way to handle exceptions in FastAPI applications. It catches exceptions, logs them, and returns appropriate responses.

### Features

- Consistent error handling across the application
- Structured error logging with severity levels
- Automatic mapping of exceptions to HTTP status codes
- Option to include traceback in responses (for development)
- Option to save errors to files for later analysis

### Usage

```python
from fastapi import FastAPI
from core.middleware import add_error_handling_middleware

app = FastAPI()

# Add error handling middleware
add_error_handling_middleware(
    app,
    log_errors=True,
    include_traceback=os.environ.get("ENVIRONMENT", "development") == "development",
    save_to_file=True
)
```

## Circuit Breaker Pattern

The circuit breaker pattern prevents cascading failures when an external service is unavailable. It "trips" after a certain number of failures and prevents further calls to the service for a specified period.

### Features

- Configurable failure threshold
- Configurable recovery timeout
- Optional timeout for the wrapped function
- Optional fallback function to call when the circuit is open
- Support for both synchronous and asynchronous functions

### Usage

```python
from core.middleware import circuit_breaker

@circuit_breaker(
    failure_threshold=3,
    recovery_timeout=30.0,
    timeout=5.0,
    fallback=lambda *args, **kwargs: {"status": "fallback"}
)
async def call_external_service(endpoint):
    # Call external service
    return await external_service.call_api(endpoint)
```

## Retry Mechanisms

The retry mechanisms automatically retry operations that fail due to transient issues, with exponential backoff to avoid overwhelming the system.

### Features

- Configurable maximum number of retries
- Configurable initial backoff time
- Configurable backoff multiplier
- Configurable maximum backoff time
- Optional jitter to prevent thundering herd problem
- Configurable list of retryable exceptions
- Support for both synchronous and asynchronous functions

### Usage

```python
from core.middleware import retry_with_backoff

@retry_with_backoff(
    max_retries=3,
    initial_backoff=1.0,
    backoff_multiplier=2.0,
    max_backoff=30.0,
    jitter=True,
    retryable_exceptions=[ConnectionError, TimeoutError]
)
async def call_external_service(endpoint):
    # Call external service
    return await external_service.call_api(endpoint)
```

## Recovery Strategies

Recovery strategies provide a flexible way to handle failures in different ways based on the type of failure.

### Available Strategies

- **RetryStrategy**: Retry the operation with exponential backoff
- **FallbackStrategy**: Use a fallback function when the primary function fails
- **CacheStrategy**: Use cached results when the function fails
- **CompositeStrategy**: Apply multiple recovery strategies in sequence

### Usage

```python
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

# Create recovery strategies
retry_strategy = RetryStrategy(
    max_retries=3,
    initial_backoff=1.0,
    backoff_multiplier=2.0,
    max_backoff=30.0,
    jitter=True
)

fallback_strategy = FallbackStrategy(
    fallback_func=fallback_function,
    handled_exceptions=[ConnectionError, TimeoutError]
)

# Create a composite strategy
composite_strategy = CompositeStrategy([
    retry_strategy,
    fallback_strategy
])

# Use the composite strategy
@with_composite_recovery(composite_strategy)
async def call_external_service(endpoint):
    # Call external service
    return await external_service.call_api(endpoint)
```

## Error Reporting and Visualization

The error reporting and visualization system provides a way to track and visualize errors for monitoring and debugging.

### Features

- Structured error reporting with severity levels and categories
- Error statistics and trends
- Error visualization in the dashboard
- Configurable error alerts

### Usage

```python
from core.utils.error_logging import (
    report_error,
    get_error_statistics,
    ErrorSeverity,
    ErrorCategory
)

try:
    # Perform operation
    result = perform_operation()
    return result
except Exception as e:
    # Report the error
    error_context = {
        "operation": "perform_operation",
        "parameters": str(parameters)
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
```

## Best Practices

### General Best Practices

1. **Use Structured Error Handling**: Always use the structured error handling mechanisms provided by the system.
2. **Provide Context**: Always provide context when reporting errors to make debugging easier.
3. **Use Appropriate Severity Levels**: Use appropriate severity levels for different types of errors.
4. **Use Appropriate Categories**: Use appropriate categories for different types of errors.
5. **Handle Errors at the Right Level**: Handle errors at the level where you have enough context to make a decision.

### Circuit Breaker Best Practices

1. **Use Circuit Breakers for External Services**: Always use circuit breakers when calling external services.
2. **Configure Appropriate Thresholds**: Configure appropriate failure thresholds based on the service's reliability.
3. **Provide Fallbacks**: Always provide fallbacks for critical operations.

### Retry Best Practices

1. **Only Retry Idempotent Operations**: Only retry operations that are idempotent (can be repeated without side effects).
2. **Use Exponential Backoff**: Always use exponential backoff to avoid overwhelming the system.
3. **Add Jitter**: Always add jitter to prevent the thundering herd problem.
4. **Limit Retries**: Limit the number of retries to avoid wasting resources on operations that are likely to fail.

### Recovery Strategy Best Practices

1. **Use Composite Strategies**: Use composite strategies to apply multiple recovery strategies in sequence.
2. **Order Strategies Appropriately**: Order strategies appropriately based on their cost and likelihood of success.
3. **Use Caching for Read Operations**: Use caching for read operations to improve performance and resilience.

## Examples

See the `examples/robust_error_handling_example.py` file for examples of how to use the error handling and recovery system.

```python
# Example of using circuit breaker decorator
@circuit_breaker(
    failure_threshold=3,
    recovery_timeout=5.0,
    timeout=1.0,
    fallback=lambda endpoint: {"status": "fallback", "endpoint": endpoint}
)
async def call_external_api_with_circuit_breaker(endpoint):
    return await external_service.call_api(endpoint)

# Example of using retry with backoff
@retry_with_backoff(
    max_retries=3,
    initial_backoff=0.5,
    backoff_multiplier=2.0,
    max_backoff=5.0,
    jitter=True
)
async def call_external_api_with_retry(endpoint):
    return await external_service.call_api(endpoint)

# Example of using error handling decorator
@with_error_handling(
    error_types=[ConnectionError, TimeoutError],
    severity=ErrorSeverity.ERROR,
    category=ErrorCategory.EXTERNAL_SERVICE,
    include_context=True,
    save_to_file=True,
    reraise=True
)
async def call_external_api_with_error_handling(endpoint):
    return await external_service.call_api(endpoint)

# Example of using composite recovery strategy
@with_composite_recovery(composite_strategy)
async def call_external_api_with_composite_recovery(endpoint):
    return await external_service.call_api(endpoint)
```

