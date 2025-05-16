# Error Handling and Logging Guide

This guide provides comprehensive documentation for the error handling and logging system in WiseFlow.

## Table of Contents

1. [Introduction](#introduction)
2. [Error Handling](#error-handling)
   - [Exception Hierarchy](#exception-hierarchy)
   - [Using the Handle Exceptions Decorator](#using-the-handle-exceptions-decorator)
   - [Using the Error Handler Context Manager](#using-the-error-handler-context-manager)
   - [Retry Mechanisms](#retry-mechanisms)
   - [Circuit Breaker Pattern](#circuit-breaker-pattern)
3. [Logging](#logging)
   - [Logging Configuration](#logging-configuration)
   - [Contextual Logging](#contextual-logging)
   - [Standardized Logging Patterns](#standardized-logging-patterns)
   - [Log Sampling](#log-sampling)
4. [Best Practices](#best-practices)
   - [Error Handling Best Practices](#error-handling-best-practices)
   - [Logging Best Practices](#logging-best-practices)
5. [Examples](#examples)
   - [Error Handling Examples](#error-handling-examples)
   - [Logging Examples](#logging-examples)

## Introduction

Proper error handling and logging are critical for system stability, debugging, and maintenance. The WiseFlow error handling and logging system provides a comprehensive set of tools for handling errors and logging information in a consistent and informative way.

## Error Handling

### Exception Hierarchy

WiseFlow provides a comprehensive exception hierarchy that allows for specific error types to be caught and handled appropriately. The base class for all WiseFlow exceptions is `WiseflowError`.

```python
from core.utils.exceptions import (
    WiseflowError,
    InputError, ValidationError, MissingParameterError, InvalidParameterError,
    ProcessingError, DataProcessingError, TransformationError, AnalysisError,
    SystemError, ConfigurationError, ResourceError, TaskError,
    ExternalError, ConnectionError, APIError, TimeoutError,
    SecurityError, AuthenticationError, AuthorizationError,
    NotFoundError
)
```

The exception hierarchy is organized as follows:

- `WiseflowError`: Base class for all WiseFlow exceptions
  - `InputError`: Base class for errors related to input validation
    - `ValidationError`: Error raised when input validation fails
    - `MissingParameterError`: Error raised when a required parameter is missing
    - `InvalidParameterError`: Error raised when a parameter has an invalid value
    - `FormatError`: Error raised when data has an invalid format
  - `ProcessingError`: Base class for errors that occur during data processing
    - `DataProcessingError`: Error raised when data processing fails
    - `TransformationError`: Error raised when data transformation fails
    - `AnalysisError`: Error raised when data analysis fails
    - `ExtractionError`: Error raised when data extraction fails
  - `SystemError`: Base class for errors related to system operations
    - `ConfigurationError`: Error raised when there is a configuration error
    - `ResourceError`: Error raised when there is a resource error
    - `TaskError`: Error raised when there is a task error
    - `ConcurrencyError`: Error raised when there is a concurrency issue
    - `PluginError`: Error raised when there is a plugin error
  - `ExternalError`: Base class for errors related to external services
    - `ConnectionError`: Error raised when a connection fails
    - `APIError`: Error raised when an API request fails
    - `RateLimitError`: Error raised when a rate limit is exceeded
    - `TimeoutError`: Error raised when a connection times out
    - `ServiceUnavailableError`: Error raised when a service is unavailable
    - `NotFoundError`: Error raised when a resource is not found
  - `SecurityError`: Base class for security-related errors
    - `AuthenticationError`: Error raised when authentication fails
    - `AuthorizationError`: Error raised when authorization fails

### Using the Handle Exceptions Decorator

The `handle_exceptions` decorator provides a convenient way to handle exceptions in functions. It can be used to catch specific exception types, log errors, and provide default return values.

```python
from core.utils.error_handling import handle_exceptions, DataProcessingError

@handle_exceptions(
    error_types=[ValueError, DataProcessingError],
    default_message="Error processing data",
    log_error=True,
    reraise=False,
    save_to_file=False,
    default_return=None
)
def process_data(data):
    # Process data
    if not data:
        raise ValueError("Data cannot be empty")
    
    # More processing
    return processed_data
```

### Using the Error Handler Context Manager

The `ErrorHandler` context manager provides a way to handle exceptions in a block of code. It can be used to catch specific exception types, log errors, and provide default return values.

```python
from core.utils.error_handling import ErrorHandler, ConnectionError

def fetch_data(url):
    with ErrorHandler(
        error_types=[ConnectionError, TimeoutError],
        default={"status": "error", "message": "Failed to fetch data"},
        log_error=True,
        save_to_file=False
    ) as handler:
        # Fetch data
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    
    if handler.error_occurred:
        # Handle error
        print(f"Error: {handler.error}")
    
    return handler.result
```

### Retry Mechanisms

WiseFlow provides retry mechanisms for operations that may fail with transient errors. The `retry` decorator and `RetryContext` context manager can be used to automatically retry operations with exponential backoff.

```python
from core.utils.retry import retry, RetryContext

@retry(
    max_attempts=3,
    delay=1.0,
    backoff_factor=2.0,
    jitter=True,
    retry_on=[ConnectionError, TimeoutError],
    max_delay=30.0,
    log_retries=True
)
def fetch_data(url):
    # Fetch data
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

def fetch_data_with_context(url):
    for _ in range(3):
        with RetryContext(
            max_attempts=3,
            delay=1.0,
            backoff_factor=2.0,
            jitter=True,
            retry_on=[ConnectionError, TimeoutError],
            max_delay=30.0,
            log_retries=True
        ) as retry_ctx:
            try:
                # Fetch data
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if not retry_ctx.should_retry:
                    raise
    
    # If we get here, all retries failed
    raise retry_ctx.last_exception
```

### Circuit Breaker Pattern

The circuit breaker pattern prevents a failing service from being repeatedly called, which can lead to cascading failures. WiseFlow provides a `CircuitBreaker` class and `with_circuit_breaker` decorator for implementing this pattern.

```python
from core.utils.circuit_breaker import with_circuit_breaker, CircuitBreakerContext

@with_circuit_breaker(
    name="api_service",
    failure_threshold=5,
    recovery_timeout=60.0,
    expected_exceptions=[ConnectionError, TimeoutError]
)
def call_api_service(endpoint):
    # Call API service
    response = requests.get(f"https://api.example.com/{endpoint}", timeout=10)
    response.raise_for_status()
    return response.json()

def call_api_with_context(endpoint):
    with CircuitBreakerContext(
        name="api_service",
        failure_threshold=5,
        recovery_timeout=60.0,
        expected_exceptions=[ConnectionError, TimeoutError]
    ):
        # Call API service
        response = requests.get(f"https://api.example.com/{endpoint}", timeout=10)
        response.raise_for_status()
        return response.json()
```

## Logging

### Logging Configuration

WiseFlow uses the [loguru](https://github.com/Delgan/loguru) library for logging. The logging system is configured in the `core.utils.logging_config` module.

```python
from core.utils.logging_config import configure_logging

# Configure logging
configure_logging(
    log_level="INFO",
    log_to_console=True,
    log_to_file=True,
    log_dir="/path/to/logs",
    app_name="wiseflow",
    structured_logging=False,
    rotation="50 MB",
    retention="10 days"
)
```

### Contextual Logging

Contextual logging allows you to add additional context to log messages. This can be useful for tracking requests, users, or other relevant information.

```python
from core.utils.logging_config import with_context, LogContext

# Add context to logger
user_logger = with_context(user_id="user-123", action="login")
user_logger.info("User logged in")

# Use context manager for temporary context
with LogContext(request_id="req-123", endpoint="/api/data"):
    logger.info("Processing request")
    logger.debug("Request details: ...")
    logger.success("Request processed successfully")
```

### Standardized Logging Patterns

WiseFlow provides standardized logging patterns for common scenarios such as API requests, task execution, and data processing.

```python
from core.utils.enhanced_logging import (
    log_api_request, log_task_execution, log_data_processing,
    log_function_call
)

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

# Log function calls
@log_function_call(
    log_args=True,
    log_result=True,
    log_level="DEBUG",
    exclude_args=["password"],
    mask_args={"api_key": "********"}
)
def process_user(user_id, password, api_key):
    # Process user
    return {"status": "success"}
```

### Log Sampling

For high-volume logs, WiseFlow provides log sampling to reduce the volume of logs while still maintaining visibility into the system.

```python
from core.utils.enhanced_logging import sample_log

# Sample logs
@sample_log(sample_rate=0.1, min_level="INFO")
def debug(self, message, *args, **kwargs):
    # Original debug method
    pass
```

## Best Practices

### Error Handling Best Practices

1. **Use specific exception types**: Use the most specific exception type that applies to the error condition. This makes it easier to catch and handle specific error types.

2. **Include context in exceptions**: When raising exceptions, include relevant context such as the operation being performed, the data being processed, and any other information that would be useful for debugging.

3. **Handle exceptions at the appropriate level**: Handle exceptions at the level where you have enough context to make a decision about how to handle the error. Don't catch exceptions too early or too late.

4. **Use retry mechanisms for transient errors**: Use retry mechanisms for operations that may fail with transient errors, such as network requests or database operations.

5. **Use circuit breakers for external services**: Use circuit breakers to prevent cascading failures when external services are unavailable or experiencing issues.

6. **Log exceptions**: Always log exceptions with enough context to understand what went wrong and how to fix it.

7. **Clean up resources**: Always clean up resources (e.g., file handles, database connections) when exceptions occur.

### Logging Best Practices

1. **Use appropriate log levels**: Use the appropriate log level for each message. For example, use DEBUG for detailed debugging information, INFO for general information, WARNING for potential issues, ERROR for errors that don't prevent the application from running, and CRITICAL for errors that prevent the application from running.

2. **Include context in logs**: Include relevant context in log messages, such as the operation being performed, the data being processed, and any other information that would be useful for debugging.

3. **Use structured logging**: Use structured logging to make it easier to parse and analyze logs.

4. **Log at entry and exit points**: Log at the entry and exit points of important operations to make it easier to trace the flow of execution.

5. **Use standardized logging patterns**: Use standardized logging patterns for common scenarios such as API requests, task execution, and data processing.

6. **Sample high-volume logs**: Sample high-volume logs to reduce the volume of logs while still maintaining visibility into the system.

7. **Monitor log performance**: Monitor the performance impact of logging and adjust as needed.

## Examples

### Error Handling Examples

```python
from core.utils.exceptions import ValidationError, APIError
from core.utils.error_handling import handle_exceptions, ErrorHandler
from core.utils.retry import retry
from core.utils.circuit_breaker import with_circuit_breaker

# Example 1: Raising specific exceptions
def validate_user(user_data):
    if not user_data:
        raise ValidationError("User data cannot be empty")
    
    if "name" not in user_data:
        raise ValidationError("Name is required", field="name")
    
    if "age" in user_data and not isinstance(user_data["age"], int):
        raise ValidationError("Age must be an integer", field="age", value=user_data["age"])
    
    return True

# Example 2: Using the handle_exceptions decorator
@handle_exceptions(
    error_types=[ValidationError],
    default_message="Error validating user",
    log_error=True,
    reraise=False,
    save_to_file=False,
    default_return=False
)
def process_user(user_data):
    # Validate user
    validate_user(user_data)
    
    # Process user
    return True

# Example 3: Using the ErrorHandler context manager
def fetch_user(user_id):
    with ErrorHandler(
        error_types=[APIError, TimeoutError],
        default={"status": "error", "message": "Failed to fetch user"},
        log_error=True,
        save_to_file=False
    ) as handler:
        # Fetch user
        response = requests.get(f"https://api.example.com/users/{user_id}", timeout=10)
        response.raise_for_status()
        return response.json()
    
    if handler.error_occurred:
        # Handle error
        print(f"Error: {handler.error}")
    
    return handler.result

# Example 4: Using the retry decorator
@retry(
    max_attempts=3,
    delay=1.0,
    backoff_factor=2.0,
    jitter=True,
    retry_on=[ConnectionError, TimeoutError],
    max_delay=30.0,
    log_retries=True
)
def fetch_data(url):
    # Fetch data
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

# Example 5: Using the circuit breaker decorator
@with_circuit_breaker(
    name="api_service",
    failure_threshold=5,
    recovery_timeout=60.0,
    expected_exceptions=[ConnectionError, TimeoutError]
)
def call_api_service(endpoint):
    # Call API service
    response = requests.get(f"https://api.example.com/{endpoint}", timeout=10)
    response.raise_for_status()
    return response.json()
```

### Logging Examples

```python
from core.utils.logging_config import logger, with_context, LogContext
from core.utils.enhanced_logging import (
    log_api_request, log_task_execution, log_data_processing,
    log_function_call, RequestContext
)

# Example 1: Basic logging
logger.debug("This is a debug message")
logger.info("This is an info message")
logger.success("This is a success message")
logger.warning("This is a warning message")
logger.error("This is an error message")
logger.critical("This is a critical message")

# Example 2: Contextual logging
user_logger = with_context(user_id="user-123", action="login")
user_logger.info("User logged in")

with LogContext(request_id="req-123", endpoint="/api/data"):
    logger.info("Processing request")
    logger.debug("Request details: ...")
    logger.success("Request processed successfully")

# Example 3: Request context
with RequestContext(user_id="user-123", request_id="req-456"):
    # All logs in this block will have user_id and request_id
    logger.info("Processing request")
    
    # Nested function calls will inherit the context
    process_data()

# Example 4: Standardized logging patterns
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

log_task_execution(
    task_id="task-123",
    task_type="data_processing",
    status="completed",
    elapsed=1.5,
    error=None,
    metadata={"items_processed": 100}
)

log_data_processing(
    data_type="user_data",
    operation="validation",
    count=100,
    status="completed",
    elapsed=0.8,
    error=None,
    metadata={"valid": 95, "invalid": 5}
)

# Example 5: Function call logging
@log_function_call(
    log_args=True,
    log_result=True,
    log_level="DEBUG",
    exclude_args=["password"],
    mask_args={"api_key": "********"}
)
def process_user(user_id, password, api_key):
    # Process user
    return {"status": "success"}
```

