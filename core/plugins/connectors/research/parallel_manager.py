"""Parallel Research Manager for WiseFlow.

This module provides a manager for running multiple research operations in parallel,
with resource management, error handling, and monitoring capabilities.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import threading
import queue
from dataclasses import dataclass, field

from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI
from core.plugins.connectors.research.state import ReportState, Sections
from core.plugins.connectors.research import get_research_graph

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class ResearchTask:
    """A research task to be executed in parallel."""
    task_id: str
    topic: str
    config: Optional[Configuration] = None
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    progress: float = 0.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        """Get the duration of the task in seconds."""
        if self.start_time is None:
            return None
        end = self.end_time or time.time()
        return end - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the task to a dictionary."""
        return {
            "task_id": self.task_id,
            "topic": self.topic,
            "status": self.status,
            "progress": self.progress,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "error": self.error,
            "metadata": self.metadata
        }

class ParallelResearchManager:
    """Manager for parallel research operations.
    
    This class provides capabilities for:
    - Running multiple research operations concurrently
    - Managing resource utilization
    - Handling errors and retries
    - Monitoring progress and status
    - Controlling concurrency levels
    """
    
    def __init__(
        self,
        max_concurrent_tasks: int = 5,
        max_retries: int = 2,
        timeout: int = 600,  # 10 minutes
        resource_limits: Optional[Dict[str, Any]] = None
    ):
        """Initialize the parallel research manager.
        
        Args:
            max_concurrent_tasks: Maximum number of concurrent research tasks
            max_retries: Maximum number of retries for failed tasks
            timeout: Timeout in seconds for research tasks
            resource_limits: Optional resource limits configuration
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_retries = max_retries
        self.timeout = timeout
        self.resource_limits = resource_limits or {}
        
        # Task management
        self.tasks: Dict[str, ResearchTask] = {}
        self.task_queue = queue.Queue()
        self.active_tasks = 0
        self.lock = threading.RLock()
        
        # Resource tracking
        self.api_usage: Dict[str, int] = {}
        self.api_last_reset: Dict[str, float] = {}
        
        # Worker thread
        self.worker_thread = None
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_tasks)
        
        # Event loop for async operations
        self.loop = asyncio.new_event_loop()
    
    def start(self):
        """Start the parallel research manager."""
        if self.running:
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        logger.info("Parallel research manager started")
    
    def stop(self):
        """Stop the parallel research manager."""
        if not self.running:
            return
        
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        
        self.executor.shutdown(wait=False)
        logger.info("Parallel research manager stopped")
    
    def _worker_loop(self):
        """Main worker loop for processing research tasks."""
        while self.running:
            try:
                # Check if we can process more tasks
                with self.lock:
                    can_process = self.active_tasks < self.max_concurrent_tasks
                
                if can_process:
                    try:
                        # Get a task from the queue (non-blocking)
                        task_id = self.task_queue.get(block=False)
                        self._process_task(task_id)
                    except queue.Empty:
                        # No tasks in queue, sleep briefly
                        time.sleep(0.1)
                else:
                    # At max capacity, sleep briefly
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in worker loop: {str(e)}")
                time.sleep(1)  # Sleep on error to prevent tight loop
    
    def _process_task(self, task_id: str):
        """Process a research task.
        
        Args:
            task_id: ID of the task to process
        """
        with self.lock:
            if task_id not in self.tasks:
                logger.warning(f"Task {task_id} not found")
                return
            
            task = self.tasks[task_id]
            if task.status != "pending":
                logger.warning(f"Task {task_id} is not pending (status: {task.status})")
                return
            
            task.status = "running"
            task.start_time = time.time()
            self.active_tasks += 1
        
        # Submit task to executor
        self.executor.submit(self._execute_task, task_id)
    
    def _execute_task(self, task_id: str):
        """Execute a research task in the thread pool.
        
        Args:
            task_id: ID of the task to execute
        """
        with self.lock:
            if task_id not in self.tasks:
                logger.warning(f"Task {task_id} not found during execution")
                self.active_tasks -= 1
                return
            
            task = self.tasks[task_id]
        
        try:
            # Run the research task
            result = self._run_research(task.topic, task.config)
            
            # Update task with result
            with self.lock:
                task.status = "completed"
                task.result = result
                task.end_time = time.time()
                task.progress = 1.0
                self.active_tasks -= 1
            
            logger.info(f"Task {task_id} completed successfully")
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {str(e)}")
            
            # Update task with error
            with self.lock:
                task.status = "failed"
                task.error = str(e)
                task.end_time = time.time()
                self.active_tasks -= 1
    
    def _run_research(self, topic: str, config: Optional[Configuration] = None) -> Dict[str, Any]:
        """Run a research operation.
        
        Args:
            topic: The topic to research
            config: Optional configuration for the research
            
        Returns:
            Dict[str, Any]: The research results
        """
        # Get the appropriate research graph
        graph = get_research_graph(config)
        
        # Initialize the state
        state = ReportState(
            topic=topic,
            sections=Sections(sections=[]),
            queries=[],
            search_results=[],
            feedback=None,
            config=config
        )
        
        # Run the research graph
        future = asyncio.run_coroutine_threadsafe(
            self._run_graph_with_timeout(graph, state),
            self.loop
        )
        result = future.result(timeout=self.timeout)
        
        # Format the results
        from core.plugins.connectors.research.utils import format_sections
        formatted_sections = format_sections(result.sections)
        
        return {
            "topic": topic,
            "sections": formatted_sections,
            "raw_sections": result.sections,
            "metadata": {
                "search_api": config.search_api.value if config else "tavily",
                "research_mode": config.research_mode.value if config else "linear",
                "search_depth": config.max_search_depth if config else 2,
                "queries_per_iteration": config.number_of_queries if config else 2
            }
        }
    
    async def _run_graph_with_timeout(self, graph, state):
        """Run a research graph with timeout.
        
        Args:
            graph: The research graph to run
            state: The initial state
            
        Returns:
            The result state
        """
        return await asyncio.wait_for(
            graph.ainvoke(state),
            timeout=self.timeout
        )
    
    def submit_task(self, topic: str, config: Optional[Configuration] = None, task_id: Optional[str] = None) -> str:
        """Submit a research task for parallel execution.
        
        Args:
            topic: The topic to research
            config: Optional configuration for the research
            task_id: Optional task ID (generated if not provided)
            
        Returns:
            str: The task ID
        """
        # Generate task ID if not provided
        if task_id is None:
            import uuid
            task_id = str(uuid.uuid4())
        
        # Create task
        task = ResearchTask(
            task_id=task_id,
            topic=topic,
            config=config
        )
        
        # Add task to manager
        with self.lock:
            self.tasks[task_id] = task
            self.task_queue.put(task_id)
        
        logger.info(f"Task {task_id} submitted for topic: {topic}")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a research task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Optional[Dict[str, Any]]: Task information or None if not found
        """
        with self.lock:
            if task_id not in self.tasks:
                return None
            
            return self.tasks[task_id].to_dict()
    
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the result of a completed research task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Optional[Dict[str, Any]]: Task result or None if not completed or not found
        """
        with self.lock:
            if task_id not in self.tasks:
                return None
            
            task = self.tasks[task_id]
            if task.status != "completed":
                return None
            
            return task.result
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a research task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            bool: True if the task was cancelled, False otherwise
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            if task.status in ["completed", "failed"]:
                return False
            
            # If the task is pending, remove it from the queue
            if task.status == "pending":
                # Note: This is not efficient for large queues, but should be fine for our use case
                with self.task_queue.mutex:
                    if task_id in self.task_queue.queue:
                        self.task_queue.queue.remove(task_id)
            
            # Mark the task as failed
            task.status = "failed"
            task.error = "Task cancelled by user"
            task.end_time = time.time()
            
            # If the task was running, decrement active tasks
            if task.status == "running":
                self.active_tasks -= 1
            
            return True
    
    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all research tasks, optionally filtered by status.
        
        Args:
            status: Optional status filter (pending, running, completed, failed)
            
        Returns:
            List[Dict[str, Any]]: List of task information
        """
        with self.lock:
            if status:
                return [task.to_dict() for task in self.tasks.values() if task.status == status]
            else:
                return [task.to_dict() for task in self.tasks.values()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the parallel research manager.
        
        Returns:
            Dict[str, Any]: Statistics about tasks and resource usage
        """
        with self.lock:
            total_tasks = len(self.tasks)
            pending_tasks = sum(1 for task in self.tasks.values() if task.status == "pending")
            running_tasks = sum(1 for task in self.tasks.values() if task.status == "running")
            completed_tasks = sum(1 for task in self.tasks.values() if task.status == "completed")
            failed_tasks = sum(1 for task in self.tasks.values() if task.status == "failed")
            
            # Calculate average duration for completed tasks
            completed_durations = [task.duration for task in self.tasks.values() 
                                if task.status == "completed" and task.duration is not None]
            avg_duration = sum(completed_durations) / len(completed_durations) if completed_durations else 0
            
            return {
                "total_tasks": total_tasks,
                "pending_tasks": pending_tasks,
                "running_tasks": running_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "active_tasks": self.active_tasks,
                "queue_size": self.task_queue.qsize(),
                "avg_duration": avg_duration,
                "api_usage": self.api_usage
            }
    
    def clear_completed_tasks(self, max_age: Optional[float] = None) -> int:
        """Clear completed and failed tasks from the manager.
        
        Args:
            max_age: Optional maximum age in seconds (only clear tasks older than this)
            
        Returns:
            int: Number of tasks cleared
        """
        with self.lock:
            current_time = time.time()
            task_ids_to_remove = []
            
            for task_id, task in self.tasks.items():
                if task.status in ["completed", "failed"]:
                    if max_age is None or (task.end_time and current_time - task.end_time > max_age):
                        task_ids_to_remove.append(task_id)
            
            for task_id in task_ids_to_remove:
                del self.tasks[task_id]
            
            return len(task_ids_to_remove)
    
    def batch_submit(self, topics: List[str], config: Optional[Configuration] = None) -> List[str]:
        """Submit multiple research tasks in batch.
        
        Args:
            topics: List of topics to research
            config: Optional configuration for the research (applied to all tasks)
            
        Returns:
            List[str]: List of task IDs
        """
        task_ids = []
        for topic in topics:
            task_id = self.submit_task(topic, config)
            task_ids.append(task_id)
        
        return task_ids
    
    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Wait for a task to complete.
        
        Args:
            task_id: ID of the task to wait for
            timeout: Optional timeout in seconds
            
        Returns:
            Optional[Dict[str, Any]]: Task result or None if timeout or task not found
        """
        start_time = time.time()
        while True:
            with self.lock:
                if task_id not in self.tasks:
                    return None
                
                task = self.tasks[task_id]
                if task.status in ["completed", "failed"]:
                    return task.to_dict()
            
            # Check timeout
            if timeout is not None and time.time() - start_time > timeout:
                return None
            
            # Sleep briefly to avoid tight loop
            time.sleep(0.1)
    
    def wait_for_tasks(self, task_ids: List[str], timeout: Optional[float] = None) -> Dict[str, Dict[str, Any]]:
        """Wait for multiple tasks to complete.
        
        Args:
            task_ids: List of task IDs to wait for
            timeout: Optional timeout in seconds
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of task results by task ID
        """
        results = {}
        remaining_ids = set(task_ids)
        start_time = time.time()
        
        while remaining_ids:
            # Check each remaining task
            for task_id in list(remaining_ids):
                with self.lock:
                    if task_id not in self.tasks:
                        remaining_ids.remove(task_id)
                        continue
                    
                    task = self.tasks[task_id]
                    if task.status in ["completed", "failed"]:
                        results[task_id] = task.to_dict()
                        remaining_ids.remove(task_id)
            
            # Check timeout
            if timeout is not None and time.time() - start_time > timeout:
                break
            
            # If tasks remain, sleep briefly
            if remaining_ids:
                time.sleep(0.1)
        
        return results
    
    def update_task_progress(self, task_id: str, progress: float) -> bool:
        """Update the progress of a task.
        
        Args:
            task_id: ID of the task
            progress: Progress value (0.0 to 1.0)
            
        Returns:
            bool: True if the task was updated, False otherwise
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            if task.status != "running":
                return False
            
            task.progress = max(0.0, min(1.0, progress))
            return True
    
    def update_task_metadata(self, task_id: str, metadata: Dict[str, Any]) -> bool:
        """Update the metadata of a task.
        
        Args:
            task_id: ID of the task
            metadata: Metadata to update
            
        Returns:
            bool: True if the task was updated, False otherwise
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            task.metadata.update(metadata)
            return True
    
    def retry_task(self, task_id: str) -> bool:
        """Retry a failed task.
        
        Args:
            task_id: ID of the task to retry
            
        Returns:
            bool: True if the task was retried, False otherwise
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            if task.status != "failed":
                return False
            
            # Reset task state
            task.status = "pending"
            task.error = None
            task.start_time = None
            task.end_time = None
            task.progress = 0.0
            task.result = None
            
            # Add back to queue
            self.task_queue.put(task_id)
            return True
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

# Singleton instance
_instance = None

def get_parallel_research_manager(
    max_concurrent_tasks: int = 5,
    max_retries: int = 2,
    timeout: int = 600,
    resource_limits: Optional[Dict[str, Any]] = None
) -> ParallelResearchManager:
    """Get the singleton instance of the parallel research manager.
    
    Args:
        max_concurrent_tasks: Maximum number of concurrent research tasks
        max_retries: Maximum number of retries for failed tasks
        timeout: Timeout in seconds for research tasks
        resource_limits: Optional resource limits configuration
        
    Returns:
        ParallelResearchManager: The parallel research manager instance
    """
    global _instance
    if _instance is None:
        _instance = ParallelResearchManager(
            max_concurrent_tasks=max_concurrent_tasks,
            max_retries=max_retries,
            timeout=timeout,
            resource_limits=resource_limits
        )
        _instance.start()
    return _instance

