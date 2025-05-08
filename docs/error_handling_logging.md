# WiseFlow Error Handling and Logging System

This document provides an overview of the error handling and logging system in WiseFlow, including best practices and examples.

## Table of Contents

1. [Logging System](#logging-system)
2. [Error Handling System](#error-handling-system)
3. [Best Practices](#best-practices)
4. [Examples](#examples)

## Logging System

WiseFlow uses [loguru](https://github.com/Delgan/loguru) for all logging needs. The logging system is configured in `core/utils/logging_config.py`.

### Key Features

- **Centralized Configuration**: All logging configuration is managed in one place.
- **Structured Logging**: Support for JSON-formatted logs for better analysis.
- **Contextual Logging**: Add context to logs for better debugging.
- **Log Rotation**: Automatic log rotation based on file size.
- **Multiple Outputs**: Log to both console and files.
- **Error-Specific Logs**: Separate log file for errors.

### Log Levels

WiseFlow uses the following log levels:

- **TRACE (5)**: Detailed debugging information.
- **DEBUG (10)**: Debugging information.
- **INFO (20)**: General information.
- **SUCCESS (25)**: Successful operations.
- **WARNING (30)**: Potential issues.
- **ERROR (40)**: Errors that don't stop the application.
- **CRITICAL (50)**: Critical errors that may stop the application.

### Basic Usage

```python
from core.utils.logging_config import logger, get_logger, with_context, LogContext

# Get a logger with a specific name
my_logger = get_logger("my_module")
my_logger.info("This is an info message")

# Add context to logs
user_logger = with_context(user_id="123", action="login")
user_logger.info("User logged in")

# Use context manager for temporary context
with LogContext(request_id="abc123", endpoint="/api/data"):
    logger.info("Processing request")
    # ... do something ...
    logger.success("Request processed successfully")
```

### Configuration

You can configure the logging system using environment variables or the configuration file:

```
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_TO_CONSOLE=true
STRUCTURED_LOGGING=false
```

## Error Handling System

WiseFlow provides a comprehensive error handling system in `core/utils/error_handling.py`.

### Key Features

- **Error Hierarchy**: A hierarchy of error classes for different types of errors.
- **Structured Errors**: All errors include context and can be serialized to JSON.
- **Error Decorators**: Decorators for handling exceptions in functions.
- **Context Managers**: Context managers for handling exceptions in blocks of code.
- **Async Support**: Support for handling exceptions in async functions.

### Error Classes

WiseFlow provides the following error classes:

- **WiseflowError**: Base class for all WiseFlow errors.
- **ConnectionError**: Errors related to connections.
- **DataProcessingError**: Errors related to data processing.
- **ConfigurationError**: Errors related to configuration.
- **ResourceError**: Errors related to resources.
- **TaskError**: Errors related to tasks.
- **PluginError**: Errors related to plugins.
- **ValidationError**: Errors related to validation.
- **AuthenticationError**: Errors related to authentication.
- **AuthorizationError**: Errors related to authorization.
- **NotFoundError**: Errors related to resources not found.

### Basic Usage

```python
from core.utils.error_handling import (
    WiseflowError, handle_exceptions, ErrorHandler, async_error_handler
)

# Raise a WiseFlow error
raise WiseflowError("Something went wrong", {"detail": "More information"})

# Use the decorator to handle exceptions
@handle_exceptions(
    error_types=[ValueError, TypeError],
    default_message="Invalid input",
    log_error=True
)
def process_data(data):
    # ... do something ...
    return result

# Use the context manager to handle exceptions
def process_request(request):
    with ErrorHandler(error_types=[Exception], default="default response") as handler:
        # ... do something that might raise an exception ...
        result = process_data(request.data)
        return result
    
    if handler.error_occurred:
        # Handle the error
        return handler.result

# Use the async utility function
async def fetch_data(url):
    result = await async_error_handler(
        fetch_url(url),
        error_types=[ConnectionError],
        default=[],
        context={"url": url}
    )
    return result
```

## Best Practices

### Logging Best Practices

1. **Use Appropriate Log Levels**:
   - `TRACE`: For very detailed debugging information.
   - `DEBUG`: For debugging information.
   - `INFO`: For general information about application progress.
   - `SUCCESS`: For successful operations.
   - `WARNING`: For potential issues that don't prevent the application from working.
   - `ERROR`: For errors that don't stop the application.
   - `CRITICAL`: For critical errors that may stop the application.

2. **Add Context to Logs**:
   - Always include relevant context in logs.
   - Use `with_context()` or `LogContext` to add context.
   - Include IDs, user information, and other relevant data.

3. **Structured Logging**:
   - Use structured logging for better analysis.
   - Include key-value pairs instead of just messages.
   - Enable `STRUCTURED_LOGGING` in production.

4. **Log Messages**:
   - Make log messages clear and concise.
   - Include enough information to understand what happened.
   - Avoid logging sensitive information.

### Error Handling Best Practices

1. **Use Appropriate Error Classes**:
   - Use the most specific error class for the situation.
   - Create new error classes if needed for specific domains.
   - Include relevant details in the error.

2. **Error Propagation**:
   - Decide whether to handle errors locally or propagate them.
   - Use `reraise=True` in `handle_exceptions` to propagate errors.
   - Add context to errors as they propagate up the stack.

3. **Error Recovery**:
   - Implement recovery mechanisms for non-critical errors.
   - Use default values or fallbacks when appropriate.
   - Log recovery attempts and results.

4. **Error Reporting**:
   - Log all errors with appropriate context.
   - Save critical errors to files for later analysis.
   - Consider sending alerts for critical errors.

## Examples

### Example 1: Basic Logging

```python
from core.utils.logging_config import logger, get_logger

# Get a logger for the current module
logger = get_logger(__name__)

def process_user(user_id, data):
    logger.info(f"Processing user {user_id}")
    
    try:
        # ... do something ...
        logger.success(f"User {user_id} processed successfully")
    except Exception as e:
        logger.error(f"Error processing user {user_id}: {e}")
        raise
```

### Example 2: Contextual Logging

```python
from core.utils.logging_config import with_context, LogContext

def process_order(order_id, items):
    # Create a logger with order context
    order_logger = with_context(order_id=order_id, item_count=len(items))
    
    order_logger.info("Processing order")
    
    # Process each item with item context
    for item in items:
        with LogContext(item_id=item.id, item_type=item.type):
            logger.info(f"Processing item {item.name}")
            # ... process item ...
            logger.success("Item processed")
    
    order_logger.success("Order processed successfully")
```

### Example 3: Error Handling with Decorator

```python
from core.utils.error_handling import handle_exceptions, DataProcessingError

@handle_exceptions(
    error_types=[ValueError, TypeError, KeyError],
    default_message="Error processing data",
    log_error=True,
    default_return=[]
)
def process_data(data):
    if not isinstance(data, dict):
        raise TypeError("Data must be a dictionary")
    
    if "id" not in data:
        raise KeyError("Data must contain an ID")
    
    if data["value"] < 0:
        raise ValueError("Value must be positive")
    
    # ... process data ...
    return processed_data
```

### Example 4: Error Handling with Context Manager

```python
from core.utils.error_handling import ErrorHandler, ConnectionError

def fetch_user_data(user_id):
    with ErrorHandler(
        error_types=[ConnectionError, ValueError],
        default={"error": "Failed to fetch user data"},
        context={"user_id": user_id}
    ) as handler:
        # ... fetch data from API ...
        return data
    
    if handler.error_occurred:
        # Log additional information
        logger.warning(f"Using cached data for user {user_id} due to error")
        return get_cached_data(user_id)
```

### Example 5: Async Error Handling

```python
from core.utils.error_handling import async_error_handler, ConnectionError

async def fetch_data_from_multiple_sources(sources):
    results = []
    
    for source in sources:
        # Use async error handler to handle exceptions
        data = await async_error_handler(
            fetch_from_source(source),
            error_types=[ConnectionError, TimeoutError],
            default=[],
            context={"source": source}
        )
        
        results.extend(data)
    
    return results
```

### Example 6: Custom Error Class

```python
from core.utils.error_handling import WiseflowError

class PaymentError(WiseflowError):
    """Error raised when a payment operation fails."""
    
    def __init__(self, message, payment_id=None, amount=None, cause=None):
        details = {
            "payment_id": payment_id,
            "amount": amount
        }
        super().__init__(message, details, cause)

# Usage
try:
    # ... payment processing ...
except Exception as e:
    raise PaymentError("Payment processing failed", payment_id="123", amount=100, cause=e)
```

