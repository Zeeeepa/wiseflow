"""
Performance tests for parallel research capabilities.
"""

import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch, AsyncMock

from core.plugins.connectors.research.parallel_manager import ParallelResearchManager
from core.plugins.connectors.research.configuration import Configuration
from core.task_management import TaskPriority


@pytest.fixture
def parallel_manager():
    """Create a parallel research manager for testing."""
    # Reset the singleton instance for each test
    ParallelResearchManager._instance = None
    ParallelResearchManager._initialized = False
    
    # Create a new parallel research manager with higher concurrency for performance testing
    manager = ParallelResearchManager(max_concurrent_research=5)
    
    # Return the manager
    yield manager


async def mock_research_task(sleep_time):
    """Mock research task that sleeps for a specified time."""
    await asyncio.sleep(sleep_time)
    return {"result": f"Completed in {sleep_time} seconds"}


@pytest.mark.asyncio
async def test_parallel_execution_performance(parallel_manager):
    """Test the performance of parallel execution."""
    # Mock the _execute_research method to use our mock_research_task
    async def mock_execute_research(research_id, state, use_multi_agent=False):
        # Sleep for a random time between 0.1 and 0.5 seconds
        sleep_time = 0.1 + (int(research_id[-1]) % 5) * 0.1
        return await mock_research_task(sleep_time)
    
    with patch.object(parallel_manager, '_execute_research', side_effect=mock_execute_research):
        # Create multiple research tasks
        task_ids = []
        for i in range(10):
            task_id = await parallel_manager.create_research_task(
                topic=f"Performance Test {i}",
                priority=TaskPriority.NORMAL
            )
            task_ids.append(task_id)
        
        # Start timing
        start_time = time.time()
        
        # Execute all tasks
        tasks = [
            parallel_manager.task_manager.execute_task(task_id)
            for task_id in task_ids
        ]
        results = await asyncio.gather(*tasks)
        
        # End timing
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Check that all tasks completed
        assert len(results) == 10
        for result in results:
            assert "result" in result
            assert "Completed in" in result["result"]
        
        # Check that the execution time is reasonable
        # With 5 concurrent tasks and each taking 0.1-0.5 seconds,
        # we expect the total time to be around 0.3-0.5 seconds (2 batches)
        assert execution_time < 1.0, f"Execution took too long: {execution_time} seconds"
        
        # Check metrics
        metrics = parallel_manager.get_metrics()
        assert metrics["total_research"] == 10
        assert metrics["completed_research"] == 10


@pytest.mark.asyncio
async def test_concurrent_research_limit(parallel_manager):
    """Test that the concurrent research limit is enforced."""
    # Create a slow mock research task
    async def slow_research_task(research_id, state, use_multi_agent=False):
        await asyncio.sleep(0.5)
        return {"result": "Slow task completed"}
    
    with patch.object(parallel_manager, '_execute_research', side_effect=slow_research_task):
        # Create more tasks than the concurrent limit
        task_ids = []
        for i in range(10):
            task_id = await parallel_manager.create_research_task(
                topic=f"Concurrency Test {i}",
                priority=TaskPriority.NORMAL
            )
            task_ids.append(task_id)
        
        # Start timing
        start_time = time.time()
        
        # Execute all tasks
        tasks = [
            parallel_manager.task_manager.execute_task(task_id)
            for task_id in task_ids
        ]
        
        # Wait for a short time to allow some tasks to start
        await asyncio.sleep(0.1)
        
        # Check that only max_concurrent_research tasks are running
        running_count = sum(1 for research in parallel_manager.active_research.values() if research["status"] == "running")
        assert running_count <= parallel_manager.max_concurrent_research
        
        # Complete all tasks
        results = await asyncio.gather(*tasks)
        
        # End timing
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Check that all tasks completed
        assert len(results) == 10
        for result in results:
            assert "result" in result
            assert "Slow task completed" in result["result"]
        
        # Check that the execution time is reasonable
        # With 5 concurrent tasks and each taking 0.5 seconds,
        # we expect the total time to be around 1.0 seconds (2 batches)
        assert execution_time >= 0.9, f"Execution was too fast: {execution_time} seconds"
        assert execution_time < 1.5, f"Execution took too long: {execution_time} seconds"


@pytest.mark.asyncio
async def test_priority_based_scheduling(parallel_manager):
    """Test that tasks are scheduled based on priority."""
    # Create a list to track execution order
    execution_order = []
    
    # Create a mock research task that records execution order
    async def priority_research_task(research_id, state, use_multi_agent=False):
        execution_order.append(research_id)
        await asyncio.sleep(0.1)
        return {"result": f"Task {research_id} completed"}
    
    with patch.object(parallel_manager, '_execute_research', side_effect=priority_research_task):
        # Create tasks with different priorities
        low_priority_tasks = []
        for i in range(3):
            task_id = await parallel_manager.create_research_task(
                topic=f"Low Priority {i}",
                priority=TaskPriority.LOW
            )
            low_priority_tasks.append(task_id)
        
        normal_priority_tasks = []
        for i in range(3):
            task_id = await parallel_manager.create_research_task(
                topic=f"Normal Priority {i}",
                priority=TaskPriority.NORMAL
            )
            normal_priority_tasks.append(task_id)
        
        high_priority_tasks = []
        for i in range(3):
            task_id = await parallel_manager.create_research_task(
                topic=f"High Priority {i}",
                priority=TaskPriority.HIGH
            )
            high_priority_tasks.append(task_id)
        
        critical_priority_tasks = []
        for i in range(1):
            task_id = await parallel_manager.create_research_task(
                topic=f"Critical Priority {i}",
                priority=TaskPriority.CRITICAL
            )
            critical_priority_tasks.append(task_id)
        
        # Execute all tasks
        all_tasks = low_priority_tasks + normal_priority_tasks + high_priority_tasks + critical_priority_tasks
        tasks = [
            parallel_manager.task_manager.execute_task(task_id)
            for task_id in all_tasks
        ]
        results = await asyncio.gather(*tasks)
        
        # Check that all tasks completed
        assert len(results) == 10
        
        # Check execution order based on research_id in active_research
        # Higher priority tasks should be executed first
        research_ids = list(parallel_manager.active_research.keys())
        critical_research_ids = [rid for rid in research_ids if parallel_manager.active_research[rid]["task_id"] in critical_priority_tasks]
        high_research_ids = [rid for rid in research_ids if parallel_manager.active_research[rid]["task_id"] in high_priority_tasks]
        normal_research_ids = [rid for rid in research_ids if parallel_manager.active_research[rid]["task_id"] in normal_priority_tasks]
        low_research_ids = [rid for rid in research_ids if parallel_manager.active_research[rid]["task_id"] in low_priority_tasks]
        
        # Check that at least some higher priority tasks were executed before lower priority tasks
        # This is a probabilistic test, so we check that the trend is generally correct
        critical_positions = [execution_order.index(rid) for rid in critical_research_ids]
        high_positions = [execution_order.index(rid) for rid in high_research_ids]
        normal_positions = [execution_order.index(rid) for rid in normal_research_ids]
        low_positions = [execution_order.index(rid) for rid in low_research_ids]
        
        # Calculate average position for each priority
        avg_critical = sum(critical_positions) / len(critical_positions) if critical_positions else 0
        avg_high = sum(high_positions) / len(high_positions) if high_positions else 0
        avg_normal = sum(normal_positions) / len(normal_positions) if normal_positions else 0
        avg_low = sum(low_positions) / len(low_positions) if low_positions else 0
        
        # Higher priority tasks should have lower average positions (executed earlier)
        assert avg_critical <= avg_high, f"Critical tasks ({avg_critical}) not executed before high tasks ({avg_high})"
        assert avg_high <= avg_normal, f"High tasks ({avg_high}) not executed before normal tasks ({avg_normal})"
        assert avg_normal <= avg_low, f"Normal tasks ({avg_normal}) not executed before low tasks ({avg_low})"


@pytest.mark.asyncio
async def test_load_testing(parallel_manager):
    """Test the system under load with many concurrent research tasks."""
    # Create a fast mock research task
    async def fast_research_task(research_id, state, use_multi_agent=False):
        await asyncio.sleep(0.05)
        return {"result": "Fast task completed"}
    
    with patch.object(parallel_manager, '_execute_research', side_effect=fast_research_task):
        # Create a large number of tasks
        task_ids = []
        for i in range(50):
            task_id = await parallel_manager.create_research_task(
                topic=f"Load Test {i}",
                priority=TaskPriority.NORMAL
            )
            task_ids.append(task_id)
        
        # Start timing
        start_time = time.time()
        
        # Execute all tasks
        tasks = [
            parallel_manager.task_manager.execute_task(task_id)
            for task_id in task_ids
        ]
        results = await asyncio.gather(*tasks)
        
        # End timing
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Check that all tasks completed
        assert len(results) == 50
        for result in results:
            assert "result" in result
            assert "Fast task completed" in result["result"]
        
        # Check that the execution time is reasonable
        # With 5 concurrent tasks and each taking 0.05 seconds,
        # we expect the total time to be around 0.5 seconds (10 batches)
        assert execution_time < 1.0, f"Execution took too long: {execution_time} seconds"
        
        # Check metrics
        metrics = parallel_manager.get_metrics()
        assert metrics["total_research"] == 50
        assert metrics["completed_research"] == 50


@pytest.mark.asyncio
async def test_benchmark_different_configurations(parallel_manager):
    """Benchmark different configurations for parallel research."""
    # Create a dictionary to store benchmark results
    benchmarks = {}
    
    # Test different concurrency levels
    concurrency_levels = [1, 2, 5, 10]
    
    for concurrency in concurrency_levels:
        # Reset the singleton instance
        ParallelResearchManager._instance = None
        ParallelResearchManager._initialized = False
        
        # Create a new parallel research manager with the current concurrency
        manager = ParallelResearchManager(max_concurrent_research=concurrency)
        
        # Create a mock research task
        async def benchmark_research_task(research_id, state, use_multi_agent=False):
            await asyncio.sleep(0.1)
            return {"result": "Benchmark task completed"}
        
        with patch.object(manager, '_execute_research', side_effect=benchmark_research_task):
            # Create a fixed number of tasks
            task_ids = []
            for i in range(20):
                task_id = await manager.create_research_task(
                    topic=f"Benchmark Test {i}",
                    priority=TaskPriority.NORMAL
                )
                task_ids.append(task_id)
            
            # Start timing
            start_time = time.time()
            
            # Execute all tasks
            tasks = [
                manager.task_manager.execute_task(task_id)
                for task_id in task_ids
            ]
            results = await asyncio.gather(*tasks)
            
            # End timing
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Store benchmark result
            benchmarks[concurrency] = execution_time
    
    # Check that higher concurrency levels result in faster execution
    for i in range(len(concurrency_levels) - 1):
        current_concurrency = concurrency_levels[i]
        next_concurrency = concurrency_levels[i + 1]
        assert benchmarks[current_concurrency] >= benchmarks[next_concurrency], \
            f"Concurrency {next_concurrency} ({benchmarks[next_concurrency]}s) not faster than {current_concurrency} ({benchmarks[current_concurrency]}s)"

