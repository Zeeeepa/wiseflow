"""
Unit tests for the ParallelResearchManager.
"""

import pytest
import time
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import threading
import queue

from core.plugins.connectors.research.parallel_manager import (
    ParallelResearchManager,
    ResearchTask,
    get_parallel_research_manager
)
from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI
from core.plugins.connectors.research.state import ReportState, Sections

@pytest.mark.unit
class TestParallelResearchManager:
    """Tests for the ParallelResearchManager."""
    
    @pytest.fixture
    def mock_research_graph(self):
        """Create a mock research graph."""
        mock = AsyncMock()
        mock.ainvoke.return_value = ReportState(
            topic="test topic",
            sections=Sections(sections=[]),
            queries=[],
            search_results=[],
            feedback=None,
            config=None
        )
        return mock
    
    @pytest.fixture
    def mock_get_research_graph(self, mock_research_graph):
        """Mock the get_research_graph function."""
        with patch("core.plugins.connectors.research.parallel_manager.get_research_graph") as mock:
            mock.return_value = mock_research_graph
            yield mock
    
    @pytest.fixture
    def manager(self):
        """Create a ParallelResearchManager instance for testing."""
        manager = ParallelResearchManager(
            max_concurrent_tasks=2,
            max_retries=1,
            timeout=10
        )
        yield manager
        manager.stop()
    
    def test_init(self):
        """Test initialization of ParallelResearchManager."""
        manager = ParallelResearchManager(
            max_concurrent_tasks=3,
            max_retries=2,
            timeout=30,
            resource_limits={"api_calls_per_minute": 60}
        )
        
        assert manager.max_concurrent_tasks == 3
        assert manager.max_retries == 2
        assert manager.timeout == 30
        assert manager.resource_limits == {"api_calls_per_minute": 60}
        assert isinstance(manager.tasks, dict)
        assert isinstance(manager.task_queue, queue.Queue)
        assert manager.active_tasks == 0
        assert isinstance(manager.lock, threading.RLock)
        assert isinstance(manager.api_usage, dict)
        assert isinstance(manager.api_last_reset, dict)
        assert manager.worker_thread is None
        assert manager.running is False
        
        manager.stop()
    
    def test_start_stop(self):
        """Test starting and stopping the manager."""
        manager = ParallelResearchManager()
        
        # Test start
        manager.start()
        assert manager.running is True
        assert manager.worker_thread is not None
        assert manager.worker_thread.is_alive()
        
        # Test stop
        manager.stop()
        assert manager.running is False
        time.sleep(0.1)  # Give the thread time to stop
        assert not manager.worker_thread.is_alive()
    
    def test_submit_task(self, manager):
        """Test submitting a task."""
        # Start the manager
        manager.start()
        
        # Submit a task
        task_id = manager.submit_task("test topic")
        
        # Check that the task was added
        assert task_id in manager.tasks
        assert manager.tasks[task_id].topic == "test topic"
        assert manager.tasks[task_id].status == "pending"
        
        # Check that the task was added to the queue
        assert manager.task_queue.qsize() > 0
    
    def test_get_task(self, manager):
        """Test getting task information."""
        # Start the manager
        manager.start()
        
        # Submit a task
        task_id = manager.submit_task("test topic")
        
        # Get the task
        task_info = manager.get_task(task_id)
        
        # Check the task info
        assert task_info is not None
        assert task_info["task_id"] == task_id
        assert task_info["topic"] == "test topic"
        assert task_info["status"] == "pending"
        
        # Test getting a non-existent task
        assert manager.get_task("non-existent") is None
    
    def test_cancel_task(self, manager):
        """Test cancelling a task."""
        # Start the manager
        manager.start()
        
        # Submit a task
        task_id = manager.submit_task("test topic")
        
        # Cancel the task
        result = manager.cancel_task(task_id)
        
        # Check the result
        assert result is True
        
        # Check that the task was cancelled
        task_info = manager.get_task(task_id)
        assert task_info["status"] == "failed"
        assert "cancelled" in task_info["error"].lower()
        
        # Test cancelling a non-existent task
        assert manager.cancel_task("non-existent") is False
    
    def test_list_tasks(self, manager):
        """Test listing tasks."""
        # Start the manager
        manager.start()
        
        # Submit tasks
        task_id1 = manager.submit_task("topic 1")
        task_id2 = manager.submit_task("topic 2")
        
        # Cancel one task
        manager.cancel_task(task_id1)
        
        # List all tasks
        all_tasks = manager.list_tasks()
        assert len(all_tasks) == 2
        
        # List pending tasks
        pending_tasks = manager.list_tasks(status="pending")
        assert len(pending_tasks) == 1
        assert pending_tasks[0]["task_id"] == task_id2
        
        # List failed tasks
        failed_tasks = manager.list_tasks(status="failed")
        assert len(failed_tasks) == 1
        assert failed_tasks[0]["task_id"] == task_id1
    
    def test_get_stats(self, manager):
        """Test getting statistics."""
        # Start the manager
        manager.start()
        
        # Submit tasks
        task_id1 = manager.submit_task("topic 1")
        task_id2 = manager.submit_task("topic 2")
        
        # Cancel one task
        manager.cancel_task(task_id1)
        
        # Get stats
        stats = manager.get_stats()
        
        # Check stats
        assert stats["total_tasks"] == 2
        assert stats["pending_tasks"] == 1
        assert stats["failed_tasks"] == 1
        assert stats["queue_size"] >= 0
    
    def test_clear_completed_tasks(self, manager):
        """Test clearing completed tasks."""
        # Start the manager
        manager.start()
        
        # Submit tasks
        task_id1 = manager.submit_task("topic 1")
        task_id2 = manager.submit_task("topic 2")
        
        # Cancel one task
        manager.cancel_task(task_id1)
        
        # Clear completed tasks
        cleared = manager.clear_completed_tasks()
        
        # Check that the failed task was cleared
        assert cleared == 1
        assert task_id1 not in manager.tasks
        assert task_id2 in manager.tasks
    
    def test_batch_submit(self, manager):
        """Test batch submission of tasks."""
        # Start the manager
        manager.start()
        
        # Submit batch of tasks
        topics = ["topic 1", "topic 2", "topic 3"]
        task_ids = manager.batch_submit(topics)
        
        # Check that all tasks were submitted
        assert len(task_ids) == 3
        for task_id in task_ids:
            assert task_id in manager.tasks
        
        # Check that the tasks are in the queue
        assert manager.task_queue.qsize() >= 3
    
    def test_update_task_progress(self, manager):
        """Test updating task progress."""
        # Start the manager
        manager.start()
        
        # Submit a task
        task_id = manager.submit_task("test topic")
        
        # Manually set the task to running
        with manager.lock:
            manager.tasks[task_id].status = "running"
        
        # Update progress
        result = manager.update_task_progress(task_id, 0.5)
        
        # Check the result
        assert result is True
        
        # Check that the progress was updated
        task_info = manager.get_task(task_id)
        assert task_info["progress"] == 0.5
        
        # Test updating a non-existent task
        assert manager.update_task_progress("non-existent", 0.5) is False
        
        # Test updating a non-running task
        with manager.lock:
            manager.tasks[task_id].status = "completed"
        assert manager.update_task_progress(task_id, 0.7) is False
    
    def test_update_task_metadata(self, manager):
        """Test updating task metadata."""
        # Start the manager
        manager.start()
        
        # Submit a task
        task_id = manager.submit_task("test topic")
        
        # Update metadata
        result = manager.update_task_metadata(task_id, {"key": "value"})
        
        # Check the result
        assert result is True
        
        # Check that the metadata was updated
        task_info = manager.get_task(task_id)
        assert task_info["metadata"]["key"] == "value"
        
        # Test updating a non-existent task
        assert manager.update_task_metadata("non-existent", {"key": "value"}) is False
    
    def test_retry_task(self, manager):
        """Test retrying a failed task."""
        # Start the manager
        manager.start()
        
        # Submit a task
        task_id = manager.submit_task("test topic")
        
        # Manually set the task to failed
        with manager.lock:
            manager.tasks[task_id].status = "failed"
            manager.tasks[task_id].error = "Test error"
        
        # Retry the task
        result = manager.retry_task(task_id)
        
        # Check the result
        assert result is True
        
        # Check that the task was reset
        task_info = manager.get_task(task_id)
        assert task_info["status"] == "pending"
        assert task_info["error"] is None
        
        # Test retrying a non-existent task
        assert manager.retry_task("non-existent") is False
        
        # Test retrying a non-failed task
        with manager.lock:
            manager.tasks[task_id].status = "running"
        assert manager.retry_task(task_id) is False
    
    def test_context_manager(self):
        """Test using the manager as a context manager."""
        with ParallelResearchManager() as manager:
            assert manager.running is True
            
            # Submit a task
            task_id = manager.submit_task("test topic")
            assert task_id in manager.tasks
        
        # Check that the manager was stopped
        assert manager.running is False
    
    def test_get_parallel_research_manager():
        """Test getting the singleton instance."""
        # Get the instance
        manager1 = get_parallel_research_manager()
        manager2 = get_parallel_research_manager()
        
        # Check that the same instance is returned
        assert manager1 is manager2
        
        # Check that the manager is running
        assert manager1.running is True
        
        # Clean up
        manager1.stop()
    
    @patch("core.plugins.connectors.research.parallel_manager.asyncio.run_coroutine_threadsafe")
    def test_execute_task(self, mock_run_coroutine, manager, mock_get_research_graph):
        """Test executing a task."""
        # Mock the run_coroutine_threadsafe function
        future = MagicMock()
        future.result.return_value = ReportState(
            topic="test topic",
            sections=Sections(sections=[]),
            queries=[],
            search_results=[],
            feedback=None,
            config=None
        )
        mock_run_coroutine.return_value = future
        
        # Start the manager
        manager.start()
        
        # Submit a task
        task_id = manager.submit_task("test topic")
        
        # Manually execute the task
        manager._execute_task(task_id)
        
        # Check that the task was executed
        task_info = manager.get_task(task_id)
        assert task_info["status"] == "completed"
        assert task_info["error"] is None
        assert task_info["end_time"] is not None
        assert task_info["progress"] == 1.0
        
        # Check that the active tasks count was decremented
        assert manager.active_tasks == 0
    
    @patch("core.plugins.connectors.research.parallel_manager.asyncio.run_coroutine_threadsafe")
    def test_execute_task_error(self, mock_run_coroutine, manager, mock_get_research_graph):
        """Test executing a task with an error."""
        # Mock the run_coroutine_threadsafe function to raise an exception
        future = MagicMock()
        future.result.side_effect = Exception("Test error")
        mock_run_coroutine.return_value = future
        
        # Start the manager
        manager.start()
        
        # Submit a task
        task_id = manager.submit_task("test topic")
        
        # Manually execute the task
        manager._execute_task(task_id)
        
        # Check that the task failed
        task_info = manager.get_task(task_id)
        assert task_info["status"] == "failed"
        assert "Test error" in task_info["error"]
        assert task_info["end_time"] is not None
        
        # Check that the active tasks count was decremented
        assert manager.active_tasks == 0
    
    def test_research_task_properties():
        """Test ResearchTask properties."""
        # Create a task
        task = ResearchTask(
            task_id="test-id",
            topic="test topic",
            status="running",
            start_time=time.time()
        )
        
        # Test duration property
        assert task.duration is not None
        assert task.duration >= 0
        
        # Test to_dict method
        task_dict = task.to_dict()
        assert task_dict["task_id"] == "test-id"
        assert task_dict["topic"] == "test topic"
        assert task_dict["status"] == "running"
        assert task_dict["duration"] is not None

