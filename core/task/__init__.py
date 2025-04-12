"""
Task management for Wiseflow.

This module provides task management and concurrency support.
"""

from typing import Dict, List, Any, Optional, Union, Callable, Tuple
import logging
import threading
import asyncio
import uuid
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, Future

logger = logging.getLogger(__name__)

class Task:
    """Represents a data mining task."""
    
    def __init__(
        self,
        task_id: str,
        focus_id: str,
        function: Callable,
        args: Tuple = (),
        kwargs: Dict[str, Any] = None,
        auto_shutdown: bool = False
    ):
        """Initialize a task."""
        self.task_id = task_id
        self.focus_id = focus_id
        self.function = function
        self.args = args
        self.kwargs = kwargs or {}
        self.auto_shutdown = auto_shutdown
        self.status = "pending"
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.result: Any = None
        self.error: Optional[Exception] = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the task to a dictionary."""
        return {
            "task_id": self.task_id,
            "focus_id": self.focus_id,
            "status": self.status,
            "auto_shutdown": self.auto_shutdown,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error": str(self.error) if self.error else None
        }


class TaskManager:
    """Manages concurrent data mining tasks."""
    
    def __init__(self, max_workers: int = 4):
        """Initialize the task manager."""
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks: Dict[str, Task] = {}
        self.futures: Dict[str, Future] = {}
        self.lock = threading.Lock()
        self._shutdown_in_progress = False
        
    def submit_task(self, task: Task) -> Future:
        """Submit a task for execution."""
        with self.lock:
            # Create a wrapper function to handle task status updates
            def task_wrapper(*args, **kwargs):
                try:
                    task.status = "running"
                    task.start_time = datetime.now()
                    logger.info(f"Task {task.task_id} started")
                    
                    # Execute the task
                    result = task.function(*args, **kwargs)
                    
                    task.status = "completed"
                    task.end_time = datetime.now()
                    task.result = result
                    logger.info(f"Task {task.task_id} completed")
                    
                    # Auto-shutdown if enabled
                    if task.auto_shutdown and not self._shutdown_in_progress:
                        logger.info(f"Auto-shutdown enabled for task {task.task_id}")
                        # Import here to avoid circular imports
                        from core.task.monitor import get_resource_monitor
                        monitor = get_resource_monitor()
                        monitor.request_shutdown()
                    
                    return result
                except Exception as e:
                    task.status = "failed"
                    task.end_time = datetime.now()
                    task.error = e
                    logger.error(f"Task {task.task_id} failed: {e}")
                    raise
            
            # Submit the task to the executor
            future = self.executor.submit(task_wrapper, *task.args, **task.kwargs)
            self.tasks[task.task_id] = task
            self.futures[task.task_id] = future
            
            # Add a callback to clean up completed tasks
            future.add_done_callback(lambda f: self._task_completed(task.task_id))
            
            return future
    
    def _task_completed(self, task_id: str) -> None:
        """Handle task completion."""
        with self.lock:
            if task_id in self.futures:
                # Get the result or exception
                future = self.futures[task_id]
                try:
                    future.result()  # This will raise any exception that occurred
                except Exception as e:
                    logger.error(f"Task {task_id} failed with exception: {e}")
                
                # Check if all tasks are complete for auto-shutdown
                self._check_all_tasks_complete()
    
    def _check_all_tasks_complete(self) -> None:
        """Check if all tasks are complete and trigger auto-shutdown if needed."""
        # Skip if shutdown is already in progress
        if self._shutdown_in_progress:
            return
            
        # Check if any task has auto_shutdown enabled and all tasks are complete
        has_auto_shutdown = any(task.auto_shutdown for task in self.tasks.values())
        all_complete = all(task.status in ["completed", "failed", "cancelled"] for task in self.tasks.values())
        
        if has_auto_shutdown and all_complete:
            logger.info("All tasks complete and auto-shutdown enabled, initiating shutdown")
            self._shutdown_in_progress = True
            
            # Import here to avoid circular imports
            from core.task.monitor import get_resource_monitor
            monitor = get_resource_monitor()
            monitor.request_shutdown()
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def get_tasks_by_focus(self, focus_id: str) -> List[Task]:
        """Get all tasks for a focus point."""
        return [task for task in self.tasks.values() if task.focus_id == focus_id]
    
    def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        return list(self.tasks.values())
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        with self.lock:
            if task_id in self.futures:
                future = self.futures[task_id]
                cancelled = future.cancel()
                if cancelled:
                    task = self.tasks[task_id]
                    task.status = "cancelled"
                    task.end_time = datetime.now()
                    logger.info(f"Task {task_id} cancelled")
                    
                    # Check if all tasks are now complete
                    self._check_all_tasks_complete()
                    
                return cancelled
            return False
    
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the task manager."""
        self._shutdown_in_progress = True
        self.executor.shutdown(wait=wait)
        logger.info("Task manager shutdown")


class AsyncTaskManager:
    """Manages concurrent asynchronous data mining tasks."""
    
    def __init__(self, max_workers: int = 4):
        """Initialize the async task manager."""
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
        self.tasks: Dict[str, Task] = {}
        self.futures: Dict[str, asyncio.Task] = {}
        self.lock = asyncio.Lock()
        self._shutdown_in_progress = False
        
    async def submit_task(self, task: Task) -> asyncio.Task:
        """Submit a task for execution."""
        async with self.lock:
            # Create a wrapper function to handle task status updates
            async def task_wrapper(*args, **kwargs):
                async with self.semaphore:
                    try:
                        task.status = "running"
                        task.start_time = datetime.now()
                        logger.info(f"Task {task.task_id} started")
                        
                        # Execute the task
                        result = await task.function(*args, **kwargs)
                        
                        task.status = "completed"
                        task.end_time = datetime.now()
                        task.result = result
                        logger.info(f"Task {task.task_id} completed")
                        
                        # Auto-shutdown if enabled
                        if task.auto_shutdown and not self._shutdown_in_progress:
                            logger.info(f"Auto-shutdown enabled for task {task.task_id}")
                            # Import here to avoid circular imports
                            from core.task.monitor import get_resource_monitor
                            monitor = get_resource_monitor()
                            monitor.request_shutdown()
                        
                        return result
                    except Exception as e:
                        task.status = "failed"
                        task.end_time = datetime.now()
                        task.error = e
                        logger.error(f"Task {task.task_id} failed: {e}")
                        raise
            
            # Create an asyncio task
            future = asyncio.create_task(task_wrapper(*task.args, **task.kwargs))
            self.tasks[task.task_id] = task
            self.futures[task.task_id] = future
            
            # Add a callback to clean up completed tasks
            future.add_done_callback(lambda f: asyncio.create_task(self._task_completed(task.task_id)))
            
            return future
    
    async def _task_completed(self, task_id: str) -> None:
        """Handle task completion."""
        async with self.lock:
            if task_id in self.futures:
                # Get the result or exception
                future = self.futures[task_id]
                try:
                    await future  # This will raise any exception that occurred
                except Exception as e:
                    logger.error(f"Task {task_id} failed with exception: {e}")
                
                # Check if all tasks are complete for auto-shutdown
                await self._check_all_tasks_complete()
    
    async def _check_all_tasks_complete(self) -> None:
        """Check if all tasks are complete and trigger auto-shutdown if needed."""
        # Skip if shutdown is already in progress
        if self._shutdown_in_progress:
            return
            
        # Check if any task has auto_shutdown enabled and all tasks are complete
        has_auto_shutdown = any(task.auto_shutdown for task in self.tasks.values())
        all_complete = all(task.status in ["completed", "failed", "cancelled"] for task in self.tasks.values())
        
        if has_auto_shutdown and all_complete:
            logger.info("All tasks complete and auto-shutdown enabled, initiating shutdown")
            self._shutdown_in_progress = True
            
            # Import here to avoid circular imports
            from core.task.monitor import get_resource_monitor
            monitor = get_resource_monitor()
            monitor.request_shutdown()
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def get_tasks_by_focus(self, focus_id: str) -> List[Task]:
        """Get all tasks for a focus point."""
        return [task for task in self.tasks.values() if task.focus_id == focus_id]
    
    def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        return list(self.tasks.values())
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        if task_id in self.futures:
            future = self.futures[task_id]
            future.cancel()
            task = self.tasks[task_id]
            task.status = "cancelled"
            task.end_time = datetime.now()
            logger.info(f"Task {task_id} cancelled")
            
            # We can't await here, so we create a task to check completion
            asyncio.create_task(self._check_all_tasks_complete())
            
            return True
        return False
    
    async def shutdown(self) -> None:
        """Shutdown the task manager."""
        self._shutdown_in_progress = True
        async with self.lock:
            for task_id, future in self.futures.items():
                if not future.done():
                    future.cancel()
            
            # Wait for all tasks to complete or be cancelled
            for future in self.futures.values():
                try:
                    await future
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
            
            logger.info("Async task manager shutdown")


def create_task_id() -> str:
    """Create a unique task ID."""
    return f"task_{uuid.uuid4().hex[:8]}"


# Import monitor module functions for easy access
from core.task.monitor import (
    initialize_resource_monitor,
    get_resource_monitor,
    shutdown_resources,
    ResourceMonitor
)
