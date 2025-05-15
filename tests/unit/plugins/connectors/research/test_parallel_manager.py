"""
Unit tests for the ParallelResearchManager class.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from core.plugins.connectors.research.parallel_manager import ParallelResearchManager
from core.plugins.connectors.research.configuration import Configuration
from core.plugins.connectors.research.state import ReportState
from core.task_management import TaskPriority, TaskStatus, TaskError


@pytest.fixture
def parallel_manager():
    """Create a parallel research manager for testing."""
    # Reset the singleton instance for each test
    ParallelResearchManager._instance = None
    ParallelResearchManager._initialized = False
    
    # Create a new parallel research manager
    manager = ParallelResearchManager(max_concurrent_research=2)
    
    # Mock the task manager
    manager.task_manager = MagicMock()
    manager.task_manager.register_task.return_value = "task_id_1"
    
    # Return the manager
    yield manager


def test_parallel_manager_initialization(parallel_manager):
    """Test ParallelResearchManager initialization."""
    assert parallel_manager.max_concurrent_research == 2
    assert isinstance(parallel_manager.active_research, dict)
    assert isinstance(parallel_manager.research_semaphore, asyncio.Semaphore)
    assert parallel_manager.research_semaphore._value == 2


@pytest.mark.asyncio
async def test_create_research_task(parallel_manager):
    """Test creating a research task."""
    # Create a research task
    task_id = await parallel_manager.create_research_task(
        topic="Test Research",
        use_multi_agent=True,
        priority=TaskPriority.HIGH,
        tags=["test", "research"],
        metadata={"meta": "data"}
    )
    
    # Check that the task was registered
    assert task_id == "task_id_1"
    parallel_manager.task_manager.register_task.assert_called_once()
    
    # Check that the research was added to active_research
    assert len(parallel_manager.active_research) == 1
    
    # Get the research ID
    research_id = list(parallel_manager.active_research.keys())[0]
    
    # Check research attributes
    research = parallel_manager.active_research[research_id]
    assert research["task_id"] == "task_id_1"
    assert research["topic"] == "Test Research"
    assert research["use_multi_agent"] is True
    assert research["status"] == "pending"
    assert isinstance(research["created_at"], datetime)


@pytest.mark.asyncio
async def test_execute_research(parallel_manager):
    """Test executing a research task."""
    # Mock the graph invoke method
    mock_graph = AsyncMock()
    mock_graph.ainvoke.return_value = {"result": "data"}
    
    # Create a research task
    task_id = await parallel_manager.create_research_task(
        topic="Test Research"
    )
    
    # Get the research ID
    research_id = list(parallel_manager.active_research.keys())[0]
    
    # Create initial state
    state = ReportState(
        topic="Test Research",
        config=Configuration(),
        sections=None,
        queries=None,
        search_results=None
    )
    
    # Execute the research with the mocked graph
    with patch("core.plugins.connectors.research.parallel_manager.research_graph", mock_graph):
        result = await parallel_manager._execute_research(
            research_id=research_id,
            state=state
        )
    
    # Check that the graph was invoked
    mock_graph.ainvoke.assert_called_once_with(state)
    
    # Check the result
    assert result == {"result": "data"}
    
    # Check research status
    assert parallel_manager.active_research[research_id]["status"] == "completed"
    assert parallel_manager.active_research[research_id]["result"] == {"result": "data"}


@pytest.mark.asyncio
async def test_execute_research_with_error(parallel_manager):
    """Test executing a research task that raises an error."""
    # Mock the graph invoke method to raise an exception
    mock_graph = AsyncMock()
    mock_graph.ainvoke.side_effect = ValueError("Test error")
    
    # Create a research task
    task_id = await parallel_manager.create_research_task(
        topic="Error Research"
    )
    
    # Get the research ID
    research_id = list(parallel_manager.active_research.keys())[0]
    
    # Create initial state
    state = ReportState(
        topic="Error Research",
        config=Configuration(),
        sections=None,
        queries=None,
        search_results=None
    )
    
    # Execute the research with the mocked graph
    with patch("core.plugins.connectors.research.parallel_manager.research_graph", mock_graph):
        with pytest.raises(TaskError):
            await parallel_manager._execute_research(
                research_id=research_id,
                state=state
            )
    
    # Check research status
    assert parallel_manager.active_research[research_id]["status"] == "failed"
    assert "error" in parallel_manager.active_research[research_id]
    assert "Test error" in parallel_manager.active_research[research_id]["error"]


@pytest.mark.asyncio
async def test_cancel_research(parallel_manager):
    """Test cancelling a research task."""
    # Mock the task manager's cancel_task method
    parallel_manager.task_manager.cancel_task.return_value = True
    
    # Create a research task
    task_id = await parallel_manager.create_research_task(
        topic="Cancel Research"
    )
    
    # Get the research ID
    research_id = list(parallel_manager.active_research.keys())[0]
    
    # Cancel the research
    cancelled = await parallel_manager.cancel_research(research_id)
    
    # Check that the task was cancelled
    assert cancelled
    parallel_manager.task_manager.cancel_task.assert_called_once_with("task_id_1")
    
    # Check research status
    assert parallel_manager.active_research[research_id]["status"] == "cancelled"


def test_get_research_status(parallel_manager):
    """Test getting research status."""
    # Create a mock task
    mock_task = MagicMock()
    mock_task.status = TaskStatus.RUNNING
    
    # Mock the task manager's get_task method
    parallel_manager.task_manager.get_task.return_value = mock_task
    parallel_manager.task_manager.get_task_progress.return_value = (0.5, "Halfway done")
    
    # Add a research task to active_research
    research_id = "research_123"
    parallel_manager.active_research[research_id] = {
        "task_id": "task_id_1",
        "topic": "Status Research",
        "state": MagicMock(),
        "use_multi_agent": False,
        "created_at": datetime.now(),
        "status": "running"
    }
    
    # Get the research status
    status = parallel_manager.get_research_status(research_id)
    
    # Check the status
    assert status["research_id"] == research_id
    assert status["task_id"] == "task_id_1"
    assert status["topic"] == "Status Research"
    assert status["status"] == "running"
    assert status["use_multi_agent"] is False
    assert "created_at" in status
    assert status["progress"] == 0.5
    assert status["progress_message"] == "Halfway done"
    
    # Try to get status for a non-existent research
    non_existent_status = parallel_manager.get_research_status("non_existent_research")
    assert non_existent_status is None


def test_get_all_research(parallel_manager):
    """Test getting all research tasks."""
    # Mock get_research_status
    parallel_manager.get_research_status = MagicMock()
    parallel_manager.get_research_status.side_effect = lambda rid: {"research_id": rid, "status": "running"}
    
    # Add research tasks to active_research
    parallel_manager.active_research = {
        "research_1": {"task_id": "task_1"},
        "research_2": {"task_id": "task_2"},
        "research_3": {"task_id": "task_3"}
    }
    
    # Get all research
    all_research = parallel_manager.get_all_research()
    
    # Check the result
    assert len(all_research) == 3
    assert {"research_id": "research_1", "status": "running"} in all_research
    assert {"research_id": "research_2", "status": "running"} in all_research
    assert {"research_id": "research_3", "status": "running"} in all_research


def test_get_active_research(parallel_manager):
    """Test getting active research tasks."""
    # Mock get_research_status
    parallel_manager.get_research_status = MagicMock()
    parallel_manager.get_research_status.side_effect = lambda rid: {"research_id": rid, "status": parallel_manager.active_research[rid]["status"]}
    
    # Add research tasks to active_research with different statuses
    parallel_manager.active_research = {
        "research_1": {"task_id": "task_1", "status": "pending"},
        "research_2": {"task_id": "task_2", "status": "running"},
        "research_3": {"task_id": "task_3", "status": "completed"},
        "research_4": {"task_id": "task_4", "status": "failed"}
    }
    
    # Get active research
    active_research = parallel_manager.get_active_research()
    
    # Check the result
    assert len(active_research) == 2
    assert {"research_id": "research_1", "status": "pending"} in active_research
    assert {"research_id": "research_2", "status": "running"} in active_research


def test_get_research_result(parallel_manager):
    """Test getting research result."""
    # Add a completed research task to active_research
    research_id = "research_123"
    parallel_manager.active_research[research_id] = {
        "task_id": "task_id_1",
        "topic": "Result Research",
        "status": "completed",
        "result": {"data": "value"}
    }
    
    # Get the research result
    result = parallel_manager.get_research_result(research_id)
    
    # Check the result
    assert result == {"data": "value"}
    
    # Try to get result for a non-existent research
    non_existent_result = parallel_manager.get_research_result("non_existent_research")
    assert non_existent_result is None
    
    # Try to get result for a non-completed research
    parallel_manager.active_research["running_research"] = {
        "task_id": "task_id_2",
        "topic": "Running Research",
        "status": "running"
    }
    running_result = parallel_manager.get_research_result("running_research")
    assert running_result is None


def test_get_metrics(parallel_manager):
    """Test getting parallel research manager metrics."""
    # Add research tasks to active_research with different statuses
    parallel_manager.active_research = {
        "research_1": {"task_id": "task_1", "status": "pending"},
        "research_2": {"task_id": "task_2", "status": "running"},
        "research_3": {"task_id": "task_3", "status": "completed"},
        "research_4": {"task_id": "task_4", "status": "failed"},
        "research_5": {"task_id": "task_5", "status": "cancelled"}
    }
    
    # Get metrics
    metrics = parallel_manager.get_metrics()
    
    # Check metrics
    assert metrics["max_concurrent_research"] == 2
    assert metrics["active_slots"] == 2
    assert metrics["total_research"] == 5
    assert metrics["pending_research"] == 1
    assert metrics["running_research"] == 1
    assert metrics["completed_research"] == 1
    assert metrics["failed_research"] == 1
    assert metrics["cancelled_research"] == 1

