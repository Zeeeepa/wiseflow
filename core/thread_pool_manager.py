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
import threading
import queue
from typing import Dict, Any, Optional, Callable, List, Set, Union, Awaitable, Tuple
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
    
    def __new__(cls):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(ThreadPoolManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the thread pool manager."""
        if self._initialized:
            return
            
        # Get configuration
        self.max_workers = config.get("MAX_THREAD_WORKERS", os.cpu_count() or 4)
        self.task_queue_size = config.get("TASK_QUEUE_SIZE", 1000)
        self.worker_timeout = config.get("WORKER_TIMEOUT", 60)  # seconds
        
        # Create thread pool with a bounded work queue
        self.task_queue = queue.Queue(maxsize=self.task_queue_size)
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="wiseflow-worker"
        )
        
        # Task tracking
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.futures: Dict[str, concurrent.futures.Future] = {}
        self.priority_queues: Dict[TaskPriority, List[str]] = {
            priority: [] for priority in TaskPriority
        }
        
        # Locks for thread safety
        self.task_lock = threading.RLock()
        self.queue_lock = threading.RLock()
        
        # Worker management
        self.active_workers = 0
        self.max_active_workers = self.max_workers
        self.worker_lock = threading.RLock()
        
        # Statistics
        self.stats = {
            "tasks_submitted": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_cancelled": 0,
            "avg_execution_time": 0.0,
            "peak_active_workers": 0
        }
        self.stats_lock = threading.RLock()
        
        self._initialized = True
        
        logger.info(f"Thread pool manager initialized with {self.max_workers} workers")
    
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
            "error": None
        }
        
        # Add task to manager with thread safety
        with self.task_lock:
            self.tasks[task_id] = task
            
            # Add to priority queue
            with self.queue_lock:
                self.priority_queues[priority].append(task_id)
        
        # Submit task to executor with wrapper for priority handling
        future = self.executor.submit(self._execute_task, task_id)
        
        with self.task_lock:
            self.futures[task_id] = future
            
            # Update task status
            task = self.tasks[task_id]
            task["status"] = TaskStatus.QUEUED
        
        # Update statistics
        with self.stats_lock:
            self.stats["tasks_submitted"] += 1
        
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
    
    def _execute_task(self, task_id: str) -> Any:
        """
        Execute a task with priority handling.
        
        Args:
            task_id: ID of the task to execute
            
        Returns:
            Result of the task
        """
        # Get task
        with self.task_lock:
            task = self.tasks.get(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found")
                return None
            
            # Update task status
            task["status"] = TaskStatus.RUNNING
            task["started_at"] = datetime.now()
            
            # Get task details
            func = task["func"]
            args = task["args"]
            kwargs = task["kwargs"]
            name = task["name"]
        
        # Update worker count
        with self.worker_lock:
            self.active_workers += 1
            if self.active_workers > self.stats["peak_active_workers"]:
                self.stats["peak_active_workers"] = self.active_workers
        
        # Execute task with timing
        start_time = time.time()
        try:
            # Execute the function
            result = func(*args, **kwargs)
            
            # Update task
            with self.task_lock:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    task["status"] = TaskStatus.COMPLETED
                    task["completed_at"] = datetime.now()
                    task["result"] = result
            
            # Update statistics
            execution_time = time.time() - start_time
            with self.stats_lock:
                self.stats["tasks_completed"] += 1
                # Update average execution time
                avg_time = self.stats["avg_execution_time"]
                completed = self.stats["tasks_completed"]
                self.stats["avg_execution_time"] = (avg_time * (completed - 1) + execution_time) / completed
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_COMPLETED,
                    task_id,
                    {"name": name}
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task completed event: {e}")
            
            logger.info(f"Task completed: {task_id} ({name}) in {execution_time:.2f}s")
            return result
        except Exception as e:
            # Update task
            with self.task_lock:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    task["status"] = TaskStatus.FAILED
                    task["completed_at"] = datetime.now()
                    task["error"] = str(e)
            
            # Update statistics
            with self.stats_lock:
                self.stats["tasks_failed"] += 1
            
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
            
            logger.error(f"Task failed: {task_id} ({name}): {e}")
            raise
        finally:
            # Update worker count
            with self.worker_lock:
                self.active_workers -= 1
    
    def cancel(self, task_id: str) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        with self.task_lock:
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
                
                # Update statistics
                with self.stats_lock:
                    self.stats["tasks_cancelled"] += 1
                
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
            
            return result
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a task by ID.
        
        Args:
            task_id: ID of the task to get
            
        Returns:
            Task dictionary or None if not found
        """
        with self.task_lock:
            return self.tasks.get(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get the status of a task.
        
        Args:
            task_id: ID of the task to get status for
            
        Returns:
            Task status or None if task not found
        """
        with self.task_lock:
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
        with self.task_lock:
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
        with self.task_lock:
            task = self.tasks.get(task_id)
            return task["error"] if task and task["status"] == TaskStatus.FAILED else None
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all tasks.
        
        Returns:
            Dictionary of all tasks
        """
        with self.task_lock:
            return self.tasks.copy()
    
    def get_pending_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all pending tasks.
        
        Returns:
            Dictionary of pending tasks
        """
        with self.task_lock:
            return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.PENDING}
    
    def get_running_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all running tasks.
        
        Returns:
            Dictionary of running tasks
        """
        with self.task_lock:
            return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.RUNNING}
    
    def get_completed_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all completed tasks.
        
        Returns:
            Dictionary of completed tasks
        """
        with self.task_lock:
            return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.COMPLETED}
    
    def get_failed_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all failed tasks.
        
        Returns:
            Dictionary of failed tasks
        """
        with self.task_lock:
            return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.FAILED}
    
    def get_cancelled_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all cancelled tasks.
        
        Returns:
            Dictionary of cancelled tasks
        """
        with self.task_lock:
            return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.CANCELLED}
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get thread pool statistics.
        
        Returns:
            Dictionary of statistics
        """
        with self.stats_lock:
            stats = self.stats.copy()
            
        # Add current counts
        with self.task_lock:
            stats["pending_tasks"] = len(self.get_pending_tasks())
            stats["running_tasks"] = len(self.get_running_tasks())
            stats["completed_tasks"] = len(self.get_completed_tasks())
            stats["failed_tasks"] = len(self.get_failed_tasks())
            stats["cancelled_tasks"] = len(self.get_cancelled_tasks())
            stats["total_tasks"] = len(self.tasks)
        
        # Add worker info
        with self.worker_lock:
            stats["active_workers"] = self.active_workers
            stats["max_workers"] = self.max_workers
        
        return stats
    
    def cleanup_completed_tasks(self, max_age_seconds: int = 3600):
        """
        Clean up completed, failed, and cancelled tasks older than the specified age.
        
        Args:
            max_age_seconds: Maximum age of tasks to keep in seconds
        """
        now = datetime.now()
        tasks_to_remove = []
        
        with self.task_lock:
            for task_id, task in self.tasks.items():
                if task["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    if task["completed_at"] and (now - task["completed_at"]).total_seconds() > max_age_seconds:
                        tasks_to_remove.append(task_id)
            
            # Remove tasks
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
                if task_id in self.futures:
                    del self.futures[task_id]
        
        logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
    
    def adjust_worker_count(self, new_max_workers: int):
        """
        Adjust the maximum number of workers.
        
        Args:
            new_max_workers: New maximum number of workers
        """
        if new_max_workers <= 0:
            logger.warning(f"Invalid worker count: {new_max_workers}, must be > 0")
            return
        
        with self.worker_lock:
            old_max = self.max_workers
            self.max_workers = new_max_workers
            
            # Create a new executor if reducing workers
            if new_max_workers < old_max:
                # Create new executor
                new_executor = concurrent.futures.ThreadPoolExecutor(
                    max_workers=new_max_workers,
                    thread_name_prefix="wiseflow-worker"
                )
                
                # Shutdown old executor after tasks complete
                self.executor.shutdown(wait=False)
                self.executor = new_executor
        
        logger.info(f"Adjusted worker count from {old_max} to {new_max_workers}")
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown the thread pool.
        
        Args:
            wait: Whether to wait for pending tasks to complete
        """
        self.executor.shutdown(wait=wait)
        logger.info(f"Thread pool manager shutdown (wait={wait})")

# Create a singleton instance
thread_pool_manager = ThreadPoolManager()
