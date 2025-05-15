"""
Common fixtures for WiseFlow tests.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from core.plugins.connectors.research.parallel_manager import ParallelResearchManager
from core.task_management.task_manager import TaskManager


@pytest.fixture
def reset_singletons():
    """Reset singleton instances for testing."""
    # Reset ParallelResearchManager singleton
    ParallelResearchManager._instance = None
    ParallelResearchManager._initialized = False
    
    # Reset TaskManager singleton
    TaskManager._instance = None
    TaskManager._initialized = False
    
    yield
    
    # Reset again after the test
    ParallelResearchManager._instance = None
    ParallelResearchManager._initialized = False
    TaskManager._instance = None
    TaskManager._initialized = False


@pytest.fixture
def mock_task_manager():
    """Create a mock task manager."""
    mock_manager = MagicMock()
    mock_manager.register_task.return_value = "task_id_1"
    mock_manager.execute_task = AsyncMock(return_value={"result": "success"})
    mock_manager.get_task_progress.return_value = (0.5, "Halfway done")
    return mock_manager


@pytest.fixture
def mock_parallel_manager():
    """Create a mock parallel research manager."""
    mock_manager = MagicMock()
    mock_manager.create_research_task = AsyncMock(return_value="task_id_1")
    mock_manager.get_research_status.return_value = {
        "research_id": "research_123",
        "task_id": "task_id_1",
        "topic": "Test Research",
        "status": "pending",
        "use_multi_agent": False,
        "created_at": "2023-01-01T00:00:00",
        "progress": 0.0,
        "progress_message": ""
    }
    mock_manager.get_all_research.return_value = [
        {
            "research_id": "research_123",
            "task_id": "task_id_1",
            "topic": "Test Research",
            "status": "pending",
            "use_multi_agent": False,
            "created_at": "2023-01-01T00:00:00",
            "progress": 0.0,
            "progress_message": ""
        }
    ]
    mock_manager.get_active_research.return_value = [
        {
            "research_id": "research_123",
            "task_id": "task_id_1",
            "topic": "Test Research",
            "status": "pending",
            "use_multi_agent": False,
            "created_at": "2023-01-01T00:00:00",
            "progress": 0.0,
            "progress_message": ""
        }
    ]
    mock_manager.get_metrics.return_value = {
        "max_concurrent_research": 3,
        "active_slots": 3,
        "total_research": 1,
        "pending_research": 1,
        "running_research": 0,
        "completed_research": 0,
        "failed_research": 0,
        "cancelled_research": 0
    }
    mock_manager.get_research_result.return_value = {
        "sections": MagicMock(sections=[{"title": "Section 1", "content": "Content 1"}]),
        "metadata": {"key": "value"}
    }
    mock_manager.cancel_research = AsyncMock(return_value=True)
    mock_manager.task_manager = MagicMock()
    return mock_manager


@pytest.fixture
def mock_event_system():
    """Mock the event system."""
    with patch("core.event_system.publish_sync") as mock_publish:
        yield mock_publish


@pytest.fixture
def event_loop():
    """Create an event loop for testing."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

