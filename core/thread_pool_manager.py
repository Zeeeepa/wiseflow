"""
Thread pool manager for WiseFlow.

This module provides a thread pool manager for executing tasks concurrently.
This is a compatibility layer that delegates to the unified task management system.
"""

import os
import time
import asyncio
import logging
import uuid
import concurrent.futures
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

# Import the unified task management system
from core.task_management import (
    Task as UnifiedTask,
    TaskManager as UnifiedTaskManager,
    TaskPriority as UnifiedTaskPriority,
    TaskStatus as UnifiedTaskStatus
)

logger = logging.getLogger(__name__)

class ThreadPoolManager:
    """
    Thread pool manager for WiseFlow.
    
    This class provides a thread pool for executing CPU-bound tasks concurrently.
    This is a compatibility class that delegates to the unified task management system.
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
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.futures: Dict[str, concurrent.futures.Future] = {}
        
        # Initialize the unified task manager
        self.unified_manager = UnifiedTaskManager(
            max_concurrent_tasks=self.max_workers,
            default_executor_type="thread_pool"
        )
        
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
        
        # Map priority to unified priority
        unified_priority = UnifiedTaskPriority.NORMAL
        if priority == TaskPriority.LOW:
            unified_priority = UnifiedTaskPriority.LOW
        elif priority == TaskPriority.HIGH:
            unified_priority = UnifiedTaskPriority.HIGH
        elif priority == TaskPriority.CRITICAL:
            unified_priority = UnifiedTaskPriority.CRITICAL
        
        # Register with unified task manager
        unified_task_id = self.unified_manager.register_task(
            name=name,
            func=func,
            *args,
            task_id=task_id,
            kwargs=kwargs,
            priority=unified_priority,
            executor_type="thread_pool",
            metadata={"legacy_task": True}
        )
        
        # Create task record for compatibility
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
        
        # Add task to manager
        self.tasks[task_id] = task
        
        # Execute the task
        asyncio.create_task(self._execute_task_async(task_id))
        
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
    
    async def _execute_task_async(self, task_id: str):
        """
        Execute a task asynchronously.
        
        Args:
            task_id: ID of the task to execute
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found for execution")
            return
        
        # Update task status
        task["status"] = TaskStatus.RUNNING
        task["started_at"] = datetime.now()
        
        try:
            # Execute the task
            result = await self.unified_manager.execute_task(task_id, wait=True)
            
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
    
    def cancel(self, task_id: str) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return False
        
        # Delegate to unified task manager
        asyncio.create_task(self._cancel_task_async(task_id))
        return True
    
    async def _cancel_task_async(self, task_id: str) -> bool:
        """
        Cancel a task asynchronously.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        result = await self.unified_manager.cancel_task(task_id)
        
        if result:
            task = self.tasks.get(task_id)
            if task:
                task["status"] = TaskStatus.CANCELLED
                task["completed_at"] = datetime.now()
        
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
        # Delegate to unified task manager
        asyncio.create_task(self.unified_manager.stop())
        logger.info(f"Thread pool manager shutdown (wait={wait})")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics for the thread pool.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "worker_count": self.max_workers,
            "active_workers": len(self.get_running_tasks()),
            "queue_size": len(self.get_pending_tasks()),
            "completed_tasks": len(self.get_completed_tasks()),
            "failed_tasks": len(self.get_failed_tasks()),
            "cancelled_tasks": len(self.get_cancelled_tasks())
        }
    
    def stop(self):
        """Stop the thread pool manager."""
        self.shutdown(wait=False)

# Create a singleton instance
thread_pool_manager = ThreadPoolManager()
