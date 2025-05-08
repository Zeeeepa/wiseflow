# WiseFlow Validation Rules

This document describes the validation rules used in the WiseFlow system. It covers schema validation, type validation, value validation, and custom validation rules.

## Table of Contents

1. [Introduction](#introduction)
2. [Schema Validation](#schema-validation)
   - [Configuration Schema](#configuration-schema)
   - [Entity Schema](#entity-schema)
   - [Relationship Schema](#relationship-schema)
   - [Reference Schema](#reference-schema)
   - [Task Schema](#task-schema)
3. [Type Validation](#type-validation)
4. [Value Validation](#value-validation)
   - [Range Validation](#range-validation)
   - [String Pattern Validation](#string-pattern-validation)
   - [URL Validation](#url-validation)
   - [Email Validation](#email-validation)
   - [Date Format Validation](#date-format-validation)
5. [Custom Validation](#custom-validation)
6. [Validation Error Handling](#validation-error-handling)
7. [Implementing Validation](#implementing-validation)
   - [Input Validation](#input-validation)
   - [Configuration Validation](#configuration-validation)
   - [Data Structure Validation](#data-structure-validation)

## Introduction

Validation is a critical aspect of the WiseFlow system, ensuring data integrity, security, and reliability. The system uses multiple validation mechanisms:

- **Schema Validation**: Validates data structures against JSON schemas
- **Type Validation**: Ensures values have the correct types
- **Value Validation**: Checks that values are within acceptable ranges or formats
- **Custom Validation**: Implements complex validation logic

## Schema Validation

Schema validation uses JSON Schema to validate data structures. The following schemas are defined in `core/utils/schemas.py`:

### Configuration Schema

The configuration schema validates the main configuration file:

```json
{
  "type": "object",
  "properties": {
    "api_keys": {
      "type": "object",
      "properties": {
        "openai": {"type": "string"},
        "exa": {"type": "string"},
        "zhipu": {"type": "string"},
        "anthropic": {"type": "string"}
      },
      "additionalProperties": true
    },
    "llm": {
      "type": "object",
      "properties": {
        "default_model": {"type": "string"},
        "temperature": {"type": "number", "minimum": 0, "maximum": 1},
        "max_tokens": {"type": "integer", "minimum": 1},
        "timeout": {"type": "integer", "minimum": 1}
      },
      "required": ["default_model"],
      "additionalProperties": true
    },
    "plugins": {
      "type": "object",
      "properties": {
        "enabled": {"type": "array", "items": {"type": "string"}},
        "paths": {"type": "array", "items": {"type": "string"}}
      },
      "additionalProperties": true
    },
    "connectors": {
      "type": "object",
      "additionalProperties": {
        "type": "object"
      }
    },
    "logging": {
      "type": "object",
      "properties": {
        "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
        "file": {"type": "string"}
      },
      "additionalProperties": true
    },
    "storage": {
      "type": "object",
      "properties": {
        "path": {"type": "string"},
        "type": {"type": "string", "enum": ["local", "s3", "azure"]}
      },
      "additionalProperties": true
    },
    "web_crawler": {
      "type": "object",
      "properties": {
        "timeout": {"type": "integer", "minimum": 1},
        "max_retries": {"type": "integer", "minimum": 0},
        "user_agent": {"type": "string"},
        "cache_mode": {"type": "string", "enum": ["DISABLED", "READ_ONLY", "WRITE_ONLY", "READ_WRITE"]}
      },
      "additionalProperties": true
    }
  },
  "required": ["llm"],
  "additionalProperties": true
}
```

### Entity Schema

The entity schema validates entity data structures:

```json
{
  "type": "object",
  "properties": {
    "entity_id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
    "name": {"type": "string"},
    "entity_type": {"type": "string"},
    "sources": {"type": "array", "items": {"type": "string"}},
    "metadata": {"type": "object"}
  },
  "required": ["entity_id", "name", "entity_type", "sources"],
  "additionalProperties": false
}
```

### Relationship Schema

The relationship schema validates relationship data structures:

```json
{
  "type": "object",
  "properties": {
    "relationship_id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
    "source_id": {"type": "string"},
    "target_id": {"type": "string"},
    "relationship_type": {"type": "string"},
    "metadata": {"type": "object"}
  },
  "required": ["relationship_id", "source_id", "target_id", "relationship_type"],
  "additionalProperties": false
}
```

### Reference Schema

The reference schema validates reference data structures:

```json
{
  "type": "object",
  "properties": {
    "reference_id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
    "focus_id": {"type": "string"},
    "content": {"type": "string"},
    "reference_type": {"type": "string"},
    "metadata": {"type": "object"}
  },
  "required": ["reference_id", "focus_id", "content", "reference_type"],
  "additionalProperties": false
}
```

### Task Schema

The task schema validates task data structures:

```json
{
  "type": "object",
  "properties": {
    "task_id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
    "name": {"type": "string"},
    "description": {"type": ["string", "null"]},
    "status": {"type": "string", "enum": ["pending", "running", "completed", "failed", "cancelled"]},
    "created_at": {"type": "string", "format": "date-time"},
    "updated_at": {"type": ["string", "null"], "format": "date-time"},
    "metadata": {"type": "object"}
  },
  "required": ["task_id", "name", "status", "created_at"],
  "additionalProperties": false
}
```

## Type Validation

Type validation ensures values have the correct types. The following functions are provided in `core/utils/validation.py`:

- `validate_type(value, expected_type)`: Validates that a value is of the expected type
- `validate_types(values, type_map)`: Validates that values match their expected types

Example:

```python
# Validate a single value
validate_type("test", str)  # True
validate_type(123, int)  # True
validate_type("test", int)  # False

# Validate multiple values
values = {
    "name": "Test",
    "age": 30,
    "is_active": True
}
type_map = {
    "name": str,
    "age": int,
    "is_active": bool
}
validate_types(values, type_map)  # True
```

## Value Validation

Value validation checks that values are within acceptable ranges or formats.

### Range Validation

Range validation ensures numeric values are within a specified range:

```python
validate_range(5, min_value=0, max_value=10)  # True
validate_range(-1, min_value=0, max_value=10)  # False
validate_range(11, min_value=0, max_value=10)  # False
```

### String Pattern Validation

String pattern validation ensures strings match a regular expression pattern:

```python
validate_string_pattern("abc123", r"^[a-z0-9]+$")  # True
validate_string_pattern("ABC123", r"^[a-z0-9]+$")  # False
```

### URL Validation

URL validation ensures strings are valid URLs:

```python
validate_url("https://example.com")  # True
validate_url("http://example.com/path?query=value")  # True
validate_url("example.com")  # False
```

### Email Validation

Email validation ensures strings are valid email addresses:

```python
validate_email("user@example.com")  # True
validate_email("user.name@example.co.uk")  # True
validate_email("user@")  # False
```

### Date Format Validation

Date format validation ensures strings are valid dates in the specified format:

```python
validate_date_format("2023-01-01", "%Y-%m-%d")  # True
validate_date_format("01/01/2023", "%m/%d/%Y")  # True
validate_date_format("2023-01-01", "%m/%d/%Y")  # False
```

## Custom Validation

Custom validation allows for complex validation logic:

```python
def is_valid_password(password):
    return (len(password) >= 8 and 
            any(c.isupper() for c in password) and 
            any(c.islower() for c in password) and 
            any(c.isdigit() for c in password))

validate_with_function("Password123", is_valid_password)  # True
validate_with_function("password", is_valid_password)  # False
```

## Validation Error Handling

Validation errors are handled using the `ValidationResult` class and the `ValidationError` exception:

```python
# Using ValidationResult
result = ValidationResult(True)
if not validate_url(url):
    result.add_error(f"Invalid URL: {url}")
if not validate_email(email):
    result.add_error(f"Invalid email: {email}")
if result:
    # Validation passed
else:
    # Validation failed, errors in result.errors

# Using ValidationError
try:
    if not validate_url(url):
        raise ValidationError(f"Invalid URL: {url}")
except ValidationError as e:
    # Handle validation error
```

## Implementing Validation

### Input Validation

Input validation should be performed at the entry points of the system:

```python
def process_user_input(data):
    """Process user input."""
    # Validate input
    if not validate_input(data, USER_INPUT_SCHEMA):
        raise ValidationError("Invalid user input")
    
    # Process input
    # ...
```

### Configuration Validation

Configuration validation should be performed when loading configuration files:

```python
def load_config(config_path):
    """Load configuration from a file."""
    # Validate configuration
    config = validate_config_file(config_path, CONFIG_SCHEMA_PATH)
    
    # Use configuration
    # ...
```

### Data Structure Validation

Data structure validation should be performed when creating or modifying data structures:

```python
def create_entity(entity_data):
    """Create an entity."""
    # Validate entity data
    if not validate_schema(entity_data, ENTITY_SCHEMA):
        raise ValidationError("Invalid entity data")
    
    # Create entity
    entity = Entity(**entity_data)
    return entity
```

