# WiseFlow Error Handling System

This document provides an overview of the WiseFlow error handling system, including error types, recovery strategies, and best practices for handling errors in your code.

## Table of Contents

1. [Introduction](#introduction)
2. [Error Hierarchy](#error-hierarchy)
3. [Error Manager](#error-manager)
4. [Recovery Strategies](#recovery-strategies)
5. [Parallel Error Handling](#parallel-error-handling)
6. [Best Practices](#best-practices)
7. [Examples](#examples)

## Introduction

The WiseFlow error handling system is designed to provide consistent error handling, reporting, and recovery mechanisms throughout the application. It consists of:

- A comprehensive hierarchy of error types
- A centralized error manager for handling and tracking errors
- Recovery strategies for different types of failures
- Integration with the event system for notifications
- Tools for handling errors in parallel operations

## Error Hierarchy

All WiseFlow errors inherit from the base `WiseflowError` class, which provides common functionality such as error details, cause tracking, and structured logging.

The error hierarchy is organized by domain:

### System Errors

- `SystemError`: Base class for system-level errors
  - `ConfigurationError`: Configuration errors
  - `StartupError`: Errors during system startup
  - `ShutdownError`: Errors during system shutdown
  - `ResourceError`: Resource-related errors
    - `MemoryError`: Insufficient memory
    - `DiskSpaceError`: Insufficient disk space
    - `CPUError`: CPU-related errors

### Network Errors

- `NetworkError`: Base class for network-related errors
  - `ConnectionError`: Connection failures
  - `TimeoutError`: Network timeouts
  - `APIError`: API call failures
  - `DNSError`: DNS resolution failures

### Data Errors

- `DataError`: Base class for data-related errors
  - `DataProcessingError`: Data processing failures
  - `DataValidationError`: Data validation failures
  - `DataCorruptionError`: Data corruption
  - `DataNotFoundError`: Data not found
  - `DataConversionError`: Data conversion failures

### Task Errors

- `TaskError`: Base class for task-related errors
  - `TaskExecutionError`: Task execution failures
  - `TaskTimeoutError`: Task timeouts
  - `TaskCancellationError`: Task cancellations
  - `TaskDependencyError`: Task dependency failures
  - `TaskNotFoundError`: Task not found

### Plugin Errors

- `PluginError`: Base class for plugin-related errors
  - `PluginLoadError`: Plugin loading failures
  - `PluginExecutionError`: Plugin execution failures
  - `PluginNotFoundError`: Plugin not found
  - `PluginConfigurationError`: Plugin configuration errors

### Security Errors

- `SecurityError`: Base class for security-related errors
  - `AuthenticationError`: Authentication failures
  - `AuthorizationError`: Authorization failures
  - `TokenError`: Token-related errors
  - `PermissionError`: Permission check failures

### Resource Errors

- `NotFoundError`: Resource not found
- `AlreadyExistsError`: Resource already exists
- `ValidationError`: Validation failures

### Parallel Processing Errors

- `ParallelError`: Base class for parallel processing errors
  - `ParallelExecutionError`: Parallel execution failures
  - `ParallelTimeoutError`: Parallel execution timeouts
  - `ParallelResourceError`: Parallel execution resource exhaustion
  - `ParallelCancellationError`: Parallel execution cancellations

### Recovery Errors

- `RecoveryError`: Base class for recovery-related errors
  - `RecoveryTimeoutError`: Recovery timeouts
  - `RecoveryFailedError`: Recovery failures
  - `MaxRetriesExceededError`: Maximum retries exceeded

### External Service Errors

- `ExternalServiceError`: Base class for external service errors
  - `DatabaseError`: Database operation failures
  - `CacheError`: Cache operation failures
  - `QueueError`: Queue operation failures
  - `StorageError`: Storage operation failures

## Error Manager

The `ErrorManager` class provides centralized error handling, tracking, and recovery. It's implemented as a singleton, so you can access it from anywhere in the code.

### Key Features

- Error tracking and frequency analysis
- Integration with the event system for notifications
- Customizable error handlers for specific error types
- Recovery strategy application
- Error logging and file saving

### Usage

```python
from core.utils.error_manager import error_manager, ErrorSeverity, RecoveryStrategy

# Handle an error
error_manager.handle_error(
    error=my_exception,
    context={"task_id": "123", "user_id": "456"},
    severity=ErrorSeverity.MEDIUM,
    recovery_strategy=RecoveryStrategy.RETRY,
    notify=True,
    log_level="error",
    save_to_file=True,
    max_recovery_attempts=3
)

# Register a custom error handler
def my_error_handler(error, context):
    # Handle the error
    return True  # Return True if handled, False otherwise

error_manager.register_error_handler(MyCustomError, my_error_handler)
```

## Recovery Strategies

The system supports several recovery strategies for different types of failures:

- `NONE`: No recovery, just log the error and continue
- `RETRY`: Retry the operation with the same parameters
- `RETRY_ALTERNATIVE`: Retry with alternative parameters or approach
- `SKIP`: Skip the current operation and continue with the next one
- `ROLLBACK`: Rollback to a previous state
- `DEGRADE`: Continue with reduced functionality
- `TERMINATE_TASK`: Terminate the current task but keep the system running
- `RESTART_COMPONENT`: Restart the system component
- `RESTART_SYSTEM`: Restart the entire system

### Choosing a Recovery Strategy

When choosing a recovery strategy, consider:

1. The severity of the error
2. The impact on the system
3. The likelihood of success
4. The cost of recovery

## Parallel Error Handling

The `ParallelManager` class provides error handling for parallel operations, including:

- Task dependency management
- Automatic retries
- Priority-based execution
- Resource management
- Comprehensive error reporting

### Usage

```python
from core.plugins.connectors.research.parallel_manager import ParallelManager, TaskPriority

# Create a parallel manager
manager = ParallelManager(max_workers=10)

# Add tasks
manager.add_task(
    task_id="task1",
    func=my_function,
    args=(arg1, arg2),
    kwargs={"param1": value1},
    dependencies=[],
    priority=TaskPriority.HIGH,
    max_retries=3
)

# Execute all tasks
results = await manager.execute_all(timeout=60, raise_on_failure=False)

# Get results and errors
all_results = manager.get_all_results()
all_errors = manager.get_all_errors()
```

### Utility Functions

The parallel manager also provides utility functions for common parallel operations:

```python
from core.plugins.connectors.research.parallel_manager import execute_in_parallel, parallel_map

# Execute multiple functions in parallel
results = await execute_in_parallel(
    functions=[func1, func2, func3],
    args_list=[(arg1_1, arg1_2), (arg2_1, arg2_2), (arg3_1, arg3_2)],
    max_workers=10
)

# Apply a function to each item in a list in parallel
results = await parallel_map(
    func=my_function,
    items=[item1, item2, item3],
    max_workers=10
)
```

## Best Practices

### 1. Use Specific Error Types

Always use the most specific error type for your exceptions. This allows for more targeted error handling and recovery.

```python
# Bad
raise Exception("Something went wrong")

# Good
raise DataValidationError("Invalid input data", {"field": "email", "value": value})
```

### 2. Include Contextual Information

Always include relevant context in your error details. This helps with debugging and recovery.

```python
raise TaskExecutionError(
    "Task execution failed",
    {
        "task_id": task_id,
        "step": current_step,
        "input_data": input_data
    },
    original_exception
)
```

### 3. Use Error Handling Decorators

Use the provided decorators for consistent error handling:

```python
from core.utils.error_manager import with_error_handling, ErrorSeverity, RecoveryStrategy

@with_error_handling(
    error_types=[DataError, NetworkError],
    severity=ErrorSeverity.MEDIUM,
    recovery_strategy=RecoveryStrategy.RETRY,
    max_recovery_attempts=3
)
def process_data(data):
    # Process data
    return result
```

### 4. Implement Retry Logic for Transient Errors

Use the retry decorator for operations that might fail due to transient issues:

```python
from core.utils.error_manager import retry

@retry(
    max_retries=3,
    retry_delay=1.0,
    backoff_factor=2.0,
    retryable_errors=[ConnectionError, TimeoutError]
)
async def fetch_data(url):
    # Fetch data
    return data
```

### 5. Handle Errors at the Appropriate Level

Handle errors at the level where you have enough context to make a decision:

```python
try:
    result = process_data(data)
except DataValidationError as e:
    # Handle validation error
    log_error(e)
    return default_result
except DataProcessingError as e:
    # Handle processing error
    error_manager.handle_error(e, {"data_id": data_id}, ErrorSeverity.HIGH, RecoveryStrategy.RETRY)
    raise
```

### 6. Use the Error Manager for Complex Recovery

For complex recovery scenarios, use the error manager:

```python
try:
    result = complex_operation()
except Exception as e:
    handled = error_manager.handle_error(
        e,
        {"operation": "complex_operation", "params": params},
        ErrorSeverity.HIGH,
        RecoveryStrategy.DEGRADE
    )
    
    if not handled:
        # Fall back to a simpler operation
        result = simple_operation()
```

### 7. Log Errors Consistently

Use the provided logging utilities for consistent error logging:

```python
from core.utils.error_handling import log_error

try:
    result = operation()
except Exception as e:
    log_error(e, "warning", {"operation": "operation", "params": params})
    # Handle the error
```

## Examples

### Basic Error Handling

```python
from core.utils.error_handling import DataValidationError, log_error

def validate_user(user_data):
    try:
        # Validate user data
        if not user_data.get("email"):
            raise DataValidationError(
                "Email is required",
                {"user_data": user_data}
            )
        
        # More validation...
        return True
    except DataValidationError as e:
        # Log the error
        log_error(e, "warning")
        return False
```

### Using the Error Manager

```python
from core.utils.error_manager import error_manager, ErrorSeverity, RecoveryStrategy

def process_payment(payment_data):
    try:
        # Process payment
        result = payment_processor.charge(payment_data)
        return result
    except Exception as e:
        # Handle the error with the error manager
        handled = error_manager.handle_error(
            e,
            {"payment_data": payment_data},
            ErrorSeverity.HIGH,
            RecoveryStrategy.RETRY,
            notify=True,
            save_to_file=True
        )
        
        if not handled:
            # Fall back to alternative payment processor
            try:
                result = alternative_payment_processor.charge(payment_data)
                return result
            except Exception as fallback_e:
                # Handle the fallback error
                error_manager.handle_error(
                    fallback_e,
                    {"payment_data": payment_data, "fallback": True},
                    ErrorSeverity.CRITICAL,
                    RecoveryStrategy.NONE
                )
                raise
```

### Parallel Processing with Error Handling

```python
from core.plugins.connectors.research.parallel_manager import ParallelManager, TaskPriority

async def process_documents(documents):
    # Create a parallel manager
    manager = ParallelManager(max_workers=10)
    
    # Add tasks for each document
    for i, doc in enumerate(documents):
        manager.add_task(
            task_id=f"process_doc_{i}",
            func=process_document,
            args=(doc,),
            priority=TaskPriority.NORMAL,
            max_retries=3
        )
    
    # Execute all tasks
    results = await manager.execute_all(timeout=300, raise_on_failure=False)
    
    # Get successful results
    processed_docs = manager.get_all_results()
    
    # Get errors
    errors = manager.get_all_errors()
    
    # Log errors
    for task_id, error in errors.items():
        log_error(error, "error", {"task_id": task_id})
    
    return processed_docs
```

### Custom Recovery Strategy

```python
from core.utils.error_manager import error_manager, ErrorSeverity, RecoveryStrategy

# Register a custom error handler
def database_error_handler(error, context):
    # Check if we can reconnect
    if isinstance(error, DatabaseError) and "connection" in context:
        try:
            # Try to reconnect
            connection = context["connection"]
            connection.reconnect()
            return True
        except Exception as reconnect_error:
            # Log the reconnection error
            log_error(reconnect_error, "error", {"original_error": str(error)})
    
    return False

# Register the handler
error_manager.register_error_handler(DatabaseError, database_error_handler)

# Use the handler
def get_user_data(user_id):
    connection = database.get_connection()
    
    try:
        # Get user data
        return connection.query(f"SELECT * FROM users WHERE id = {user_id}")
    except Exception as e:
        # Handle the error
        handled = error_manager.handle_error(
            e,
            {"connection": connection, "user_id": user_id},
            ErrorSeverity.MEDIUM,
            RecoveryStrategy.RETRY
        )
        
        if handled:
            # Try again
            return connection.query(f"SELECT * FROM users WHERE id = {user_id}")
        else:
            # Fall back to cache
            return cache.get(f"user:{user_id}")
```

