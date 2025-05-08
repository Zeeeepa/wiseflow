"""
Tests for the task management system.
"""

import os
import sys
import asyncio
import unittest
import time
from unittest.mock import patch, MagicMock

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.task.unified_manager import unified_task_manager
from core.task_manager import TaskManager, TaskStatus, TaskPriority
from core.thread_pool_manager import ThreadPoolManager
from core.task.monitor import TaskMonitor

class TestTaskManagement(unittest.TestCase):
    """Test the task management system."""
    
    def setUp(self):
        """Set up the test environment."""
        # Mock the config
        self.config_patcher = patch('core.config.config', {
            "MAX_CONCURRENT_TASKS": 4,
            "MAX_THREAD_WORKERS": 4,
            "USE_NEW_TASK_SYSTEM": True
        })
        self.mock_config = self.config_patcher.start()
        
        # Mock the logger
        self.logger_patcher = patch('logging.getLogger')
        self.mock_logger = self.logger_patcher.start()
        
        # Mock the event system
        self.event_patcher = patch('core.event_system.publish_sync')
        self.mock_publish = self.event_patcher.start()
        
        # Reset the singleton instances
        TaskManager._instance = None
        ThreadPoolManager._instance = None
        TaskMonitor._instance = None
        unified_task_manager._instance = None
    
    def tearDown(self):
        """Clean up after the test."""
        self.config_patcher.stop()
        self.logger_patcher.stop()
        self.event_patcher.stop()
    
    def test_task_registration(self):
        """Test task registration."""
        # Define a simple task function
        def task_func(x, y):
            return x + y
        
        # Register the task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            task_id = loop.run_until_complete(unified_task_manager.register_task(
                name="Test Task",
                func=task_func,
                args=(1, 2),
                task_type="test",
                description="Test task description"
            ))
            
            # Verify the task was registered
            self.assertIsNotNone(task_id)
            
            # Get the task status
            status = loop.run_until_complete(unified_task_manager.get_task_status(task_id))
            
            # Verify the task status
            self.assertEqual(status, "pending")
        finally:
            loop.close()
    
    def test_task_execution(self):
        """Test task execution."""
        # Define a simple task function
        def task_func(x, y):
            return x + y
        
        # Register and execute the task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            task_id = loop.run_until_complete(unified_task_manager.register_task(
                name="Test Task",
                func=task_func,
                args=(1, 2),
                task_type="test",
                description="Test task description",
                metadata={"func": task_func, "args": (1, 2), "kwargs": {}}
            ))
            
            # Execute the task
            result = loop.run_until_complete(unified_task_manager.execute_task(task_id, wait=True))
            
            # Verify the result
            self.assertEqual(result, 3)
            
            # Get the task status
            status = loop.run_until_complete(unified_task_manager.get_task_status(task_id))
            
            # Verify the task status
            self.assertEqual(status, "completed")
        finally:
            loop.close()
    
    def test_task_cancellation(self):
        """Test task cancellation."""
        # Define a task function that sleeps
        def task_func():
            time.sleep(10)
            return "Done"
        
        # Register the task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            task_id = loop.run_until_complete(unified_task_manager.register_task(
                name="Test Task",
                func=task_func,
                task_type="test",
                description="Test task description",
                metadata={"func": task_func, "args": (), "kwargs": {}}
            ))
            
            # Start the task
            loop.run_until_complete(unified_task_manager.execute_task(task_id))
            
            # Wait a bit for the task to start
            time.sleep(0.1)
            
            # Cancel the task
            cancelled = loop.run_until_complete(unified_task_manager.cancel_task(task_id))
            
            # Verify the task was cancelled
            self.assertTrue(cancelled)
            
            # Get the task status
            status = loop.run_until_complete(unified_task_manager.get_task_status(task_id))
            
            # Verify the task status
            self.assertEqual(status, "cancelled")
        finally:
            loop.close()
    
    def test_task_error_handling(self):
        """Test task error handling."""
        # Define a task function that raises an exception
        def task_func():
            raise ValueError("Test error")
        
        # Register the task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            task_id = loop.run_until_complete(unified_task_manager.register_task(
                name="Test Task",
                func=task_func,
                task_type="test",
                description="Test task description",
                metadata={"func": task_func, "args": (), "kwargs": {}}
            ))
            
            # Execute the task
            loop.run_until_complete(unified_task_manager.execute_task(task_id))
            
            # Wait a bit for the task to complete
            time.sleep(0.1)
            
            # Get the task status
            status = loop.run_until_complete(unified_task_manager.get_task_status(task_id))
            
            # Verify the task status
            self.assertEqual(status, "failed")
            
            # Get the task error
            error = loop.run_until_complete(unified_task_manager.get_task_error(task_id))
            
            # Verify the error
            self.assertIn("Test error", error)
        finally:
            loop.close()
    
    def test_concurrent_tasks(self):
        """Test concurrent task execution."""
        # Define a task function that sleeps
        def task_func(task_id, sleep_time):
            time.sleep(sleep_time)
            return f"Task {task_id} completed"
        
        # Register multiple tasks
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            task_ids = []
            for i in range(5):
                task_id = loop.run_until_complete(unified_task_manager.register_task(
                    name=f"Test Task {i}",
                    func=task_func,
                    args=(i, 0.1),
                    task_type="test",
                    description=f"Test task {i} description",
                    metadata={"func": task_func, "args": (i, 0.1), "kwargs": {}}
                ))
                task_ids.append(task_id)
            
            # Execute all tasks
            for task_id in task_ids:
                loop.run_until_complete(unified_task_manager.execute_task(task_id))
            
            # Wait for all tasks to complete
            time.sleep(0.5)
            
            # Verify all tasks completed
            for task_id in task_ids:
                status = loop.run_until_complete(unified_task_manager.get_task_status(task_id))
                self.assertEqual(status, "completed")
                
                result = loop.run_until_complete(unified_task_manager.get_task_result(task_id))
                self.assertIn("Task", result)
                self.assertIn("completed", result)
        finally:
            loop.close()
    
    def test_task_cleanup(self):
        """Test task cleanup."""
        # Define a simple task function
        def task_func():
            return "Done"
        
        # Register and execute the task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            task_id = loop.run_until_complete(unified_task_manager.register_task(
                name="Test Task",
                func=task_func,
                task_type="test",
                description="Test task description",
                metadata={"func": task_func, "args": (), "kwargs": {}}
            ))
            
            # Execute the task
            loop.run_until_complete(unified_task_manager.execute_task(task_id))
            
            # Wait for the task to complete
            time.sleep(0.1)
            
            # Clean up completed tasks
            cleaned_up = loop.run_until_complete(unified_task_manager.cleanup_completed_tasks(0))
            
            # Verify the task was cleaned up
            self.assertEqual(cleaned_up, 1)
            
            # Try to get the task status
            status = loop.run_until_complete(unified_task_manager.get_task_status(task_id))
            
            # Verify the task is gone
            self.assertIsNone(status)
        finally:
            loop.close()

if __name__ == '__main__':
    unittest.main()

