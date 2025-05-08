# Data Processing and Connector Module Fixes

This document outlines the fixes and improvements made to the data processing and connector modules in the Wiseflow project.

## Overview

The data processing and connector modules are responsible for collecting and processing data from various sources. These components had several issues that were causing runtime errors, including initialization problems, resource leaks, inconsistent error handling, and race conditions.

## Fixes Implemented

### 1. Connector Module Improvements

#### 1.1 Base Connector Class Enhancements
- Fixed initialization issues in the `ConnectorBase` class
- Added proper resource management with session cleanup
- Implemented consistent error handling across all methods
- Added tracking for error counts and last run time
- Improved status reporting with sensitive information filtering

#### 1.2 GitHub Connector Fixes
- Enhanced initialization with proper connection testing
- Improved error handling for API requests with specific error types
- Added timeout handling for network requests
- Implemented proper resource cleanup in shutdown method
- Added validation for configuration parameters
- Enhanced data collection with better error recovery

### 2. Data Processing Enhancements

#### 2.1 Processor Base Class
- Created a standardized `ProcessorBase` class for all processors
- Implemented consistent error handling and reporting
- Added batch processing capabilities with error recovery
- Added asynchronous processing support
- Implemented status reporting and metrics

#### 2.2 Text Processor Improvements
- Enhanced memory management with usage monitoring
- Improved content chunking for large datasets
- Added retry logic for LLM processing failures
- Enhanced error handling and reporting
- Improved JSON response parsing with better error recovery

### 3. Utility Classes for Common Functionality

#### 3.1 Concurrency Utilities
- Implemented async locks and semaphores for thread safety
- Added read-write locks for concurrent data access
- Created an async cache for improved performance
- Implemented a task manager for handling async operations
- Added timeout utilities for preventing hanging operations

#### 3.2 Error Handling Utilities
- Created retry decorators for automatic retry logic
- Implemented error capture and reporting
- Added safe execution wrappers for error recovery
- Created exception handling decorators for consistent error handling

#### 3.3 Data Validation Utilities
- Implemented validators for various data types
- Added schema validation for complex data structures
- Created validation utilities for data items and processed data
- Implemented custom validation functions

### 4. Integration with Event System

- Enhanced connector and processor integration with the event system
- Added event publishing for important operations
- Implemented resource monitoring events
- Added error reporting through events

## Testing

Comprehensive tests have been added to verify the fixes:

- `test_connector_fixes.py`: Tests for connector base class and GitHub connector fixes
- `test_processor_fixes.py`: Tests for processor base class and text processor fixes

## Usage Examples

### Using the Connector Base Class

```python
from core.connectors import ConnectorBase, DataItem

class MyConnector(ConnectorBase):
    name = "my_connector"
    description = "My custom connector"
    source_type = "custom"
    
    def __init__(self, config=None):
        super().__init__(config or {})
        # Initialize connector-specific attributes
    
    def initialize(self) -> bool:
        # Perform initialization
        return True
    
    def collect(self, params=None) -> List[DataItem]:
        # Collect data from source
        return [
            DataItem(
                source_id="custom-1",
                content="Custom content",
                metadata={"key": "value"}
            )
        ]
    
    def shutdown(self) -> bool:
        # Clean up resources
        return True
```

### Using the Processor Base Class

```python
from core.plugins.processors import ProcessorBase, ProcessedData
from core.connectors import DataItem

class MyProcessor(ProcessorBase):
    name = "my_processor"
    description = "My custom processor"
    processor_type = "custom"
    
    def __init__(self, config=None):
        super().__init__(config or {})
        # Initialize processor-specific attributes
    
    def process(self, data_item: DataItem, params=None) -> ProcessedData:
        # Process the data item
        return ProcessedData(
            original_item=data_item,
            processed_content=[
                {
                    "content": f"Processed: {data_item.content}",
                    "type": "text"
                }
            ],
            metadata={"source": data_item.source_id}
        )
```

### Using the Concurrency Utilities

```python
from core.utils.concurrency import AsyncLock, AsyncCache

# Using async lock
async def safe_operation():
    async with AsyncLock("my_lock"):
        # Thread-safe operation
        pass

# Using async cache
cache = AsyncCache(ttl=60.0)
await cache.set("key", "value")
value = await cache.get("key")
```

### Using the Error Handling Utilities

```python
from core.utils.error_handling import retry, handle_exceptions

# Using retry decorator
@retry(max_retries=3, retry_delay=1.0)
def operation_with_retry():
    # Operation that might fail
    pass

# Using exception handler
@handle_exceptions(error_types=ValueError, default_message="Invalid value")
def operation_with_error_handling():
    # Operation that might raise exceptions
    pass
```

### Using the Data Validation Utilities

```python
from core.utils.validation import StringValidator, DictValidator

# Validate a string
validator = StringValidator(field_name="username", min_length=3, max_length=20)
valid_username = validator.validate("user123")

# Validate a dictionary
schema = {
    "name": StringValidator(field_name="name", min_length=1),
    "age": NumberValidator(field_name="age", min_value=0)
}
validator = DictValidator(field_name="user", schema=schema, required_keys=["name"])
valid_user = validator.validate({"name": "John", "age": 30})
```

## Conclusion

These fixes address the identified issues in the data processing and connector modules, providing a more robust and reliable foundation for the Wiseflow project. The improvements include better error handling, resource management, and integration with the event system, as well as new utilities for concurrency, error handling, and data validation.

