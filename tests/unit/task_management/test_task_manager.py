"""
Unit tests for the TaskManager class in the task management system.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from core.task_management.task_manager import TaskManager
from core.task_management.task import TaskStatus, TaskPriority
from core.task_management.exceptions import TaskNotFoundError, TaskDependencyError


@pytest.fixture
def task_manager():
    """Create a task manager for testing."""
    # Reset the singleton instance for each test
    TaskManager._instance = None
    TaskManager._initialized = False
    
    # Create a new task manager
    manager = TaskManager(max_concurrent_tasks=2)
    
    # Return the manager
    yield manager


def test_task_manager_initialization(task_manager):
    """Test TaskManager initialization."""
    assert task_manager.max_concurrent_tasks == 2
    assert task_manager.default_executor_type == "async"
    assert "sequential" in task_manager.executors
    assert "thread_pool" in task_manager.executors
    assert "async" in task_manager.executors
    assert isinstance(task_manager.tasks, dict)
    assert len(task_manager.running_tasks) == 0
    assert len(task_manager.completed_tasks) == 0
    assert len(task_manager.failed_tasks) == 0
    assert len(task_manager.cancelled_tasks) == 0
    assert len(task_manager.waiting_tasks) == 0


def test_register_task(task_manager):
    """Test registering a task."""
    # Create a mock function
    mock_func = MagicMock(return_value="result")
    
    # Register a task
    task_id = task_manager.register_task(
        name="Test Task",
        func=mock_func,
        1, 2, 3,
        kwargs={"key": "value"},
        priority=TaskPriority.HIGH,
        description="Test task description",
        tags=["test", "unit"],
        metadata={"meta": "data"}
    )
    
    # Check that the task was registered
    assert task_id in task_manager.tasks
    task = task_manager.tasks[task_id]
    
    # Check task attributes
    assert task.name == "Test Task"
    assert task.func == mock_func
    assert task.args == (1, 2, 3)
    assert task.kwargs == {"key": "value"}
    assert task.priority == TaskPriority.HIGH
    assert task.description == "Test task description"
    assert task.tags == ["test", "unit"]
    assert task.metadata == {"meta": "data"}
    assert task.status == TaskStatus.PENDING


def test_register_task_with_dependencies(task_manager):
    """Test registering a task with dependencies."""
    # Create mock functions
    mock_func1 = MagicMock(return_value="result1")
    mock_func2 = MagicMock(return_value="result2")
    
    # Register first task
    task_id1 = task_manager.register_task(
        name="Task 1",
        func=mock_func1
    )
    
    # Register second task with dependency on first task
    task_id2 = task_manager.register_task(
        name="Task 2",
        func=mock_func2,
        dependencies=[task_id1]
    )
    
    # Check that the second task is waiting
    assert task_id2 in task_manager.waiting_tasks
    assert task_manager.tasks[task_id2].status == TaskStatus.WAITING


def test_register_task_with_invalid_dependency(task_manager):
    """Test registering a task with an invalid dependency."""
    # Create a mock function
    mock_func = MagicMock(return_value="result")
    
    # Try to register a task with an invalid dependency
    with pytest.raises(TaskDependencyError):
        task_manager.register_task(
            name="Invalid Dependency Task",
            func=mock_func,
            dependencies=["non_existent_task"]
        )


def test_get_task(task_manager):
    """Test getting a task."""
    # Create a mock function
    mock_func = MagicMock(return_value="result")
    
    # Register a task
    task_id = task_manager.register_task(
        name="Get Task Test",
        func=mock_func
    )
    
    # Get the task
    task = task_manager.get_task(task_id)
    
    # Check that the task was retrieved
    assert task is not None
    assert task.task_id == task_id
    assert task.name == "Get Task Test"
    
    # Try to get a non-existent task
    non_existent_task = task_manager.get_task("non_existent_task")
    assert non_existent_task is None


def test_get_task_status(task_manager):
    """Test getting task status."""
    # Create a mock function
    mock_func = MagicMock(return_value="result")
    
    # Register a task
    task_id = task_manager.register_task(
        name="Status Test",
        func=mock_func
    )
    
    # Get the task status
    status = task_manager.get_task_status(task_id)
    
    # Check that the status was retrieved
    assert status == TaskStatus.PENDING
    
    # Try to get status of a non-existent task
    non_existent_status = task_manager.get_task_status("non_existent_task")
    assert non_existent_status is None


@pytest.mark.asyncio
async def test_execute_task(task_manager):
    """Test executing a task."""
    # Create a mock function
    mock_func = AsyncMock(return_value="result")
    
    # Register a task
    task_id = task_manager.register_task(
        name="Execute Task Test",
        func=mock_func,
        1, 2,
        kwargs={"key": "value"}
    )
    
    # Execute the task
    result = await task_manager.execute_task(task_id)
    
    # Check that the task was executed
    assert result == "result"
    mock_func.assert_called_once_with(1, 2, key="value")
    
    # Check task status
    assert task_manager.tasks[task_id].status == TaskStatus.COMPLETED
    assert task_id in task_manager.completed_tasks
    assert task_manager.tasks[task_id].result == "result"


@pytest.mark.asyncio
async def test_execute_task_with_error(task_manager):
    """Test executing a task that raises an error."""
    # Create a mock function that raises an exception
    mock_func = AsyncMock(side_effect=ValueError("Test error"))
    
    # Register a task
    task_id = task_manager.register_task(
        name="Error Task Test",
        func=mock_func
    )
    
    # Execute the task
    with pytest.raises(ValueError, match="Test error"):
        await task_manager.execute_task(task_id)
    
    # Check task status
    assert task_manager.tasks[task_id].status == TaskStatus.FAILED
    assert task_id in task_manager.failed_tasks
    assert isinstance(task_manager.tasks[task_id].error, ValueError)


@pytest.mark.asyncio
async def test_cancel_task(task_manager):
    """Test cancelling a task."""
    # Create a mock function that takes time to complete
    async def slow_func():
        await asyncio.sleep(1)
        return "result"
    
    # Register a task
    task_id = task_manager.register_task(
        name="Cancel Task Test",
        func=slow_func
    )
    
    # Start the task
    task_future = asyncio.create_task(task_manager.execute_task(task_id))
    
    # Give the task a moment to start
    await asyncio.sleep(0.1)
    
    # Cancel the task
    cancelled = await task_manager.cancel_task(task_id)
    
    # Check that the task was cancelled
    assert cancelled
    assert task_manager.tasks[task_id].status == TaskStatus.CANCELLED
    assert task_id in task_manager.cancelled_tasks
    
    # Clean up
    try:
        await task_future
    except:
        pass


@pytest.mark.asyncio
async def test_update_task_progress(task_manager):
    """Test updating task progress."""
    # Create a mock function
    mock_func = AsyncMock(return_value="result")
    
    # Register a task
    task_id = task_manager.register_task(
        name="Progress Test",
        func=mock_func
    )
    
    # Update progress
    task_manager.update_task_progress(task_id, 0.5, "Halfway done")
    
    # Check progress values
    assert task_manager.tasks[task_id].progress == 0.5
    assert task_manager.tasks[task_id].progress_message == "Halfway done"
    
    # Try to update progress for a non-existent task
    result = task_manager.update_task_progress("non_existent_task", 0.5)
    assert not result


@pytest.mark.asyncio
async def test_get_metrics(task_manager):
    """Test getting task manager metrics."""
    # Create mock functions
    mock_func1 = AsyncMock(return_value="result1")
    mock_func2 = AsyncMock(return_value="result2")
    
    # Register tasks
    task_id1 = task_manager.register_task(
        name="Metrics Test 1",
        func=mock_func1
    )
    
    task_id2 = task_manager.register_task(
        name="Metrics Test 2",
        func=mock_func2
    )
    
    # Execute one task
    await task_manager.execute_task(task_id1)
    
    # Get metrics
    metrics = task_manager.get_metrics()
    
    # Check metrics
    assert metrics["total_tasks"] == 2
    assert metrics["pending_tasks"] == 1
    assert metrics["running_tasks"] == 0
    assert metrics["completed_tasks"] == 1
    assert metrics["failed_tasks"] == 0
    assert metrics["cancelled_tasks"] == 0
    assert metrics["waiting_tasks"] == 0
    assert "executors" in metrics

