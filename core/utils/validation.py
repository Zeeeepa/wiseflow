"""
Data validation utilities for Wiseflow.

This module provides utilities for validating data in various formats
and ensuring data integrity.
"""

import logging
import re
import json
from typing import Dict, List, Any, Optional, Union, Callable, Type, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ValidationError(Exception):
    """Exception raised when data validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        """
        Initialize the validation error.
        
        Args:
            message: Error message
            field: Optional field name that failed validation
            value: Optional value that failed validation
        """
        self.field = field
        self.value = value
        super().__init__(message)


class Validator(Generic[T]):
    """
    Base class for data validators.
    
    This class provides a foundation for implementing data validators
    for various data types.
    """
    
    def __init__(self, field_name: Optional[str] = None):
        """
        Initialize the validator.
        
        Args:
            field_name: Optional field name for error messages
        """
        self.field_name = field_name
    
    def validate(self, value: Any) -> T:
        """
        Validate a value.
        
        Args:
            value: Value to validate
            
        Returns:
            T: Validated value
            
        Raises:
            ValidationError: If validation fails
        """
        raise NotImplementedError("Subclasses must implement validate()")


class StringValidator(Validator[str]):
    """Validator for string values."""
    
    def __init__(
        self,
        field_name: Optional[str] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
        strip: bool = True
    ):
        """
        Initialize the string validator.
        
        Args:
            field_name: Optional field name for error messages
            min_length: Optional minimum length
            max_length: Optional maximum length
            pattern: Optional regex pattern
            strip: Whether to strip whitespace
        """
        super().__init__(field_name)
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if pattern else None
        self.strip = strip
    
    def validate(self, value: Any) -> str:
        """
        Validate a string value.
        
        Args:
            value: Value to validate
            
        Returns:
            str: Validated string
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            raise ValidationError(
                f"Value for {self.field_name or 'field'} cannot be None",
                self.field_name,
                value
            )
        
        if not isinstance(value, str):
            raise ValidationError(
                f"Value for {self.field_name or 'field'} must be a string, got {type(value).__name__}",
                self.field_name,
                value
            )
        
        # Strip whitespace if requested
        if self.strip:
            value = value.strip()
        
        # Check length constraints
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(
                f"Value for {self.field_name or 'field'} must be at least {self.min_length} characters",
                self.field_name,
                value
            )
        
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(
                f"Value for {self.field_name or 'field'} must be at most {self.max_length} characters",
                self.field_name,
                value
            )
        
        # Check pattern
        if self.pattern and not self.pattern.match(value):
            raise ValidationError(
                f"Value for {self.field_name or 'field'} does not match pattern",
                self.field_name,
                value
            )
        
        return value


class NumberValidator(Validator[Union[int, float]]):
    """Validator for numeric values."""
    
    def __init__(
        self,
        field_name: Optional[str] = None,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        integer_only: bool = False
    ):
        """
        Initialize the number validator.
        
        Args:
            field_name: Optional field name for error messages
            min_value: Optional minimum value
            max_value: Optional maximum value
            integer_only: Whether to allow only integers
        """
        super().__init__(field_name)
        self.min_value = min_value
        self.max_value = max_value
        self.integer_only = integer_only
    
    def validate(self, value: Any) -> Union[int, float]:
        """
        Validate a numeric value.
        
        Args:
            value: Value to validate
            
        Returns:
            Union[int, float]: Validated number
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            raise ValidationError(
                f"Value for {self.field_name or 'field'} cannot be None",
                self.field_name,
                value
            )
        
        # Convert to number if string
        if isinstance(value, str):
            try:
                if self.integer_only:
                    value = int(value)
                else:
                    value = float(value)
            except ValueError:
                raise ValidationError(
                    f"Value for {self.field_name or 'field'} must be a valid number",
                    self.field_name,
                    value
                )
        
        # Check type
        if self.integer_only and not isinstance(value, int):
            raise ValidationError(
                f"Value for {self.field_name or 'field'} must be an integer",
                self.field_name,
                value
            )
        
        if not isinstance(value, (int, float)):
            raise ValidationError(
                f"Value for {self.field_name or 'field'} must be a number",
                self.field_name,
                value
            )
        
        # Check range constraints
        if self.min_value is not None and value < self.min_value:
            raise ValidationError(
                f"Value for {self.field_name or 'field'} must be at least {self.min_value}",
                self.field_name,
                value
            )
        
        if self.max_value is not None and value > self.max_value:
            raise ValidationError(
                f"Value for {self.field_name or 'field'} must be at most {self.max_value}",
                self.field_name,
                value
            )
        
        return value


class BooleanValidator(Validator[bool]):
    """Validator for boolean values."""
    
    def validate(self, value: Any) -> bool:
        """
        Validate a boolean value.
        
        Args:
            value: Value to validate
            
        Returns:
            bool: Validated boolean
            
        Raises:
            ValidationError: If validation fails
        """
        if isinstance(value, bool):
            return value
        
        # Convert string values
        if isinstance(value, str):
            value = value.lower()
            if value in ('true', 'yes', '1', 'y', 't'):
                return True
            if value in ('false', 'no', '0', 'n', 'f'):
                return False
        
        # Convert numeric values
        if isinstance(value, (int, float)):
            if value == 1:
                return True
            if value == 0:
                return False
        
        raise ValidationError(
            f"Value for {self.field_name or 'field'} must be a boolean",
            self.field_name,
            value
        )


class ListValidator(Validator[List[T]]):
    """Validator for list values."""
    
    def __init__(
        self,
        field_name: Optional[str] = None,
        item_validator: Optional[Validator[T]] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        unique: bool = False
    ):
        """
        Initialize the list validator.
        
        Args:
            field_name: Optional field name for error messages
            item_validator: Optional validator for list items
            min_length: Optional minimum length
            max_length: Optional maximum length
            unique: Whether list items must be unique
        """
        super().__init__(field_name)
        self.item_validator = item_validator
        self.min_length = min_length
        self.max_length = max_length
        self.unique = unique
    
    def validate(self, value: Any) -> List[T]:
        """
        Validate a list value.
        
        Args:
            value: Value to validate
            
        Returns:
            List[T]: Validated list
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            raise ValidationError(
                f"Value for {self.field_name or 'field'} cannot be None",
                self.field_name,
                value
            )
        
        # Convert to list if string or other iterable
        if isinstance(value, str):
            try:
                value = json.loads(value)
                if not isinstance(value, list):
                    raise ValidationError(
                        f"Value for {self.field_name or 'field'} must be a list",
                        self.field_name,
                        value
                    )
            except json.JSONDecodeError:
                raise ValidationError(
                    f"Value for {self.field_name or 'field'} must be a valid JSON list",
                    self.field_name,
                    value
                )
        elif not isinstance(value, list):
            try:
                value = list(value)
            except (TypeError, ValueError):
                raise ValidationError(
                    f"Value for {self.field_name or 'field'} must be a list",
                    self.field_name,
                    value
                )
        
        # Check length constraints
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(
                f"List for {self.field_name or 'field'} must have at least {self.min_length} items",
                self.field_name,
                value
            )
        
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(
                f"List for {self.field_name or 'field'} must have at most {self.max_length} items",
                self.field_name,
                value
            )
        
        # Check uniqueness
        if self.unique and len(value) != len(set(value)):
            raise ValidationError(
                f"List for {self.field_name or 'field'} must contain unique items",
                self.field_name,
                value
            )
        
        # Validate items
        if self.item_validator:
            validated_items = []
            for i, item in enumerate(value):
                try:
                    validated_item = self.item_validator.validate(item)
                    validated_items.append(validated_item)
                except ValidationError as e:
                    raise ValidationError(
                        f"Item {i} in list for {self.field_name or 'field'} is invalid: {str(e)}",
                        self.field_name,
                        item
                    )
            return validated_items
        
        return value


class DictValidator(Validator[Dict[str, Any]]):
    """Validator for dictionary values."""
    
    def __init__(
        self,
        field_name: Optional[str] = None,
        schema: Optional[Dict[str, Validator]] = None,
        required_keys: Optional[List[str]] = None,
        allow_extra_keys: bool = True
    ):
        """
        Initialize the dictionary validator.
        
        Args:
            field_name: Optional field name for error messages
            schema: Optional schema for dictionary keys
            required_keys: Optional list of required keys
            allow_extra_keys: Whether to allow keys not in the schema
        """
        super().__init__(field_name)
        self.schema = schema or {}
        self.required_keys = required_keys or []
        self.allow_extra_keys = allow_extra_keys
    
    def validate(self, value: Any) -> Dict[str, Any]:
        """
        Validate a dictionary value.
        
        Args:
            value: Value to validate
            
        Returns:
            Dict[str, Any]: Validated dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            raise ValidationError(
                f"Value for {self.field_name or 'field'} cannot be None",
                self.field_name,
                value
            )
        
        # Convert to dict if string
        if isinstance(value, str):
            try:
                value = json.loads(value)
                if not isinstance(value, dict):
                    raise ValidationError(
                        f"Value for {self.field_name or 'field'} must be a dictionary",
                        self.field_name,
                        value
                    )
            except json.JSONDecodeError:
                raise ValidationError(
                    f"Value for {self.field_name or 'field'} must be a valid JSON object",
                    self.field_name,
                    value
                )
        
        if not isinstance(value, dict):
            raise ValidationError(
                f"Value for {self.field_name or 'field'} must be a dictionary",
                self.field_name,
                value
            )
        
        # Check required keys
        for key in self.required_keys:
            if key not in value:
                raise ValidationError(
                    f"Dictionary for {self.field_name or 'field'} is missing required key: {key}",
                    self.field_name,
                    value
                )
        
        # Check extra keys
        if not self.allow_extra_keys:
            extra_keys = set(value.keys()) - set(self.schema.keys())
            if extra_keys:
                raise ValidationError(
                    f"Dictionary for {self.field_name or 'field'} contains extra keys: {', '.join(extra_keys)}",
                    self.field_name,
                    value
                )
        
        # Validate values
        validated_dict = {}
        for key, validator in self.schema.items():
            if key in value:
                try:
                    validated_dict[key] = validator.validate(value[key])
                except ValidationError as e:
                    raise ValidationError(
                        f"Value for key '{key}' in {self.field_name or 'field'} is invalid: {str(e)}",
                        self.field_name,
                        value[key]
                    )
            elif key in self.required_keys:
                raise ValidationError(
                    f"Dictionary for {self.field_name or 'field'} is missing required key: {key}",
                    self.field_name,
                    value
                )
        
        # Copy extra keys
        if self.allow_extra_keys:
            for key in value:
                if key not in self.schema:
                    validated_dict[key] = value[key]
        
        return validated_dict


class OptionalValidator(Validator[Optional[T]]):
    """Validator for optional values."""
    
    def __init__(
        self,
        validator: Validator[T],
        default_value: Optional[T] = None
    ):
        """
        Initialize the optional validator.
        
        Args:
            validator: Validator for non-None values
            default_value: Default value to use if None
        """
        super().__init__(validator.field_name)
        self.validator = validator
        self.default_value = default_value
    
    def validate(self, value: Any) -> Optional[T]:
        """
        Validate an optional value.
        
        Args:
            value: Value to validate
            
        Returns:
            Optional[T]: Validated value or default
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            return self.default_value
        
        return self.validator.validate(value)


class CustomValidator(Validator[T]):
    """Validator using a custom validation function."""
    
    def __init__(
        self,
        field_name: Optional[str] = None,
        validation_func: Callable[[Any], T] = None,
        error_message: str = "Validation failed"
    ):
        """
        Initialize the custom validator.
        
        Args:
            field_name: Optional field name for error messages
            validation_func: Function to validate values
            error_message: Error message to use if validation fails
        """
        super().__init__(field_name)
        self.validation_func = validation_func
        self.error_message = error_message
    
    def validate(self, value: Any) -> T:
        """
        Validate a value using the custom function.
        
        Args:
            value: Value to validate
            
        Returns:
            T: Validated value
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            result = self.validation_func(value)
            return result
        except Exception as e:
            raise ValidationError(
                f"{self.error_message}: {str(e)}",
                self.field_name,
                value
            )


def validate_data_item(data_item: Any) -> bool:
    """
    Validate a data item.
    
    Args:
        data_item: Data item to validate
        
    Returns:
        bool: True if validation passes, False otherwise
    """
    from core.connectors import DataItem
    
    if not isinstance(data_item, DataItem):
        logger.error(f"Invalid data item type: {type(data_item).__name__}")
        return False
    
    # Check required fields
    if not data_item.source_id:
        logger.error("Data item missing source_id")
        return False
    
    # Check content
    if data_item.content is None:
        logger.error("Data item has None content")
        return False
    
    # Check metadata
    if not isinstance(data_item.metadata, dict):
        logger.error(f"Data item has invalid metadata type: {type(data_item.metadata).__name__}")
        return False
    
    return True


def validate_processed_data(processed_data: Any) -> bool:
    """
    Validate processed data.
    
    Args:
        processed_data: Processed data to validate
        
    Returns:
        bool: True if validation passes, False otherwise
    """
    from core.plugins.processors import ProcessedData
    
    if not isinstance(processed_data, ProcessedData):
        logger.error(f"Invalid processed data type: {type(processed_data).__name__}")
        return False
    
    # Check original item
    if not validate_data_item(processed_data.original_item):
        logger.error("Processed data has invalid original item")
        return False
    
    # Check processed content
    if not isinstance(processed_data.processed_content, list):
        logger.error(f"Processed data has invalid content type: {type(processed_data.processed_content).__name__}")
        return False
    
    # Check metadata
    if not isinstance(processed_data.metadata, dict):
        logger.error(f"Processed data has invalid metadata type: {type(processed_data.metadata).__name__}")
        return False
    
    return True

