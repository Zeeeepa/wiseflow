"""
System tests for parallel research performance.
"""

import pytest
import time
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import threading
import concurrent.futures

from core.plugins.connectors.research.parallel_manager import (
    ParallelResearchManager,
    get_parallel_research_manager
)
from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI
from core.plugins.connectors.research.state import ReportState, Sections

@pytest.mark.system
@pytest.mark.performance
@pytest.mark.slow
class TestParallelResearchPerformance:
    """System tests for parallel research performance."""
    
    @pytest.fixture
    def mock_research_graph(self):
        """Create a mock research graph with controlled response times."""
        with patch("core.plugins.connectors.research.parallel_manager.get_research_graph") as mock:
            async def mock_ainvoke(state):
                # Simulate processing time based on research mode
                if state.config and state.config.research_mode == ResearchMode.MULTI_AGENT:
                    await asyncio.sleep(0.5)  # Slower for multi-agent
                elif state.config and state.config.research_mode == ResearchMode.GRAPH:
                    await asyncio.sleep(0.3)  # Medium for graph
                else:
                    await asyncio.sleep(0.1)  # Faster for linear
                
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
            max_retries=1,
            timeout=10
        )
        manager.start()
        yield manager
        manager.stop()
    
    def test_single_task_performance(self, manager):
        """Test the performance of a single research task."""
        # Submit a task
        start_time = time.time()
        task_id = manager.submit_task("test topic")
        
        # Wait for the task to complete
        task_info = manager.wait_for_task(task_id, timeout=5)
        end_time = time.time()
        
        # Check that the task completed
        assert task_info is not None
        assert task_info["status"] == "completed"
        
        # Check the performance
        duration = end_time - start_time
        assert duration < 1.0, f"Single task took too long: {duration:.2f} seconds"
    
    def test_multiple_sequential_tasks_performance(self, manager):
        """Test the performance of multiple sequential research tasks."""
        # Submit multiple tasks sequentially
        start_time = time.time()
        task_ids = []
        for i in range(3):
            task_id = manager.submit_task(f"test topic {i}")
            task_ids.append(task_id)
            # Wait for each task to complete before submitting the next
            manager.wait_for_task(task_id, timeout=5)
        
        end_time = time.time()
        
        # Check that all tasks completed
        for task_id in task_ids:
            task_info = manager.get_task(task_id)
            assert task_info["status"] == "completed"
        
        # Check the performance
        duration = end_time - start_time
        assert duration < 3.0, f"Sequential tasks took too long: {duration:.2f} seconds"
    
    def test_multiple_parallel_tasks_performance(self, manager):
        """Test the performance of multiple parallel research tasks."""
        # Submit multiple tasks in parallel
        start_time = time.time()
        task_ids = manager.batch_submit([f"test topic {i}" for i in range(5)])
        
        # Wait for all tasks to complete
        results = manager.wait_for_tasks(task_ids, timeout=5)
        end_time = time.time()
        
        # Check that all tasks completed
        assert len(results) == 5
        for task_id, result in results.items():
            assert result["status"] == "completed"
        
        # Check the performance
        duration = end_time - start_time
        assert duration < 2.0, f"Parallel tasks took too long: {duration:.2f} seconds"
    
    def test_mixed_research_modes_performance(self, manager):
        """Test the performance with different research modes."""
        # Submit tasks with different research modes
        start_time = time.time()
        
        # Linear mode (fastest)
        linear_config = Configuration(research_mode=ResearchMode.LINEAR)
        linear_task_id = manager.submit_task("linear topic", config=linear_config)
        
        # Graph mode (medium)
        graph_config = Configuration(research_mode=ResearchMode.GRAPH)
        graph_task_id = manager.submit_task("graph topic", config=graph_config)
        
        # Multi-agent mode (slowest)
        multi_agent_config = Configuration(research_mode=ResearchMode.MULTI_AGENT)
        multi_agent_task_id = manager.submit_task("multi-agent topic", config=multi_agent_config)
        
        # Wait for all tasks to complete
        results = manager.wait_for_tasks([linear_task_id, graph_task_id, multi_agent_task_id], timeout=5)
        end_time = time.time()
        
        # Check that all tasks completed
        assert len(results) == 3
        
        # Check the performance
        duration = end_time - start_time
        assert duration < 2.0, f"Mixed research modes took too long: {duration:.2f} seconds"
        
        # Check that the tasks completed in the expected order (linear first, multi-agent last)
        linear_end_time = results[linear_task_id]["end_time"]
        graph_end_time = results[graph_task_id]["end_time"]
        multi_agent_end_time = results[multi_agent_task_id]["end_time"]
        
        assert linear_end_time <= graph_end_time
        assert graph_end_time <= multi_agent_end_time
    
    def test_resource_contention_performance(self, manager):
        """Test performance under resource contention."""
        # Submit more tasks than the max_concurrent_tasks
        start_time = time.time()
        task_ids = manager.batch_submit([f"test topic {i}" for i in range(10)])
        
        # Wait for all tasks to complete
        results = manager.wait_for_tasks(task_ids, timeout=10)
        end_time = time.time()
        
        # Check that all tasks completed
        assert len(results) == 10
        for task_id, result in results.items():
            assert result["status"] == "completed"
        
        # Check the performance
        duration = end_time - start_time
        assert duration < 5.0, f"Resource contention test took too long: {duration:.2f} seconds"
    
    def test_concurrent_api_requests_performance(self, mock_research_graph):
        """Test performance of concurrent API requests."""
        # Create a fresh manager for this test
        manager = ParallelResearchManager(
            max_concurrent_tasks=10,
            max_retries=1,
            timeout=10
        )
        manager.start()
        
        try:
            # Number of concurrent requests
            num_requests = 10
            
            # Function to submit a task and wait for it
            def submit_and_wait():
                task_id = manager.submit_task(f"concurrent topic {threading.get_ident()}")
                return manager.wait_for_task(task_id, timeout=5)
            
            # Use ThreadPoolExecutor to make concurrent requests
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
                futures = [executor.submit(submit_and_wait) for _ in range(num_requests)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            end_time = time.time()
            
            # Check that all tasks completed
            assert len(results) == num_requests
            for result in results:
                assert result["status"] == "completed"
            
            # Check the performance
            duration = end_time - start_time
            assert duration < 5.0, f"Concurrent API requests took too long: {duration:.2f} seconds"
        finally:
            manager.stop()
    
    def test_error_handling_performance(self, manager):
        """Test performance of error handling and retries."""
        # Patch the _run_research method to simulate errors
        original_run_research = manager._run_research
        error_count = 0
        
        def mock_run_research(topic, config=None):
            nonlocal error_count
            if error_count < 1:  # Fail the first attempt
                error_count += 1
                raise Exception("Simulated error")
            return original_run_research(topic, config)
        
        manager._run_research = mock_run_research
        
        try:
            # Submit a task that will fail on first attempt
            start_time = time.time()
            task_id = manager.submit_task("error topic")
            
            # Wait for the task to complete or fail
            task_info = manager.wait_for_task(task_id, timeout=5)
            
            # Retry the task
            if task_info["status"] == "failed":
                manager.retry_task(task_id)
                task_info = manager.wait_for_task(task_id, timeout=5)
            
            end_time = time.time()
            
            # Check the performance
            duration = end_time - start_time
            assert duration < 3.0, f"Error handling and retry took too long: {duration:.2f} seconds"
            
            # Check that the task eventually completed
            assert task_info["status"] == "completed"
        finally:
            # Restore the original method
            manager._run_research = original_run_research
    
    def test_long_running_task_timeout(self, manager):
        """Test timeout handling for long-running tasks."""
        # Patch the _run_graph_with_timeout method to simulate a long-running task
        original_run_graph = manager._run_graph_with_timeout
        
        async def mock_run_graph_with_timeout(graph, state):
            await asyncio.sleep(10)  # Sleep longer than the timeout
            return state
        
        manager._run_graph_with_timeout = mock_run_graph_with_timeout
        
        try:
            # Set a short timeout for this test
            manager.timeout = 1
            
            # Submit a task that will timeout
            start_time = time.time()
            task_id = manager.submit_task("timeout topic")
            
            # Wait for the task to fail
            task_info = manager.wait_for_task(task_id, timeout=5)
            end_time = time.time()
            
            # Check the performance
            duration = end_time - start_time
            assert duration < 3.0, f"Timeout handling took too long: {duration:.2f} seconds"
            
            # Check that the task failed with a timeout error
            assert task_info["status"] == "failed"
            assert "timeout" in task_info["error"].lower() or "timed out" in task_info["error"].lower()
        finally:
            # Restore the original method and timeout
            manager._run_graph_with_timeout = original_run_graph
            manager.timeout = 10

