"""
Integration tests for parallel research functionality.
"""

import pytest
import time
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import json

from fastapi.testclient import TestClient
from api_server import app as api_app

from core.plugins.connectors.research.parallel_manager import (
    ParallelResearchManager,
    get_parallel_research_manager
)
from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI
from core.plugins.connectors.research.state import ReportState, Sections

@pytest.mark.integration
class TestParallelResearchIntegration:
    """Integration tests for parallel research functionality."""
    
    @pytest.fixture
    def mock_parallel_research_manager(self):
        """Create a mock parallel research manager."""
        with patch("core.plugins.connectors.research.parallel_manager.get_parallel_research_manager") as mock:
            manager = MagicMock()
            
            # Mock submit_task
            manager.submit_task.return_value = "test-task-id"
            
            # Mock get_task
            manager.get_task.return_value = {
                "task_id": "test-task-id",
                "topic": "test topic",
                "status": "completed",
                "progress": 1.0,
                "start_time": time.time() - 5,
                "end_time": time.time(),
                "duration": 5.0,
                "error": None,
                "metadata": {}
            }
            
            # Mock get_task_result
            manager.get_task_result.return_value = {
                "topic": "test topic",
                "sections": [
                    {"title": "Introduction", "content": "Test introduction content"},
                    {"title": "Main Section", "content": "Test main section content"},
                    {"title": "Conclusion", "content": "Test conclusion content"}
                ],
                "metadata": {
                    "search_api": "tavily",
                    "research_mode": "linear",
                    "search_depth": 2,
                    "queries_per_iteration": 2
                }
            }
            
            # Mock cancel_task
            manager.cancel_task.return_value = True
            
            # Mock retry_task
            manager.retry_task.return_value = True
            
            # Mock list_tasks
            manager.list_tasks.return_value = [
                {
                    "task_id": "test-task-id",
                    "topic": "test topic",
                    "status": "completed",
                    "progress": 1.0,
                    "start_time": time.time() - 5,
                    "end_time": time.time(),
                    "duration": 5.0,
                    "error": None,
                    "metadata": {}
                }
            ]
            
            # Mock get_stats
            manager.get_stats.return_value = {
                "total_tasks": 1,
                "pending_tasks": 0,
                "running_tasks": 0,
                "completed_tasks": 1,
                "failed_tasks": 0,
                "active_tasks": 0,
                "queue_size": 0,
                "avg_duration": 5.0,
                "api_usage": {}
            }
            
            # Mock batch_submit
            manager.batch_submit.return_value = ["test-task-id-1", "test-task-id-2"]
            
            # Mock wait_for_task
            manager.wait_for_task.return_value = {
                "task_id": "test-task-id",
                "topic": "test topic",
                "status": "completed",
                "progress": 1.0,
                "start_time": time.time() - 5,
                "end_time": time.time(),
                "duration": 5.0,
                "error": None,
                "metadata": {}
            }
            
            # Mock wait_for_tasks
            manager.wait_for_tasks.return_value = {
                "test-task-id-1": {
                    "task_id": "test-task-id-1",
                    "topic": "test topic 1",
                    "status": "completed",
                    "progress": 1.0,
                    "start_time": time.time() - 5,
                    "end_time": time.time(),
                    "duration": 5.0,
                    "error": None,
                    "metadata": {}
                },
                "test-task-id-2": {
                    "task_id": "test-task-id-2",
                    "topic": "test topic 2",
                    "status": "completed",
                    "progress": 1.0,
                    "start_time": time.time() - 5,
                    "end_time": time.time(),
                    "duration": 5.0,
                    "error": None,
                    "metadata": {}
                }
            }
            
            # Mock clear_completed_tasks
            manager.clear_completed_tasks.return_value = 1
            
            mock.return_value = manager
            yield manager
    
    @pytest.fixture
    def api_client(self, mock_parallel_research_manager, test_env_vars):
        """Create a FastAPI TestClient for the API server."""
        return TestClient(api_app)
    
    def test_research_endpoint(self, api_client, mock_parallel_research_manager):
        """Test the research endpoint."""
        # Make the request
        response = api_client.post(
            "/api/v1/integration/research",
            headers={"X-API-Key": "test-api-key"},
            json={
                "topic": "test topic",
                "search_api": "tavily",
                "research_mode": "linear",
                "max_search_depth": 2,
                "number_of_queries": 2
            }
        )
        
        # Check the response
        assert response.status_code == 200
        
        # Verify the manager was called correctly
        mock_parallel_research_manager.research.assert_called_once()
        args, kwargs = mock_parallel_research_manager.research.call_args
        assert kwargs["topic"] == "test topic"
        assert kwargs["search_api"] == "tavily"
        assert kwargs["research_mode"] == "linear"
        assert kwargs["max_search_depth"] == 2
        assert kwargs["number_of_queries"] == 2
    
    def test_parallel_research_endpoint(self, api_client, mock_parallel_research_manager):
        """Test the parallel research endpoint."""
        # Make the request
        response = api_client.post(
            "/api/v1/integration/parallel-research",
            headers={"X-API-Key": "test-api-key"},
            json={
                "topics": ["topic 1", "topic 2", "topic 3"],
                "search_api": "tavily",
                "research_mode": "linear",
                "max_search_depth": 2,
                "number_of_queries": 2,
                "max_concurrent_tasks": 3
            }
        )
        
        # Check the response
        assert response.status_code == 200
        
        # Verify the manager was called correctly
        mock_parallel_research_manager.parallel_research.assert_called_once()
        args, kwargs = mock_parallel_research_manager.parallel_research.call_args
        assert kwargs["topics"] == ["topic 1", "topic 2", "topic 3"]
        assert kwargs["search_api"] == "tavily"
        assert kwargs["research_mode"] == "linear"
        assert kwargs["max_search_depth"] == 2
        assert kwargs["number_of_queries"] == 2
        assert kwargs["max_concurrent_tasks"] == 3
    
    def test_task_status_endpoint(self, api_client, mock_parallel_research_manager):
        """Test the task status endpoint."""
        # Make the request
        response = api_client.post(
            "/api/v1/integration/task-status",
            headers={"X-API-Key": "test-api-key"},
            json={
                "task_id": "test-task-id"
            }
        )
        
        # Check the response
        assert response.status_code == 200
        
        # Verify the manager was called correctly
        mock_parallel_research_manager.get_task_status.assert_called_once_with(
            task_id="test-task-id"
        )
    
    def test_task_cancel_endpoint(self, api_client, mock_parallel_research_manager):
        """Test the task cancel endpoint."""
        # Make the request
        response = api_client.post(
            "/api/v1/integration/task-cancel",
            headers={"X-API-Key": "test-api-key"},
            json={
                "task_id": "test-task-id"
            }
        )
        
        # Check the response
        assert response.status_code == 200
        
        # Verify the manager was called correctly
        mock_parallel_research_manager.cancel_task.assert_called_once_with(
            task_id="test-task-id"
        )
    
    def test_task_retry_endpoint(self, api_client, mock_parallel_research_manager):
        """Test the task retry endpoint."""
        # Make the request
        response = api_client.post(
            "/api/v1/integration/task-retry",
            headers={"X-API-Key": "test-api-key"},
            json={
                "task_id": "test-task-id"
            }
        )
        
        # Check the response
        assert response.status_code == 200
        
        # Verify the manager was called correctly
        mock_parallel_research_manager.retry_task.assert_called_once_with(
            task_id="test-task-id"
        )
    
    def test_task_batch_status_endpoint(self, api_client, mock_parallel_research_manager):
        """Test the task batch status endpoint."""
        # Make the request
        response = api_client.post(
            "/api/v1/integration/task-batch-status",
            headers={"X-API-Key": "test-api-key"},
            json={
                "task_ids": ["test-task-id-1", "test-task-id-2"],
                "wait": True,
                "timeout": 10
            }
        )
        
        # Check the response
        assert response.status_code == 200
        
        # Verify the manager was called correctly
        mock_parallel_research_manager.get_task_batch_status.assert_called_once_with(
            task_ids=["test-task-id-1", "test-task-id-2"],
            wait=True,
            timeout=10
        )
    
    def test_invalid_api_key(self, api_client):
        """Test with an invalid API key."""
        # Make the request with an invalid API key
        response = api_client.post(
            "/api/v1/integration/research",
            headers={"X-API-Key": "invalid-key"},
            json={
                "topic": "test topic",
                "search_api": "tavily",
                "research_mode": "linear",
                "max_search_depth": 2,
                "number_of_queries": 2
            }
        )
        
        # Check the response
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
    
    def test_missing_api_key(self, api_client):
        """Test with a missing API key."""
        # Make the request without an API key
        response = api_client.post(
            "/api/v1/integration/research",
            json={
                "topic": "test topic",
                "search_api": "tavily",
                "research_mode": "linear",
                "max_search_depth": 2,
                "number_of_queries": 2
            }
        )
        
        # Check the response
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

