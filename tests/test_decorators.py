#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the decorators module.

This module contains tests for the decorators module to ensure it works correctly.
"""

import time
import logging
import unittest
from typing import Dict, List, Any, Optional, Union
from unittest.mock import patch, MagicMock

import pytest

from core.decorators import (
    validate_input, validate_output, handle_exceptions,
    log_execution, retry, memoize, deprecated
)


class TestValidateInput(unittest.TestCase):
    """Tests for the validate_input decorator."""
    
    def test_validate_input_types(self):
        """Test validating input types."""
        # Define a function with validate_input
        @validate_input(arg_types={"a": int, "b": str})
        def test_func(a, b):
            return f"{a} {b}"
        
        # Valid inputs
        result = test_func(1, "test")
        self.assertEqual(result, "1 test")
        
        # Invalid inputs
        with self.assertRaises(TypeError):
            test_func("1", "test")  # a should be int
        
        with self.assertRaises(TypeError):
            test_func(1, 2)  # b should be str
    
    def test_validate_input_schema(self):
        """Test validating input schema."""
        # Define a schema
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
        
        # Define a function with validate_input
        @validate_input(schema=schema)
        def test_func(data):
            return f"{data['name']} is {data['age']} years old"
        
        # Valid input
        result = test_func({"name": "John", "age": 30})
        self.assertEqual(result, "John is 30 years old")
        
        # Invalid input (wrong type)
        with self.assertRaises(ValueError):
            test_func({"name": "John", "age": "30"})
        
        # Invalid input (missing required field)
        with self.assertRaises(ValueError):
            test_func({"name": "John"})
    
    def test_validate_input_allow_extra_fields(self):
        """Test allowing extra fields in input schema."""
        # Define a schema
        schema = {
            "name": {
                "type": str,
                "required": True
            }
        }
        
        # Define functions with different allow_extra_fields settings
        @validate_input(schema=schema, allow_extra_fields=False)
        def test_func_no_extra(data):
            return data["name"]
        
        @validate_input(schema=schema, allow_extra_fields=True)
        def test_func_allow_extra(data):
            return data["name"]
        
        # Test with extra fields
        data = {"name": "John", "age": 30}
        
        # Should raise error when extra fields not allowed
        with self.assertRaises(ValueError):
            test_func_no_extra(data)
        
        # Should work when extra fields allowed
        result = test_func_allow_extra(data)
        self.assertEqual(result, "John")


class TestValidateOutput(unittest.TestCase):
    """Tests for the validate_output decorator."""
    
    def test_validate_output_type(self):
        """Test validating output type."""
        # Define functions with validate_output
        @validate_output(expected_type=int)
        def test_func_int():
            return 42
        
        @validate_output(expected_type=str)
        def test_func_str():
            return "test"
        
        @validate_output(expected_type=int)
        def test_func_wrong():
            return "not an int"
        
        # Valid outputs
        self.assertEqual(test_func_int(), 42)
        self.assertEqual(test_func_str(), "test")
        
        # Invalid output
        with self.assertRaises(TypeError):
            test_func_wrong()
    
    def test_validate_output_schema(self):
        """Test validating output schema."""
        # Define a schema
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
        
        # Define functions with validate_output
        @validate_output(schema=schema)
        def test_func_valid():
            return {"name": "John", "age": 30}
        
        @validate_output(schema=schema)
        def test_func_invalid():
            return {"name": "John", "age": "30"}
        
        # Valid output
        result = test_func_valid()
        self.assertEqual(result, {"name": "John", "age": 30})
        
        # Invalid output
        with self.assertRaises(ValueError):
            test_func_invalid()


class TestHandleExceptions(unittest.TestCase):
    """Tests for the handle_exceptions decorator."""
    
    def test_handle_specific_exception(self):
        """Test handling a specific exception."""
        # Define a function with handle_exceptions
        @handle_exceptions(ValueError, reraise=False, default_return="default")
        def test_func(raise_error=False):
            if raise_error:
                raise ValueError("Test error")
            return "success"
        
        # No exception
        self.assertEqual(test_func(), "success")
        
        # Handled exception
        self.assertEqual(test_func(True), "default")
    
    def test_handle_multiple_exceptions(self):
        """Test handling multiple exception types."""
        # Define a function with handle_exceptions
        @handle_exceptions(ValueError, TypeError, reraise=False, default_return="default")
        def test_func(error_type=None):
            if error_type == "value":
                raise ValueError("Value error")
            elif error_type == "type":
                raise TypeError("Type error")
            return "success"
        
        # No exception
        self.assertEqual(test_func(), "success")
        
        # Handled ValueError
        self.assertEqual(test_func("value"), "default")
        
        # Handled TypeError
        self.assertEqual(test_func("type"), "default")
    
    def test_reraise_exception(self):
        """Test reraising an exception after handling."""
        # Define a function with handle_exceptions
        @handle_exceptions(ValueError, reraise=True)
        def test_func():
            raise ValueError("Test error")
        
        # Exception should be reraised
        with self.assertRaises(ValueError):
            test_func()
    
    def test_unhandled_exception(self):
        """Test an unhandled exception type."""
        # Define a function with handle_exceptions
        @handle_exceptions(ValueError, reraise=False, default_return="default")
        def test_func():
            raise TypeError("Test error")
        
        # TypeError is not handled, so it should be raised
        with self.assertRaises(TypeError):
            test_func()


class TestLogExecution(unittest.TestCase):
    """Tests for the log_execution decorator."""
    
    @patch("core.decorators.logger")
    def test_log_execution_basic(self, mock_logger):
        """Test basic logging of function execution."""
        # Define a function with log_execution
        @log_execution()
        def test_func():
            return "result"
        
        # Call the function
        result = test_func()
        
        # Check result
        self.assertEqual(result, "result")
        
        # Check logging
        self.assertEqual(mock_logger.log.call_count, 3)  # Call, time, result
        
        # Check log messages
        call_args_list = mock_logger.log.call_args_list
        self.assertIn("Calling test_func", str(call_args_list[0]))
        self.assertIn("executed in", str(call_args_list[1]))
        self.assertIn("returned: result", str(call_args_list[2]))
    
    @patch("core.decorators.logger")
    def test_log_execution_with_args(self, mock_logger):
        """Test logging with function arguments."""
        # Define a function with log_execution
        @log_execution(log_args=True, log_result=True)
        def test_func(a, b, c=None):
            return a + b
        
        # Call the function
        result = test_func(1, 2, c=3)
        
        # Check result
        self.assertEqual(result, 3)
        
        # Check logging
        call_args_list = mock_logger.log.call_args_list
        self.assertIn("Calling test_func", str(call_args_list[0]))
        self.assertIn("1, 2, c=3", str(call_args_list[0]))
    
    @patch("core.decorators.logger")
    def test_log_execution_no_args_no_result(self, mock_logger):
        """Test logging without arguments or result."""
        # Define a function with log_execution
        @log_execution(log_args=False, log_result=False)
        def test_func(a, b):
            return a + b
        
        # Call the function
        result = test_func(1, 2)
        
        # Check result
        self.assertEqual(result, 3)
        
        # Check logging
        self.assertEqual(mock_logger.log.call_count, 2)  # Call, time
        
        # Check log messages
        call_args_list = mock_logger.log.call_args_list
        self.assertIn("Calling test_func", str(call_args_list[0]))
        self.assertNotIn("1, 2", str(call_args_list[0]))
        self.assertIn("executed in", str(call_args_list[1]))
        
        # Check that result was not logged
        for call in call_args_list:
            self.assertNotIn("returned: 3", str(call))


class TestRetry(unittest.TestCase):
    """Tests for the retry decorator."""
    
    def test_retry_success_first_attempt(self):
        """Test successful execution on first attempt."""
        # Mock function that succeeds
        mock_func = MagicMock(return_value="success")
        
        # Apply retry decorator
        decorated_func = retry(max_attempts=3, delay=0.01)(mock_func)
        
        # Call the function
        result = decorated_func()
        
        # Check result
        self.assertEqual(result, "success")
        
        # Check that function was called once
        mock_func.assert_called_once()
    
    def test_retry_success_after_failures(self):
        """Test successful execution after some failures."""
        # Mock function that fails twice then succeeds
        side_effects = [ValueError("Attempt 1"), ValueError("Attempt 2"), "success"]
        mock_func = MagicMock(side_effect=side_effects)
        
        # Apply retry decorator
        decorated_func = retry(max_attempts=3, delay=0.01)(mock_func)
        
        # Call the function
        result = decorated_func()
        
        # Check result
        self.assertEqual(result, "success")
        
        # Check that function was called three times
        self.assertEqual(mock_func.call_count, 3)
    
    def test_retry_all_attempts_fail(self):
        """Test all retry attempts failing."""
        # Mock function that always fails
        mock_func = MagicMock(side_effect=ValueError("Failed"))
        
        # Apply retry decorator
        decorated_func = retry(max_attempts=3, delay=0.01)(mock_func)
        
        # Call the function (should raise after all attempts)
        with self.assertRaises(ValueError):
            decorated_func()
        
        # Check that function was called max_attempts times
        self.assertEqual(mock_func.call_count, 3)
    
    def test_retry_specific_exceptions(self):
        """Test retrying only for specific exceptions."""
        # Mock function that raises different exceptions
        side_effects = [ValueError("Retry this"), TypeError("Don't retry this")]
        mock_func = MagicMock(side_effect=side_effects)
        
        # Apply retry decorator for ValueError only
        decorated_func = retry(max_attempts=3, delay=0.01, exceptions=ValueError)(mock_func)
        
        # Call the function (should retry for ValueError, but not for TypeError)
        with self.assertRaises(TypeError):
            decorated_func()
        
        # Check that function was called twice (once for ValueError, once for TypeError)
        self.assertEqual(mock_func.call_count, 2)


class TestMemoize(unittest.TestCase):
    """Tests for the memoize decorator."""
    
    def test_memoize_basic(self):
        """Test basic memoization."""
        # Define a function with memoize
        call_count = 0
        
        @memoize()
        def test_func(a, b):
            nonlocal call_count
            call_count += 1
            return a + b
        
        # Call the function multiple times with same arguments
        result1 = test_func(1, 2)
        result2 = test_func(1, 2)
        
        # Check results
        self.assertEqual(result1, 3)
        self.assertEqual(result2, 3)
        
        # Check that function was called only once
        self.assertEqual(call_count, 1)
        
        # Call with different arguments
        result3 = test_func(2, 3)
        
        # Check result
        self.assertEqual(result3, 5)
        
        # Check that function was called again
        self.assertEqual(call_count, 2)
    
    def test_memoize_with_ttl(self):
        """Test memoization with time-to-live."""
        # Define a function with memoize
        call_count = 0
        
        @memoize(ttl=0.1)  # Short TTL for testing
        def test_func():
            nonlocal call_count
            call_count += 1
            return call_count
        
        # Call the function
        result1 = test_func()
        self.assertEqual(result1, 1)
        
        # Call again immediately (should use cached result)
        result2 = test_func()
        self.assertEqual(result2, 1)
        self.assertEqual(call_count, 1)
        
        # Wait for TTL to expire
        time.sleep(0.2)
        
        # Call again (should recompute)
        result3 = test_func()
        self.assertEqual(result3, 2)
        self.assertEqual(call_count, 2)
    
    def test_memoize_with_maxsize(self):
        """Test memoization with maximum cache size."""
        # Define a function with memoize
        call_count = 0
        
        @memoize(maxsize=2)
        def test_func(n):
            nonlocal call_count
            call_count += 1
            return n * 2
        
        # Call with different arguments
        test_func(1)  # Cache: {1: 2}
        test_func(2)  # Cache: {1: 2, 2: 4}
        
        # Check call count
        self.assertEqual(call_count, 2)
        
        # Call with a new argument (should evict oldest entry)
        test_func(3)  # Cache: {2: 4, 3: 6}
        
        # Check call count
        self.assertEqual(call_count, 3)
        
        # Call with evicted argument (should recompute)
        test_func(1)  # Cache: {3: 6, 1: 2}
        
        # Check call count
        self.assertEqual(call_count, 4)
        
        # Call with cached argument (should use cache)
        test_func(3)  # Cache: {3: 6, 1: 2}
        
        # Check call count (unchanged)
        self.assertEqual(call_count, 4)
    
    def test_clear_cache(self):
        """Test clearing the memoization cache."""
        # Define a function with memoize
        call_count = 0
        
        @memoize()
        def test_func(n):
            nonlocal call_count
            call_count += 1
            return n * 2
        
        # Call the function
        test_func(1)
        self.assertEqual(call_count, 1)
        
        # Call again (should use cache)
        test_func(1)
        self.assertEqual(call_count, 1)
        
        # Clear the cache
        test_func.clear_cache()
        
        # Call again (should recompute)
        test_func(1)
        self.assertEqual(call_count, 2)


class TestDeprecated(unittest.TestCase):
    """Tests for the deprecated decorator."""
    
    @patch("core.decorators.logger")
    def test_deprecated_basic(self, mock_logger):
        """Test basic deprecation warning."""
        # Define a function with deprecated
        @deprecated()
        def old_func():
            return "result"
        
        # Call the function
        result = old_func()
        
        # Check result
        self.assertEqual(result, "result")
        
        # Check warning was logged
        mock_logger.warning.assert_called_once()
        self.assertIn("old_func is deprecated", str(mock_logger.warning.call_args))
    
    @patch("core.decorators.logger")
    def test_deprecated_with_message(self, mock_logger):
        """Test deprecation with custom message."""
        # Define a function with deprecated
        @deprecated(message="Custom deprecation message")
        def old_func():
            return "result"
        
        # Call the function
        result = old_func()
        
        # Check result
        self.assertEqual(result, "result")
        
        # Check warning was logged with custom message
        mock_logger.warning.assert_called_once()
        self.assertIn("Custom deprecation message", str(mock_logger.warning.call_args))
    
    @patch("core.decorators.logger")
    def test_deprecated_with_alternative(self, mock_logger):
        """Test deprecation with alternative function."""
        # Define a function with deprecated
        @deprecated(alternative="new_func")
        def old_func():
            return "result"
        
        # Call the function
        result = old_func()
        
        # Check result
        self.assertEqual(result, "result")
        
        # Check warning was logged with alternative
        mock_logger.warning.assert_called_once()
        self.assertIn("use new_func instead", str(mock_logger.warning.call_args))


if __name__ == "__main__":
    unittest.main()

