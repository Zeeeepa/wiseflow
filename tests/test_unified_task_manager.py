"""
Tests for the unified_task_manager module.
"""

import unittest
import asyncio
import time
from unittest.mock import patch, MagicMock

from core.unified_task_manager import (
    UnifiedTaskManager,
    Task,
    TaskStatus,
    TaskPriority
)

class TestUnifiedTaskManager(unittest.TestCase):
    """Test cases for UnifiedTaskManager."""
    
    def setUp(self):
        """Set up test environment."""
        self.task_manager = UnifiedTaskManager(max_workers=2)
    
    def tearDown(self):
        """Clean up test environment."""
        self.task_manager.stop()
    
    def test_register_task(self):
        """Test registering a task."""
        # Define a simple test function
        def test_func(x, y):
            return x + y
        
        # Register the task
        task_id = self.task_manager.register_task(
            function=test_func,
            args=(1, 2),
            name="test_task",
            priority=TaskPriority.HIGH,
            tags=["test"]
        )
        
        # Check that the task was registered
        self.assertIn(task_id, self.task_manager.tasks)
        task = self.task_manager.get_task(task_id)
        self.assertEqual(task.name, "test_task")
        self.assertEqual(task.priority, TaskPriority.HIGH)
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertIn(task_id, self.task_manager.pending_tasks)
        self.assertEqual(task.tags, ["test"])
    
    def test_execute_sync_task(self):
        """Test executing a synchronous task."""
        # Define a simple test function
        def test_func(x, y):
            return x + y
        
        # Register and execute the task
        task_id = self.task_manager.register_task(
            function=test_func,
            args=(1, 2),
            name="test_sync_task"
        )
        execution_id = self.task_manager.execute_task(task_id, wait=True)
        
        # Check that the task was executed
        self.assertIsNotNone(execution_id)
        task = self.task_manager.get_task(task_id)
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertEqual(task.result, 3)
        self.assertIn(task_id, self.task_manager.completed_tasks)
    
    def test_execute_async_task(self):
        """Test executing an asynchronous task."""
        # Define a simple async test function
        async def test_async_func(x, y):
            await asyncio.sleep(0.1)
            return x + y
        
        # Register and execute the task
        task_id = self.task_manager.register_task(
            function=test_async_func,
            args=(1, 2),
            name="test_async_task"
        )
        
        # Create event loop and run the task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            execution_id = self.task_manager.execute_task(task_id)
            self.assertIsNotNone(execution_id)
            
            # Wait for task to complete
            task = self.task_manager.get_task(task_id)
            loop.run_until_complete(task.task_object)
            
            # Check that the task was executed
            self.assertEqual(task.status, TaskStatus.COMPLETED)
            self.assertEqual(task.result, 3)
            self.assertIn(task_id, self.task_manager.completed_tasks)
            
        finally:
            loop.close()
    
    def test_task_dependencies(self):
        """Test task dependencies."""
        # Define test functions
        def task_a():
            return "A"
        
        def task_b():
            return "B"
        
        # Register tasks
        task_a_id = self.task_manager.register_task(
            function=task_a,
            name="task_a"
        )
        
        task_b_id = self.task_manager.register_task(
            function=task_b,
            name="task_b",
            dependencies=[task_a_id]
        )
        
        # Try to execute task B (should wait for task A)
        execution_id = self.task_manager.execute_task(task_b_id)
        self.assertIsNone(execution_id)
        
        task_b = self.task_manager.get_task(task_b_id)
        self.assertEqual(task_b.status, TaskStatus.WAITING)
        self.assertIn(task_b_id, self.task_manager.waiting_tasks)
        
        # Execute task A
        execution_id = self.task_manager.execute_task(task_a_id, wait=True)
        self.assertIsNotNone(execution_id)
        
        # Check that task B is now ready
        task_b = self.task_manager.get_task(task_b_id)
        self.assertEqual(task_b.status, TaskStatus.PENDING)
        self.assertIn(task_b_id, self.task_manager.pending_tasks)
        
        # Execute task B
        execution_id = self.task_manager.execute_task(task_b_id, wait=True)
        self.assertIsNotNone(execution_id)
        
        # Check that both tasks completed
        task_a = self.task_manager.get_task(task_a_id)
        task_b = self.task_manager.get_task(task_b_id)
        self.assertEqual(task_a.status, TaskStatus.COMPLETED)
        self.assertEqual(task_b.status, TaskStatus.COMPLETED)
        self.assertEqual(task_a.result, "A")
        self.assertEqual(task_b.result, "B")
    
    def test_cancel_task(self):
        """Test cancelling a task."""
        # Define a long-running test function
        def long_task():
            time.sleep(1)
            return "done"
        
        # Register and execute the task
        task_id = self.task_manager.register_task(
            function=long_task,
            name="long_task"
        )
        execution_id = self.task_manager.execute_task(task_id)
        self.assertIsNotNone(execution_id)
        
        # Cancel the task
        result = self.task_manager.cancel_task(task_id)
        self.assertTrue(result)
        
        # Check that the task was cancelled
        task = self.task_manager.get_task(task_id)
        self.assertEqual(task.status, TaskStatus.CANCELLED)
        self.assertIn(task_id, self.task_manager.cancelled_tasks)
    
    def test_get_tasks_by_status(self):
        """Test getting tasks by status."""
        # Define test functions
        def task_a():
            return "A"
        
        def task_b():
            return "B"
        
        def task_c():
            raise ValueError("Error in task C")
        
        # Register tasks
        task_a_id = self.task_manager.register_task(function=task_a, name="task_a")
        task_b_id = self.task_manager.register_task(function=task_b, name="task_b")
        task_c_id = self.task_manager.register_task(function=task_c, name="task_c")
        
        # Execute tasks
        self.task_manager.execute_task(task_a_id, wait=True)
        self.task_manager.execute_task(task_b_id, wait=True)
        
        try:
            self.task_manager.execute_task(task_c_id, wait=True)
        except ValueError:
            pass  # Expected error
        
        # Get tasks by status
        completed_tasks = self.task_manager.get_tasks_by_status(TaskStatus.COMPLETED)
        failed_tasks = self.task_manager.get_tasks_by_status(TaskStatus.FAILED)
        
        # Check results
        self.assertEqual(len(completed_tasks), 2)
        self.assertEqual(len(failed_tasks), 1)
        
        completed_ids = [task.task_id for task in completed_tasks]
        failed_ids = [task.task_id for task in failed_tasks]
        
        self.assertIn(task_a_id, completed_ids)
        self.assertIn(task_b_id, completed_ids)
        self.assertIn(task_c_id, failed_ids)
    
    def test_get_tasks_by_tag(self):
        """Test getting tasks by tag."""
        # Define test functions
        def task_a():
            return "A"
        
        def task_b():
            return "B"
        
        # Register tasks with tags
        task_a_id = self.task_manager.register_task(
            function=task_a,
            name="task_a",
            tags=["tag1", "tag2"]
        )
        
        task_b_id = self.task_manager.register_task(
            function=task_b,
            name="task_b",
            tags=["tag2", "tag3"]
        )
        
        # Get tasks by tag
        tag1_tasks = self.task_manager.get_tasks_by_tag("tag1")
        tag2_tasks = self.task_manager.get_tasks_by_tag("tag2")
        tag3_tasks = self.task_manager.get_tasks_by_tag("tag3")
        
        # Check results
        self.assertEqual(len(tag1_tasks), 1)
        self.assertEqual(len(tag2_tasks), 2)
        self.assertEqual(len(tag3_tasks), 1)
        
        self.assertEqual(tag1_tasks[0].task_id, task_a_id)
        
        tag2_ids = [task.task_id for task in tag2_tasks]
        self.assertIn(task_a_id, tag2_ids)
        self.assertIn(task_b_id, tag2_ids)
        
        self.assertEqual(tag3_tasks[0].task_id, task_b_id)
    
    def test_get_metrics(self):
        """Test getting task manager metrics."""
        # Define test functions
        def task_a():
            return "A"
        
        def task_b():
            return "B"
        
        def task_c():
            raise ValueError("Error in task C")
        
        # Register tasks
        task_a_id = self.task_manager.register_task(function=task_a, name="task_a")
        task_b_id = self.task_manager.register_task(function=task_b, name="task_b")
        task_c_id = self.task_manager.register_task(function=task_c, name="task_c")
        
        # Execute tasks
        self.task_manager.execute_task(task_a_id, wait=True)
        self.task_manager.execute_task(task_b_id, wait=True)
        
        try:
            self.task_manager.execute_task(task_c_id, wait=True)
        except ValueError:
            pass  # Expected error
        
        # Get metrics
        metrics = self.task_manager.get_metrics()
        
        # Check metrics
        self.assertEqual(metrics["total_tasks"], 3)
        self.assertEqual(metrics["pending_tasks"], 0)
        self.assertEqual(metrics["running_tasks"], 0)
        self.assertEqual(metrics["completed_tasks"], 2)
        self.assertEqual(metrics["failed_tasks"], 1)
        self.assertEqual(metrics["cancelled_tasks"], 0)
    
    @patch('core.unified_task_manager.publish_sync')
    def test_events(self, mock_publish_sync):
        """Test that events are published."""
        # Define a simple test function
        def test_func():
            return "done"
        
        # Register and execute the task
        task_id = self.task_manager.register_task(function=test_func, name="test_task")
        self.task_manager.execute_task(task_id, wait=True)
        
        # Check that events were published
        self.assertTrue(mock_publish_sync.called)
        
        # At least 3 events should be published: registered, started, completed
        self.assertGreaterEqual(mock_publish_sync.call_count, 3)

if __name__ == '__main__':
    unittest.main()

