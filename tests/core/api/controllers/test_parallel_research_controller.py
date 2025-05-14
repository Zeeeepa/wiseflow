#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the parallel research controller.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime

from core.api.controllers.parallel_research_controller import router
from core.plugins.connectors.research.parallel_manager import (
    ParallelResearchManager,
    ResearchFlowStatus
)

# Create a test client
client = TestClient(router)

@pytest.fixture
def mock_manager():
    """Create a mock parallel research manager."""
    manager = MagicMock(spec=ParallelResearchManager)
    return manager

def test_start_parallel_research(mock_manager):
    """Test starting parallel research flows."""
    # Mock the get_parallel_research_manager function
    with patch("core.api.controllers.parallel_research_controller.get_parallel_research_manager", return_value=mock_manager):
        # Mock the create_flow method
        mock_manager.create_flow.side_effect = ["flow1", "flow2"]
        
        # Mock the start_all_pending_flows method
        mock_manager.start_all_pending_flows.return_value = None
        
        # Make the request
        response = client.post(
            "",
            json={
                "topics": ["Topic 1", "Topic 2"],
                "config": {
                    "search_api": "tavily",
                    "research_mode": "linear",
                    "max_search_depth": 3,
                    "number_of_queries": 4
                },
                "metadata": {"user_id": "123"}
            }
        )
        
        # Check the response
        assert response.status_code == 200
        assert response.json()["flow_ids"] == ["flow1", "flow2"]
        assert response.json()["status"] == "success"
        
        # Check that the manager methods were called
        assert mock_manager.create_flow.call_count == 2
        mock_manager.create_flow.assert_any_call(
            topic="Topic 1",
            config=None,  # Configuration is created inside the endpoint
            metadata={"user_id": "123"}
        )
        mock_manager.create_flow.assert_any_call(
            topic="Topic 2",
            config=None,  # Configuration is created inside the endpoint
            metadata={"user_id": "123"}
        )
        mock_manager.start_all_pending_flows.assert_called_once()

def test_start_parallel_research_max_concurrent(mock_manager):
    """Test starting parallel research flows when the maximum number of concurrent flows is reached."""
    # Mock the get_parallel_research_manager function
    with patch("core.api.controllers.parallel_research_controller.get_parallel_research_manager", return_value=mock_manager):
        # Mock the create_flow method to raise a ValueError
        mock_manager.create_flow.side_effect = ValueError("Maximum number of concurrent flows reached")
        
        # Make the request
        response = client.post(
            "",
            json={
                "topics": ["Topic 1"],
                "config": None,
                "metadata": None
            }
        )
        
        # Check the response
        assert response.status_code == 429
        assert "Maximum number of concurrent flows reached" in response.json()["detail"]

def test_start_continuous_research(mock_manager):
    """Test starting a continuous research flow."""
    # Mock the get_parallel_research_manager function
    with patch("core.api.controllers.parallel_research_controller.get_parallel_research_manager", return_value=mock_manager):
        # Mock the get_flow method
        mock_flow = MagicMock()
        mock_flow.status = ResearchFlowStatus.COMPLETED
        mock_flow.config = MagicMock()
        mock_flow.result = {"topic": "Previous topic", "sections": []}
        mock_manager.get_flow.return_value = mock_flow
        
        # Mock the create_flow method
        mock_manager.create_flow.return_value = "flow1"
        
        # Mock the start_flow method
        mock_manager.start_flow.return_value = None
        
        # Make the request
        response = client.post(
            "/continuous",
            json={
                "previous_flow_id": "previous_flow",
                "new_topic": "New topic",
                "config": {
                    "search_api": "tavily",
                    "research_mode": "linear",
                    "max_search_depth": 3,
                    "number_of_queries": 4
                },
                "metadata": {"user_id": "123"}
            }
        )
        
        # Check the response
        assert response.status_code == 200
        assert response.json()["flow_ids"] == ["flow1"]
        assert response.json()["status"] == "success"
        
        # Check that the manager methods were called
        mock_manager.get_flow.assert_called_once_with("previous_flow")
        mock_manager.create_flow.assert_called_once()
        mock_manager.start_flow.assert_called_once_with("flow1")

def test_start_continuous_research_previous_flow_not_found(mock_manager):
    """Test starting a continuous research flow when the previous flow is not found."""
    # Mock the get_parallel_research_manager function
    with patch("core.api.controllers.parallel_research_controller.get_parallel_research_manager", return_value=mock_manager):
        # Mock the get_flow method to return None
        mock_manager.get_flow.return_value = None
        
        # Make the request
        response = client.post(
            "/continuous",
            json={
                "previous_flow_id": "non_existent",
                "new_topic": "New topic",
                "config": None,
                "metadata": None
            }
        )
        
        # Check the response
        assert response.status_code == 404
        assert "Previous flow not found" in response.json()["detail"]

def test_start_continuous_research_previous_flow_not_completed(mock_manager):
    """Test starting a continuous research flow when the previous flow is not completed."""
    # Mock the get_parallel_research_manager function
    with patch("core.api.controllers.parallel_research_controller.get_parallel_research_manager", return_value=mock_manager):
        # Mock the get_flow method
        mock_flow = MagicMock()
        mock_flow.status = ResearchFlowStatus.RUNNING
        mock_manager.get_flow.return_value = mock_flow
        
        # Make the request
        response = client.post(
            "/continuous",
            json={
                "previous_flow_id": "running_flow",
                "new_topic": "New topic",
                "config": None,
                "metadata": None
            }
        )
        
        # Check the response
        assert response.status_code == 400
        assert "Previous flow is not completed" in response.json()["detail"]

def test_get_all_research_flows(mock_manager):
    """Test getting the status of all research flows."""
    # Mock the get_parallel_research_manager function
    with patch("core.api.controllers.parallel_research_controller.get_parallel_research_manager", return_value=mock_manager):
        # Mock the list_flows method
        mock_manager.list_flows.return_value = [
            {"flow_id": "flow1", "topic": "Topic 1", "status": "running"},
            {"flow_id": "flow2", "topic": "Topic 2", "status": "completed"}
        ]
        
        # Make the request
        response = client.get("/status")
        
        # Check the response
        assert response.status_code == 200
        assert len(response.json()["flows"]) == 2
        assert response.json()["count"] == 2
        
        # Check that the manager methods were called
        mock_manager.list_flows.assert_called_once_with(status=None)

def test_get_all_research_flows_with_status_filter(mock_manager):
    """Test getting the status of all research flows with a status filter."""
    # Mock the get_parallel_research_manager function
    with patch("core.api.controllers.parallel_research_controller.get_parallel_research_manager", return_value=mock_manager):
        # Mock the list_flows method
        mock_manager.list_flows.return_value = [
            {"flow_id": "flow1", "topic": "Topic 1", "status": "running"}
        ]
        
        # Make the request
        response = client.get("/status?status=running")
        
        # Check the response
        assert response.status_code == 200
        assert len(response.json()["flows"]) == 1
        assert response.json()["flows"][0]["status"] == "running"
        
        # Check that the manager methods were called with the status filter
        mock_manager.list_flows.assert_called_once()

def test_get_research_flow(mock_manager):
    """Test getting the status of a specific research flow."""
    # Mock the get_parallel_research_manager function
    with patch("core.api.controllers.parallel_research_controller.get_parallel_research_manager", return_value=mock_manager):
        # Mock the get_flow method
        mock_flow = MagicMock()
        mock_flow.to_dict.return_value = {
            "flow_id": "flow1",
            "topic": "Topic 1",
            "status": "completed",
            "created_at": datetime.now().isoformat(),
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "progress": 1.0,
            "error": None,
            "metadata": {},
            "config": {}
        }
        mock_flow.status = ResearchFlowStatus.COMPLETED
        mock_flow.result = {"topic": "Topic 1", "sections": []}
        mock_manager.get_flow.return_value = mock_flow
        
        # Make the request
        response = client.get("/flow1")
        
        # Check the response
        assert response.status_code == 200
        assert response.json()["flow"]["flow_id"] == "flow1"
        assert response.json()["flow"]["status"] == "completed"
        assert response.json()["result"] is not None
        
        # Check that the manager methods were called
        mock_manager.get_flow.assert_called_once_with("flow1")

def test_get_research_flow_not_found(mock_manager):
    """Test getting the status of a research flow that doesn't exist."""
    # Mock the get_parallel_research_manager function
    with patch("core.api.controllers.parallel_research_controller.get_parallel_research_manager", return_value=mock_manager):
        # Mock the get_flow method to return None
        mock_manager.get_flow.return_value = None
        
        # Make the request
        response = client.get("/non_existent")
        
        # Check the response
        assert response.status_code == 404
        assert "Flow not found" in response.json()["detail"]

def test_cancel_research_flow(mock_manager):
    """Test cancelling a research flow."""
    # Mock the get_parallel_research_manager function
    with patch("core.api.controllers.parallel_research_controller.get_parallel_research_manager", return_value=mock_manager):
        # Mock the cancel_flow method
        mock_manager.cancel_flow.return_value = True
        
        # Make the request
        response = client.post("/flow1/cancel")
        
        # Check the response
        assert response.status_code == 200
        assert response.json()["flow_id"] == "flow1"
        assert response.json()["status"] == "success"
        assert response.json()["message"] == "Research flow cancelled"
        
        # Check that the manager methods were called
        mock_manager.cancel_flow.assert_called_once_with("flow1")

def test_cancel_research_flow_not_found(mock_manager):
    """Test cancelling a research flow that doesn't exist."""
    # Mock the get_parallel_research_manager function
    with patch("core.api.controllers.parallel_research_controller.get_parallel_research_manager", return_value=mock_manager):
        # Mock the cancel_flow method to return False
        mock_manager.cancel_flow.return_value = False
        
        # Make the request
        response = client.post("/non_existent/cancel")
        
        # Check the response
        assert response.status_code == 404
        assert "Flow not found or cannot be cancelled" in response.json()["detail"]

