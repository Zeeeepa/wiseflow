#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the validation module.

This module contains tests for the validation module to ensure it works correctly.
"""

import re
import json
import unittest
import datetime
from enum import Enum
from typing import Dict, Any, List, Optional

import pytest
from unittest.mock import MagicMock, patch

from core.validation import (
    ValidationLevel, ValidationResult, Validator,
    TypeValidator, RangeValidator, LengthValidator, PatternValidator,
    EnumValidator, SchemaValidator, ListValidator, URLValidator,
    DateTimeValidator, JSONValidator,
    validate_type, validate_range, validate_length, validate_pattern,
    validate_enum, validate_schema, validate_list, validate_url,
    validate_datetime, validate_json
)


class TestValidationResult(unittest.TestCase):
    """Tests for the ValidationResult class."""
    
    def test_init(self):
        """Test initializing a ValidationResult."""
        # Valid result
        result = ValidationResult(True, "test_value")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, "test_value")
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])
        
        # Invalid result
        result = ValidationResult(False, None, ["Error 1", "Error 2"], ["Warning 1"])
        self.assertFalse(result.is_valid)
        self.assertIsNone(result.value)
        self.assertEqual(result.errors, ["Error 1", "Error 2"])
        self.assertEqual(result.warnings, ["Warning 1"])
    
    def test_bool(self):
        """Test boolean conversion of ValidationResult."""
        # Valid result
        result = ValidationResult(True, "test_value")
        self.assertTrue(bool(result))
        
        # Invalid result
        result = ValidationResult(False, None, ["Error"])
        self.assertFalse(bool(result))
    
    def test_str(self):
        """Test string representation of ValidationResult."""
        # Valid result
        result = ValidationResult(True, "test_value")
        self.assertEqual(str(result), "Valid: test_value")
        
        # Invalid result
        result = ValidationResult(False, None, ["Error 1", "Error 2"])
        self.assertEqual(str(result), "Invalid: Error 1, Error 2")


class TestTypeValidator(unittest.TestCase):
    """Tests for the TypeValidator class."""
    
    def test_validate_single_type(self):
        """Test validating a single type."""
        validator = TypeValidator(str)
        
        # Valid
        result = validator.validate("test")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, "test")
        
        # Invalid
        result = validator.validate(123)
        self.assertFalse(result.is_valid)
        self.assertIn("Expected type str, got int", result.errors[0])
    
    def test_validate_multiple_types(self):
        """Test validating multiple types."""
        validator = TypeValidator((str, int))
        
        # Valid string
        result = validator.validate("test")
        self.assertTrue(result.is_valid)
        
        # Valid int
        result = validator.validate(123)
        self.assertTrue(result.is_valid)
        
        # Invalid
        result = validator.validate(1.23)
        self.assertFalse(result.is_valid)
        self.assertIn("Expected type str or int, got float", result.errors[0])
    
    def test_call_with_strict_level(self):
        """Test calling the validator with strict level."""
        validator = TypeValidator(str, ValidationLevel.STRICT)
        
        # Valid
        result = validator("test")
        self.assertTrue(result.is_valid)
        
        # Invalid
        with self.assertRaises(ValueError):
            validator(123)
    
    def test_call_with_warning_level(self):
        """Test calling the validator with warning level."""
        validator = TypeValidator(str, ValidationLevel.WARNING)
        
        # Valid
        result = validator("test")
        self.assertTrue(result.is_valid)
        
        # Invalid
        with patch("core.validation.logger") as mock_logger:
            result = validator(123)
            self.assertFalse(result.is_valid)
            mock_logger.warning.assert_called()


class TestRangeValidator(unittest.TestCase):
    """Tests for the RangeValidator class."""
    
    def test_init(self):
        """Test initializing a RangeValidator."""
        # Valid initialization
        validator = RangeValidator(min_value=0, max_value=100)
        self.assertEqual(validator.min_value, 0)
        self.assertEqual(validator.max_value, 100)
        self.assertTrue(validator.inclusive)
        
        # Invalid initialization (no bounds)
        with self.assertRaises(ValueError):
            RangeValidator()
    
    def test_validate_inclusive(self):
        """Test validating with inclusive bounds."""
        validator = RangeValidator(min_value=0, max_value=100, inclusive=True)
        
        # Valid (within range)
        result = validator.validate(50)
        self.assertTrue(result.is_valid)
        
        # Valid (at min bound)
        result = validator.validate(0)
        self.assertTrue(result.is_valid)
        
        # Valid (at max bound)
        result = validator.validate(100)
        self.assertTrue(result.is_valid)
        
        # Invalid (below min)
        result = validator.validate(-1)
        self.assertFalse(result.is_valid)
        
        # Invalid (above max)
        result = validator.validate(101)
        self.assertFalse(result.is_valid)
        
        # Invalid (wrong type)
        result = validator.validate("50")
        self.assertFalse(result.is_valid)
    
    def test_validate_exclusive(self):
        """Test validating with exclusive bounds."""
        validator = RangeValidator(min_value=0, max_value=100, inclusive=False)
        
        # Valid (within range)
        result = validator.validate(50)
        self.assertTrue(result.is_valid)
        
        # Invalid (at min bound)
        result = validator.validate(0)
        self.assertFalse(result.is_valid)
        
        # Invalid (at max bound)
        result = validator.validate(100)
        self.assertFalse(result.is_valid)
    
    def test_validate_min_only(self):
        """Test validating with only a minimum bound."""
        validator = RangeValidator(min_value=0)
        
        # Valid (above min)
        result = validator.validate(50)
        self.assertTrue(result.is_valid)
        
        # Valid (at min)
        result = validator.validate(0)
        self.assertTrue(result.is_valid)
        
        # Invalid (below min)
        result = validator.validate(-1)
        self.assertFalse(result.is_valid)
    
    def test_validate_max_only(self):
        """Test validating with only a maximum bound."""
        validator = RangeValidator(max_value=100)
        
        # Valid (below max)
        result = validator.validate(50)
        self.assertTrue(result.is_valid)
        
        # Valid (at max)
        result = validator.validate(100)
        self.assertTrue(result.is_valid)
        
        # Invalid (above max)
        result = validator.validate(101)
        self.assertFalse(result.is_valid)


class TestLengthValidator(unittest.TestCase):
    """Tests for the LengthValidator class."""
    
    def test_init(self):
        """Test initializing a LengthValidator."""
        # Valid initialization
        validator = LengthValidator(min_length=1, max_length=10)
        self.assertEqual(validator.min_length, 1)
        self.assertEqual(validator.max_length, 10)
        
        # Invalid initialization (no bounds)
        with self.assertRaises(ValueError):
            LengthValidator()
        
        # Invalid initialization (negative min_length)
        with self.assertRaises(ValueError):
            LengthValidator(min_length=-1)
        
        # Invalid initialization (negative max_length)
        with self.assertRaises(ValueError):
            LengthValidator(max_length=-1)
        
        # Invalid initialization (min_length > max_length)
        with self.assertRaises(ValueError):
            LengthValidator(min_length=10, max_length=5)
    
    def test_validate_string(self):
        """Test validating string length."""
        validator = LengthValidator(min_length=2, max_length=5)
        
        # Valid (within range)
        result = validator.validate("abc")
        self.assertTrue(result.is_valid)
        
        # Valid (at min)
        result = validator.validate("ab")
        self.assertTrue(result.is_valid)
        
        # Valid (at max)
        result = validator.validate("abcde")
        self.assertTrue(result.is_valid)
        
        # Invalid (too short)
        result = validator.validate("a")
        self.assertFalse(result.is_valid)
        
        # Invalid (too long)
        result = validator.validate("abcdef")
        self.assertFalse(result.is_valid)
    
    def test_validate_list(self):
        """Test validating list length."""
        validator = LengthValidator(min_length=2, max_length=5)
        
        # Valid (within range)
        result = validator.validate([1, 2, 3])
        self.assertTrue(result.is_valid)
        
        # Invalid (too short)
        result = validator.validate([1])
        self.assertFalse(result.is_valid)
    
    def test_validate_no_length(self):
        """Test validating an object with no length."""
        validator = LengthValidator(min_length=2, max_length=5)
        
        # Invalid (no length)
        result = validator.validate(123)
        self.assertFalse(result.is_valid)


class TestPatternValidator(unittest.TestCase):
    """Tests for the PatternValidator class."""
    
    def test_init_with_string(self):
        """Test initializing with a string pattern."""
        validator = PatternValidator(r"^\d{3}-\d{2}-\d{4}$")
        self.assertEqual(validator.pattern.pattern, r"^\d{3}-\d{2}-\d{4}$")
    
    def test_init_with_pattern(self):
        """Test initializing with a compiled pattern."""
        pattern = re.compile(r"^\d{3}-\d{2}-\d{4}$")
        validator = PatternValidator(pattern)
        self.assertEqual(validator.pattern, pattern)
    
    def test_validate(self):
        """Test validating against a pattern."""
        validator = PatternValidator(r"^\d{3}-\d{2}-\d{4}$")
        
        # Valid
        result = validator.validate("123-45-6789")
        self.assertTrue(result.is_valid)
        
        # Invalid
        result = validator.validate("123-456-789")
        self.assertFalse(result.is_valid)
        
        # Invalid (wrong type)
        result = validator.validate(12345)
        self.assertFalse(result.is_valid)


class TestEnumValidator(unittest.TestCase):
    """Tests for the EnumValidator class."""
    
    class Color(Enum):
        """Test enum for validation."""
        RED = "red"
        GREEN = "green"
        BLUE = "blue"
    
    def test_validate_enum_instance(self):
        """Test validating an enum instance."""
        validator = EnumValidator(self.Color)
        
        # Valid (enum instance)
        result = validator.validate(self.Color.RED)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, self.Color.RED)
    
    def test_validate_enum_value(self):
        """Test validating an enum value."""
        validator = EnumValidator(self.Color)
        
        # Valid (enum value)
        result = validator.validate("red")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, self.Color.RED)
    
    def test_validate_enum_name(self):
        """Test validating an enum name."""
        validator = EnumValidator(self.Color)
        
        # Valid (enum name)
        result = validator.validate("RED")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, self.Color.RED)
    
    def test_validate_invalid(self):
        """Test validating an invalid value."""
        validator = EnumValidator(self.Color)
        
        # Invalid
        result = validator.validate("yellow")
        self.assertFalse(result.is_valid)
        self.assertIn("Valid values: ['red', 'green', 'blue']", result.errors[0])


class TestSchemaValidator(unittest.TestCase):
    """Tests for the SchemaValidator class."""
    
    def test_validate_valid_schema(self):
        """Test validating a valid schema."""
        schema = {
            "name": {
                "type": str,
                "required": True
            },
            "age": {
                "type": int,
                "required": True,
                "validator": RangeValidator(min_value=0, max_value=120)
            },
            "email": {
                "type": str,
                "required": False,
                "validator": PatternValidator(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
            }
        }
        validator = SchemaValidator(schema)
        
        # Valid
        data = {
            "name": "John Doe",
            "age": 30,
            "email": "john.doe@example.com"
        }
        result = validator.validate(data)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, data)
    
    def test_validate_missing_required(self):
        """Test validating with missing required fields."""
        schema = {
            "name": {
                "type": str,
                "required": True
            },
            "age": {
                "type": int,
                "required": True
            }
        }
        validator = SchemaValidator(schema)
        
        # Invalid (missing required field)
        data = {
            "name": "John Doe"
        }
        result = validator.validate(data)
        self.assertFalse(result.is_valid)
        self.assertIn("Required field 'age' is missing", result.errors)
    
    def test_validate_extra_fields(self):
        """Test validating with extra fields."""
        schema = {
            "name": {
                "type": str,
                "required": True
            }
        }
        
        # Disallow extra fields
        validator = SchemaValidator(schema, allow_extra_fields=False)
        data = {
            "name": "John Doe",
            "age": 30
        }
        result = validator.validate(data)
        self.assertFalse(result.is_valid)
        self.assertIn("Extra fields not allowed: age", result.errors[0])
        
        # Allow extra fields
        validator = SchemaValidator(schema, allow_extra_fields=True)
        result = validator.validate(data)
        self.assertTrue(result.is_valid)
    
    def test_validate_field_type(self):
        """Test validating field types."""
        schema = {
            "name": {
                "type": str,
                "required": True
            },
            "age": {
                "type": int,
                "required": True
            }
        }
        validator = SchemaValidator(schema)
        
        # Invalid (wrong field type)
        data = {
            "name": "John Doe",
            "age": "30"
        }
        result = validator.validate(data)
        self.assertFalse(result.is_valid)
        self.assertIn("Field 'age' has incorrect type", result.errors[0])
    
    def test_validate_field_validator(self):
        """Test validating with field validators."""
        schema = {
            "age": {
                "type": int,
                "required": True,
                "validator": RangeValidator(min_value=0, max_value=120)
            }
        }
        validator = SchemaValidator(schema)
        
        # Valid
        data = {"age": 30}
        result = validator.validate(data)
        self.assertTrue(result.is_valid)
        
        # Invalid (field validator fails)
        data = {"age": 150}
        result = validator.validate(data)
        self.assertFalse(result.is_valid)
        self.assertIn("Field 'age':", result.errors[0])


class TestListValidator(unittest.TestCase):
    """Tests for the ListValidator class."""
    
    def test_validate_valid_list(self):
        """Test validating a valid list."""
        item_validator = TypeValidator(int)
        validator = ListValidator(item_validator)
        
        # Valid
        result = validator.validate([1, 2, 3])
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, [1, 2, 3])
    
    def test_validate_invalid_list(self):
        """Test validating an invalid list."""
        item_validator = TypeValidator(int)
        validator = ListValidator(item_validator)
        
        # Invalid (wrong item type)
        result = validator.validate([1, "2", 3])
        self.assertFalse(result.is_valid)
        self.assertIn("Item 1:", result.errors[0])
    
    def test_validate_not_a_list(self):
        """Test validating a non-list value."""
        item_validator = TypeValidator(int)
        validator = ListValidator(item_validator)
        
        # Invalid (not a list)
        result = validator.validate("not a list")
        self.assertFalse(result.is_valid)
        self.assertIn("Expected list", result.errors[0])


class TestURLValidator(unittest.TestCase):
    """Tests for the URLValidator class."""
    
    def test_validate_valid_url(self):
        """Test validating a valid URL."""
        validator = URLValidator()
        
        # Valid
        result = validator.validate("https://example.com/path?query=value#fragment")
        self.assertTrue(result.is_valid)
    
    def test_validate_invalid_url(self):
        """Test validating an invalid URL."""
        validator = URLValidator()
        
        # Invalid
        result = validator.validate("not a url")
        self.assertFalse(result.is_valid)
    
    def test_validate_scheme(self):
        """Test validating URL schemes."""
        # Allow only http
        validator = URLValidator(schemes=["http"])
        
        # Valid
        result = validator.validate("http://example.com")
        self.assertTrue(result.is_valid)
        
        # Invalid (wrong scheme)
        result = validator.validate("https://example.com")
        self.assertFalse(result.is_valid)
    
    def test_validate_require_scheme(self):
        """Test requiring a URL scheme."""
        # Require scheme
        validator = URLValidator(require_scheme=True)
        
        # Valid
        result = validator.validate("https://example.com")
        self.assertTrue(result.is_valid)
        
        # Invalid (no scheme)
        result = validator.validate("example.com")
        self.assertFalse(result.is_valid)
        
        # Don't require scheme
        validator = URLValidator(require_scheme=False)
        
        # Valid (no scheme)
        result = validator.validate("example.com")
        self.assertTrue(result.is_valid)


class TestDateTimeValidator(unittest.TestCase):
    """Tests for the DateTimeValidator class."""
    
    def test_validate_datetime_object(self):
        """Test validating a datetime object."""
        validator = DateTimeValidator()
        
        # Valid
        dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
        result = validator.validate(dt)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, dt)
    
    def test_validate_iso_string(self):
        """Test validating an ISO format string."""
        validator = DateTimeValidator()
        
        # Valid
        result = validator.validate("2023-01-01T12:00:00")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, datetime.datetime(2023, 1, 1, 12, 0, 0))
    
    def test_validate_custom_format(self):
        """Test validating with a custom format."""
        validator = DateTimeValidator(format_str="%Y-%m-%d %H:%M:%S")
        
        # Valid
        result = validator.validate("2023-01-01 12:00:00")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, datetime.datetime(2023, 1, 1, 12, 0, 0))
        
        # Invalid (wrong format)
        result = validator.validate("2023-01-01T12:00:00")
        self.assertFalse(result.is_valid)
    
    def test_validate_min_max_date(self):
        """Test validating with min and max dates."""
        min_date = datetime.datetime(2023, 1, 1)
        max_date = datetime.datetime(2023, 12, 31)
        validator = DateTimeValidator(min_date=min_date, max_date=max_date)
        
        # Valid
        result = validator.validate("2023-06-15T12:00:00")
        self.assertTrue(result.is_valid)
        
        # Invalid (before min)
        result = validator.validate("2022-12-31T12:00:00")
        self.assertFalse(result.is_valid)
        
        # Invalid (after max)
        result = validator.validate("2024-01-01T12:00:00")
        self.assertFalse(result.is_valid)


class TestJSONValidator(unittest.TestCase):
    """Tests for the JSONValidator class."""
    
    def test_validate_json_string(self):
        """Test validating a JSON string."""
        validator = JSONValidator()
        
        # Valid
        result = validator.validate('{"name": "John", "age": 30}')
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, {"name": "John", "age": 30})
        
        # Invalid (not valid JSON)
        result = validator.validate('{"name": "John", age: 30}')
        self.assertFalse(result.is_valid)
    
    def test_validate_dict(self):
        """Test validating a dictionary."""
        validator = JSONValidator()
        
        # Valid
        data = {"name": "John", "age": 30}
        result = validator.validate(data)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, data)
    
    def test_validate_with_schema(self):
        """Test validating with a schema."""
        schema = {
            "name": {
                "type": str,
                "required": True
            },
            "age": {
                "type": int,
                "required": True
            }
        }
        schema_validator = SchemaValidator(schema)
        validator = JSONValidator(schema_validator=schema_validator)
        
        # Valid
        result = validator.validate('{"name": "John", "age": 30}')
        self.assertTrue(result.is_valid)
        
        # Invalid (schema validation fails)
        result = validator.validate('{"name": "John", "age": "30"}')
        self.assertFalse(result.is_valid)


class TestConvenienceFunctions(unittest.TestCase):
    """Tests for the convenience functions."""
    
    def test_validate_type(self):
        """Test the validate_type function."""
        # Valid
        result = validate_type("test", str)
        self.assertTrue(result.is_valid)
        
        # Invalid
        result = validate_type(123, str)
        self.assertFalse(result.is_valid)
    
    def test_validate_range(self):
        """Test the validate_range function."""
        # Valid
        result = validate_range(50, min_value=0, max_value=100)
        self.assertTrue(result.is_valid)
        
        # Invalid
        result = validate_range(150, min_value=0, max_value=100)
        self.assertFalse(result.is_valid)
    
    def test_validate_length(self):
        """Test the validate_length function."""
        # Valid
        result = validate_length("test", min_length=2, max_length=10)
        self.assertTrue(result.is_valid)
        
        # Invalid
        result = validate_length("test", min_length=5)
        self.assertFalse(result.is_valid)
    
    def test_validate_pattern(self):
        """Test the validate_pattern function."""
        # Valid
        result = validate_pattern("123-45-6789", r"^\d{3}-\d{2}-\d{4}$")
        self.assertTrue(result.is_valid)
        
        # Invalid
        result = validate_pattern("123-456-789", r"^\d{3}-\d{2}-\d{4}$")
        self.assertFalse(result.is_valid)
    
    def test_validate_enum(self):
        """Test the validate_enum function."""
        class Color(Enum):
            RED = "red"
            GREEN = "green"
            BLUE = "blue"
        
        # Valid
        result = validate_enum("red", Color)
        self.assertTrue(result.is_valid)
        
        # Invalid
        result = validate_enum("yellow", Color)
        self.assertFalse(result.is_valid)
    
    def test_validate_schema(self):
        """Test the validate_schema function."""
        schema = {
            "name": {
                "type": str,
                "required": True
            }
        }
        
        # Valid
        result = validate_schema({"name": "John"}, schema)
        self.assertTrue(result.is_valid)
        
        # Invalid
        result = validate_schema({"age": 30}, schema)
        self.assertFalse(result.is_valid)
    
    def test_validate_list(self):
        """Test the validate_list function."""
        item_validator = TypeValidator(int)
        
        # Valid
        result = validate_list([1, 2, 3], item_validator)
        self.assertTrue(result.is_valid)
        
        # Invalid
        result = validate_list([1, "2", 3], item_validator)
        self.assertFalse(result.is_valid)
    
    def test_validate_url(self):
        """Test the validate_url function."""
        # Valid
        result = validate_url("https://example.com")
        self.assertTrue(result.is_valid)
        
        # Invalid
        result = validate_url("not a url")
        self.assertFalse(result.is_valid)
    
    def test_validate_datetime(self):
        """Test the validate_datetime function."""
        # Valid
        result = validate_datetime("2023-01-01T12:00:00")
        self.assertTrue(result.is_valid)
        
        # Invalid
        result = validate_datetime("not a date")
        self.assertFalse(result.is_valid)
    
    def test_validate_json(self):
        """Test the validate_json function."""
        # Valid
        result = validate_json('{"name": "John", "age": 30}')
        self.assertTrue(result.is_valid)
        
        # Invalid
        result = validate_json('{"name": "John", age: 30}')
        self.assertFalse(result.is_valid)


if __name__ == "__main__":
    unittest.main()

