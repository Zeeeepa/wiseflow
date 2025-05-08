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
            
        self.max_workers = config.get("MAX_THREAD_WORKERS", os.cpu_count() or 4)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.futures: Dict[str, concurrent.futures.Future] = {}
        self.tasks_lock = threading.RLock()  # Added lock for thread safety
        
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
            "error": None,
            "resources": []  # Track resources allocated to this task
        }
        
        # Add task to manager with lock to ensure thread safety
        with self.tasks_lock:
            self.tasks[task_id] = task
            
            # Submit task to executor
            future = self.executor.submit(self._wrapped_func, task_id, func, *args, **kwargs)
            self.futures[task_id] = future
            
            # Update task status
            task["status"] = TaskStatus.RUNNING
            task["started_at"] = datetime.now()
        
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
    
    def _wrapped_func(self, task_id: str, func: Callable, *args, **kwargs):
        """
        Wrapper function to catch exceptions and track resources.
        
        Args:
            task_id: ID of the task
            func: Function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Result of the function
        """
        try:
            # Execute the function
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            raise
        finally:
            # Ensure resources are cleaned up even if the function raises an exception
            self._cleanup_task_resources(task_id)
    
    def _handle_completion(self, task_id: str, future: concurrent.futures.Future):
        """
        Handle task completion.
        
        Args:
            task_id: ID of the task
            future: Future object for the task
        """
        with self.tasks_lock:
            task = self.tasks.get(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found")
                return
            
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
            except concurrent.futures.CancelledError:
                # Task was cancelled
                task["status"] = TaskStatus.CANCELLED
                task["completed_at"] = datetime.now()
                task["error"] = "Task was cancelled"
                
                # Publish event
                try:
                    event = create_task_event(
                        EventType.TASK_CANCELLED,
                        task_id,
                        {"name": task["name"], "reason": "cancelled"}
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish task cancelled event: {e}")
                
                logger.info(f"Task cancelled: {task_id} ({task['name']})")
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
            finally:
                # Clean up resources
                self._cleanup_task_resources(task_id)
                
                # Remove future
                if task_id in self.futures:
                    del self.futures[task_id]
    
    def _cleanup_task_resources(self, task_id: str):
        """
        Clean up resources allocated to a task.
        
        Args:
            task_id: ID of the task
        """
        with self.tasks_lock:
            task = self.tasks.get(task_id)
            if not task:
                return
            
            # Clean up any resources allocated to the task
            for resource in task.get("resources", []):
                try:
                    if hasattr(resource, "close"):
                        resource.close()
                    elif hasattr(resource, "cleanup"):
                        resource.cleanup()
                    elif hasattr(resource, "__del__"):
                        resource.__del__()
                except Exception as e:
                    logger.warning(f"Error cleaning up resource for task {task_id}: {e}")
            
            # Clear resources list
            task["resources"] = []
    
    def register_resource(self, task_id: str, resource: Any):
        """
        Register a resource with a task for cleanup.
        
        Args:
            task_id: ID of the task
            resource: Resource to register
        """
        with self.tasks_lock:
            task = self.tasks.get(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found")
                return
            
            task.setdefault("resources", []).append(resource)
    
    def cancel(self, task_id: str) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        with self.tasks_lock:
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
                    task["error"] = "Task was cancelled"
                
                # Clean up resources
                self._cleanup_task_resources(task_id)
                
                # Publish event
                try:
                    event = create_task_event(
                        EventType.TASK_CANCELLED,
                        task_id,
                        {"name": task["name"] if task else "Unknown", "reason": "cancelled by user"}
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
