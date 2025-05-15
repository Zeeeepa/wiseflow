"""
Integration tests for the research API.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from dashboard.research_api import router as research_router
from core.plugins.connectors.research.parallel_manager import ParallelResearchManager
from core.plugins.connectors.research.configuration import Configuration
from core.task_management import TaskPriority


@pytest.fixture
def app():
    """Create a FastAPI app for testing."""
    app = FastAPI()
    app.include_router(research_router)
    return app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_parallel_manager():
    """Mock the parallel research manager."""
    # Create a mock parallel research manager
    mock_manager = MagicMock()
    
    # Mock create_research_task
    mock_manager.create_research_task = AsyncMock(return_value="task_id_1")
    
    # Mock get_research_status
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
    
    # Mock get_all_research
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
    
    # Mock get_active_research
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
    
    # Mock get_metrics
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
    
    # Mock get_research_result
    mock_manager.get_research_result.return_value = {
        "sections": MagicMock(sections=[{"title": "Section 1", "content": "Content 1"}]),
        "metadata": {"key": "value"}
    }
    
    # Mock cancel_research
    mock_manager.cancel_research = AsyncMock(return_value=True)
    
    # Mock active_research
    mock_manager.active_research = {
        "research_123": {
            "task_id": "task_id_1",
            "topic": "Test Research"
        }
    }
    
    # Mock task_manager
    mock_manager.task_manager = MagicMock()
    
    return mock_manager


def test_create_research(client, mock_parallel_manager):
    """Test creating a research task."""
    # Patch the parallel research manager
    with patch("dashboard.research_api.parallel_research_manager", mock_parallel_manager):
        # Send a request to create a research task
        response = client.post(
            "/research/",
            json={
                "topic": "Test Research",
                "use_multi_agent": False,
                "priority": "NORMAL",
                "tags": ["test", "integration"],
                "metadata": {"key": "value"},
                "config": {"search_api": "GOOGLE"}
            }
        )
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["task_id"] == "task_id_1"
    assert response.json()["topic"] == "Test Research"
    assert response.json()["status"] == "pending"
    
    # Check that create_research_task was called with the correct arguments
    mock_parallel_manager.create_research_task.assert_called_once()
    call_args = mock_parallel_manager.create_research_task.call_args[1]
    assert call_args["topic"] == "Test Research"
    assert call_args["use_multi_agent"] is False
    assert call_args["priority"] == TaskPriority.NORMAL
    assert call_args["tags"] == ["test", "integration"]
    assert call_args["metadata"] == {"key": "value"}
    assert isinstance(call_args["config"], Configuration)
    assert call_args["config"].search_api.name == "GOOGLE"


def test_get_all_research(client, mock_parallel_manager):
    """Test getting all research tasks."""
    # Patch the parallel research manager
    with patch("dashboard.research_api.parallel_research_manager", mock_parallel_manager):
        # Send a request to get all research tasks
        response = client.get("/research/")
    
    # Check the response
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["research_id"] == "research_123"
    assert response.json()[0]["task_id"] == "task_id_1"
    assert response.json()[0]["topic"] == "Test Research"
    assert response.json()[0]["status"] == "pending"
    
    # Check that get_all_research was called
    mock_parallel_manager.get_all_research.assert_called_once()


def test_get_all_research_with_status_filter(client, mock_parallel_manager):
    """Test getting all research tasks with status filter."""
    # Patch the parallel research manager
    with patch("dashboard.research_api.parallel_research_manager", mock_parallel_manager):
        # Send a request to get all research tasks with status filter
        response = client.get("/research/?status=pending")
    
    # Check the response
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["research_id"] == "research_123"
    assert response.json()[0]["status"] == "pending"
    
    # Check that get_all_research was called
    mock_parallel_manager.get_all_research.assert_called_once()


def test_get_active_research(client, mock_parallel_manager):
    """Test getting active research tasks."""
    # Patch the parallel research manager
    with patch("dashboard.research_api.parallel_research_manager", mock_parallel_manager):
        # Send a request to get active research tasks
        response = client.get("/research/active")
    
    # Check the response
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["research_id"] == "research_123"
    assert response.json()[0]["status"] == "pending"
    
    # Check that get_active_research was called
    mock_parallel_manager.get_active_research.assert_called_once()


def test_get_research_metrics(client, mock_parallel_manager):
    """Test getting research metrics."""
    # Patch the parallel research manager
    with patch("dashboard.research_api.parallel_research_manager", mock_parallel_manager):
        # Send a request to get research metrics
        response = client.get("/research/metrics")
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["max_concurrent_research"] == 3
    assert response.json()["total_research"] == 1
    assert response.json()["pending_research"] == 1
    
    # Check that get_metrics was called
    mock_parallel_manager.get_metrics.assert_called_once()


def test_get_research(client, mock_parallel_manager):
    """Test getting a specific research task."""
    # Patch the parallel research manager
    with patch("dashboard.research_api.parallel_research_manager", mock_parallel_manager):
        # Send a request to get a specific research task
        response = client.get("/research/research_123")
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["task_id"] == "task_id_1"
    assert response.json()["topic"] == "Test Research"
    assert response.json()["status"] == "pending"
    
    # Check that get_research_status was called with the correct arguments
    mock_parallel_manager.get_research_status.assert_called_once_with("research_123")


def test_get_research_not_found(client, mock_parallel_manager):
    """Test getting a non-existent research task."""
    # Mock get_research_status to return None
    mock_parallel_manager.get_research_status.return_value = None
    
    # Patch the parallel research manager
    with patch("dashboard.research_api.parallel_research_manager", mock_parallel_manager):
        # Send a request to get a non-existent research task
        response = client.get("/research/non_existent")
    
    # Check the response
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
    
    # Check that get_research_status was called with the correct arguments
    mock_parallel_manager.get_research_status.assert_called_once_with("non_existent")


def test_get_research_result(client, mock_parallel_manager):
    """Test getting a research result."""
    # Mock get_research_status to return a completed research
    mock_parallel_manager.get_research_status.return_value = {
        "research_id": "research_123",
        "task_id": "task_id_1",
        "topic": "Test Research",
        "status": "completed",
        "use_multi_agent": False,
        "created_at": "2023-01-01T00:00:00",
        "progress": 1.0,
        "progress_message": "Completed"
    }
    
    # Patch the parallel research manager
    with patch("dashboard.research_api.parallel_research_manager", mock_parallel_manager):
        # Send a request to get a research result
        response = client.get("/research/research_123/result")
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["topic"] == "Test Research"
    assert response.json()["sections"] == [{"title": "Section 1", "content": "Content 1"}]
    assert response.json()["metadata"] == {"key": "value"}
    
    # Check that get_research_status and get_research_result were called with the correct arguments
    mock_parallel_manager.get_research_status.assert_called_once_with("research_123")
    mock_parallel_manager.get_research_result.assert_called_once_with("research_123")


def test_get_research_result_not_completed(client, mock_parallel_manager):
    """Test getting a result for a non-completed research task."""
    # Mock get_research_status to return a pending research
    mock_parallel_manager.get_research_status.return_value = {
        "research_id": "research_123",
        "task_id": "task_id_1",
        "topic": "Test Research",
        "status": "pending",
        "use_multi_agent": False,
        "created_at": "2023-01-01T00:00:00",
        "progress": 0.5,
        "progress_message": "In progress"
    }
    
    # Patch the parallel research manager
    with patch("dashboard.research_api.parallel_research_manager", mock_parallel_manager):
        # Send a request to get a result for a non-completed research task
        response = client.get("/research/research_123/result")
    
    # Check the response
    assert response.status_code == 400
    assert "not completed" in response.json()["detail"]
    
    # Check that get_research_status was called with the correct arguments
    mock_parallel_manager.get_research_status.assert_called_once_with("research_123")
    # get_research_result should not be called
    mock_parallel_manager.get_research_result.assert_not_called()


def test_cancel_research(client, mock_parallel_manager):
    """Test cancelling a research task."""
    # Patch the parallel research manager
    with patch("dashboard.research_api.parallel_research_manager", mock_parallel_manager):
        # Send a request to cancel a research task
        response = client.post("/research/research_123/cancel")
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["cancelled"] is True
    assert "cancelled successfully" in response.json()["message"]
    
    # Check that cancel_research was called with the correct arguments
    mock_parallel_manager.cancel_research.assert_called_once_with("research_123")


def test_cancel_research_failure(client, mock_parallel_manager):
    """Test cancelling a research task that fails."""
    # Mock cancel_research to return False
    mock_parallel_manager.cancel_research = AsyncMock(return_value=False)
    
    # Patch the parallel research manager
    with patch("dashboard.research_api.parallel_research_manager", mock_parallel_manager):
        # Send a request to cancel a research task
        response = client.post("/research/research_123/cancel")
    
    # Check the response
    assert response.status_code == 400
    assert "Failed to cancel" in response.json()["detail"]
    
    # Check that cancel_research was called with the correct arguments
    mock_parallel_manager.cancel_research.assert_called_once_with("research_123")

