"""
End-to-end tests for parallel research workflows.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

from dashboard.main import app as dashboard_app
from core.plugins.connectors.research.parallel_manager import ParallelResearchManager
from core.plugins.connectors.research.configuration import Configuration, SearchAPI
from core.task_management import TaskPriority


@pytest.fixture
def client():
    """Create a test client for the dashboard app."""
    return TestClient(dashboard_app)


@pytest.fixture
def mock_research_result():
    """Create a mock research result."""
    return {
        "sections": MagicMock(
            sections=[
                {
                    "title": "Introduction",
                    "content": "This is an introduction to the research topic."
                },
                {
                    "title": "Key Findings",
                    "content": "These are the key findings of the research."
                },
                {
                    "title": "Conclusion",
                    "content": "This is the conclusion of the research."
                }
            ]
        ),
        "metadata": {
            "sources": [
                {"title": "Source 1", "url": "https://example.com/1"},
                {"title": "Source 2", "url": "https://example.com/2"}
            ],
            "query_count": 5,
            "processing_time": 10.5
        }
    }


@pytest.mark.asyncio
async def test_complete_research_workflow(client, mock_research_result):
    """Test a complete research workflow from creation to visualization."""
    # Mock the parallel research manager
    mock_manager = MagicMock()
    mock_manager.create_research_task = AsyncMock(return_value="task_id_1")
    mock_manager.task_manager = MagicMock()
    mock_manager.task_manager.execute_task = AsyncMock(return_value=mock_research_result)
    
    # Mock research status progression
    status_progression = [
        # Initial status
        {
            "research_id": "research_123",
            "task_id": "task_id_1",
            "topic": "Workflow Test",
            "status": "pending",
            "use_multi_agent": False,
            "created_at": "2023-01-01T00:00:00",
            "progress": 0.0,
            "progress_message": ""
        },
        # Running status
        {
            "research_id": "research_123",
            "task_id": "task_id_1",
            "topic": "Workflow Test",
            "status": "running",
            "use_multi_agent": False,
            "created_at": "2023-01-01T00:00:00",
            "progress": 0.5,
            "progress_message": "Processing data"
        },
        # Completed status
        {
            "research_id": "research_123",
            "task_id": "task_id_1",
            "topic": "Workflow Test",
            "status": "completed",
            "use_multi_agent": False,
            "created_at": "2023-01-01T00:00:00",
            "progress": 1.0,
            "progress_message": "Research completed"
        }
    ]
    
    # Set up the get_research_status mock to return different statuses in sequence
    mock_manager.get_research_status = MagicMock(side_effect=status_progression)
    
    # Mock get_research_result
    mock_manager.get_research_result = MagicMock(return_value=mock_research_result)
    
    # Mock active_research
    mock_manager.active_research = {
        "research_123": {
            "task_id": "task_id_1",
            "topic": "Workflow Test",
            "status": "completed"
        }
    }
    
    # Step 1: Create a research task
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager):
        # Send a request to create a research task
        response = client.post(
            "/research/",
            json={
                "topic": "Workflow Test",
                "use_multi_agent": False,
                "priority": "NORMAL",
                "tags": ["test", "workflow"],
                "metadata": {"key": "value"},
                "config": {"search_api": "GOOGLE"}
            }
        )
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["task_id"] == "task_id_1"
    assert response.json()["topic"] == "Workflow Test"
    assert response.json()["status"] == "pending"
    
    # Check that create_research_task was called with the correct arguments
    mock_manager.create_research_task.assert_called_once()
    call_args = mock_manager.create_research_task.call_args[1]
    assert call_args["topic"] == "Workflow Test"
    assert call_args["use_multi_agent"] is False
    assert call_args["priority"] == TaskPriority.NORMAL
    assert call_args["tags"] == ["test", "workflow"]
    assert call_args["metadata"] == {"key": "value"}
    assert isinstance(call_args["config"], Configuration)
    assert call_args["config"].search_api.name == "GOOGLE"
    
    # Step 2: Check research status (running)
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager):
        # Send a request to get research status
        response = client.get("/research/research_123")
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["status"] == "running"
    assert response.json()["progress"] == 0.5
    assert response.json()["progress_message"] == "Processing data"
    
    # Step 3: Check research status (completed)
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager):
        # Send a request to get research status
        response = client.get("/research/research_123")
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["status"] == "completed"
    assert response.json()["progress"] == 1.0
    assert response.json()["progress_message"] == "Research completed"
    
    # Step 4: Get research result
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager):
        # Send a request to get research result
        response = client.get("/research/research_123/result")
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["topic"] == "Workflow Test"
    assert len(response.json()["sections"]) == 3
    assert response.json()["sections"][0]["title"] == "Introduction"
    assert response.json()["metadata"]["sources"][0]["title"] == "Source 1"
    
    # Step 5: Visualize research result
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager), \
         patch("dashboard.visualization.knowledge_graph.visualize_knowledge_graph", return_value={"nodes": [], "edges": []}):
        # Send a request to visualize research result
        response = client.post(
            "/research/research_123/visualize",
            json={
                "research_id": "research_123",
                "visualization_type": "knowledge_graph",
                "config": {}
            }
        )
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["visualization_type"] == "knowledge_graph"
    assert "visualization" in response.json()


@pytest.mark.asyncio
async def test_error_handling_workflow(client):
    """Test error handling in the research workflow."""
    # Mock the parallel research manager
    mock_manager = MagicMock()
    mock_manager.create_research_task = AsyncMock(return_value="task_id_1")
    mock_manager.task_manager = MagicMock()
    mock_manager.task_manager.execute_task = AsyncMock(side_effect=ValueError("Test error"))
    
    # Mock research status progression
    status_progression = [
        # Initial status
        {
            "research_id": "research_123",
            "task_id": "task_id_1",
            "topic": "Error Test",
            "status": "pending",
            "use_multi_agent": False,
            "created_at": "2023-01-01T00:00:00",
            "progress": 0.0,
            "progress_message": ""
        },
        # Running status
        {
            "research_id": "research_123",
            "task_id": "task_id_1",
            "topic": "Error Test",
            "status": "running",
            "use_multi_agent": False,
            "created_at": "2023-01-01T00:00:00",
            "progress": 0.5,
            "progress_message": "Processing data"
        },
        # Failed status
        {
            "research_id": "research_123",
            "task_id": "task_id_1",
            "topic": "Error Test",
            "status": "failed",
            "use_multi_agent": False,
            "created_at": "2023-01-01T00:00:00",
            "progress": 0.5,
            "progress_message": "Processing data",
            "error": "Test error"
        }
    ]
    
    # Set up the get_research_status mock to return different statuses in sequence
    mock_manager.get_research_status = MagicMock(side_effect=status_progression)
    
    # Mock active_research
    mock_manager.active_research = {
        "research_123": {
            "task_id": "task_id_1",
            "topic": "Error Test",
            "status": "failed",
            "error": "Test error"
        }
    }
    
    # Step 1: Create a research task
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager):
        # Send a request to create a research task
        response = client.post(
            "/research/",
            json={
                "topic": "Error Test",
                "use_multi_agent": False,
                "priority": "NORMAL"
            }
        )
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["task_id"] == "task_id_1"
    assert response.json()["topic"] == "Error Test"
    assert response.json()["status"] == "pending"
    
    # Step 2: Check research status (running)
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager):
        # Send a request to get research status
        response = client.get("/research/research_123")
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["status"] == "running"
    assert response.json()["progress"] == 0.5
    assert response.json()["progress_message"] == "Processing data"
    
    # Step 3: Check research status (failed)
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager):
        # Send a request to get research status
        response = client.get("/research/research_123")
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["status"] == "failed"
    assert response.json()["error"] == "Test error"
    
    # Step 4: Try to get research result (should fail)
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager):
        # Send a request to get research result
        response = client.get("/research/research_123/result")
    
    # Check the response
    assert response.status_code == 400
    assert "not completed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_cancellation_workflow(client):
    """Test cancellation in the research workflow."""
    # Mock the parallel research manager
    mock_manager = MagicMock()
    mock_manager.create_research_task = AsyncMock(return_value="task_id_1")
    mock_manager.cancel_research = AsyncMock(return_value=True)
    mock_manager.task_manager = MagicMock()
    
    # Mock research status progression
    status_progression = [
        # Initial status
        {
            "research_id": "research_123",
            "task_id": "task_id_1",
            "topic": "Cancellation Test",
            "status": "pending",
            "use_multi_agent": False,
            "created_at": "2023-01-01T00:00:00",
            "progress": 0.0,
            "progress_message": ""
        },
        # Running status
        {
            "research_id": "research_123",
            "task_id": "task_id_1",
            "topic": "Cancellation Test",
            "status": "running",
            "use_multi_agent": False,
            "created_at": "2023-01-01T00:00:00",
            "progress": 0.5,
            "progress_message": "Processing data"
        },
        # Cancelled status
        {
            "research_id": "research_123",
            "task_id": "task_id_1",
            "topic": "Cancellation Test",
            "status": "cancelled",
            "use_multi_agent": False,
            "created_at": "2023-01-01T00:00:00",
            "progress": 0.5,
            "progress_message": "Processing data"
        }
    ]
    
    # Set up the get_research_status mock to return different statuses in sequence
    mock_manager.get_research_status = MagicMock(side_effect=status_progression)
    
    # Mock active_research
    mock_manager.active_research = {
        "research_123": {
            "task_id": "task_id_1",
            "topic": "Cancellation Test",
            "status": "running"
        }
    }
    
    # Step 1: Create a research task
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager):
        # Send a request to create a research task
        response = client.post(
            "/research/",
            json={
                "topic": "Cancellation Test",
                "use_multi_agent": False,
                "priority": "NORMAL"
            }
        )
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["task_id"] == "task_id_1"
    assert response.json()["topic"] == "Cancellation Test"
    assert response.json()["status"] == "pending"
    
    # Step 2: Check research status (running)
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager):
        # Send a request to get research status
        response = client.get("/research/research_123")
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["status"] == "running"
    assert response.json()["progress"] == 0.5
    assert response.json()["progress_message"] == "Processing data"
    
    # Step 3: Cancel the research
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager):
        # Send a request to cancel the research
        response = client.post("/research/research_123/cancel")
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["cancelled"] is True
    assert "cancelled successfully" in response.json()["message"]
    
    # Check that cancel_research was called with the correct arguments
    mock_manager.cancel_research.assert_called_once_with("research_123")
    
    # Step 4: Check research status (cancelled)
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager):
        # Send a request to get research status
        response = client.get("/research/research_123")
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["status"] == "cancelled"
    
    # Step 5: Try to get research result (should fail)
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager):
        # Send a request to get research result
        response = client.get("/research/research_123/result")
    
    # Check the response
    assert response.status_code == 400
    assert "not completed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_multi_agent_workflow(client, mock_research_result):
    """Test a multi-agent research workflow."""
    # Mock the parallel research manager
    mock_manager = MagicMock()
    mock_manager.create_research_task = AsyncMock(return_value="task_id_1")
    mock_manager.task_manager = MagicMock()
    mock_manager.task_manager.execute_task = AsyncMock(return_value=mock_research_result)
    
    # Mock research status progression
    status_progression = [
        # Initial status
        {
            "research_id": "research_123",
            "task_id": "task_id_1",
            "topic": "Multi-Agent Test",
            "status": "pending",
            "use_multi_agent": True,
            "created_at": "2023-01-01T00:00:00",
            "progress": 0.0,
            "progress_message": ""
        },
        # Running status
        {
            "research_id": "research_123",
            "task_id": "task_id_1",
            "topic": "Multi-Agent Test",
            "status": "running",
            "use_multi_agent": True,
            "created_at": "2023-01-01T00:00:00",
            "progress": 0.5,
            "progress_message": "Agents collaborating"
        },
        # Completed status
        {
            "research_id": "research_123",
            "task_id": "task_id_1",
            "topic": "Multi-Agent Test",
            "status": "completed",
            "use_multi_agent": True,
            "created_at": "2023-01-01T00:00:00",
            "progress": 1.0,
            "progress_message": "Research completed"
        }
    ]
    
    # Set up the get_research_status mock to return different statuses in sequence
    mock_manager.get_research_status = MagicMock(side_effect=status_progression)
    
    # Mock get_research_result
    mock_manager.get_research_result = MagicMock(return_value=mock_research_result)
    
    # Mock active_research
    mock_manager.active_research = {
        "research_123": {
            "task_id": "task_id_1",
            "topic": "Multi-Agent Test",
            "status": "completed",
            "use_multi_agent": True
        }
    }
    
    # Step 1: Create a multi-agent research task
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager):
        # Send a request to create a research task
        response = client.post(
            "/research/",
            json={
                "topic": "Multi-Agent Test",
                "use_multi_agent": True,
                "priority": "HIGH",
                "tags": ["test", "multi-agent"],
                "metadata": {"key": "value"},
                "config": {"search_api": "GOOGLE"}
            }
        )
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["task_id"] == "task_id_1"
    assert response.json()["topic"] == "Multi-Agent Test"
    assert response.json()["status"] == "pending"
    assert response.json()["use_multi_agent"] is True
    
    # Check that create_research_task was called with the correct arguments
    mock_manager.create_research_task.assert_called_once()
    call_args = mock_manager.create_research_task.call_args[1]
    assert call_args["topic"] == "Multi-Agent Test"
    assert call_args["use_multi_agent"] is True
    assert call_args["priority"] == TaskPriority.HIGH
    
    # Step 2: Check research status (running)
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager):
        # Send a request to get research status
        response = client.get("/research/research_123")
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["status"] == "running"
    assert response.json()["progress"] == 0.5
    assert response.json()["progress_message"] == "Agents collaborating"
    assert response.json()["use_multi_agent"] is True
    
    # Step 3: Check research status (completed)
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager):
        # Send a request to get research status
        response = client.get("/research/research_123")
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["status"] == "completed"
    assert response.json()["progress"] == 1.0
    assert response.json()["progress_message"] == "Research completed"
    assert response.json()["use_multi_agent"] is True
    
    # Step 4: Get research result
    with patch("dashboard.research_api.parallel_research_manager", mock_manager), \
         patch("dashboard.routes.parallel_research_manager", mock_manager):
        # Send a request to get research result
        response = client.get("/research/research_123/result")
    
    # Check the response
    assert response.status_code == 200
    assert response.json()["research_id"] == "research_123"
    assert response.json()["topic"] == "Multi-Agent Test"
    assert len(response.json()["sections"]) == 3
    assert response.json()["sections"][0]["title"] == "Introduction"
    assert response.json()["metadata"]["sources"][0]["title"] == "Source 1"

