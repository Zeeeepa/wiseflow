#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the parallel research manager.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from core.plugins.connectors.research.parallel_manager import (
    ParallelResearchManager,
    ResearchFlow,
    ResearchFlowStatus
)
from core.plugins.connectors.research.configuration import Configuration

@pytest.fixture
def manager():
    """Create a parallel research manager for testing."""
    manager = ParallelResearchManager()
    manager.flows = {}  # Clear any existing flows
    return manager

def test_create_flow(manager):
    """Test creating a research flow."""
    # Create a flow
    flow_id = manager.create_flow(topic="Test topic")
    
    # Check that the flow was created
    assert flow_id in manager.flows
    assert manager.flows[flow_id].topic == "Test topic"
    assert manager.flows[flow_id].status == ResearchFlowStatus.PENDING

def test_create_flow_with_config(manager):
    """Test creating a research flow with a custom configuration."""
    # Create a configuration
    config = Configuration(max_search_depth=3, number_of_queries=4)
    
    # Create a flow
    flow_id = manager.create_flow(topic="Test topic", config=config)
    
    # Check that the flow was created with the custom configuration
    assert flow_id in manager.flows
    assert manager.flows[flow_id].config.max_search_depth == 3
    assert manager.flows[flow_id].config.number_of_queries == 4

def test_create_flow_with_metadata(manager):
    """Test creating a research flow with metadata."""
    # Create a flow
    metadata = {"user_id": "123", "source": "api"}
    flow_id = manager.create_flow(topic="Test topic", metadata=metadata)
    
    # Check that the flow was created with the metadata
    assert flow_id in manager.flows
    assert manager.flows[flow_id].metadata == metadata

def test_create_flow_max_concurrent(manager):
    """Test creating a research flow when the maximum number of concurrent flows is reached."""
    # Set the maximum number of concurrent flows
    manager.max_concurrent_flows = 2
    
    # Create two flows
    flow_id1 = manager.create_flow(topic="Test topic 1")
    flow_id2 = manager.create_flow(topic="Test topic 2")
    
    # Try to create a third flow
    with pytest.raises(ValueError):
        manager.create_flow(topic="Test topic 3")
    
    # Check that only two flows were created
    assert len(manager.flows) == 2
    assert flow_id1 in manager.flows
    assert flow_id2 in manager.flows

def test_get_flow(manager):
    """Test getting a research flow."""
    # Create a flow
    flow_id = manager.create_flow(topic="Test topic")
    
    # Get the flow
    flow = manager.get_flow(flow_id)
    
    # Check that the flow was retrieved
    assert flow is not None
    assert flow.flow_id == flow_id
    assert flow.topic == "Test topic"

def test_get_flow_not_found(manager):
    """Test getting a research flow that doesn't exist."""
    # Get a non-existent flow
    flow = manager.get_flow("non-existent")
    
    # Check that the flow was not found
    assert flow is None

def test_list_flows(manager):
    """Test listing all research flows."""
    # Create some flows
    flow_id1 = manager.create_flow(topic="Test topic 1")
    flow_id2 = manager.create_flow(topic="Test topic 2")
    
    # List all flows
    flows = manager.list_flows()
    
    # Check that all flows were listed
    assert len(flows) == 2
    assert any(flow["flow_id"] == flow_id1 for flow in flows)
    assert any(flow["flow_id"] == flow_id2 for flow in flows)

def test_list_flows_with_status_filter(manager):
    """Test listing research flows filtered by status."""
    # Create some flows with different statuses
    flow_id1 = manager.create_flow(topic="Test topic 1")
    flow_id2 = manager.create_flow(topic="Test topic 2")
    
    # Set the status of the second flow to RUNNING
    manager.flows[flow_id2].status = ResearchFlowStatus.RUNNING
    
    # List flows with status PENDING
    flows = manager.list_flows(status=ResearchFlowStatus.PENDING)
    
    # Check that only the pending flow was listed
    assert len(flows) == 1
    assert flows[0]["flow_id"] == flow_id1
    
    # List flows with status RUNNING
    flows = manager.list_flows(status=ResearchFlowStatus.RUNNING)
    
    # Check that only the running flow was listed
    assert len(flows) == 1
    assert flows[0]["flow_id"] == flow_id2
    
    # List flows with multiple statuses
    flows = manager.list_flows(status=[ResearchFlowStatus.PENDING, ResearchFlowStatus.RUNNING])
    
    # Check that both flows were listed
    assert len(flows) == 2
    assert any(flow["flow_id"] == flow_id1 for flow in flows)
    assert any(flow["flow_id"] == flow_id2 for flow in flows)

def test_cancel_flow(manager):
    """Test cancelling a research flow."""
    # Create a flow
    flow_id = manager.create_flow(topic="Test topic")
    
    # Set the status to RUNNING
    manager.flows[flow_id].status = ResearchFlowStatus.RUNNING
    
    # Cancel the flow
    success = manager.cancel_flow(flow_id)
    
    # Check that the flow was cancelled
    assert success
    assert manager.flows[flow_id].status == ResearchFlowStatus.CANCELLED

def test_cancel_flow_not_found(manager):
    """Test cancelling a research flow that doesn't exist."""
    # Cancel a non-existent flow
    success = manager.cancel_flow("non-existent")
    
    # Check that the flow was not cancelled
    assert not success

def test_cancel_flow_already_completed(manager):
    """Test cancelling a research flow that is already completed."""
    # Create a flow
    flow_id = manager.create_flow(topic="Test topic")
    
    # Set the status to COMPLETED
    manager.flows[flow_id].status = ResearchFlowStatus.COMPLETED
    
    # Try to cancel the flow
    success = manager.cancel_flow(flow_id)
    
    # Check that the flow was not cancelled
    assert not success
    assert manager.flows[flow_id].status == ResearchFlowStatus.COMPLETED

def test_cleanup_completed_flows(manager):
    """Test cleaning up completed flows."""
    # Create some flows
    flow_id1 = manager.create_flow(topic="Test topic 1")
    flow_id2 = manager.create_flow(topic="Test topic 2")
    flow_id3 = manager.create_flow(topic="Test topic 3")
    
    # Set the status of the first flow to COMPLETED
    manager.flows[flow_id1].status = ResearchFlowStatus.COMPLETED
    manager.flows[flow_id1].completed_at = datetime.now() - timedelta(hours=25)
    
    # Set the status of the second flow to FAILED
    manager.flows[flow_id2].status = ResearchFlowStatus.FAILED
    manager.flows[flow_id2].completed_at = datetime.now() - timedelta(hours=25)
    
    # Clean up completed flows older than 24 hours
    count = manager.cleanup_completed_flows(max_age_hours=24)
    
    # Check that the completed and failed flows were cleaned up
    assert count == 2
    assert flow_id1 not in manager.flows
    assert flow_id2 not in manager.flows
    assert flow_id3 in manager.flows

@pytest.mark.asyncio
async def test_start_flow(manager):
    """Test starting a research flow."""
    # Create a flow
    flow_id = manager.create_flow(topic="Test topic")
    
    # Mock the _execute_flow method
    manager._execute_flow = MagicMock()
    
    # Start the flow
    success = await manager.start_flow(flow_id)
    
    # Check that the flow was started
    assert success
    assert manager.flows[flow_id].status == ResearchFlowStatus.RUNNING
    assert manager.flows[flow_id].started_at is not None
    assert manager.flows[flow_id].task is not None

@pytest.mark.asyncio
async def test_start_flow_not_found(manager):
    """Test starting a research flow that doesn't exist."""
    # Start a non-existent flow
    success = await manager.start_flow("non-existent")
    
    # Check that the flow was not started
    assert not success

@pytest.mark.asyncio
async def test_start_flow_already_running(manager):
    """Test starting a research flow that is already running."""
    # Create a flow
    flow_id = manager.create_flow(topic="Test topic")
    
    # Set the status to RUNNING
    manager.flows[flow_id].status = ResearchFlowStatus.RUNNING
    
    # Try to start the flow
    success = await manager.start_flow(flow_id)
    
    # Check that the flow was not started again
    assert not success

@pytest.mark.asyncio
async def test_start_all_pending_flows(manager):
    """Test starting all pending flows."""
    # Create some flows
    flow_id1 = manager.create_flow(topic="Test topic 1")
    flow_id2 = manager.create_flow(topic="Test topic 2")
    
    # Set the status of the second flow to RUNNING
    manager.flows[flow_id2].status = ResearchFlowStatus.RUNNING
    
    # Mock the start_flow method
    original_start_flow = manager.start_flow
    manager.start_flow = MagicMock(return_value=asyncio.Future())
    manager.start_flow.return_value.set_result(True)
    
    # Start all pending flows
    count = await manager.start_all_pending_flows()
    
    # Check that only the pending flow was started
    assert count == 1
    manager.start_flow.assert_called_once_with(flow_id1)
    
    # Restore the original start_flow method
    manager.start_flow = original_start_flow

@pytest.mark.asyncio
async def test_execute_flow_success(manager):
    """Test executing a research flow successfully."""
    # Create a flow
    flow_id = manager.create_flow(topic="Test topic")
    flow = manager.flows[flow_id]
    
    # Mock the research graph
    mock_graph = MagicMock()
    mock_result = MagicMock()
    mock_result.sections = MagicMock()
    mock_graph.ainvoke = MagicMock(return_value=asyncio.Future())
    mock_graph.ainvoke.return_value.set_result(mock_result)
    
    # Mock the format_sections function
    mock_format_sections = MagicMock(return_value=[])
    
    # Execute the flow
    with patch("core.plugins.connectors.research.get_research_graph", return_value=mock_graph), \
         patch("core.plugins.connectors.research.utils.format_sections", mock_format_sections):
        await manager._execute_flow(flow)
    
    # Check that the flow was executed successfully
    assert flow.status == ResearchFlowStatus.COMPLETED
    assert flow.completed_at is not None
    assert flow.result is not None
    assert flow.progress == 1.0

@pytest.mark.asyncio
async def test_execute_flow_cancelled(manager):
    """Test executing a research flow that gets cancelled."""
    # Create a flow
    flow_id = manager.create_flow(topic="Test topic")
    flow = manager.flows[flow_id]
    
    # Mock the research graph to raise a CancelledError
    mock_graph = MagicMock()
    mock_graph.ainvoke = MagicMock(side_effect=asyncio.CancelledError())
    
    # Execute the flow
    with patch("core.plugins.connectors.research.get_research_graph", return_value=mock_graph):
        await manager._execute_flow(flow)
    
    # Check that the flow was marked as cancelled
    assert flow.status == ResearchFlowStatus.CANCELLED
    assert flow.completed_at is not None
    assert flow.error == "Flow was cancelled"

@pytest.mark.asyncio
async def test_execute_flow_error(manager):
    """Test executing a research flow that encounters an error."""
    # Create a flow
    flow_id = manager.create_flow(topic="Test topic")
    flow = manager.flows[flow_id]
    
    # Mock the research graph to raise an exception
    mock_graph = MagicMock()
    mock_graph.ainvoke = MagicMock(side_effect=Exception("Test error"))
    
    # Execute the flow
    with patch("core.plugins.connectors.research.get_research_graph", return_value=mock_graph):
        await manager._execute_flow(flow)
    
    # Check that the flow was marked as failed
    assert flow.status == ResearchFlowStatus.FAILED
    assert flow.completed_at is not None
    assert flow.error == "Test error"

