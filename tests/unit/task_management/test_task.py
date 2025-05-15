"""
Unit tests for the Task class in the task management system.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from core.task_management.task import Task, TaskStatus, TaskPriority, create_task_id


def test_create_task_id():
    """Test creating a task ID."""
    task_id = create_task_id()
    assert isinstance(task_id, str)
    assert len(task_id) > 0


def test_task_initialization():
    """Test Task initialization."""
    # Create a mock function
    mock_func = MagicMock()
    
    # Create a task
    task = Task(
        task_id="test_task_1",
        name="Test Task",
        func=mock_func,
        args=(1, 2),
        kwargs={"key": "value"},
        priority=TaskPriority.HIGH,
        dependencies=["dep1", "dep2"],
        max_retries=3,
        retry_delay=1.5,
        timeout=10.0,
        description="Test task description",
        tags=["test", "unit"],
        metadata={"meta": "data"}
    )
    
    # Check task attributes
    assert task.task_id == "test_task_1"
    assert task.name == "Test Task"
    assert task.func == mock_func
    assert task.args == (1, 2)
    assert task.kwargs == {"key": "value"}
    assert task.priority == TaskPriority.HIGH
    assert task.dependencies == ["dep1", "dep2"]
    assert task.max_retries == 3
    assert task.retry_delay == 1.5
    assert task.timeout == 10.0
    assert task.description == "Test task description"
    assert task.tags == ["test", "unit"]
    assert task.metadata == {"meta": "data"}
    
    # Check default values
    assert task.status == TaskStatus.PENDING
    assert task.result is None
    assert task.error is None
    assert task.created_at is not None
    assert task.started_at is None
    assert task.completed_at is None
    assert task.retry_count == 0
    assert task.progress == 0.0
    assert task.progress_message == ""


def test_task_update_progress():
    """Test updating task progress."""
    task = Task(
        task_id="test_task_2",
        name="Progress Test",
        func=MagicMock()
    )
    
    # Update progress
    task.update_progress(0.5, "Halfway done")
    
    # Check progress values
    assert task.progress == 0.5
    assert task.progress_message == "Halfway done"
    
    # Test invalid progress values
    with pytest.raises(ValueError):
        task.update_progress(-0.1, "Invalid")
    
    with pytest.raises(ValueError):
        task.update_progress(1.1, "Invalid")


def test_task_execution_lifecycle():
    """Test task execution lifecycle."""
    # Create a mock function that returns a value
    mock_func = MagicMock(return_value="result")
    
    # Create a task
    task = Task(
        task_id="test_task_3",
        name="Lifecycle Test",
        func=mock_func
    )
    
    # Initial state
    assert task.status == TaskStatus.PENDING
    assert task.started_at is None
    assert task.completed_at is None
    
    # Start the task
    task.status = TaskStatus.RUNNING
    task.started_at = datetime.now()
    
    assert task.status == TaskStatus.RUNNING
    assert task.started_at is not None
    
    # Complete the task
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.now()
    task.result = "result"
    
    assert task.status == TaskStatus.COMPLETED
    assert task.completed_at is not None
    assert task.result == "result"


def test_task_failure():
    """Test task failure."""
    # Create a mock function that raises an exception
    mock_func = MagicMock(side_effect=ValueError("Test error"))
    
    # Create a task
    task = Task(
        task_id="test_task_4",
        name="Failure Test",
        func=mock_func
    )
    
    # Set task as failed
    task.status = TaskStatus.FAILED
    task.completed_at = datetime.now()
    task.error = ValueError("Test error")
    
    assert task.status == TaskStatus.FAILED
    assert task.completed_at is not None
    assert isinstance(task.error, ValueError)
    assert str(task.error) == "Test error"


def test_task_cancellation():
    """Test task cancellation."""
    # Create a task
    task = Task(
        task_id="test_task_5",
        name="Cancellation Test",
        func=MagicMock()
    )
    
    # Set task as cancelled
    task.status = TaskStatus.CANCELLED
    task.completed_at = datetime.now()
    
    assert task.status == TaskStatus.CANCELLED
    assert task.completed_at is not None


def test_task_with_dependencies():
    """Test task with dependencies."""
    # Create a task with dependencies
    task = Task(
        task_id="test_task_6",
        name="Dependency Test",
        func=MagicMock(),
        dependencies=["dep1", "dep2", "dep3"]
    )
    
    assert task.dependencies == ["dep1", "dep2", "dep3"]
    
    # Set task as waiting
    task.status = TaskStatus.WAITING
    
    assert task.status == TaskStatus.WAITING


def test_task_priority_ordering():
    """Test task priority ordering."""
    # Create tasks with different priorities
    task_low = Task(
        task_id="test_task_low",
        name="Low Priority",
        func=MagicMock(),
        priority=TaskPriority.LOW
    )
    
    task_normal = Task(
        task_id="test_task_normal",
        name="Normal Priority",
        func=MagicMock(),
        priority=TaskPriority.NORMAL
    )
    
    task_high = Task(
        task_id="test_task_high",
        name="High Priority",
        func=MagicMock(),
        priority=TaskPriority.HIGH
    )
    
    task_critical = Task(
        task_id="test_task_critical",
        name="Critical Priority",
        func=MagicMock(),
        priority=TaskPriority.CRITICAL
    )
    
    # Check priority values
    assert task_low.priority.value < task_normal.priority.value
    assert task_normal.priority.value < task_high.priority.value
    assert task_high.priority.value < task_critical.priority.value

