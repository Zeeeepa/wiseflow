"""
Thread pool manager for WiseFlow.

This module provides a thread pool manager for executing tasks concurrently.
"""

import os
import time
import asyncio
import logging
import uuid
import concurrent.futures
import traceback
from typing import Dict, Any, Optional, Callable, List, Set, Union, Awaitable
from datetime import datetime
from enum import Enum, auto

from core.config import config
from core.task_manager import TaskPriority, TaskStatus
from core.event_system import (
    EventType, Event, publish_sync,
    create_task_event
)
from core.utils.error_handling import handle_exceptions, TaskError

logger = logging.getLogger(__name__)

class ThreadPoolManager:
    """
    Thread pool manager for WiseFlow.
    
    This class provides a thread pool for executing CPU-bound tasks concurrently.
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(ThreadPoolManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, max_workers=None, min_workers=None):
        """Initialize the thread pool manager."""
        if self._initialized:
            return
            
        self.max_workers = max_workers or config.get("MAX_THREAD_WORKERS", os.cpu_count() or 4)
        self.min_workers = min_workers or config.get("MIN_THREAD_WORKERS", 2)
        
        # Ensure min_workers is at least 1 and max_workers is at least min_workers
        self.min_workers = max(1, self.min_workers)
        self.max_workers = max(self.min_workers, self.max_workers)
        
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.futures: Dict[str, concurrent.futures.Future] = {}
        
        # Track resource usage
        self.active_workers = 0
        self.queue_size = 0
        self.last_adjustment_time = datetime.now()
        self.adjustment_cooldown = 60  # seconds between worker count adjustments
        
        self._initialized = True
        
        logger.info(f"Thread pool manager initialized with {self.min_workers}-{self.max_workers} workers")
    
    def submit(
        self,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        name: str = "Unnamed Task",
        priority: TaskPriority = TaskPriority.NORMAL,
        **kwargs
    ) -> str:
        """
        Submit a task to the thread pool.
        
        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            task_id: Optional task ID, if not provided a new one will be generated
            name: Name of the task
            priority: Priority of the task
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Task ID
        """
        task_id = task_id or str(uuid.uuid4())
        
        # Create task
        task = {
            "task_id": task_id,
            "name": name,
            "func": func,
            "args": args,
            "kwargs": kwargs,
            "priority": priority,
            "status": TaskStatus.PENDING,
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
            "resource_usage": {
                "cpu_time": 0,
                "memory_peak": 0
            }
        }
        
        # Add task to manager
        self.tasks[task_id] = task
        
        try:
            # Submit task to executor
            future = self.executor.submit(self._execute_task_wrapper, task_id, func, *args, **kwargs)
            self.futures[task_id] = future
            
            # Update task status
            task["status"] = TaskStatus.RUNNING
            task["started_at"] = datetime.now()
            
            # Update active workers count
            self.active_workers += 1
            
            # Add callback to handle completion
            future.add_done_callback(lambda f: self._handle_completion(task_id, f))
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_CREATED,
                    task_id,
                    {"name": name, "priority": priority.name}
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task created event: {e}")
            
            logger.info(f"Task submitted to thread pool: {task_id} ({name})")
            return task_id
        except Exception as e:
            # Update task status on error
            task["status"] = TaskStatus.FAILED
            task["error"] = str(e)
            task["completed_at"] = datetime.now()
            
            logger.error(f"Error submitting task {task_id} ({name}) to thread pool: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_FAILED,
                    task_id,
                    {"name": name, "error": str(e)}
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task failed event: {e}")
            
            return task_id
    
    def _execute_task_wrapper(self, task_id, func, *args, **kwargs):
        """
        Wrapper for executing a task with resource tracking.
        
        Args:
            task_id: ID of the task
            func: Function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Result of the function
        """
        import psutil
        import time
        import os
        
        try:
            # Get current process
            process = psutil.Process(os.getpid())
            
            # Record start time and initial memory usage
            start_time = time.time()
            start_memory = process.memory_info().rss
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # Record end time and peak memory usage
            end_time = time.time()
            end_memory = process.memory_info().rss
            
            # Calculate resource usage
            cpu_time = end_time - start_time
            memory_peak = max(0, end_memory - start_memory)
            
            # Update task resource usage
            task = self.tasks.get(task_id)
            if task:
                task["resource_usage"] = {
                    "cpu_time": cpu_time,
                    "memory_peak": memory_peak
                }
            
            return result
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _handle_completion(self, task_id: str, future: concurrent.futures.Future):
        """
        Handle task completion.
        
        Args:
            task_id: ID of the task
            future: Future object for the task
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return
        
        # Update active workers count
        self.active_workers = max(0, self.active_workers - 1)
        
        try:
            # Get result
            result = future.result()
            
            # Update task
            task["status"] = TaskStatus.COMPLETED
            task["completed_at"] = datetime.now()
            task["result"] = result
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_COMPLETED,
                    task_id,
                    {"name": task["name"]}
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task completed event: {e}")
            
            logger.info(f"Task completed: {task_id} ({task['name']})")
        except Exception as e:
            # Update task
            task["status"] = TaskStatus.FAILED
            task["completed_at"] = datetime.now()
            task["error"] = str(e)
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_FAILED,
                    task_id,
                    {"name": task["name"], "error": str(e)}
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task failed event: {e}")
            
            logger.error(f"Task failed: {task_id} ({task['name']}): {e}")
        
        # Clean up
        self.futures.pop(task_id, None)
    
    def cancel(self, task_id: str) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        future = self.futures.get(task_id)
        if not future:
            logger.warning(f"Task {task_id} not found")
            return False
        
        # Cancel future
        result = future.cancel()
        
        if result:
            # Update task
            task = self.tasks.get(task_id)
            if task:
                task["status"] = TaskStatus.CANCELLED
                task["completed_at"] = datetime.now()
                
                # Update active workers count
                self.active_workers = max(0, self.active_workers - 1)
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_CANCELLED,
                    task_id,
                    {"name": task["name"] if task else "Unknown", "reason": "cancelled"}
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task cancelled event: {e}")
            
            logger.info(f"Task cancelled: {task_id}")
            
            # Clean up
            self.futures.pop(task_id, None)
        
        return result
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a task by ID.
        
        Args:
            task_id: ID of the task to get
            
        Returns:
            Task dictionary or None if not found
        """
        return self.tasks.get(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get the status of a task.
        
        Args:
            task_id: ID of the task to get status for
            
        Returns:
            Task status or None if task not found
        """
        task = self.tasks.get(task_id)
        return task["status"] if task else None
    
    def get_task_result(self, task_id: str) -> Any:
        """
        Get the result of a task.
        
        Args:
            task_id: ID of the task to get result for
            
        Returns:
            Task result or None if task not found or not completed
        """
        task = self.tasks.get(task_id)
        return task["result"] if task and task["status"] == TaskStatus.COMPLETED else None
    
    def get_task_error(self, task_id: str) -> Optional[str]:
        """
        Get the error of a failed task.
        
        Args:
            task_id: ID of the task to get error for
            
        Returns:
            Task error or None if task not found or not failed
        """
        task = self.tasks.get(task_id)
        return task["error"] if task and task["status"] == TaskStatus.FAILED else None
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all tasks.
        
        Returns:
            Dictionary of all tasks
        """
        return self.tasks.copy()
    
    def get_pending_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all pending tasks.
        
        Returns:
            Dictionary of pending tasks
        """
        return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.PENDING}
    
    def get_running_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all running tasks.
        
        Returns:
            Dictionary of running tasks
        """
        return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.RUNNING}
    
    def get_completed_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all completed tasks.
        
        Returns:
            Dictionary of completed tasks
        """
        return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.COMPLETED}
    
    def get_failed_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all failed tasks.
        
        Returns:
            Dictionary of failed tasks
        """
        return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.FAILED}
    
    def get_cancelled_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all cancelled tasks.
        
        Returns:
            Dictionary of cancelled tasks
        """
        return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.CANCELLED}
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get thread pool metrics.
        
        Returns:
            Dictionary of thread pool metrics
        """
        return {
            "worker_count": self.max_workers,
            "min_workers": self.min_workers,
            "max_workers": self.max_workers,
            "active_workers": self.active_workers,
            "queue_size": self.queue_size,
            "pending_tasks": len(self.get_pending_tasks()),
            "running_tasks": len(self.get_running_tasks()),
            "completed_tasks": len(self.get_completed_tasks()),
            "failed_tasks": len(self.get_failed_tasks()),
            "cancelled_tasks": len(self.get_cancelled_tasks()),
            "total_tasks": len(self.tasks)
        }
    
    def adjust_worker_count(self, new_count: int) -> bool:
        """
        Adjust the number of worker threads.
        
        Args:
            new_count: New number of worker threads
            
        Returns:
            True if the worker count was adjusted, False otherwise
        """
        # Check if we're in the cooldown period
        if (datetime.now() - self.last_adjustment_time).total_seconds() < self.adjustment_cooldown:
            logger.debug("Worker count adjustment in cooldown period")
            return False
        
        # Ensure new_count is within bounds
        new_count = max(self.min_workers, min(new_count, self.max_workers))
        
        # Check if the count is actually changing
        if new_count == self.executor._max_workers:
            return False
        
        try:
            # Create a new executor with the new worker count
            old_executor = self.executor
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=new_count)
            
            # Submit all pending tasks to the new executor
            for task_id, future in list(self.futures.items()):
                if not future.done() and not future.running():
                    task = self.tasks.get(task_id)
                    if task and task["status"] == TaskStatus.PENDING:
                        # Cancel the old future
                        future.cancel()
                        
                        # Submit to the new executor
                        new_future = self.executor.submit(
                            self._execute_task_wrapper,
                            task_id,
                            task["func"],
                            *task["args"],
                            **task["kwargs"]
                        )
                        self.futures[task_id] = new_future
                        new_future.add_done_callback(lambda f: self._handle_completion(task_id, f))
            
            # Shutdown the old executor without waiting for tasks to complete
            # (they've been cancelled and resubmitted)
            old_executor.shutdown(wait=False)
            
            logger.info(f"Adjusted worker count from {self.executor._max_workers} to {new_count}")
            self.last_adjustment_time = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Error adjusting worker count: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return False
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown the thread pool.
        
        Args:
            wait: Whether to wait for pending tasks to complete
        """
        self.executor.shutdown(wait=wait)
        logger.info(f"Thread pool manager shutdown (wait={wait})")
    
    def stop(self):
        """Stop the thread pool manager."""
        # Cancel all running tasks
        for task_id in list(self.futures.keys()):
            self.cancel(task_id)
        
        # Shutdown the executor
        self.shutdown(wait=False)
        
        logger.info("Thread pool manager stopped")

# Create a singleton instance
thread_pool_manager = ThreadPoolManager()
