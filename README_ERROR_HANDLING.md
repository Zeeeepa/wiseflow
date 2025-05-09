# WiseFlow Error Handling and Logging Improvements

This document outlines the improvements made to the error handling and logging systems in the WiseFlow project.

## Overview

The error handling and logging improvements focus on:

1. Standardizing error handling across the codebase
2. Enhancing logging with more context and structured formats
3. Providing utilities for common error handling patterns
4. Implementing retry mechanisms for transient errors
5. Documenting best practices for error handling and logging

## Key Components

### Error Handling

The error handling system has been improved with:

- **Enhanced WiseflowError Classes**: Added more specific error types and improved error context
- **Retry Mechanism**: Added retry functionality for transient errors
- **Error Handler Context Manager**: Improved context manager for complex error handling scenarios
- **Async Error Handling**: Added utilities for handling errors in async code

### Logging

The logging system has been improved with:

- **Enhanced Logging Configuration**: Added more configuration options for logging
- **Structured Logging**: Added support for structured logging in JSON format
- **Log Context**: Improved context management for adding context to logs
- **Log Execution Decorator**: Added decorator for automatically logging function calls
- **Log Method Calls Decorator**: Added decorator for automatically logging all method calls in a class

## Files Modified

- `core/utils/error_handling.py`: Enhanced error handling utilities
- `core/utils/logging_config.py`: Enhanced logging configuration
- `core/utils/general_utils.py`: Updated to use improved error handling and logging
- `dashboard/general_utils.py`: Updated to use improved error handling and logging
- `core/llms/openai_wrapper.py`: Updated to use improved error handling and logging

## Files Added

- `docs/error_handling_logging_guide.md`: Comprehensive guide for error handling and logging
- `examples/error_handling_logging_example.py`: Example script demonstrating the improved error handling and logging

## Usage Examples

### Error Handling

```python
from core.utils.error_handling import handle_exceptions, ValidationError

@handle_exceptions(
    error_types=[ValueError, TypeError],
    default_message="Failed to process data",
    log_error=True,
    reraise=False,
    default_return=[]
)
def process_data(data):
    if not isinstance(data, dict):
        raise ValidationError("Data must be a dictionary", {"provided_type": type(data).__name__})
    
    # Process data
    return processed_data
```

### Retry Mechanism

```python
from core.utils.error_handling import retry, ConnectionError

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

### Logging with Context

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

```python
from core.utils.logging_config import log_execution

@log_execution(log_args=True, log_result=True, level="DEBUG")
def calculate_total(items):
    total = sum(item.price for item in items)
    return total
```

## Documentation

For detailed documentation on the error handling and logging improvements, see:

- [Error Handling and Logging Guide](./docs/error_handling_logging_guide.md)
- [Error Handling and Logging Example](./examples/error_handling_logging_example.py)

## Benefits

The improved error handling and logging systems provide several benefits:

1. **Consistency**: Standardized error handling and logging across the codebase
2. **Robustness**: Better handling of errors and retries for transient failures
3. **Debuggability**: More context in logs and errors for easier debugging
4. **Maintainability**: Cleaner code with reusable error handling patterns
5. **Performance**: Optimized logging with structured formats and appropriate log levels

