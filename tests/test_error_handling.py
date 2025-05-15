#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the error handling system.

This module contains tests for the error handling and recovery system.
"""

import asyncio
import logging
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

# Add the parent directory to the path so we can import the core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.utils.error_handling import (
    WiseflowError, ConnectionError, DataProcessingError, TaskError,
    ValidationError, NotFoundError, ParallelError
)
from core.utils.error_manager import (
    ErrorManager, ErrorSeverity, RecoveryStrategy, with_error_handling, retry
)
from core.plugins.connectors.research.parallel_manager import (
    ParallelManager, TaskPriority, ParallelExecutionError, TaskExecutionError
)

# Disable logging during tests
logging.disable(logging.CRITICAL)

class TestErrorHandling(unittest.TestCase):
    """Tests for the error handling system."""
    
    def setUp(self):
        """Set up the test environment."""
        # Reset the error manager
        self.error_manager = ErrorManager()
        self.error_manager._error_counts = {}
        self.error_manager._error_timestamps = {}
        self.error_manager._recovery_attempts = {}
    
    def test_wiseflow_error_creation(self):
        """Test creating a WiseflowError."""
        error = WiseflowError("Test error", {"key": "value"})
        
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.details, {"key": "value"})
        self.assertIsNone(error.cause)
    
    def test_wiseflow_error_with_cause(self):
        """Test creating a WiseflowError with a cause."""
        cause = ValueError("Original error")
        error = WiseflowError("Test error", {"key": "value"}, cause)
        
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.details, {"key": "value"})
        self.assertEqual(error.cause, cause)
    
    def test_wiseflow_error_to_dict(self):
        """Test converting a WiseflowError to a dictionary."""
        error = WiseflowError("Test error", {"key": "value"})
        error_dict = error.to_dict()
        
        self.assertEqual(error_dict["error_type"], "WiseflowError")
        self.assertEqual(error_dict["message"], "Test error")
        self.assertEqual(error_dict["details"], {"key": "value"})
        self.assertIn("timestamp", error_dict)
    
    def test_error_hierarchy(self):
        """Test the error hierarchy."""
        # Test that all error types inherit from WiseflowError
        self.assertTrue(issubclass(ConnectionError, WiseflowError))
        self.assertTrue(issubclass(DataProcessingError, WiseflowError))
        self.assertTrue(issubclass(TaskError, WiseflowError))
        self.assertTrue(issubclass(ValidationError, WiseflowError))
        self.assertTrue(issubclass(NotFoundError, WiseflowError))
        self.assertTrue(issubclass(ParallelError, WiseflowError))
    
    def test_error_manager_handle_error(self):
        """Test handling an error with the error manager."""
        error = ConnectionError("Connection failed", {"url": "http://example.com"})
        context = {"function": "test_function"}
        
        # Handle the error
        result = self.error_manager.handle_error(
            error,
            context,
            ErrorSeverity.MEDIUM,
            RecoveryStrategy.NONE,
            notify=False,
            log_level="error",
            save_to_file=False
        )
        
        # Check that the error was tracked
        error_id = self.error_manager._get_error_id(error)
        self.assertEqual(self.error_manager._error_counts.get(error_id, 0), 1)
        self.assertEqual(len(self.error_manager._error_timestamps.get(error_id, [])), 1)
        self.assertEqual(self.error_manager._recovery_attempts.get(error_id, 0), 1)
    
    def test_error_manager_max_recovery_attempts(self):
        """Test that the error manager respects max recovery attempts."""
        error = ConnectionError("Connection failed", {"url": "http://example.com"})
        context = {"function": "test_function"}
        
        # Handle the error multiple times
        for _ in range(3):
            result = self.error_manager.handle_error(
                error,
                context,
                ErrorSeverity.MEDIUM,
                RecoveryStrategy.RETRY,
                notify=False,
                log_level="error",
                save_to_file=False,
                max_recovery_attempts=2
            )
        
        # Check that the error was tracked
        error_id = self.error_manager._get_error_id(error)
        self.assertEqual(self.error_manager._error_counts.get(error_id, 0), 3)
        self.assertEqual(len(self.error_manager._error_timestamps.get(error_id, [])), 3)
        self.assertEqual(self.error_manager._recovery_attempts.get(error_id, 0), 3)
        
        # The third attempt should return False since we've exceeded max_recovery_attempts
        self.assertFalse(result)
    
    def test_with_error_handling_decorator(self):
        """Test the with_error_handling decorator."""
        # Define a function that raises an error
        @with_error_handling(
            error_types=[ValueError],
            severity=ErrorSeverity.MEDIUM,
            recovery_strategy=RecoveryStrategy.NONE,
            notify=False,
            log_level="error",
            default_return=42
        )
        def function_that_raises():
            raise ValueError("Test error")
        
        # Call the function
        result = function_that_raises()
        
        # Check that the default return value was used
        self.assertEqual(result, 42)
    
    def test_retry_decorator(self):
        """Test the retry decorator."""
        # Create a mock function that raises an error on the first two calls
        mock_func = MagicMock(side_effect=[ValueError("First error"), ValueError("Second error"), "success"])
        
        # Define a function that uses the retry decorator
        @retry(
            max_retries=2,
            retry_delay=0.01,
            backoff_factor=1.0,
            retryable_errors=[ValueError]
        )
        def function_with_retry():
            return mock_func()
        
        # Call the function
        result = function_with_retry()
        
        # Check that the function was called three times
        self.assertEqual(mock_func.call_count, 3)
        
        # Check that the final result is correct
        self.assertEqual(result, "success")
    
    def test_retry_decorator_max_retries(self):
        """Test that the retry decorator respects max retries."""
        # Create a mock function that always raises an error
        mock_func = MagicMock(side_effect=ValueError("Test error"))
        
        # Define a function that uses the retry decorator
        @retry(
            max_retries=2,
            retry_delay=0.01,
            backoff_factor=1.0,
            retryable_errors=[ValueError]
        )
        def function_with_retry():
            return mock_func()
        
        # Call the function and expect it to raise an error
        with self.assertRaises(ValueError):
            function_with_retry()
        
        # Check that the function was called three times (initial + 2 retries)
        self.assertEqual(mock_func.call_count, 3)

class TestParallelManager(unittest.TestCase):
    """Tests for the parallel manager."""
    
    def setUp(self):
        """Set up the test environment."""
        self.parallel_manager = ParallelManager(max_workers=2)
    
    def tearDown(self):
        """Clean up after the test."""
        self.parallel_manager.reset()
    
    def test_add_task(self):
        """Test adding a task to the parallel manager."""
        # Add a task
        task_id = self.parallel_manager.add_task(
            task_id="test_task",
            func=lambda: "result",
            args=(),
            kwargs={},
            dependencies=[],
            priority=TaskPriority.NORMAL,
            max_retries=3
        )
        
        # Check that the task was added
        self.assertEqual(task_id, "test_task")
        self.assertIn(task_id, self.parallel_manager.tasks)
        self.assertEqual(self.parallel_manager.tasks[task_id].id, task_id)
        self.assertEqual(self.parallel_manager.tasks[task_id].max_retries, 3)
    
    def test_add_duplicate_task(self):
        """Test adding a duplicate task to the parallel manager."""
        # Add a task
        self.parallel_manager.add_task(
            task_id="test_task",
            func=lambda: "result"
        )
        
        # Try to add a duplicate task
        with self.assertRaises(ValueError):
            self.parallel_manager.add_task(
                task_id="test_task",
                func=lambda: "result"
            )
    
    async def test_execute_all(self):
        """Test executing all tasks."""
        # Add tasks
        self.parallel_manager.add_task(
            task_id="task1",
            func=lambda: "result1"
        )
        
        self.parallel_manager.add_task(
            task_id="task2",
            func=lambda: "result2"
        )
        
        # Execute all tasks
        results = await self.parallel_manager.execute_all()
        
        # Check the results
        self.assertEqual(results["task1"], "result1")
        self.assertEqual(results["task2"], "result2")
    
    async def test_execute_with_dependencies(self):
        """Test executing tasks with dependencies."""
        # Add tasks with dependencies
        self.parallel_manager.add_task(
            task_id="task1",
            func=lambda: "result1"
        )
        
        self.parallel_manager.add_task(
            task_id="task2",
            func=lambda: "result2",
            dependencies=["task1"]
        )
        
        # Execute all tasks
        results = await self.parallel_manager.execute_all()
        
        # Check the results
        self.assertEqual(results["task1"], "result1")
        self.assertEqual(results["task2"], "result2")
    
    async def test_execute_with_error(self):
        """Test executing tasks with an error."""
        # Add tasks
        self.parallel_manager.add_task(
            task_id="task1",
            func=lambda: "result1"
        )
        
        self.parallel_manager.add_task(
            task_id="task2",
            func=lambda: 1/0  # This will raise a ZeroDivisionError
        )
        
        # Execute all tasks
        results = await self.parallel_manager.execute_all(raise_on_failure=False)
        
        # Check the results
        self.assertEqual(results["task1"], "result1")
        self.assertNotIn("task2", results)
        
        # Check that task2 failed
        self.assertIn("task2", self.parallel_manager.failed_tasks)
        self.assertEqual(self.parallel_manager.tasks["task2"].status.value, "failed")
        self.assertIsInstance(self.parallel_manager.tasks["task2"].error, ZeroDivisionError)
    
    async def test_execute_with_retry(self):
        """Test executing tasks with retry."""
        # Create a mock function that raises an error on the first call
        mock_func = MagicMock(side_effect=[ZeroDivisionError("First error"), "result"])
        
        # Add a task with the mock function
        self.parallel_manager.add_task(
            task_id="task1",
            func=mock_func,
            max_retries=1
        )
        
        # Execute all tasks
        results = await self.parallel_manager.execute_all()
        
        # Check the results
        self.assertEqual(results["task1"], "result")
        
        # Check that the function was called twice
        self.assertEqual(mock_func.call_count, 2)
    
    async def test_execute_with_timeout(self):
        """Test executing tasks with a timeout."""
        # Add a task that sleeps
        self.parallel_manager.add_task(
            task_id="task1",
            func=lambda: asyncio.sleep(1)
        )
        
        # Execute all tasks with a short timeout
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(self.parallel_manager.execute_all(), 0.1)

if __name__ == "__main__":
    unittest.main()

