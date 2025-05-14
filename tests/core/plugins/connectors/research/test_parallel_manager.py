"""Tests for the ParallelResearchManager."""

import asyncio
import pytest
import time
from unittest.mock import MagicMock, patch

from core.plugins.connectors.research.parallel_manager import ParallelResearchManager, FlowStatus
from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI

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
def mock_research_connector():
    """Create a mock ResearchConnector."""
    with patch("core.plugins.connectors.research.parallel_manager.ResearchConnector") as mock:
        connector_instance = mock.return_value
        connector_instance.research.return_value = MOCK_RESEARCH_RESULTS
        connector_instance.continuous_research.return_value = MOCK_RESEARCH_RESULTS
        yield mock

@pytest.mark.asyncio
async def test_start_research_flow(mock_research_connector):
    """Test starting a research flow."""
    manager = ParallelResearchManager(max_concurrent_flows=2)
    
    # Start a research flow
    flow_id = await manager.start_research_flow("test topic")
    
    # Check that the flow was created
    assert flow_id in manager.active_flows
    
    # Wait for the flow to complete
    await asyncio.sleep(0.1)
    
    # Check flow status
    flow_status = manager.get_flow_status(flow_id)
    assert flow_status["status"] == FlowStatus.COMPLETED.value
    
    # Check flow results
    flow_results = manager.get_flow_results(flow_id)
    assert flow_results == MOCK_RESEARCH_RESULTS

@pytest.mark.asyncio
async def test_concurrent_flows(mock_research_connector):
    """Test running multiple concurrent flows."""
    manager = ParallelResearchManager(max_concurrent_flows=2)
    
    # Start multiple flows
    flow_ids = []
    for i in range(5):
        flow_id = await manager.start_research_flow(f"test topic {i}")
        flow_ids.append(flow_id)
    
    # Check that all flows were created
    for flow_id in flow_ids:
        assert flow_id in manager.active_flows
    
    # Wait for flows to complete
    await asyncio.sleep(0.5)
    
    # Check that all flows completed
    for flow_id in flow_ids:
        flow_status = manager.get_flow_status(flow_id)
        assert flow_status["status"] == FlowStatus.COMPLETED.value

@pytest.mark.asyncio
async def test_cancel_flow(mock_research_connector):
    """Test cancelling a research flow."""
    # Make research take longer
    mock_research_connector.return_value.research.side_effect = lambda topic: time.sleep(0.5) or MOCK_RESEARCH_RESULTS
    
    manager = ParallelResearchManager(max_concurrent_flows=2)
    
    # Start a research flow
    flow_id = await manager.start_research_flow("test topic")
    
    # Cancel the flow
    cancelled = await manager.cancel_flow(flow_id)
    assert cancelled is True
    
    # Check flow status
    flow_status = manager.get_flow_status(flow_id)
    assert flow_status["status"] == FlowStatus.CANCELLED.value

@pytest.mark.asyncio
async def test_retry_flow(mock_research_connector):
    """Test retrying a failed research flow."""
    # Make the first research call fail
    mock_research_connector.return_value.research.side_effect = [Exception("Test error"), MOCK_RESEARCH_RESULTS]
    
    manager = ParallelResearchManager(max_concurrent_flows=2)
    
    # Start a research flow that will fail
    flow_id = await manager.start_research_flow("test topic")
    
    # Wait for the flow to fail
    await asyncio.sleep(0.1)
    
    # Check flow status
    flow_status = manager.get_flow_status(flow_id)
    assert flow_status["status"] == FlowStatus.FAILED.value
    
    # Retry the flow
    new_flow_id = await manager.retry_flow(flow_id)
    assert new_flow_id is not None
    assert new_flow_id != flow_id
    
    # Wait for the retry to complete
    await asyncio.sleep(0.1)
    
    # Check new flow status
    new_flow_status = manager.get_flow_status(new_flow_id)
    assert new_flow_status["status"] == FlowStatus.COMPLETED.value

@pytest.mark.asyncio
async def test_continuous_research(mock_research_connector):
    """Test continuous research based on previous results."""
    manager = ParallelResearchManager(max_concurrent_flows=2)
    
    # Start a research flow
    flow_id = await manager.start_research_flow("test topic")
    
    # Wait for the flow to complete
    await asyncio.sleep(0.1)
    
    # Start continuous research
    new_flow_id = await manager.continuous_research(flow_id, "follow-up question")
    assert new_flow_id is not None
    assert new_flow_id != flow_id
    
    # Wait for the continuous research to complete
    await asyncio.sleep(0.1)
    
    # Check new flow status
    new_flow_status = manager.get_flow_status(new_flow_id)
    assert new_flow_status["status"] == FlowStatus.COMPLETED.value
    
    # Check that the previous flow ID is in the metadata
    assert new_flow_status["metadata"]["previous_flow_id"] == flow_id

@pytest.mark.asyncio
async def test_cleanup_completed_flows(mock_research_connector):
    """Test cleaning up completed flows."""
    manager = ParallelResearchManager(max_concurrent_flows=2)
    
    # Start multiple flows
    flow_ids = []
    for i in range(3):
        flow_id = await manager.start_research_flow(f"test topic {i}")
        flow_ids.append(flow_id)
    
    # Wait for flows to complete
    await asyncio.sleep(0.1)
    
    # Manually set the completed_at time to be older
    for flow_id in flow_ids:
        manager.active_flows[flow_id].completed_at = time.time() - 25 * 3600  # 25 hours ago
    
    # Clean up flows
    cleaned_count = await manager.cleanup_completed_flows(max_age_hours=24.0)
    
    # Check that all flows were cleaned up
    assert cleaned_count == 3
    assert len(manager.active_flows) == 0

@pytest.mark.asyncio
async def test_update_progress(mock_research_connector):
    """Test updating the progress of a research flow."""
    # Make research take longer
    mock_research_connector.return_value.research.side_effect = lambda topic: time.sleep(0.5) or MOCK_RESEARCH_RESULTS
    
    manager = ParallelResearchManager(max_concurrent_flows=2)
    
    # Start a research flow
    flow_id = await manager.start_research_flow("test topic")
    
    # Update progress
    updated = await manager.update_progress(flow_id, 0.5)
    assert updated is True
    
    # Check flow progress
    flow_status = manager.get_flow_status(flow_id)
    assert flow_status["progress"] == 0.5

@pytest.mark.asyncio
async def test_add_flow_metadata(mock_research_connector):
    """Test adding metadata to a research flow."""
    manager = ParallelResearchManager(max_concurrent_flows=2)
    
    # Start a research flow
    flow_id = await manager.start_research_flow("test topic")
    
    # Add metadata
    added = await manager.add_flow_metadata(flow_id, "test_key", "test_value")
    assert added is True
    
    # Check flow metadata
    flow_status = manager.get_flow_status(flow_id)
    assert flow_status["metadata"]["test_key"] == "test_value"

@pytest.mark.asyncio
async def test_rate_limiting(mock_research_connector):
    """Test API-specific rate limiting."""
    manager = ParallelResearchManager(max_concurrent_flows=5)
    
    # Configure the semaphore for a specific API to only allow 1 concurrent request
    manager._api_rate_limits[SearchAPI.TAVILY] = asyncio.Semaphore(1)
    
    # Create a configuration that uses the rate-limited API
    config = Configuration(search_api=SearchAPI.TAVILY)
    
    # Start multiple flows with the same API
    flow_ids = []
    start_time = time.time()
    for i in range(3):
        flow_id = await manager.start_research_flow(f"test topic {i}", config)
        flow_ids.append(flow_id)
    
    # Wait for flows to complete
    await asyncio.sleep(0.5)
    
    # Check that all flows completed
    for flow_id in flow_ids:
        flow_status = manager.get_flow_status(flow_id)
        assert flow_status["status"] == FlowStatus.COMPLETED.value

