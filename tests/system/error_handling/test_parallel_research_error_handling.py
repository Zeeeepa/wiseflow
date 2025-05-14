"""
System tests for parallel research error handling.
"""

import pytest
import time
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import threading
import concurrent.futures

from core.plugins.connectors.research.parallel_manager import (
    ParallelResearchManager,
    get_parallel_research_manager
)
from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI
from core.plugins.connectors.research.state import ReportState, Sections

@pytest.mark.system
@pytest.mark.error_handling
class TestParallelResearchErrorHandling:
    """System tests for parallel research error handling."""
    
    @pytest.fixture
    def mock_research_graph(self):
        """Create a mock research graph that can be configured to raise errors."""
        with patch("core.plugins.connectors.research.parallel_manager.get_research_graph") as mock:
            graph = AsyncMock()
            # Default behavior is to return the state
            graph.ainvoke.side_effect = lambda state: state
            mock.return_value = graph
            yield graph
    
    @pytest.fixture
    def manager(self, mock_research_graph):
        """Create a ParallelResearchManager instance for testing."""
        manager = ParallelResearchManager(
            max_concurrent_tasks=3,
            max_retries=2,
            timeout=5
        )
        manager.start()
        yield manager
        manager.stop()
    
    def test_task_execution_error(self, manager, mock_research_graph):
        """Test handling of errors during task execution."""
        # Configure the mock to raise an exception
        mock_research_graph.ainvoke.side_effect = Exception("Simulated research error")
        
        # Submit a task
        task_id = manager.submit_task("error topic")
        
        # Wait for the task to fail
        task_info = manager.wait_for_task(task_id, timeout=5)
        
        # Check that the task failed with the expected error
        assert task_info["status"] == "failed"
        assert "Simulated research error" in task_info["error"]
    
    def test_task_timeout(self, manager, mock_research_graph):
        """Test handling of task timeouts."""
        # Configure the mock to sleep longer than the timeout
        async def sleep_long(state):
            await asyncio.sleep(10)  # Longer than the manager's timeout
            return state
        
        mock_research_graph.ainvoke.side_effect = sleep_long
        
        # Submit a task
        task_id = manager.submit_task("timeout topic")
        
        # Wait for the task to fail
        task_info = manager.wait_for_task(task_id, timeout=10)
        
        # Check that the task failed with a timeout error
        assert task_info["status"] == "failed"
        assert "timeout" in task_info["error"].lower() or "timed out" in task_info["error"].lower()
    
    def test_task_cancellation(self, manager):
        """Test cancellation of tasks."""
        # Submit a task
        task_id = manager.submit_task("cancel topic")
        
        # Cancel the task
        result = manager.cancel_task(task_id)
        
        # Check that the task was cancelled
        assert result is True
        
        # Get the task info
        task_info = manager.get_task(task_id)
        
        # Check that the task is marked as failed with a cancellation message
        assert task_info["status"] == "failed"
        assert "cancelled" in task_info["error"].lower()
    
    def test_task_retry_success(self, manager, mock_research_graph):
        """Test successful retry of a failed task."""
        # Configure the mock to fail once then succeed
        attempt = 0
        
        async def fail_then_succeed(state):
            nonlocal attempt
            if attempt == 0:
                attempt += 1
                raise Exception("Simulated error on first attempt")
            return state
        
        mock_research_graph.ainvoke.side_effect = fail_then_succeed
        
        # Submit a task
        task_id = manager.submit_task("retry topic")
        
        # Wait for the task to fail
        task_info = manager.wait_for_task(task_id, timeout=5)
        assert task_info["status"] == "failed"
        
        # Retry the task
        result = manager.retry_task(task_id)
        assert result is True
        
        # Wait for the retry to complete
        task_info = manager.wait_for_task(task_id, timeout=5)
        
        # Check that the retry succeeded
        assert task_info["status"] == "completed"
    
    def test_task_retry_failure(self, manager, mock_research_graph):
        """Test failed retry of a task."""
        # Configure the mock to always fail
        mock_research_graph.ainvoke.side_effect = Exception("Persistent error")
        
        # Submit a task
        task_id = manager.submit_task("persistent error topic")
        
        # Wait for the task to fail
        task_info = manager.wait_for_task(task_id, timeout=5)
        assert task_info["status"] == "failed"
        
        # Retry the task
        result = manager.retry_task(task_id)
        assert result is True
        
        # Wait for the retry to fail
        task_info = manager.wait_for_task(task_id, timeout=5)
        
        # Check that the retry also failed
        assert task_info["status"] == "failed"
        assert "Persistent error" in task_info["error"]
    
    def test_invalid_configuration(self, manager):
        """Test handling of invalid configuration."""
        # Create an invalid configuration
        invalid_config = Configuration(
            search_api="invalid_api",  # Invalid search API
            research_mode=ResearchMode.LINEAR
        )
        
        # Submit a task with invalid configuration
        task_id = manager.submit_task("invalid config topic", config=invalid_config)
        
        # Wait for the task to fail
        task_info = manager.wait_for_task(task_id, timeout=5)
        
        # Check that the task failed with a configuration error
        assert task_info["status"] == "failed"
        assert "configuration" in task_info["error"].lower() or "invalid" in task_info["error"].lower()
    
    def test_concurrent_error_handling(self, manager, mock_research_graph):
        """Test handling of errors in concurrent tasks."""
        # Configure the mock to fail for specific topics
        async def conditional_fail(state):
            if "fail" in state.topic.lower():
                raise Exception(f"Simulated error for {state.topic}")
            return state
        
        mock_research_graph.ainvoke.side_effect = conditional_fail
        
        # Submit a mix of tasks that will succeed and fail
        task_ids = manager.batch_submit([
            "success topic 1",
            "fail topic 1",
            "success topic 2",
            "fail topic 2",
            "success topic 3"
        ])
        
        # Wait for all tasks to complete or fail
        results = manager.wait_for_tasks(task_ids, timeout=10)
        
        # Check that the correct tasks succeeded and failed
        for task_id, result in results.items():
            if "fail" in result["topic"].lower():
                assert result["status"] == "failed"
                assert "Simulated error" in result["error"]
            else:
                assert result["status"] == "completed"
    
    def test_resource_exhaustion(self, manager):
        """Test handling of resource exhaustion."""
        # Set a very low max_concurrent_tasks
        manager.max_concurrent_tasks = 2
        
        # Submit more tasks than can be processed concurrently
        task_ids = manager.batch_submit([f"resource topic {i}" for i in range(10)])
        
        # Wait a short time for some tasks to start
        time.sleep(0.5)
        
        # Check that only max_concurrent_tasks are running
        stats = manager.get_stats()
        assert stats["running_tasks"] <= manager.max_concurrent_tasks
        
        # Wait for all tasks to complete
        results = manager.wait_for_tasks(task_ids, timeout=10)
        
        # Check that all tasks eventually completed
        for task_id, result in results.items():
            assert result["status"] == "completed"
    
    def test_manager_shutdown_with_pending_tasks(self):
        """Test manager shutdown with pending tasks."""
        # Create a fresh manager
        manager = ParallelResearchManager(
            max_concurrent_tasks=1,  # Only process one task at a time
            max_retries=1,
            timeout=5
        )
        manager.start()
        
        try:
            # Submit more tasks than can be immediately processed
            task_ids = manager.batch_submit([f"shutdown topic {i}" for i in range(5)])
            
            # Wait a short time for the first task to start
            time.sleep(0.5)
            
            # Stop the manager
            manager.stop()
            
            # Check that some tasks were left pending
            pending_tasks = manager.list_tasks(status="pending")
            assert len(pending_tasks) > 0
        finally:
            # Ensure the manager is stopped
            if manager.running:
                manager.stop()
    
    def test_invalid_task_id(self, manager):
        """Test handling of invalid task IDs."""
        # Try to get a non-existent task
        result = manager.get_task("non-existent-task-id")
        assert result is None
        
        # Try to cancel a non-existent task
        result = manager.cancel_task("non-existent-task-id")
        assert result is False
        
        # Try to retry a non-existent task
        result = manager.retry_task("non-existent-task-id")
        assert result is False
        
        # Try to update progress of a non-existent task
        result = manager.update_task_progress("non-existent-task-id", 0.5)
        assert result is False
        
        # Try to update metadata of a non-existent task
        result = manager.update_task_metadata("non-existent-task-id", {"key": "value"})
        assert result is False
    
    def test_wait_for_task_timeout(self, manager, mock_research_graph):
        """Test timeout when waiting for a task."""
        # Configure the mock to sleep longer than the wait timeout
        async def sleep_long(state):
            await asyncio.sleep(5)  # Longer than our wait timeout
            return state
        
        mock_research_graph.ainvoke.side_effect = sleep_long
        
        # Submit a task
        task_id = manager.submit_task("wait timeout topic")
        
        # Wait for the task with a short timeout
        result = manager.wait_for_task(task_id, timeout=0.1)
        
        # Check that the wait timed out
        assert result is None
    
    def test_wait_for_tasks_partial_timeout(self, manager, mock_research_graph):
        """Test partial timeout when waiting for multiple tasks."""
        # Configure the mock to sleep for different durations based on topic
        async def variable_sleep(state):
            if "fast" in state.topic.lower():
                await asyncio.sleep(0.1)
            else:
                await asyncio.sleep(5)  # Longer than our wait timeout
            return state
        
        mock_research_graph.ainvoke.side_effect = variable_sleep
        
        # Submit a mix of fast and slow tasks
        task_ids = manager.batch_submit([
            "fast topic 1",
            "slow topic 1",
            "fast topic 2",
            "slow topic 2"
        ])
        
        # Wait for tasks with a timeout that allows only fast tasks to complete
        results = manager.wait_for_tasks(task_ids, timeout=1)
        
        # Check that only the fast tasks completed
        completed_tasks = [task_id for task_id, result in results.items() 
                          if result["status"] == "completed"]
        assert len(completed_tasks) == 2  # Only the fast tasks
    
    def test_clear_completed_tasks(self, manager, mock_research_graph):
        """Test clearing of completed and failed tasks."""
        # Configure the mock to fail for specific topics
        async def conditional_fail(state):
            if "fail" in state.topic.lower():
                raise Exception(f"Simulated error for {state.topic}")
            await asyncio.sleep(0.1)
            return state
        
        mock_research_graph.ainvoke.side_effect = conditional_fail
        
        # Submit a mix of tasks that will succeed and fail
        task_ids = manager.batch_submit([
            "success topic 1",
            "fail topic 1",
            "success topic 2",
            "fail topic 2"
        ])
        
        # Wait for all tasks to complete or fail
        manager.wait_for_tasks(task_ids, timeout=5)
        
        # Check the number of tasks before clearing
        assert len(manager.tasks) == 4
        
        # Clear completed and failed tasks
        cleared = manager.clear_completed_tasks()
        
        # Check that all tasks were cleared
        assert cleared == 4
        assert len(manager.tasks) == 0

