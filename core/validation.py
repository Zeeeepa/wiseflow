#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Validation module for Wiseflow.

This module provides utilities for validating inputs and outputs throughout the codebase.
It includes validators for common data types, structures, and domain-specific objects.
"""

import re
import json
import logging
import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Tuple, Callable, TypeVar, Generic, Type

from core.event_system import publish_sync, Event, EventType

# Set up logging
logger = logging.getLogger(__name__)

# Type variable for generic validation
T = TypeVar('T')


class ValidationLevel(Enum):
    """Validation level for determining how strict validation should be."""
    STRICT = "strict"  # Raise exceptions for validation failures
    WARNING = "warning"  # Log warnings for validation failures
    SILENT = "silent"  # Silently return validation result without logging


class ValidationResult(Generic[T]):
    """Result of a validation operation."""
    
    def __init__(
        self,
        is_valid: bool,
        value: Optional[T] = None,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None
    ):
        """Initialize a ValidationResult.
        
        Args:
            is_valid: Whether the validation passed
            value: The validated value (possibly transformed)
            errors: List of error messages if validation failed
            warnings: List of warning messages (even if validation passed)
        """
        self.is_valid = is_valid
        self.value = value
        self.errors = errors or []
        self.warnings = warnings or []
    
    def __bool__(self) -> bool:
        """Return whether the validation passed."""
        return self.is_valid
    
    def __str__(self) -> str:
        """Return a string representation of the validation result."""
        if self.is_valid:
            return f"Valid: {self.value}"
        return f"Invalid: {', '.join(self.errors)}"


class Validator:
    """Base class for validators."""
    
    def __init__(self, level: ValidationLevel = ValidationLevel.STRICT):
        """Initialize a validator.
        
        Args:
            level: The validation level to use
        """
        self.level = level
    
    def validate(self, value: Any) -> ValidationResult:
        """Validate a value.
        
        Args:
            value: The value to validate
            
        Returns:
            A ValidationResult object
        """
        raise NotImplementedError("Subclasses must implement validate()")
    
    def __call__(self, value: Any) -> ValidationResult:
        """Call the validator on a value.
        
        Args:
            value: The value to validate
            
        Returns:
            A ValidationResult object
        """
        result = self.validate(value)
        
        # Handle validation result based on level
        if not result.is_valid:
            if self.level == ValidationLevel.STRICT:
                error_msg = "; ".join(result.errors)
                raise ValueError(f"Validation failed: {error_msg}")
            elif self.level == ValidationLevel.WARNING:
                for error in result.errors:
                    logger.warning(f"Validation error: {error}")
        
        # Log warnings regardless of validation result
        if result.warnings and self.level != ValidationLevel.SILENT:
            for warning in result.warnings:
                logger.warning(f"Validation warning: {warning}")
        
        # Publish validation event
        self._publish_validation_event(result)
        
        return result
    
    def _publish_validation_event(self, result: ValidationResult) -> None:
        """Publish a validation event.
        
        Args:
            result: The validation result
        """
        event_data = {
            "validator": self.__class__.__name__,
            "is_valid": result.is_valid,
            "errors": result.errors,
            "warnings": result.warnings
        }
        
        event = Event(
            event_type=EventType.VALIDATION_RESULT,
            data=event_data,
            source="validation"
        )
        
        publish_sync(event)


class TypeValidator(Validator):
    """Validator for checking the type of a value."""
    
    def __init__(
        self,
        expected_type: Union[Type, Tuple[Type, ...]],
        level: ValidationLevel = ValidationLevel.STRICT
    ):
        """Initialize a TypeValidator.
        
        Args:
            expected_type: The expected type or tuple of types
            level: The validation level to use
        """
        super().__init__(level)
        self.expected_type = expected_type
    
    def validate(self, value: Any) -> ValidationResult:
        """Validate that a value is of the expected type.
        
        Args:
            value: The value to validate
            
        Returns:
            A ValidationResult object
        """
        if isinstance(value, self.expected_type):
            return ValidationResult(True, value)
        
        if isinstance(self.expected_type, tuple):
            expected_type_names = [t.__name__ for t in self.expected_type]
            expected_type_str = " or ".join(expected_type_names)
        else:
            expected_type_str = self.expected_type.__name__
        
        actual_type = type(value).__name__
        error = f"Expected type {expected_type_str}, got {actual_type}"
        
        return ValidationResult(False, None, [error])


class RangeValidator(Validator):
    """Validator for checking that a numeric value is within a range."""
    
    def __init__(
        self,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        inclusive: bool = True,
        level: ValidationLevel = ValidationLevel.STRICT
    ):
        """Initialize a RangeValidator.
        
        Args:
            min_value: The minimum allowed value (or None for no minimum)
            max_value: The maximum allowed value (or None for no maximum)
            inclusive: Whether the range bounds are inclusive
            level: The validation level to use
        """
        super().__init__(level)
        self.min_value = min_value
        self.max_value = max_value
        self.inclusive = inclusive
        
        # Validate that at least one bound is specified
        if min_value is None and max_value is None:
            raise ValueError("At least one of min_value or max_value must be specified")
    
    def validate(self, value: Union[int, float]) -> ValidationResult:
        """Validate that a value is within the specified range.
        
        Args:
            value: The value to validate
            
        Returns:
            A ValidationResult object
        """
        # Check type first
        if not isinstance(value, (int, float)):
            return ValidationResult(
                False,
                None,
                [f"Expected numeric value, got {type(value).__name__}"]
            )
        
        errors = []
        
        # Check minimum bound
        if self.min_value is not None:
            if self.inclusive:
                if value < self.min_value:
                    errors.append(f"Value {value} is less than minimum {self.min_value}")
            else:
                if value <= self.min_value:
                    errors.append(f"Value {value} is less than or equal to minimum {self.min_value}")
        
        # Check maximum bound
        if self.max_value is not None:
            if self.inclusive:
                if value > self.max_value:
                    errors.append(f"Value {value} is greater than maximum {self.max_value}")
            else:
                if value >= self.max_value:
                    errors.append(f"Value {value} is greater than or equal to maximum {self.max_value}")
        
        if errors:
            return ValidationResult(False, None, errors)
        
        return ValidationResult(True, value)


class LengthValidator(Validator):
    """Validator for checking the length of a value."""
    
    def __init__(
        self,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        level: ValidationLevel = ValidationLevel.STRICT
    ):
        """Initialize a LengthValidator.
        
        Args:
            min_length: The minimum allowed length (or None for no minimum)
            max_length: The maximum allowed length (or None for no maximum)
            level: The validation level to use
        """
        super().__init__(level)
        self.min_length = min_length
        self.max_length = max_length
        
        # Validate that at least one bound is specified
        if min_length is None and max_length is None:
            raise ValueError("At least one of min_length or max_length must be specified")
        
        # Validate that bounds are non-negative
        if min_length is not None and min_length < 0:
            raise ValueError("min_length must be non-negative")
        if max_length is not None and max_length < 0:
            raise ValueError("max_length must be non-negative")
        
        # Validate that min_length <= max_length if both are specified
        if min_length is not None and max_length is not None and min_length > max_length:
            raise ValueError("min_length must be less than or equal to max_length")
    
    def validate(self, value: Any) -> ValidationResult:
        """Validate that a value has the expected length.
        
        Args:
            value: The value to validate
            
        Returns:
            A ValidationResult object
        """
        # Check if value has a length
        try:
            length = len(value)
        except (TypeError, AttributeError):
            return ValidationResult(
                False,
                None,
                [f"Value of type {type(value).__name__} does not have a length"]
            )
        
        errors = []
        
        # Check minimum length
        if self.min_length is not None and length < self.min_length:
            errors.append(f"Length {length} is less than minimum {self.min_length}")
        
        # Check maximum length
        if self.max_length is not None and length > self.max_length:
            errors.append(f"Length {length} is greater than maximum {self.max_length}")
        
        if errors:
            return ValidationResult(False, None, errors)
        
        return ValidationResult(True, value)


class PatternValidator(Validator):
    """Validator for checking that a string matches a pattern."""
    
    def __init__(
        self,
        pattern: Union[str, re.Pattern],
        level: ValidationLevel = ValidationLevel.STRICT
    ):
        """Initialize a PatternValidator.
        
        Args:
            pattern: The regex pattern to match against
            level: The validation level to use
        """
        super().__init__(level)
        
        if isinstance(pattern, str):
            self.pattern = re.compile(pattern)
        else:
            self.pattern = pattern
    
    def validate(self, value: str) -> ValidationResult:
        """Validate that a string matches the pattern.
        
        Args:
            value: The string to validate
            
        Returns:
            A ValidationResult object
        """
        # Check type first
        if not isinstance(value, str):
            return ValidationResult(
                False,
                None,
                [f"Expected string, got {type(value).__name__}"]
            )
        
        if self.pattern.match(value):
            return ValidationResult(True, value)
        
        return ValidationResult(
            False,
            None,
            [f"String '{value}' does not match pattern '{self.pattern.pattern}'"]
        )


class EnumValidator(Validator):
    """Validator for checking that a value is a member of an enumeration."""
    
    def __init__(
        self,
        enum_class: Type[Enum],
        level: ValidationLevel = ValidationLevel.STRICT
    ):
        """Initialize an EnumValidator.
        
        Args:
            enum_class: The Enum class to validate against
            level: The validation level to use
        """
        super().__init__(level)
        self.enum_class = enum_class
    
    def validate(self, value: Any) -> ValidationResult:
        """Validate that a value is a member of the enumeration.
        
        Args:
            value: The value to validate
            
        Returns:
            A ValidationResult object
        """
        # Check if value is an instance of the enum
        if isinstance(value, self.enum_class):
            return ValidationResult(True, value)
        
        # Check if value is a valid enum value
        try:
            enum_value = self.enum_class(value)
            return ValidationResult(True, enum_value)
        except ValueError:
            pass
        
        # Check if value is a valid enum name
        if isinstance(value, str):
            try:
                enum_value = self.enum_class[value]
                return ValidationResult(True, enum_value)
            except KeyError:
                pass
        
        # Value is not a valid enum member
        valid_values = [e.value for e in self.enum_class]
        valid_names = [e.name for e in self.enum_class]
        
        return ValidationResult(
            False,
            None,
            [f"Value '{value}' is not a valid member of {self.enum_class.__name__}. "
             f"Valid values: {valid_values}, valid names: {valid_names}"]
        )


class SchemaValidator(Validator):
    """Validator for checking that a dictionary conforms to a schema."""
    
    def __init__(
        self,
        schema: Dict[str, Dict[str, Any]],
        allow_extra_fields: bool = False,
        level: ValidationLevel = ValidationLevel.STRICT
    ):
        """Initialize a SchemaValidator.
        
        Args:
            schema: The schema to validate against
            allow_extra_fields: Whether to allow fields not in the schema
            level: The validation level to use
        """
        super().__init__(level)
        self.schema = schema
        self.allow_extra_fields = allow_extra_fields
    
    def validate(self, value: Dict[str, Any]) -> ValidationResult:
        """Validate that a dictionary conforms to the schema.
        
        Args:
            value: The dictionary to validate
            
        Returns:
            A ValidationResult object
        """
        # Check type first
        if not isinstance(value, dict):
            return ValidationResult(
                False,
                None,
                [f"Expected dictionary, got {type(value).__name__}"]
            )
        
        errors = []
        warnings = []
        
        # Check for required fields
        for field_name, field_schema in self.schema.items():
            required = field_schema.get("required", False)
            
            if required and field_name not in value:
                errors.append(f"Required field '{field_name}' is missing")
        
        # Check for extra fields
        if not self.allow_extra_fields:
            extra_fields = set(value.keys()) - set(self.schema.keys())
            if extra_fields:
                errors.append(f"Extra fields not allowed: {', '.join(extra_fields)}")
        
        # Validate field values
        for field_name, field_value in value.items():
            if field_name in self.schema:
                field_schema = self.schema[field_name]
                field_type = field_schema.get("type")
                
                # Check field type
                if field_type and not isinstance(field_value, field_type):
                    errors.append(
                        f"Field '{field_name}' has incorrect type. "
                        f"Expected {field_type.__name__}, got {type(field_value).__name__}"
                    )
                
                # Check field validator
                validator = field_schema.get("validator")
                if validator:
                    field_result = validator(field_value)
                    if not field_result.is_valid:
                        for error in field_result.errors:
                            errors.append(f"Field '{field_name}': {error}")
                    
                    for warning in field_result.warnings:
                        warnings.append(f"Field '{field_name}': {warning}")
        
        if errors:
            return ValidationResult(False, None, errors, warnings)
        
        return ValidationResult(True, value, [], warnings)


class ListValidator(Validator):
    """Validator for checking that each item in a list meets certain criteria."""
    
    def __init__(
        self,
        item_validator: Validator,
        level: ValidationLevel = ValidationLevel.STRICT
    ):
        """Initialize a ListValidator.
        
        Args:
            item_validator: The validator to apply to each item
            level: The validation level to use
        """
        super().__init__(level)
        self.item_validator = item_validator
    
    def validate(self, value: List[Any]) -> ValidationResult:
        """Validate that each item in the list meets the criteria.
        
        Args:
            value: The list to validate
            
        Returns:
            A ValidationResult object
        """
        # Check type first
        if not isinstance(value, list):
            return ValidationResult(
                False,
                None,
                [f"Expected list, got {type(value).__name__}"]
            )
        
        errors = []
        warnings = []
        valid_items = []
        
        # Validate each item
        for i, item in enumerate(value):
            item_result = self.item_validator(item)
            
            if not item_result.is_valid:
                for error in item_result.errors:
                    errors.append(f"Item {i}: {error}")
            else:
                valid_items.append(item_result.value)
            
            for warning in item_result.warnings:
                warnings.append(f"Item {i}: {warning}")
        
        if errors:
            return ValidationResult(False, None, errors, warnings)
        
        return ValidationResult(True, valid_items, [], warnings)


class URLValidator(Validator):
    """Validator for checking that a string is a valid URL."""
    
    def __init__(
        self,
        schemes: Optional[List[str]] = None,
        require_scheme: bool = True,
        require_netloc: bool = True,
        level: ValidationLevel = ValidationLevel.STRICT
    ):
        """Initialize a URLValidator.
        
        Args:
            schemes: List of allowed schemes (e.g., ['http', 'https'])
            require_scheme: Whether to require a scheme
            require_netloc: Whether to require a network location
            level: The validation level to use
        """
        super().__init__(level)
        self.schemes = schemes or ["http", "https"]
        self.require_scheme = require_scheme
        self.require_netloc = require_netloc
        
        # Compile regex for URL validation
        scheme_pattern = r"(?P<scheme>[a-z][a-z0-9+.-]*)://" if require_scheme else r"(?P<scheme>[a-z][a-z0-9+.-]*://)?"
        netloc_pattern = r"(?P<netloc>[a-z0-9.-]+(?::[0-9]+)?)" if require_netloc else r"(?P<netloc>[a-z0-9.-]+(?::[0-9]+)?)?"
        self.pattern = re.compile(
            rf"^{scheme_pattern}{netloc_pattern}(?P<path>/[^?#]*)?(?P<query>\?[^#]*)?(?P<fragment>#.*)?$",
            re.IGNORECASE
        )
    
    def validate(self, value: str) -> ValidationResult:
        """Validate that a string is a valid URL.
        
        Args:
            value: The string to validate
            
        Returns:
            A ValidationResult object
        """
        # Check type first
        if not isinstance(value, str):
            return ValidationResult(
                False,
                None,
                [f"Expected string, got {type(value).__name__}"]
            )
        
        # Match URL pattern
        match = self.pattern.match(value)
        if not match:
            return ValidationResult(
                False,
                None,
                [f"String '{value}' is not a valid URL"]
            )
        
        # Check scheme
        scheme = match.group("scheme")
        if scheme:
            scheme = scheme.rstrip(":/")
            if self.schemes and scheme not in self.schemes:
                return ValidationResult(
                    False,
                    None,
                    [f"URL scheme '{scheme}' is not allowed. Allowed schemes: {', '.join(self.schemes)}"]
                )
        elif self.require_scheme:
            return ValidationResult(
                False,
                None,
                ["URL scheme is required"]
            )
        
        # Check netloc
        netloc = match.group("netloc")
        if not netloc and self.require_netloc:
            return ValidationResult(
                False,
                None,
                ["URL network location is required"]
            )
        
        return ValidationResult(True, value)


class DateTimeValidator(Validator):
    """Validator for checking that a string is a valid date/time."""
    
    def __init__(
        self,
        format_str: Optional[str] = None,
        min_date: Optional[datetime.datetime] = None,
        max_date: Optional[datetime.datetime] = None,
        level: ValidationLevel = ValidationLevel.STRICT
    ):
        """Initialize a DateTimeValidator.
        
        Args:
            format_str: The datetime format string (or None to use ISO format)
            min_date: The minimum allowed date (or None for no minimum)
            max_date: The maximum allowed date (or None for no maximum)
            level: The validation level to use
        """
        super().__init__(level)
        self.format_str = format_str
        self.min_date = min_date
        self.max_date = max_date
    
    def validate(self, value: Union[str, datetime.datetime]) -> ValidationResult:
        """Validate that a value is a valid date/time.
        
        Args:
            value: The value to validate (string or datetime)
            
        Returns:
            A ValidationResult object
        """
        # If value is already a datetime, use it directly
        if isinstance(value, datetime.datetime):
            dt = value
        # Otherwise, parse the string
        elif isinstance(value, str):
            try:
                if self.format_str:
                    dt = datetime.datetime.strptime(value, self.format_str)
                else:
                    dt = datetime.datetime.fromisoformat(value)
            except ValueError as e:
                return ValidationResult(
                    False,
                    None,
                    [f"Invalid datetime format: {str(e)}"]
                )
        else:
            return ValidationResult(
                False,
                None,
                [f"Expected string or datetime, got {type(value).__name__}"]
            )
        
        errors = []
        
        # Check minimum date
        if self.min_date and dt < self.min_date:
            errors.append(f"Datetime {dt} is before minimum {self.min_date}")
        
        # Check maximum date
        if self.max_date and dt > self.max_date:
            errors.append(f"Datetime {dt} is after maximum {self.max_date}")
        
        if errors:
            return ValidationResult(False, None, errors)
        
        return ValidationResult(True, dt)


class JSONValidator(Validator):
    """Validator for checking that a string is valid JSON."""
    
    def __init__(
        self,
        schema_validator: Optional[SchemaValidator] = None,
        level: ValidationLevel = ValidationLevel.STRICT
    ):
        """Initialize a JSONValidator.
        
        Args:
            schema_validator: Optional validator for the parsed JSON
            level: The validation level to use
        """
        super().__init__(level)
        self.schema_validator = schema_validator
    
    def validate(self, value: Union[str, Dict[str, Any], List[Any]]) -> ValidationResult:
        """Validate that a value is valid JSON.
        
        Args:
            value: The value to validate (string or parsed JSON)
            
        Returns:
            A ValidationResult object
        """
        # If value is a string, try to parse it as JSON
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as e:
                return ValidationResult(
                    False,
                    None,
                    [f"Invalid JSON: {str(e)}"]
                )
        # If value is already a dict or list, use it directly
        elif isinstance(value, (dict, list)):
            parsed = value
        else:
            return ValidationResult(
                False,
                None,
                [f"Expected string, dict, or list, got {type(value).__name__}"]
            )
        
        # If a schema validator is provided and the parsed value is a dict,
        # validate against the schema
        if self.schema_validator and isinstance(parsed, dict):
            schema_result = self.schema_validator(parsed)
            if not schema_result.is_valid:
                return schema_result
        
        return ValidationResult(True, parsed)


# Convenience functions for common validations

def validate_type(
    value: Any,
    expected_type: Union[Type, Tuple[Type, ...]],
    level: ValidationLevel = ValidationLevel.STRICT
) -> ValidationResult:
    """Validate that a value is of the expected type.
    
    Args:
        value: The value to validate
        expected_type: The expected type or tuple of types
        level: The validation level to use
        
    Returns:
        A ValidationResult object
    """
    validator = TypeValidator(expected_type, level)
    return validator(value)


def validate_range(
    value: Union[int, float],
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    inclusive: bool = True,
    level: ValidationLevel = ValidationLevel.STRICT
) -> ValidationResult:
    """Validate that a numeric value is within a range.
    
    Args:
        value: The value to validate
        min_value: The minimum allowed value (or None for no minimum)
        max_value: The maximum allowed value (or None for no maximum)
        inclusive: Whether the range bounds are inclusive
        level: The validation level to use
        
    Returns:
        A ValidationResult object
    """
    validator = RangeValidator(min_value, max_value, inclusive, level)
    return validator(value)


def validate_length(
    value: Any,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    level: ValidationLevel = ValidationLevel.STRICT
) -> ValidationResult:
    """Validate that a value has the expected length.
    
    Args:
        value: The value to validate
        min_length: The minimum allowed length (or None for no minimum)
        max_length: The maximum allowed length (or None for no maximum)
        level: The validation level to use
        
    Returns:
        A ValidationResult object
    """
    validator = LengthValidator(min_length, max_length, level)
    return validator(value)


def validate_pattern(
    value: str,
    pattern: Union[str, re.Pattern],
    level: ValidationLevel = ValidationLevel.STRICT
) -> ValidationResult:
    """Validate that a string matches a pattern.
    
    Args:
        value: The string to validate
        pattern: The regex pattern to match against
        level: The validation level to use
        
    Returns:
        A ValidationResult object
    """
    validator = PatternValidator(pattern, level)
    return validator(value)


def validate_enum(
    value: Any,
    enum_class: Type[Enum],
    level: ValidationLevel = ValidationLevel.STRICT
) -> ValidationResult:
    """Validate that a value is a member of an enumeration.
    
    Args:
        value: The value to validate
        enum_class: The Enum class to validate against
        level: The validation level to use
        
    Returns:
        A ValidationResult object
    """
    validator = EnumValidator(enum_class, level)
    return validator(value)


def validate_schema(
    value: Dict[str, Any],
    schema: Dict[str, Dict[str, Any]],
    allow_extra_fields: bool = False,
    level: ValidationLevel = ValidationLevel.STRICT
) -> ValidationResult:
    """Validate that a dictionary conforms to a schema.
    
    Args:
        value: The dictionary to validate
        schema: The schema to validate against
        allow_extra_fields: Whether to allow fields not in the schema
        level: The validation level to use
        
    Returns:
        A ValidationResult object
    """
    validator = SchemaValidator(schema, allow_extra_fields, level)
    return validator(value)


def validate_list(
    value: List[Any],
    item_validator: Validator,
    level: ValidationLevel = ValidationLevel.STRICT
) -> ValidationResult:
    """Validate that each item in a list meets certain criteria.
    
    Args:
        value: The list to validate
        item_validator: The validator to apply to each item
        level: The validation level to use
        
    Returns:
        A ValidationResult object
    """
    validator = ListValidator(item_validator, level)
    return validator(value)


def validate_url(
    value: str,
    schemes: Optional[List[str]] = None,
    require_scheme: bool = True,
    require_netloc: bool = True,
    level: ValidationLevel = ValidationLevel.STRICT
) -> ValidationResult:
    """Validate that a string is a valid URL.
    
    Args:
        value: The string to validate
        schemes: List of allowed schemes (e.g., ['http', 'https'])
        require_scheme: Whether to require a scheme
        require_netloc: Whether to require a network location
        level: The validation level to use
        
    Returns:
        A ValidationResult object
    """
    validator = URLValidator(schemes, require_scheme, require_netloc, level)
    return validator(value)


def validate_datetime(
    value: Union[str, datetime.datetime],
    format_str: Optional[str] = None,
    min_date: Optional[datetime.datetime] = None,
    max_date: Optional[datetime.datetime] = None,
    level: ValidationLevel = ValidationLevel.STRICT
) -> ValidationResult:
    """Validate that a value is a valid date/time.
    
    Args:
        value: The value to validate (string or datetime)
        format_str: The datetime format string (or None to use ISO format)
        min_date: The minimum allowed date (or None for no minimum)
        max_date: The maximum allowed date (or None for no maximum)
        level: The validation level to use
        
    Returns:
        A ValidationResult object
    """
    validator = DateTimeValidator(format_str, min_date, max_date, level)
    return validator(value)


def validate_json(
    value: Union[str, Dict[str, Any], List[Any]],
    schema_validator: Optional[SchemaValidator] = None,
    level: ValidationLevel = ValidationLevel.STRICT
) -> ValidationResult:
    """Validate that a value is valid JSON.
    
    Args:
        value: The value to validate (string or parsed JSON)
        schema_validator: Optional validator for the parsed JSON
        level: The validation level to use
        
    Returns:
        A ValidationResult object
    """
    validator = JSONValidator(schema_validator, level)
    return validator(value)

