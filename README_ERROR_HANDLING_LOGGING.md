# WiseFlow Error Handling and Logging Improvements

This PR implements comprehensive improvements to the error handling and logging system in WiseFlow. These improvements enhance reliability, debugging capabilities, and overall system robustness.

## Key Improvements

### 1. Centralized Logging Configuration

- Created a new `core/utils/logging_config.py` module for centralized logging configuration
- Standardized on `loguru` for all logging needs
- Added support for structured logging (JSON format)
- Implemented log rotation and retention policies
- Added separate error log file for easier troubleshooting

### 2. Enhanced Error Handling

- Improved the `WiseflowError` base class with better context support
- Added new error types for more specific error handling
- Enhanced the `handle_exceptions` decorator with better type support
- Added context managers for error handling
- Implemented async error handling utilities

### 3. Contextual Logging

- Added support for adding context to logs
- Implemented a context manager for temporary log context
- Improved error logging with structured context

### 4. Configuration Options

- Added new configuration options for logging
- Standardized log levels across the application
- Added support for environment variable configuration

### 5. Documentation

- Created comprehensive documentation for the error handling and logging system
- Added examples of best practices
- Provided code examples for common use cases

## Files Changed

- `core/utils/error_handling.py`: Enhanced error handling system
- `core/utils/logging_config.py`: New centralized logging configuration
- `core/config.py`: Added logging configuration options
- `core/imports.py`: Updated imports for new logging system
- `core/initialize.py`: Updated to use new error handling and logging
- `core/utils/general_utils.py`: Updated to use new logging system
- `docs/error_handling_logging.md`: New documentation
- `examples/error_handling_logging_example.py`: Example usage

## Usage Examples

### Logging Example

```python
from core.utils.logging_config import logger, get_logger, with_context, LogContext

# Get a module-specific logger
module_logger = get_logger(__name__)

# Basic logging
module_logger.info("This is an info message")
module_logger.error("This is an error message")

# Contextual logging
user_logger = with_context(user_id="123", action="login")
user_logger.info("User logged in")

# Context manager
with LogContext(request_id="abc123", endpoint="/api/data"):
    logger.info("Processing request")
    # ... do something ...
    logger.success("Request processed successfully")
```

### Error Handling Example

```python
from core.utils.error_handling import handle_exceptions, ErrorHandler, WiseflowError

# Using the decorator
@handle_exceptions(
    error_types=[ValueError, TypeError],
    default_message="Error processing data",
    log_error=True
)
def process_data(data):
    # ... do something ...
    return result

# Using the context manager
def process_request(request):
    with ErrorHandler(error_types=[Exception], default="default response") as handler:
        # ... do something that might raise an exception ...
        result = process_data(request.data)
        return result
    
    if handler.error_occurred:
        # Handle the error
        return handler.result

# Custom error
class PaymentError(WiseflowError):
    def __init__(self, message, payment_id=None, amount=None, cause=None):
        details = {"payment_id": payment_id, "amount": amount}
        super().__init__(message, details, cause)
```

## Configuration

The logging system can be configured using the following environment variables or configuration settings:

```
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_TO_CONSOLE=true
LOG_DIR=/path/to/logs
STRUCTURED_LOGGING=false
LOG_ROTATION=50 MB
LOG_RETENTION=10 days
```

## Documentation

For detailed documentation, see [docs/error_handling_logging.md](docs/error_handling_logging.md).

For example usage, see [examples/error_handling_logging_example.py](examples/error_handling_logging_example.py).

