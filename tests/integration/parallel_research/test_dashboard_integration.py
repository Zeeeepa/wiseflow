"""
Integration tests for the dashboard with parallel research.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from dashboard.main import app as dashboard_app
from core.plugins.connectors.research.parallel_manager import ParallelResearchManager
from core.plugins.connectors.research.configuration import Configuration
from core.task_management import TaskPriority


@pytest.fixture
def client():
    """Create a test client for the dashboard app."""
    return TestClient(dashboard_app)


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


def test_dashboard_home(client):
    """Test the dashboard home page."""
    # Send a request to the home page
    response = client.get("/")
    
    # Check the response
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_dashboard_research_page(client, mock_parallel_manager):
    """Test the dashboard research page."""
    # Patch the parallel research manager
    with patch("dashboard.routes.parallel_research_manager", mock_parallel_manager):
        # Send a request to the research page
        response = client.get("/research")
    
    # Check the response
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    # Check that get_all_research was called
    mock_parallel_manager.get_all_research.assert_called_once()


def test_dashboard_research_detail_page(client, mock_parallel_manager):
    """Test the dashboard research detail page."""
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
    with patch("dashboard.routes.parallel_research_manager", mock_parallel_manager):
        # Send a request to the research detail page
        response = client.get("/research/research_123")
    
    # Check the response
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    # Check that get_research_status was called with the correct arguments
    mock_parallel_manager.get_research_status.assert_called_once_with("research_123")


def test_dashboard_create_research_form(client):
    """Test the dashboard create research form."""
    # Send a request to the create research form
    response = client.get("/research/create")
    
    # Check the response
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_dashboard_create_research_submit(client, mock_parallel_manager):
    """Test submitting the create research form."""
    # Patch the parallel research manager
    with patch("dashboard.routes.parallel_research_manager", mock_parallel_manager):
        # Send a request to submit the create research form
        response = client.post(
            "/research/create",
            data={
                "topic": "Test Research",
                "use_multi_agent": "false",
                "priority": "NORMAL",
                "search_api": "GOOGLE"
            },
            follow_redirects=False
        )
    
    # Check the response
    assert response.status_code == 302  # Redirect
    assert "/research" in response.headers["location"]
    
    # Check that create_research_task was called with the correct arguments
    mock_parallel_manager.create_research_task.assert_called_once()
    call_args = mock_parallel_manager.create_research_task.call_args[1]
    assert call_args["topic"] == "Test Research"
    assert call_args["use_multi_agent"] is False
    assert call_args["priority"] == TaskPriority.NORMAL
    assert isinstance(call_args["config"], Configuration)
    assert call_args["config"].search_api.name == "GOOGLE"


def test_dashboard_cancel_research(client, mock_parallel_manager):
    """Test cancelling a research task from the dashboard."""
    # Patch the parallel research manager
    with patch("dashboard.routes.parallel_research_manager", mock_parallel_manager):
        # Send a request to cancel a research task
        response = client.post(
            "/research/research_123/cancel",
            follow_redirects=False
        )
    
    # Check the response
    assert response.status_code == 302  # Redirect
    assert "/research" in response.headers["location"]
    
    # Check that cancel_research was called with the correct arguments
    mock_parallel_manager.cancel_research.assert_called_once_with("research_123")


def test_dashboard_research_visualization(client, mock_parallel_manager):
    """Test the dashboard research visualization."""
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
    
    # Mock visualization functions
    with patch("dashboard.routes.parallel_research_manager", mock_parallel_manager), \
         patch("dashboard.visualization.knowledge_graph.visualize_knowledge_graph", return_value={"nodes": [], "edges": []}):
        # Send a request to the research visualization page
        response = client.get("/research/research_123/visualize/knowledge_graph")
    
    # Check the response
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    # Check that get_research_status and get_research_result were called with the correct arguments
    mock_parallel_manager.get_research_status.assert_called_once_with("research_123")
    mock_parallel_manager.get_research_result.assert_called_once_with("research_123")

