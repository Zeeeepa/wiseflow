"""
Unit tests for the error handling and logging utilities.
"""

import os
import re
import pytest
import logging
import tempfile
from unittest.mock import patch, MagicMock

from core.utils.error_handling import (
    handle_exception,
    retry,
    validate_input,
    log_error,
    ErrorCode,
    WiseflowError,
    ValidationError,
    APIError,
    DatabaseError
)
from core.utils.logging_config import configure_logging


@pytest.mark.unit
class TestErrorHandling:
    """Test the error handling utilities."""
    
    def test_handle_exception(self):
        """Test the handle_exception function."""
        # Create a mock logger
        mock_logger = MagicMock()
        
        # Test handling a standard exception
        exception = ValueError("Test error")
        result = handle_exception(exception, logger=mock_logger)
        
        assert result["success"] is False
        assert result["error"] == "ValueError: Test error"
        mock_logger.error.assert_called_once()
        
        # Reset the mock
        mock_logger.reset_mock()
        
        # Test handling a WiseflowError
        exception = WiseflowError(
            message="Test Wiseflow error",
            error_code=ErrorCode.VALIDATION_ERROR,
            details={"field": "test_field"}
        )
        result = handle_exception(exception, logger=mock_logger)
        
        assert result["success"] is False
        assert result["error"] == "WiseflowError: Test Wiseflow error"
        assert result["error_code"] == ErrorCode.VALIDATION_ERROR
        assert result["details"] == {"field": "test_field"}
        mock_logger.error.assert_called_once()
    
    def test_retry_decorator(self):
        """Test the retry decorator."""
        # Create a function that fails twice then succeeds
        mock_func = MagicMock()
        mock_func.side_effect = [ValueError("First error"), ValueError("Second error"), "success"]
        
        # Apply the retry decorator
        @retry(max_retries=3, retry_delay=0.01)
        def test_func():
            return mock_func()
        
        # Call the function
        result = test_func()
        
        # Check that the function was called 3 times
        assert mock_func.call_count == 3
        assert result == "success"
        
        # Reset the mock
        mock_func.reset_mock()
        mock_func.side_effect = [ValueError("Error")] * 4
        
        # Apply the retry decorator with fewer retries
        @retry(max_retries=2, retry_delay=0.01)
        def test_func_fail():
            return mock_func()
        
        # Call the function and check that it raises an exception
        with pytest.raises(ValueError):
            test_func_fail()
        
        # Check that the function was called 3 times (initial + 2 retries)
        assert mock_func.call_count == 3
    
    def test_validate_input(self):
        """Test the validate_input function."""
        # Test with valid input
        data = {"name": "Test", "age": 30}
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0}
            },
            "required": ["name", "age"]
        }
        
        result = validate_input(data, schema)
        assert result is True
        
        # Test with invalid input (wrong type)
        data = {"name": "Test", "age": "thirty"}
        with pytest.raises(ValidationError):
            validate_input(data, schema)
        
        # Test with invalid input (missing required field)
        data = {"name": "Test"}
        with pytest.raises(ValidationError):
            validate_input(data, schema)
        
        # Test with invalid input (value out of range)
        data = {"name": "Test", "age": -1}
        with pytest.raises(ValidationError):
            validate_input(data, schema)
    
    def test_log_error(self):
        """Test the log_error function."""
        # Create a mock logger
        mock_logger = MagicMock()
        
        # Test logging a standard error
        error = ValueError("Test error")
        log_error(error, logger=mock_logger)
        mock_logger.error.assert_called_once()
        
        # Reset the mock
        mock_logger.reset_mock()
        
        # Test logging a WiseflowError
        error = WiseflowError(
            message="Test Wiseflow error",
            error_code=ErrorCode.VALIDATION_ERROR,
            details={"field": "test_field"}
        )
        log_error(error, logger=mock_logger)
        mock_logger.error.assert_called_once()
        
        # Reset the mock
        mock_logger.reset_mock()
        
        # Test logging with additional context
        context = {"user_id": "123", "action": "test_action"}
        log_error(error, context=context, logger=mock_logger)
        mock_logger.error.assert_called_once()
        
        # Check that the context was included in the log message
        args, kwargs = mock_logger.error.call_args
        log_message = args[0]
        assert "user_id" in log_message
        assert "action" in log_message


@pytest.mark.unit
class TestErrorClasses:
    """Test the error classes."""
    
    def test_wiseflow_error(self):
        """Test the WiseflowError class."""
        # Create a WiseflowError
        error = WiseflowError(
            message="Test error",
            error_code=ErrorCode.VALIDATION_ERROR,
            details={"field": "test_field"}
        )
        
        assert str(error) == "Test error"
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.details == {"field": "test_field"}
        
        # Test with default values
        error = WiseflowError(message="Test error")
        assert error.error_code == ErrorCode.UNKNOWN_ERROR
        assert error.details == {}
    
    def test_validation_error(self):
        """Test the ValidationError class."""
        # Create a ValidationError
        error = ValidationError(
            message="Invalid input",
            details={"field": "test_field", "error": "Required field missing"}
        )
        
        assert str(error) == "Invalid input"
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.details == {"field": "test_field", "error": "Required field missing"}
        
        # Test with default values
        error = ValidationError(message="Invalid input")
        assert error.details == {}
    
    def test_api_error(self):
        """Test the APIError class."""
        # Create an APIError
        error = APIError(
            message="API request failed",
            status_code=404,
            details={"endpoint": "/api/test"}
        )
        
        assert str(error) == "API request failed"
        assert error.error_code == ErrorCode.API_ERROR
        assert error.status_code == 404
        assert error.details == {"endpoint": "/api/test"}
        
        # Test with default values
        error = APIError(message="API request failed")
        assert error.status_code == 500
        assert error.details == {}
    
    def test_database_error(self):
        """Test the DatabaseError class."""
        # Create a DatabaseError
        error = DatabaseError(
            message="Database operation failed",
            details={"operation": "insert", "table": "users"}
        )
        
        assert str(error) == "Database operation failed"
        assert error.error_code == ErrorCode.DATABASE_ERROR
        assert error.details == {"operation": "insert", "table": "users"}
        
        # Test with default values
        error = DatabaseError(message="Database operation failed")
        assert error.details == {}


@pytest.mark.unit
class TestLoggingConfig:
    """Test the logging configuration."""
    
    def test_configure_logging(self):
        """Test the configure_logging function."""
        # Create a temporary log file
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as temp_file:
            log_file = temp_file.name
        
        try:
            # Configure logging
            logger = configure_logging(
                log_file=log_file,
                log_level=logging.DEBUG,
                log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            
            # Check that the logger was configured correctly
            assert logger.level == logging.DEBUG
            assert len(logger.handlers) > 0
            
            # Log a message
            test_message = "Test log message"
            logger.info(test_message)
            
            # Check that the message was written to the log file
            with open(log_file, "r") as f:
                log_content = f.read()
                assert test_message in log_content
            
            # Test logging at different levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")
            
            # Check that all messages were written to the log file
            with open(log_file, "r") as f:
                log_content = f.read()
                assert "Debug message" in log_content
                assert "Info message" in log_content
                assert "Warning message" in log_content
                assert "Error message" in log_content
                assert "Critical message" in log_content
        
        finally:
            # Clean up
            if os.path.exists(log_file):
                os.remove(log_file)

