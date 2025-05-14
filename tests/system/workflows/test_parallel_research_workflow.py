"""
System tests for parallel research workflows.
"""

import pytest
import time
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import threading
import concurrent.futures

from fastapi.testclient import TestClient
from api_server import app as api_app

from core.plugins.connectors.research.parallel_manager import (
    ParallelResearchManager,
    get_parallel_research_manager
)
from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI
from core.plugins.connectors.research.state import ReportState, Sections

@pytest.mark.system
@pytest.mark.workflow
class TestParallelResearchWorkflow:
    """System tests for parallel research workflows."""
    
    @pytest.fixture
    def mock_research_graph(self):
        """Create a mock research graph with realistic behavior."""
        with patch("core.plugins.connectors.research.parallel_manager.get_research_graph") as mock:
            async def mock_ainvoke(state):
                # Simulate realistic processing time and behavior
                mode = state.config.research_mode if state.config else ResearchMode.LINEAR
                
                # Different processing times based on mode
                if mode == ResearchMode.MULTI_AGENT:
                    await asyncio.sleep(0.5)
                elif mode == ResearchMode.GRAPH:
                    await asyncio.sleep(0.3)
                else:
                    await asyncio.sleep(0.2)
                
                # Create some sample sections based on the topic
                sections = []
                sections.append({
                    "title": "Introduction",
                    "content": f"This is an introduction to {state.topic}.",
                    "subsections": []
                })
                
                sections.append({
                    "title": "Main Findings",
                    "content": f"These are the main findings about {state.topic}.",
                    "subsections": [
                        {
                            "title": "Key Aspect 1",
                            "content": f"This is a key aspect of {state.topic}."
                        },
                        {
                            "title": "Key Aspect 2",
                            "content": f"This is another key aspect of {state.topic}."
                        }
                    ]
                })
                
                sections.append({
                    "title": "Conclusion",
                    "content": f"This is the conclusion about {state.topic}.",
                    "subsections": []
                })
                
                # Update the state with the sections
                state.sections = Sections(sections=sections)
                
                # Add some sample queries and search results
                state.queries = [
                    {"text": f"information about {state.topic}", "metadata": {}},
                    {"text": f"latest research on {state.topic}", "metadata": {}}
                ]
                
                state.search_results = [
                    {
                        "query": f"information about {state.topic}",
                        "results": [
                            {"title": "Result 1", "url": "https://example.com/1", "content": "Sample content 1"},
                            {"title": "Result 2", "url": "https://example.com/2", "content": "Sample content 2"}
                        ],
                        "metadata": {}
                    },
                    {
                        "query": f"latest research on {state.topic}",
                        "results": [
                            {"title": "Result 3", "url": "https://example.com/3", "content": "Sample content 3"},
                            {"title": "Result 4", "url": "https://example.com/4", "content": "Sample content 4"}
                        ],
                        "metadata": {}
                    }
                ]
                
                return state
            
            graph = AsyncMock()
            graph.ainvoke.side_effect = mock_ainvoke
            mock.return_value = graph
            yield mock
    
    @pytest.fixture
    def manager(self, mock_research_graph):
        """Create a ParallelResearchManager instance for testing."""
        manager = ParallelResearchManager(
            max_concurrent_tasks=5,
            max_retries=2,
            timeout=10
        )
        manager.start()
        yield manager
        manager.stop()
    
    @pytest.fixture
    def api_client(self, test_env_vars):
        """Create a FastAPI TestClient for the API server."""
        return TestClient(api_app)
    
    def test_end_to_end_single_research(self, manager):
        """Test end-to-end workflow for a single research task."""
        # Submit a research task
        topic = "artificial intelligence"
        config = Configuration(
            research_mode=ResearchMode.LINEAR,
            search_api=SearchAPI.TAVILY,
            max_search_depth=2,
            number_of_queries=2
        )
        
        task_id = manager.submit_task(topic, config)
        
        # Wait for the task to complete
        task_info = manager.wait_for_task(task_id, timeout=5)
        
        # Check that the task completed successfully
        assert task_info["status"] == "completed"
        assert task_info["error"] is None
        
        # Get the task result
        result = manager.get_task_result(task_id)
        
        # Check the result structure
        assert result is not None
        assert result["topic"] == topic
        assert "sections" in result
        assert len(result["sections"]) > 0
        assert "metadata" in result
        assert result["metadata"]["research_mode"] == "linear"
        assert result["metadata"]["search_api"] == "tavily"
    
    def test_end_to_end_parallel_research(self, manager):
        """Test end-to-end workflow for parallel research tasks."""
        # Submit multiple research tasks
        topics = ["artificial intelligence", "machine learning", "deep learning"]
        config = Configuration(
            research_mode=ResearchMode.LINEAR,
            search_api=SearchAPI.TAVILY,
            max_search_depth=2,
            number_of_queries=2
        )
        
        task_ids = manager.batch_submit(topics)
        
        # Wait for all tasks to complete
        results = manager.wait_for_tasks(task_ids, timeout=10)
        
        # Check that all tasks completed successfully
        assert len(results) == len(topics)
        for task_id, task_info in results.items():
            assert task_info["status"] == "completed"
            assert task_info["error"] is None
            
            # Get the task result
            result = manager.get_task_result(task_id)
            
            # Check the result structure
            assert result is not None
            assert result["topic"] in topics
            assert "sections" in result
            assert len(result["sections"]) > 0
            assert "metadata" in result
    
    def test_different_research_modes_workflow(self, manager):
        """Test workflow with different research modes."""
        # Submit tasks with different research modes
        linear_config = Configuration(research_mode=ResearchMode.LINEAR)
        graph_config = Configuration(research_mode=ResearchMode.GRAPH)
        multi_agent_config = Configuration(research_mode=ResearchMode.MULTI_AGENT)
        
        linear_task_id = manager.submit_task("linear research", linear_config)
        graph_task_id = manager.submit_task("graph research", graph_config)
        multi_agent_task_id = manager.submit_task("multi-agent research", multi_agent_config)
        
        # Wait for all tasks to complete
        task_ids = [linear_task_id, graph_task_id, multi_agent_task_id]
        results = manager.wait_for_tasks(task_ids, timeout=10)
        
        # Check that all tasks completed successfully
        assert len(results) == 3
        
        # Check the results for each mode
        for task_id in task_ids:
            result = manager.get_task_result(task_id)
            assert result is not None
            
            # Check that the research mode in the result matches the configuration
            if task_id == linear_task_id:
                assert result["metadata"]["research_mode"] == "linear"
            elif task_id == graph_task_id:
                assert result["metadata"]["research_mode"] == "graph"
            elif task_id == multi_agent_task_id:
                assert result["metadata"]["research_mode"] == "multi_agent"
    
    def test_api_integration_workflow(self, api_client, mock_research_graph):
        """Test workflow through the API endpoints."""
        # Mock the parallel_research_manager module
        with patch("api_server.get_parallel_research_manager") as mock_get_manager:
            # Create a mock manager
            mock_manager = MagicMock()
            
            # Mock the research method
            async def mock_research(**kwargs):
                await asyncio.sleep(0.2)
                return {
                    "topic": kwargs["topic"],
                    "sections": [
                        {"title": "Introduction", "content": "This is an introduction."},
                        {"title": "Main Findings", "content": "These are the main findings."},
                        {"title": "Conclusion", "content": "This is the conclusion."}
                    ],
                    "metadata": {
                        "search_api": kwargs["search_api"],
                        "research_mode": kwargs["research_mode"],
                        "search_depth": kwargs["max_search_depth"],
                        "queries_per_iteration": kwargs["number_of_queries"]
                    }
                }
            
            mock_manager.research = AsyncMock(side_effect=mock_research)
            
            # Mock the parallel_research method
            async def mock_parallel_research(**kwargs):
                await asyncio.sleep(0.5)
                results = []
                for topic in kwargs["topics"]:
                    results.append({
                        "topic": topic,
                        "sections": [
                            {"title": "Introduction", "content": f"This is an introduction to {topic}."},
                            {"title": "Main Findings", "content": f"These are the main findings about {topic}."},
                            {"title": "Conclusion", "content": f"This is the conclusion about {topic}."}
                        ],
                        "metadata": {
                            "search_api": kwargs["search_api"],
                            "research_mode": kwargs["research_mode"],
                            "search_depth": kwargs["max_search_depth"],
                            "queries_per_iteration": kwargs["number_of_queries"]
                        }
                    })
                return {
                    "results": results,
                    "summary": f"Completed research on {len(kwargs['topics'])} topics."
                }
            
            mock_manager.parallel_research = AsyncMock(side_effect=mock_parallel_research)
            
            # Mock the get_task_status method
            async def mock_get_task_status(**kwargs):
                return {
                    "task_id": kwargs["task_id"],
                    "status": "completed",
                    "progress": 1.0,
                    "start_time": time.time() - 1,
                    "end_time": time.time(),
                    "duration": 1.0,
                    "error": None,
                    "metadata": {}
                }
            
            mock_manager.get_task_status = AsyncMock(side_effect=mock_get_task_status)
            
            # Set the mock manager
            mock_get_manager.return_value = mock_manager
            
            # Test the research endpoint
            response = api_client.post(
                "/api/v1/integration/research",
                headers={"X-API-Key": "test-api-key"},
                json={
                    "topic": "artificial intelligence",
                    "search_api": "tavily",
                    "research_mode": "linear",
                    "max_search_depth": 2,
                    "number_of_queries": 2
                }
            )
            
            # Check the response
            assert response.status_code == 200
            result = response.json()
            assert result["topic"] == "artificial intelligence"
            assert len(result["sections"]) == 3
            assert result["metadata"]["search_api"] == "tavily"
            assert result["metadata"]["research_mode"] == "linear"
            
            # Test the parallel research endpoint
            response = api_client.post(
                "/api/v1/integration/parallel-research",
                headers={"X-API-Key": "test-api-key"},
                json={
                    "topics": ["artificial intelligence", "machine learning", "deep learning"],
                    "search_api": "tavily",
                    "research_mode": "linear",
                    "max_search_depth": 2,
                    "number_of_queries": 2,
                    "max_concurrent_tasks": 3
                }
            )
            
            # Check the response
            assert response.status_code == 200
            result = response.json()
            assert "results" in result
            assert len(result["results"]) == 3
            assert "summary" in result
            
            # Test the task status endpoint
            response = api_client.post(
                "/api/v1/integration/task-status",
                headers={"X-API-Key": "test-api-key"},
                json={
                    "task_id": "test-task-id"
                }
            )
            
            # Check the response
            assert response.status_code == 200
            result = response.json()
            assert result["task_id"] == "test-task-id"
            assert result["status"] == "completed"
    
    def test_cancel_and_retry_workflow(self, manager):
        """Test workflow with task cancellation and retry."""
        # Submit a task
        task_id = manager.submit_task("cancel and retry topic")
        
        # Cancel the task
        result = manager.cancel_task(task_id)
        assert result is True
        
        # Check that the task was cancelled
        task_info = manager.get_task(task_id)
        assert task_info["status"] == "failed"
        assert "cancelled" in task_info["error"].lower()
        
        # Retry the task
        result = manager.retry_task(task_id)
        assert result is True
        
        # Wait for the task to complete
        task_info = manager.wait_for_task(task_id, timeout=5)
        
        # Check that the retry succeeded
        assert task_info["status"] == "completed"
        assert task_info["error"] is None
        
        # Get the task result
        result = manager.get_task_result(task_id)
        assert result is not None
        assert result["topic"] == "cancel and retry topic"
    
    def test_resource_management_workflow(self, manager):
        """Test workflow with resource management."""
        # Set a low max_concurrent_tasks
        manager.max_concurrent_tasks = 2
        
        # Submit more tasks than can be processed concurrently
        task_ids = manager.batch_submit([f"resource topic {i}" for i in range(5)])
        
        # Check initial stats
        stats = manager.get_stats()
        assert stats["total_tasks"] == 5
        assert stats["running_tasks"] <= 2  # Should be limited by max_concurrent_tasks
        assert stats["pending_tasks"] >= 3  # At least 3 should be pending
        
        # Wait for all tasks to complete
        results = manager.wait_for_tasks(task_ids, timeout=10)
        
        # Check final stats
        stats = manager.get_stats()
        assert stats["total_tasks"] == 5
        assert stats["completed_tasks"] == 5
        assert stats["running_tasks"] == 0
        assert stats["pending_tasks"] == 0
        
        # Clear completed tasks
        cleared = manager.clear_completed_tasks()
        assert cleared == 5
        
        # Check that tasks were cleared
        stats = manager.get_stats()
        assert stats["total_tasks"] == 0

