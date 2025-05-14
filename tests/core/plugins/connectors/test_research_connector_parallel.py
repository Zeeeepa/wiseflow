"""Tests for the ResearchConnector with parallel research capabilities."""

import asyncio
import pytest
from unittest.mock import MagicMock, patch

from core.plugins.connectors.research_connector import ResearchConnector
from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI
from core.plugins.connectors.research.parallel_manager import FlowStatus

# Mock research results
MOCK_RESEARCH_RESULTS = {
    "topic": "test topic",
    "sections": [
        {
            "title": "Introduction",
            "content": "This is an introduction.",
            "subsections": []
        },
        {
            "title": "Main Content",
            "content": "This is the main content.",
            "subsections": []
        },
        {
            "title": "Conclusion",
            "content": "This is a conclusion.",
            "subsections": []
        }
    ],
    "metadata": {
        "search_api": "tavily",
        "research_mode": "linear",
        "search_depth": 2,
        "queries_per_iteration": 2
    }
}

@pytest.fixture
def mock_parallel_manager():
    """Create a mock ParallelResearchManager."""
    with patch("core.plugins.connectors.research.parallel_manager.ParallelResearchManager") as mock:
        manager_instance = mock.return_value
        
        # Mock start_research_flow
        manager_instance.start_research_flow.return_value = asyncio.Future()
        manager_instance.start_research_flow.return_value.set_result("test-flow-id")
        
        # Mock get_flow_status
        manager_instance.get_flow_status.return_value = {
            "id": "test-flow-id",
            "topic": "test topic",
            "status": FlowStatus.COMPLETED.value,
            "progress": 1.0,
            "has_results": True
        }
        
        # Mock get_flow_results
        manager_instance.get_flow_results.return_value = MOCK_RESEARCH_RESULTS
        
        # Mock cancel_flow
        manager_instance.cancel_flow.return_value = asyncio.Future()
        manager_instance.cancel_flow.return_value.set_result(True)
        
        # Mock get_all_flows
        manager_instance.get_all_flows.return_value = [
            {
                "id": "test-flow-id",
                "topic": "test topic",
                "status": FlowStatus.COMPLETED.value,
                "progress": 1.0,
                "has_results": True
            }
        ]
        
        # Mock continuous_research
        manager_instance.continuous_research.return_value = asyncio.Future()
        manager_instance.continuous_research.return_value.set_result("test-flow-id-2")
        
        yield mock

@pytest.mark.asyncio
async def test_start_parallel_research(mock_parallel_manager):
    """Test starting a parallel research flow."""
    connector = ResearchConnector()
    
    # Start a parallel research flow
    flow_id = await connector.start_parallel_research("test topic")
    
    # Check that the flow was started
    assert flow_id == "test-flow-id"
    assert mock_parallel_manager.return_value.start_research_flow.called

@pytest.mark.asyncio
async def test_get_parallel_research_status(mock_parallel_manager):
    """Test getting the status of a parallel research flow."""
    connector = ResearchConnector()
    
    # Initialize the parallel manager
    await connector.start_parallel_research("test topic")
    
    # Get flow status
    status = await connector.get_parallel_research_status("test-flow-id")
    
    # Check status
    assert status["id"] == "test-flow-id"
    assert status["status"] == FlowStatus.COMPLETED.value
    assert mock_parallel_manager.return_value.get_flow_status.called

@pytest.mark.asyncio
async def test_get_parallel_research_results(mock_parallel_manager):
    """Test getting the results of a parallel research flow."""
    connector = ResearchConnector()
    
    # Initialize the parallel manager
    await connector.start_parallel_research("test topic")
    
    # Get flow results
    results = await connector.get_parallel_research_results("test-flow-id")
    
    # Check results
    assert results == MOCK_RESEARCH_RESULTS
    assert mock_parallel_manager.return_value.get_flow_results.called

@pytest.mark.asyncio
async def test_cancel_parallel_research(mock_parallel_manager):
    """Test cancelling a parallel research flow."""
    connector = ResearchConnector()
    
    # Initialize the parallel manager
    await connector.start_parallel_research("test topic")
    
    # Cancel flow
    cancelled = await connector.cancel_parallel_research("test-flow-id")
    
    # Check result
    assert cancelled is True
    assert mock_parallel_manager.return_value.cancel_flow.called

@pytest.mark.asyncio
async def test_get_all_parallel_research_flows(mock_parallel_manager):
    """Test getting all parallel research flows."""
    connector = ResearchConnector()
    
    # Initialize the parallel manager
    await connector.start_parallel_research("test topic")
    
    # Get all flows
    flows = await connector.get_all_parallel_research_flows()
    
    # Check flows
    assert len(flows) == 1
    assert flows[0]["id"] == "test-flow-id"
    assert mock_parallel_manager.return_value.get_all_flows.called

@pytest.mark.asyncio
async def test_start_continuous_parallel_research(mock_parallel_manager):
    """Test starting a continuous parallel research flow."""
    connector = ResearchConnector()
    
    # Initialize the parallel manager
    await connector.start_parallel_research("test topic")
    
    # Start continuous research
    flow_id = await connector.start_continuous_parallel_research("test-flow-id", "follow-up question")
    
    # Check result
    assert flow_id == "test-flow-id-2"
    assert mock_parallel_manager.return_value.continuous_research.called

