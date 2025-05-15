"""
Unit tests for the error handling middleware.
"""

import pytest
import asyncio
import os
import tempfile
from unittest.mock import MagicMock, patch

from core.utils.error_handling import (
    WiseflowError,
    ConnectionError,
    DataProcessingError,
    TaskError,
    handle_exceptions,
    log_error,
    save_error_to_file,
    ErrorHandler,
    async_error_handler
)


def test_wiseflow_error_initialization():
    """Test WiseflowError initialization."""
    # Create a basic error
    error = WiseflowError("Test error")
    assert error.message == "Test error"
    assert error.details == {}
    assert error.cause is None
    
    # Create an error with details and cause
    cause = ValueError("Original error")
    error_with_details = WiseflowError(
        "Detailed error",
        details={"key": "value"},
        cause=cause
    )
    assert error_with_details.message == "Detailed error"
    assert error_with_details.details == {"key": "value"}
    assert error_with_details.cause == cause


def test_wiseflow_error_to_dict():
    """Test converting WiseflowError to dictionary."""
    # Create an error with details and cause
    cause = ValueError("Original error")
    error = WiseflowError(
        "Detailed error",
        details={"key": "value"},
        cause=cause
    )
    
    # Convert to dictionary
    error_dict = error.to_dict()
    
    # Check dictionary contents
    assert error_dict["error_type"] == "WiseflowError"
    assert error_dict["message"] == "Detailed error"
    assert "timestamp" in error_dict
    assert error_dict["details"] == {"key": "value"}
    assert error_dict["cause"]["error_type"] == "ValueError"
    assert error_dict["cause"]["message"] == "Original error"


def test_error_subclasses():
    """Test WiseflowError subclasses."""
    # Test ConnectionError
    conn_error = ConnectionError("Connection failed")
    assert isinstance(conn_error, WiseflowError)
    assert conn_error.message == "Connection failed"
    
    # Test DataProcessingError
    data_error = DataProcessingError("Data processing failed")
    assert isinstance(data_error, WiseflowError)
    assert data_error.message == "Data processing failed"
    
    # Test TaskError
    task_error = TaskError("Task failed")
    assert isinstance(task_error, WiseflowError)
    assert task_error.message == "Task failed"


def test_handle_exceptions_decorator():
    """Test handle_exceptions decorator."""
    # Define a function that raises an exception
    @handle_exceptions(error_types=[ValueError], default_return="default")
    def failing_function():
        raise ValueError("Test error")
    
    # Call the function
    result = failing_function()
    
    # Check that the default value was returned
    assert result == "default"
    
    # Define a function that returns a value
    @handle_exceptions(error_types=[ValueError], default_return="default")
    def successful_function():
        return "success"
    
    # Call the function
    result = successful_function()
    
    # Check that the actual value was returned
    assert result == "success"


def test_handle_exceptions_with_reraise():
    """Test handle_exceptions decorator with reraise=True."""
    # Define a function that raises an exception
    @handle_exceptions(error_types=[ValueError], reraise=True)
    def failing_function():
        raise ValueError("Test error")
    
    # Call the function
    with pytest.raises(ValueError, match="Test error"):
        failing_function()


@pytest.mark.asyncio
async def test_handle_exceptions_async():
    """Test handle_exceptions decorator with async functions."""
    # Define an async function that raises an exception
    @handle_exceptions(error_types=[ValueError], default_return="default")
    async def failing_async_function():
        await asyncio.sleep(0.1)
        raise ValueError("Test error")
    
    # Call the function
    result = await failing_async_function()
    
    # Check that the default value was returned
    assert result == "default"
    
    # Define an async function that returns a value
    @handle_exceptions(error_types=[ValueError], default_return="default")
    async def successful_async_function():
        await asyncio.sleep(0.1)
        return "success"
    
    # Call the function
    result = await successful_async_function()
    
    # Check that the actual value was returned
    assert result == "success"


def test_handle_exceptions_with_error_transformer():
    """Test handle_exceptions decorator with error_transformer."""
    # Define an error transformer
    def transform_error(error):
        return DataProcessingError(f"Transformed: {str(error)}")
    
    # Define a function that raises an exception
    @handle_exceptions(
        error_types=[ValueError],
        default_return="default",
        error_transformer=transform_error
    )
    def failing_function():
        raise ValueError("Test error")
    
    # Call the function
    result = failing_function()
    
    # Check that the default value was returned
    assert result == "default"


def test_save_error_to_file():
    """Test saving an error to a file."""
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save an error to a file
        filepath = save_error_to_file(
            function_name="test_function",
            error_message="Test error",
            traceback_str="Traceback...",
            directory=temp_dir,
            context={"key": "value"}
        )
        
        # Check that the file was created
        assert os.path.exists(filepath)
        
        # Check file contents
        with open(filepath, "r") as f:
            content = f.read()
            assert "Error in test_function" in content
            assert "Error message: Test error" in content
            assert "Context:" in content
            assert "\"key\": \"value\"" in content
            assert "Traceback:" in content
            assert "Traceback..." in content


def test_error_handler_context_manager():
    """Test ErrorHandler context manager."""
    # Use ErrorHandler to catch an exception
    with ErrorHandler(default="default") as handler:
        raise ValueError("Test error")
    
    # Check that the error was caught
    assert handler.error_occurred
    assert isinstance(handler.error, ValueError)
    assert str(handler.error) == "Test error"
    assert handler.result == "default"
    
    # Use ErrorHandler with a successful operation
    with ErrorHandler(default="default") as handler:
        result = "success"
    
    # Check that no error was caught
    assert not handler.error_occurred
    assert handler.error is None
    assert handler.result == "default"  # Result is not updated by the context manager


@pytest.mark.asyncio
async def test_async_error_handler():
    """Test async_error_handler function."""
    # Use async_error_handler to catch an exception
    async def failing_coroutine():
        await asyncio.sleep(0.1)
        raise ValueError("Test error")
    
    result = await async_error_handler(
        failing_coroutine(),
        default="default"
    )
    
    # Check that the default value was returned
    assert result == "default"
    
    # Use async_error_handler with a successful operation
    async def successful_coroutine():
        await asyncio.sleep(0.1)
        return "success"
    
    result = await async_error_handler(
        successful_coroutine(),
        default="default"
    )
    
    # Check that the actual value was returned
    assert result == "success"

