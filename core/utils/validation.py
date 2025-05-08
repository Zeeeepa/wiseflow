"""
Validation utilities for WiseFlow.

This module provides validation functions and classes for ensuring data integrity
and proper configuration throughout the WiseFlow system.
"""

import os
import re
import json
import jsonschema
from typing import Any, Dict, List, Optional, Union, Callable
from pydantic import BaseModel, ValidationError, validator
from datetime import datetime

# Schema validation
def validate_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """
    Validate data against a JSON schema.
    
    Args:
        data: The data to validate
        schema: The JSON schema to validate against
        
    Returns:
        bool: True if validation succeeds, False otherwise
    """
    try:
        jsonschema.validate(instance=data, schema=schema)
        return True
    except jsonschema.exceptions.ValidationError:
        return False


def validate_config_file(config_path: str, schema_path: str) -> Dict[str, Any]:
    """
    Validate a configuration file against a schema.
    
    Args:
        config_path: Path to the configuration file
        schema_path: Path to the schema file
        
    Returns:
        Dict: The validated configuration
        
    Raises:
        FileNotFoundError: If the config or schema file is not found
        jsonschema.exceptions.ValidationError: If validation fails
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    
    with open(schema_path, 'r') as schema_file:
        schema = json.load(schema_file)
    
    jsonschema.validate(instance=config, schema=schema)
    return config


# Type validation
def validate_type(value: Any, expected_type: type) -> bool:
    """
    Validate that a value is of the expected type.
    
    Args:
        value: The value to validate
        expected_type: The expected type
        
    Returns:
        bool: True if validation succeeds, False otherwise
    """
    return isinstance(value, expected_type)


def validate_types(values: Dict[str, Any], type_map: Dict[str, type]) -> bool:
    """
    Validate that values match their expected types.
    
    Args:
        values: Dictionary of values to validate
        type_map: Dictionary mapping keys to expected types
        
    Returns:
        bool: True if all validations succeed, False otherwise
    """
    for key, expected_type in type_map.items():
        if key not in values:
            return False
        if not validate_type(values[key], expected_type):
            return False
    return True


# Value validation
def validate_range(value: Union[int, float], min_value: Optional[Union[int, float]] = None, 
                  max_value: Optional[Union[int, float]] = None) -> bool:
    """
    Validate that a numeric value is within a specified range.
    
    Args:
        value: The value to validate
        min_value: The minimum allowed value (inclusive)
        max_value: The maximum allowed value (inclusive)
        
    Returns:
        bool: True if validation succeeds, False otherwise
    """
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def validate_string_pattern(value: str, pattern: str) -> bool:
    """
    Validate that a string matches a regular expression pattern.
    
    Args:
        value: The string to validate
        pattern: The regular expression pattern
        
    Returns:
        bool: True if validation succeeds, False otherwise
    """
    return bool(re.match(pattern, value))


def validate_url(url: str) -> bool:
    """
    Validate that a string is a valid URL.
    
    Args:
        url: The URL to validate
        
    Returns:
        bool: True if validation succeeds, False otherwise
    """
    pattern = r'^(https?|ftp)://[^\s/$.?#].[^\s]*$'
    return validate_string_pattern(url, pattern)


def validate_email(email: str) -> bool:
    """
    Validate that a string is a valid email address.
    
    Args:
        email: The email to validate
        
    Returns:
        bool: True if validation succeeds, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return validate_string_pattern(email, pattern)


def validate_date_format(date_str: str, format_str: str = "%Y-%m-%d") -> bool:
    """
    Validate that a string is a valid date in the specified format.
    
    Args:
        date_str: The date string to validate
        format_str: The expected date format
        
    Returns:
        bool: True if validation succeeds, False otherwise
    """
    try:
        datetime.strptime(date_str, format_str)
        return True
    except ValueError:
        return False


# Custom validation
def validate_with_function(value: Any, validation_func: Callable[[Any], bool]) -> bool:
    """
    Validate a value using a custom validation function.
    
    Args:
        value: The value to validate
        validation_func: A function that takes the value and returns a boolean
        
    Returns:
        bool: True if validation succeeds, False otherwise
    """
    return validation_func(value)


# Validation error handling
class ValidationResult:
    """Class to represent the result of a validation operation."""
    
    def __init__(self, is_valid: bool, errors: Optional[List[str]] = None):
        """
        Initialize a ValidationResult.
        
        Args:
            is_valid: Whether the validation succeeded
            errors: List of error messages if validation failed
        """
        self.is_valid = is_valid
        self.errors = errors or []
    
    def __bool__(self):
        """Allow using the result in boolean context."""
        return self.is_valid
    
    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)
        self.is_valid = False
    
    def merge(self, other: 'ValidationResult'):
        """Merge with another ValidationResult."""
        if not other.is_valid:
            self.is_valid = False
            self.errors.extend(other.errors)


# Pydantic models for common data structures
class Entity(BaseModel):
    """Base model for entities in the system."""
    entity_id: str
    name: str
    entity_type: str
    sources: List[str]
    metadata: Dict[str, Any] = {}
    
    @validator('entity_id')
    def validate_entity_id(cls, v):
        """Validate entity_id format."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('entity_id must contain only alphanumeric characters, underscores, and hyphens')
        return v


class Relationship(BaseModel):
    """Base model for relationships between entities."""
    relationship_id: str
    source_id: str
    target_id: str
    relationship_type: str
    metadata: Dict[str, Any] = {}
    
    @validator('relationship_id')
    def validate_relationship_id(cls, v):
        """Validate relationship_id format."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('relationship_id must contain only alphanumeric characters, underscores, and hyphens')
        return v


class Reference(BaseModel):
    """Base model for references."""
    reference_id: str
    focus_id: str
    content: str
    reference_type: str
    metadata: Dict[str, Any] = {}
    
    @validator('reference_id')
    def validate_reference_id(cls, v):
        """Validate reference_id format."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('reference_id must contain only alphanumeric characters, underscores, and hyphens')
        return v


class Task(BaseModel):
    """Base model for tasks."""
    task_id: str
    name: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}
    
    @validator('status')
    def validate_status(cls, v):
        """Validate task status."""
        valid_statuses = ['pending', 'running', 'completed', 'failed', 'cancelled']
        if v not in valid_statuses:
            raise ValueError(f'status must be one of {valid_statuses}')
        return v

