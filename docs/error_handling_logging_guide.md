# WiseFlow Error Handling and Logging Guide

This guide outlines the best practices for error handling and logging in the WiseFlow project.

## Table of Contents

1. [Error Handling](#error-handling)
   - [Using WiseflowError Classes](#using-wiseflowerror-classes)
   - [Using Error Handling Decorators](#using-error-handling-decorators)
   - [Using Error Handler Context Managers](#using-error-handler-context-managers)
   - [Retry Mechanism](#retry-mechanism)
2. [Logging](#logging)
   - [Logger Configuration](#logger-configuration)
   - [Logging with Context](#logging-with-context)
   - [Log Execution Decorator](#log-execution-decorator)
   - [Log Method Calls Decorator](#log-method-calls-decorator)
3. [Best Practices](#best-practices)
   - [Error Handling Best Practices](#error-handling-best-practices)
   - [Logging Best Practices](#logging-best-practices)
4. [Examples](#examples)
   - [Error Handling Examples](#error-handling-examples)
   - [Logging Examples](#logging-examples)

## Error Handling

WiseFlow provides a comprehensive error handling system that allows for consistent error handling across the codebase.

### Using WiseflowError Classes

WiseFlow defines a hierarchy of error classes that should be used for different types of errors:

```python
from core.utils.error_handling import ValidationError, ConnectionError, NotFoundError

# Raise a validation error
if not isinstance(data, dict):
    raise ValidationError("Data must be a dictionary", {"provided_type": type(data).__name__})

# Raise a connection error
if not response.ok:
    raise ConnectionError(
        "Failed to connect to API", 
        {"status_code": response.status_code, "url": response.url},
        cause=response.exception
    )

# Raise a not found error
if not os.path.exists(file_path):
    raise NotFoundError(f"File not found: {file_path}")
```

### Using Error Handling Decorators

The `handle_exceptions` decorator provides a convenient way to handle exceptions in functions:

```python
from core.utils.error_handling import handle_exceptions

@handle_exceptions(
    error_types=[ValueError, TypeError],
    default_message="Failed to process data",
    log_error=True,
    reraise=False,
    save_to_file=False,
    default_return=[]
)
def process_data(data):
    # Process data
    return processed_data
```

For functions that need retry logic, use the `retry` decorator:

```python
from core.utils.error_handling import retry

@retry(
    max_retries=3,
    retry_delay=1,
    retry_backoff=2.0,
    retry_exceptions=[ConnectionError, TimeoutError]
)
def fetch_data_from_api(url):
    # Fetch data from API
    return data
```

### Using Error Handler Context Managers

For more complex error handling scenarios, use the `ErrorHandler` context manager:

```python
from core.utils.error_handling import ErrorHandler

def process_complex_data(data):
    with ErrorHandler(
        error_types=[ValueError, TypeError],
        default=[],
        log_error=True,
        save_to_file=True,
        context={"data_id": data.get("id")}
    ) as handler:
        # Process data
        result = process_data(data)
        return result
    
    if handler.error_occurred:
        # Handle error
        print(f"Error: {handler.error}")
    
    return handler.result
```

For async code, use the `async_error_handler` function:

```python
from core.utils.error_handling import async_error_handler

async def fetch_and_process_data(url):
    data = await async_error_handler(
        fetch_data_from_api(url),
        error_types=[ConnectionError, TimeoutError],
        default={},
        log_error=True,
        retry_count=3,
        retry_delay=1,
        retry_backoff=2.0
    )
    
    if not data:
        return None
    
    return process_data(data)
```

### Retry Mechanism

WiseFlow provides a retry mechanism for operations that may fail temporarily:

```python
from core.utils.error_handling import retry

@retry(
    max_retries=3,
    retry_delay=1,
    retry_backoff=2.0,
    retry_exceptions=[ConnectionError, TimeoutError],
    retry_condition=lambda e: isinstance(e, ConnectionError) and e.details.get("status_code") == 429
)
def fetch_data_with_retry(url):
    # Fetch data from API
    return data
```

## Logging

WiseFlow uses the Loguru library for logging, with additional utilities for structured logging and context.

### Logger Configuration

The logging system is configured in `core.utils.logging_config`:

```python
from core.utils.logging_config import configure_logging

# Configure logging
configure_logging(
    log_level="DEBUG",
    log_to_console=True,
    log_to_file=True,
    app_name="my_module",
    structured_logging=True,
    enhanced_format=True
)
```

### Logging with Context

Add context to logs to make them more informative:

```python
from core.utils.logging_config import logger, with_context

# Log with context
with_context(user_id="123", action="login").info("User logged in")

# Use LogContext context manager
from core.utils.logging_config import LogContext

def process_user_data(user_id, data):
    with LogContext(user_id=user_id, data_size=len(data)):
        logger.info("Processing user data")
        # Process data
        logger.info("User data processed successfully")
```

### Log Execution Decorator

Use the `log_execution` decorator to automatically log function calls:

```python
from core.utils.logging_config import log_execution

@log_execution(log_args=True, log_result=True, level="DEBUG")
def calculate_total(items):
    total = sum(item.price for item in items)
    return total
```

### Log Method Calls Decorator

Use the `log_method_calls` decorator to automatically log all method calls in a class:

```python
from core.utils.logging_config import log_method_calls

@log_method_calls(exclude=["__init__", "internal_helper"], level="DEBUG")
class UserService:
    def __init__(self, db):
        self.db = db
    
    def get_user(self, user_id):
        # Get user from database
        return user
    
    def update_user(self, user_id, data):
        # Update user in database
        return updated_user
    
    def internal_helper(self):
        # Internal helper method
        pass
```

## Best Practices

### Error Handling Best Practices

1. **Use Specific Error Types**: Use the most specific error type for each situation.
2. **Include Context**: Always include relevant context in error details.
3. **Handle Errors at the Right Level**: Handle errors at the level where you have enough context to make a decision.
4. **Log Errors**: Always log errors with appropriate context.
5. **Provide Meaningful Error Messages**: Error messages should be clear and actionable.
6. **Use Retry for Transient Errors**: Use retry logic for operations that may fail temporarily.
7. **Fail Fast**: Validate inputs early to fail fast and provide clear error messages.
8. **Don't Swallow Exceptions**: Don't catch exceptions without handling them properly.
9. **Use Context Managers**: Use context managers for complex error handling scenarios.
10. **Document Error Handling**: Document error handling behavior in function docstrings.

### Logging Best Practices

1. **Use Structured Logging**: Use structured logging to make logs easier to search and analyze.
2. **Include Context**: Always include relevant context in logs.
3. **Use Appropriate Log Levels**: Use the appropriate log level for each message.
4. **Log at Entry and Exit Points**: Log at the entry and exit points of important functions.
5. **Log Exceptions**: Always log exceptions with appropriate context.
6. **Use Decorators**: Use decorators to automatically log function calls.
7. **Don't Log Sensitive Information**: Don't log sensitive information like passwords or API keys.
8. **Use Consistent Formatting**: Use consistent formatting for log messages.
9. **Log Metrics**: Log metrics to track performance and usage.
10. **Configure Logging Appropriately**: Configure logging appropriately for each environment.

## Examples

### Error Handling Examples

**Example 1: Basic Error Handling**

```python
from core.utils.error_handling import handle_exceptions, ValidationError

@handle_exceptions(error_types=[ValueError, TypeError], default_return=None)
def parse_json(json_str):
    if not isinstance(json_str, str):
        raise ValidationError("Input must be a string", {"provided_type": type(json_str).__name__})
    
    import json
    return json.loads(json_str)
```

**Example 2: Retry Logic**

```python
from core.utils.error_handling import retry, ConnectionError

@retry(max_retries=3, retry_delay=1, retry_backoff=2.0)
def fetch_data_from_api(url):
    import requests
    response = requests.get(url)
    
    if not response.ok:
        raise ConnectionError(
            f"Failed to fetch data from API: {response.status_code}",
            {"status_code": response.status_code, "url": url}
        )
    
    return response.json()
```

**Example 3: Complex Error Handling**

```python
from core.utils.error_handling import ErrorHandler, ValidationError, ConnectionError, DataProcessingError

def process_user_data(user_id, data):
    # Validate inputs
    if not user_id:
        raise ValidationError("User ID is required")
    
    if not data:
        raise ValidationError("Data is required")
    
    # Fetch user from API
    with ErrorHandler(error_types=[ConnectionError], default=None) as handler:
        user = fetch_user_from_api(user_id)
    
    if handler.error_occurred:
        # Handle connection error
        return {"error": "Failed to fetch user data"}
    
    # Process user data
    try:
        processed_data = process_data(user, data)
    except Exception as e:
        raise DataProcessingError("Failed to process user data", {"user_id": user_id}, cause=e)
    
    return processed_data
```

### Logging Examples

**Example 1: Basic Logging**

```python
from core.utils.logging_config import logger

def process_data(data):
    logger.info(f"Processing data with {len(data)} items")
    
    try:
        result = perform_processing(data)
        logger.info(f"Data processing completed successfully with {len(result)} results")
        return result
    except Exception as e:
        logger.error(f"Error processing data: {e}")
        raise
```

**Example 2: Logging with Context**

```python
from core.utils.logging_config import with_context

def process_user_data(user_id, data):
    log = with_context(user_id=user_id, data_size=len(data))
    
    log.info("Processing user data")
    
    try:
        result = perform_processing(user_id, data)
        log.info("User data processed successfully", result_size=len(result))
        return result
    except Exception as e:
        log.error(f"Error processing user data: {e}")
        raise
```

**Example 3: Automatic Logging with Decorators**

```python
from core.utils.logging_config import log_execution, log_method_calls

@log_execution(log_args=True, log_result=True)
def calculate_total(items):
    return sum(item.price for item in items)

@log_method_calls
class UserService:
    def __init__(self, db):
        self.db = db
    
    def get_user(self, user_id):
        return self.db.get_user(user_id)
    
    def update_user(self, user_id, data):
        return self.db.update_user(user_id, data)
```

**Example 4: Combining Error Handling and Logging**

```python
from core.utils.error_handling import handle_exceptions, ValidationError
from core.utils.logging_config import log_execution

@log_execution(log_args=True, log_result=True)
@handle_exceptions(error_types=[ValueError, TypeError], default_return=None)
def process_data(data):
    if not isinstance(data, dict):
        raise ValidationError("Data must be a dictionary", {"provided_type": type(data).__name__})
    
    # Process data
    result = perform_processing(data)
    
    return result
```

