"""
Asynchronous Task Manager for WiseFlow.

This module provides an asynchronous task manager for executing tasks concurrently
with proper dependency management, error handling, and resource management.
"""

import os
import time
import asyncio
import logging
import uuid
import traceback
from typing import Dict, Any, Optional, Callable, List, Set, Union, Awaitable
from datetime import datetime
from enum import Enum, auto
import concurrent.futures

from core.config import config
from core.event_system import (
    EventType, Event, publish_sync,
    create_task_event
)
from core.utils.error_handling import handle_exceptions, TaskError

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    """Task priority levels."""
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL = auto()

class TaskStatus(Enum):
    """Task status values."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING = "waiting"

class TaskDependencyError(Exception):
    """Error raised when a task dependency cannot be satisfied."""
    pass

def create_task_id() -> str:
    """Create a unique task ID."""
    return str(uuid.uuid4())

class Task:
    """
    Task class for the asynchronous task manager.
    
    This class represents a task that can be executed asynchronously.
    """
    
    def __init__(
        self,
        task_id: str,
        name: str = None,
        func: Callable = None,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: List[str] = None,
        max_retries: int = 0,
        retry_delay: float = 1.0,
        timeout: Optional[float] = None,
        description: str = "",
        tags: List[str] = None,
        focus_id: str = None,
        auto_shutdown: bool = False
    ):
        """
        Initialize a task.
        
        Args:
            task_id: Unique identifier for the task
            name: Name of the task
            func: Function to execute
            args: Arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
            priority: Priority of the task
            dependencies: List of task IDs that must complete before this task
            max_retries: Maximum number of retries if the task fails
            retry_delay: Delay in seconds between retries
            timeout: Timeout in seconds for the task
            description: Description of the task
            tags: List of tags for the task
            focus_id: ID of the focus point associated with the task
            auto_shutdown: Whether to shut down the system after the task completes
        """
        self.task_id = task_id
        self.name = name or f"Task-{task_id[:8]}"
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.priority = priority
        self.dependencies = dependencies or []
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.description = description
        self.tags = tags or []
        self.focus_id = focus_id
        self.auto_shutdown = auto_shutdown
        
        self.status = TaskStatus.PENDING.value
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.retry_count = 0
        self.task_object = None
        self.execution_id = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the task to a dictionary.
        
        Returns:
            Dictionary representation of the task
        """
        return {
            "task_id": self.task_id,
            "name": self.name,
            "priority": self.priority.name if isinstance(self.priority, TaskPriority) else self.priority,
            "status": self.status,
            "dependencies": self.dependencies,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error": str(self.error) if self.error else None,
            "description": self.description,
            "tags": self.tags,
            "focus_id": self.focus_id,
            "auto_shutdown": self.auto_shutdown,
            "execution_id": self.execution_id
        }

class AsyncTaskManager:
    """
    Asynchronous Task Manager for WiseFlow.
    
    This class provides functionality to manage and execute tasks asynchronously
    with proper dependency management, error handling, and resource management.
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(AsyncTaskManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, max_workers: int = None):
        """
        Initialize the task manager.
        
        Args:
            max_workers: Maximum number of concurrent tasks
        """
        if self._initialized:
            return
            
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.cancelled_tasks: Set[str] = set()
        self.waiting_tasks: Set[str] = set()
        
        self.max_workers = max_workers or config.get("MAX_CONCURRENT_TASKS", 4)
        self.task_lock = asyncio.Lock()
        self.is_running = False
        self.scheduler_task = None
        
        # Thread pool for CPU-bound tasks
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="task_worker"
        )
        
        self._initialized = True
        
        logger.info(f"AsyncTaskManager initialized with {self.max_workers} workers")
    
    def register_task(
        self,
        name: str,
        func: Callable,
        *args,
        dependencies: List[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 0,
        retry_delay: float = 1.0,
        timeout: Optional[float] = None,
        description: str = "",
        tags: List[str] = None,
        focus_id: str = None,
        auto_shutdown: bool = False,
        task_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Register a task with the task manager.
        
        Args:
            name: Name of the task
            func: Function to execute
            *args: Arguments to pass to the function
            dependencies: List of task IDs that must complete before this task
            priority: Priority of the task
            max_retries: Maximum number of retries if the task fails
            retry_delay: Delay in seconds between retries
            timeout: Timeout in seconds for the task
            description: Description of the task
            tags: List of tags for the task
            focus_id: ID of the focus point associated with the task
            auto_shutdown: Whether to shut down the system after the task completes
            task_id: Optional task ID, if not provided a new one will be generated
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Task ID
        """
        task_id = task_id or create_task_id()
        
        # Check if dependencies exist
        if dependencies:
            for dep_id in dependencies:
                if dep_id not in self.tasks:
                    raise TaskDependencyError(f"Dependency {dep_id} does not exist")
        
        # Create task
        task = Task(
            task_id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            dependencies=dependencies or [],
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            description=description,
            tags=tags or [],
            focus_id=focus_id,
            auto_shutdown=auto_shutdown
        )
        
        # Add task to manager
        self.tasks[task_id] = task
        
        # If task has dependencies, mark it as waiting
        if dependencies:
            task.status = TaskStatus.WAITING.value
            self.waiting_tasks.add(task_id)
        
        # Publish event
        try:
            event = create_task_event(
                EventType.TASK_CREATED,
                task_id,
                {"name": name, "priority": priority.name if isinstance(priority, TaskPriority) else priority}
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish task created event: {e}")
        
        logger.info(f"Task registered: {task_id} ({name})")
        return task_id
    
    def execute_task(self, task_id: str, wait: bool = False) -> Optional[str]:
        """
        Execute a registered task.
        
        Args:
            task_id: ID of the task to execute
            wait: Whether to wait for the task to complete
            
        Returns:
            Execution ID if successful, None otherwise
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return None
        
        # Generate execution ID
        execution_id = f"exec_{create_task_id()}"
        task.execution_id = execution_id
        
        # Start the task manager if not already running
        if not self.is_running:
            asyncio.create_task(self.start())
        
        # If task has dependencies, it will be executed when dependencies complete
        if task.dependencies and task.status == TaskStatus.WAITING.value:
            logger.info(f"Task {task_id} ({task.name}) will be executed when dependencies complete")
            return execution_id
        
        # If task is already running, return the execution ID
        if task.status == TaskStatus.RUNNING.value:
            logger.warning(f"Task {task_id} ({task.name}) is already running")
            return execution_id
        
        # Mark task as pending to be picked up by the scheduler
        task.status = TaskStatus.PENDING.value
        
        logger.info(f"Task scheduled for execution: {task_id} ({task.name})")
        
        # If wait is True, wait for the task to complete
        if wait:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self._wait_for_task(task_id))
        
        return execution_id
    
    async def _wait_for_task(self, task_id: str) -> Any:
        """
        Wait for a task to complete.
        
        Args:
            task_id: ID of the task to wait for
            
        Returns:
            Task result
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return None
        
        # If task is already completed, return the result
        if task.status == TaskStatus.COMPLETED.value:
            return task.result
        
        # Wait for the task to complete
        while task.status not in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
            await asyncio.sleep(0.1)
        
        # Return the result or raise an exception
        if task.status == TaskStatus.COMPLETED.value:
            return task.result
        elif task.status == TaskStatus.FAILED.value:
            raise TaskError(f"Task {task_id} failed: {task.error}")
        else:
            raise TaskError(f"Task {task_id} was cancelled")
    
    def cancel_task(self, task_id: str) -> bool:
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
        
        # Cleanup any allocated resources
        self._cleanup_task_resources(task)
        
        if task.status == TaskStatus.RUNNING.value:
            if task.task_object and not task.task_object.done():
                task.task_object.cancel()
            
            self.running_tasks.discard(task_id)
            self.cancelled_tasks.add(task_id)
        elif task.status == TaskStatus.PENDING.value:
            self.cancelled_tasks.add(task_id)
        elif task.status == TaskStatus.WAITING.value:
            self.waiting_tasks.discard(task_id)
            self.cancelled_tasks.add(task_id)
        else:
            logger.warning(f"Cannot cancel task {task_id} with status {task.status}")
            return False
        
        task.status = TaskStatus.CANCELLED.value
        task.completed_at = datetime.now()
        
        # Publish event
        try:
            event = create_task_event(
                EventType.TASK_CANCELLED,
                task_id,
                {"name": task.name, "reason": "cancelled by user"}
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish task cancelled event: {e}")
        
        logger.info(f"Task cancelled: {task_id} ({task.name})")
        return True
    
    def _cleanup_task_resources(self, task: Task) -> None:
        """
        Clean up resources allocated for a task.
        
        Args:
            task: Task to clean up resources for
        """
        # Implement resource cleanup logic here
        # This could include closing file handles, network connections, etc.
        pass
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id: ID of the task to get
            
        Returns:
            Task object or None if not found
        """
        return self.tasks.get(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[str]:
        """
        Get the status of a task.
        
        Args:
            task_id: ID of the task to get status for
            
        Returns:
            Task status or None if task not found
        """
        task = self.tasks.get(task_id)
        return task.status if task else None
    
    def get_task_result(self, task_id: str) -> Any:
        """
        Get the result of a task.
        
        Args:
            task_id: ID of the task to get result for
            
        Returns:
            Task result or None if task not found or not completed
        """
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.COMPLETED.value:
            return None
        return task.result
    
    def get_task_error(self, task_id: str) -> Optional[str]:
        """
        Get the error of a failed task.
        
        Args:
            task_id: ID of the task to get error for
            
        Returns:
            Task error or None if task not found or not failed
        """
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.FAILED.value:
            return None
        return str(task.error) if task.error else None
    
    def get_tasks_by_status(self, status: str) -> Dict[str, Task]:
        """
        Get all tasks with a specific status.
        
        Args:
            status: Status to filter by
            
        Returns:
            Dictionary of tasks with the specified status
        """
        return {task_id: task for task_id, task in self.tasks.items() if task.status == status}
    
    def get_tasks_by_focus(self, focus_id: str) -> List[Task]:
        """
        Get all tasks associated with a specific focus point.
        
        Args:
            focus_id: ID of the focus point
            
        Returns:
            List of tasks associated with the focus point
        """
        return [task for task in self.tasks.values() if task.focus_id == focus_id]
    
    def get_tasks_by_tag(self, tag: str) -> List[Task]:
        """
        Get all tasks with a specific tag.
        
        Args:
            tag: Tag to filter by
            
        Returns:
            List of tasks with the specified tag
        """
        return [task for task in self.tasks.values() if tag in task.tags]
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about the task manager.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "total_tasks": len(self.tasks),
            "pending_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING.value]),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "cancelled_tasks": len(self.cancelled_tasks),
            "waiting_tasks": len(self.waiting_tasks),
            "max_workers": self.max_workers,
            "is_running": self.is_running
        }
    
    async def start(self):
        """Start the task manager."""
        if self.is_running:
            logger.warning("Task manager is already running")
            return
        
        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler())
        logger.info("Task manager started")
    
    async def stop(self):
        """Stop the task manager."""
        if not self.is_running:
            logger.warning("Task manager is not running")
            return
        
        self.is_running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all running tasks
        for task_id in list(self.running_tasks):
            self.cancel_task(task_id)
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        logger.info("Task manager stopped")
    
    async def shutdown(self, wait: bool = True):
        """
        Shutdown the task manager.
        
        Args:
            wait: Whether to wait for running tasks to complete
        """
        if not wait:
            # Cancel all running tasks
            for task_id in list(self.running_tasks):
                self.cancel_task(task_id)
        
        await self.stop()
    
    async def _scheduler(self):
        """Scheduler loop for the task manager."""
        try:
            while self.is_running:
                await self._schedule_tasks()
                await asyncio.sleep(0.1)  # Small delay to prevent CPU hogging
        except asyncio.CancelledError:
            logger.info("Task scheduler cancelled")
        except Exception as e:
            logger.error(f"Error in task scheduler: {e}")
            logger.error(traceback.format_exc())
    
    async def _schedule_tasks(self):
        """Schedule tasks for execution."""
        async with self.task_lock:
            # Check if we can run more tasks
            if len(self.running_tasks) >= self.max_workers:
                return
            
            # Check for waiting tasks that can now run
            for task_id in list(self.waiting_tasks):
                task = self.tasks.get(task_id)
                if not task:
                    self.waiting_tasks.discard(task_id)
                    continue
                
                # Check if all dependencies are completed
                can_run = True
                for dep_id in task.dependencies:
                    dep_task = self.tasks.get(dep_id)
                    if not dep_task or dep_task.status != TaskStatus.COMPLETED.value:
                        can_run = False
                        break
                
                if can_run:
                    task.status = TaskStatus.PENDING.value
                    self.waiting_tasks.discard(task_id)
                    logger.info(f"Task {task_id} ({task.name}) dependencies satisfied, marked as pending")
            
            # Get pending tasks sorted by priority
            pending_tasks = sorted(
                [(task_id, task) for task_id, task in self.tasks.items() if task.status == TaskStatus.PENDING.value],
                key=lambda x: x[1].priority.value if isinstance(x[1].priority, TaskPriority) else x[1].priority,
                reverse=True  # Higher priority first
            )
            
            # Schedule tasks up to max_workers
            for task_id, task in pending_tasks:
                if len(self.running_tasks) >= self.max_workers:
                    break
                
                # Start task
                task.status = TaskStatus.RUNNING.value
                task.started_at = datetime.now()
                self.running_tasks.add(task_id)
                
                # Create task
                task.task_object = asyncio.create_task(self._execute_task(task))
                
                # Publish event
                try:
                    event = create_task_event(
                        EventType.TASK_STARTED,
                        task_id,
                        {"name": task.name}
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish task started event: {e}")
                
                logger.info(f"Task started: {task_id} ({task.name})")
    
    @handle_exceptions(default_message="Error executing task", log_error=True)
    async def _execute_task(self, task: Task):
        """
        Execute a task.
        
        Args:
            task: Task to execute
        """
        try:
            # Execute task with timeout if specified
            if task.timeout:
                task.result = await asyncio.wait_for(self._call_task_func(task), task.timeout)
            else:
                task.result = await self._call_task_func(task)
            
            # Mark task as completed
            task.status = TaskStatus.COMPLETED.value
            task.completed_at = datetime.now()
            self.running_tasks.discard(task.task_id)
            self.completed_tasks.add(task.task_id)
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_COMPLETED,
                    task.task_id,
                    {"name": task.name}
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task completed event: {e}")
            
            logger.info(f"Task completed: {task.task_id} ({task.name})")
            
            # Check for waiting tasks that depend on this task
            await self._check_dependent_tasks(task.task_id)
            
            # Check if auto-shutdown is enabled for this task
            if task.auto_shutdown:
                logger.info(f"Auto-shutdown enabled for task {task.task_id}, initiating shutdown")
                # Implement auto-shutdown logic here
        except asyncio.TimeoutError:
            # Handle timeout
            task.error = asyncio.TimeoutError(f"Task timed out after {task.timeout} seconds")
            await self._handle_task_error(task)
        except asyncio.CancelledError:
            # Handle cancellation
            task.error = asyncio.CancelledError("Task was cancelled")
            task.status = TaskStatus.CANCELLED.value
            task.completed_at = datetime.now()
            self.running_tasks.discard(task.task_id)
            self.cancelled_tasks.add(task.task_id)
            
            # Clean up resources
            self._cleanup_task_resources(task)
            
            logger.info(f"Task cancelled: {task.task_id} ({task.name})")
        except Exception as e:
            # Handle other errors
            task.error = e
            await self._handle_task_error(task)
    
    async def _call_task_func(self, task: Task) -> Any:
        """
        Call the task function.
        
        Args:
            task: Task to execute
            
        Returns:
            Result of the task function
        """
        if asyncio.iscoroutinefunction(task.func):
            # Function is already a coroutine
            return await task.func(*task.args, **task.kwargs)
        else:
            # Function is synchronous, run it in a thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.thread_pool,
                lambda: task.func(*task.args, **task.kwargs)
            )
    
    async def _handle_task_error(self, task: Task):
        """
        Handle a task error.
        
        Args:
            task: Task that failed
        """
        # Check if we should retry
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.PENDING.value
            self.running_tasks.discard(task.task_id)
            
            logger.warning(f"Task {task.task_id} ({task.name}) failed, retrying ({task.retry_count}/{task.max_retries}): {task.error}")
            
            # Wait before retrying with exponential backoff
            retry_delay = task.retry_delay * (2 ** (task.retry_count - 1))
            await asyncio.sleep(retry_delay)
        else:
            # Mark task as failed
            task.status = TaskStatus.FAILED.value
            task.completed_at = datetime.now()
            self.running_tasks.discard(task.task_id)
            self.failed_tasks.add(task.task_id)
            
            # Clean up resources
            self._cleanup_task_resources(task)
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_FAILED,
                    task.task_id,
                    {"name": task.name, "error": str(task.error)}
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task failed event: {e}")
            
            logger.error(f"Task failed: {task.task_id} ({task.name}): {task.error}")
            logger.error(traceback.format_exc())
    
    async def _check_dependent_tasks(self, completed_task_id: str):
        """
        Check for waiting tasks that depend on a completed task.
        
        Args:
            completed_task_id: ID of the completed task
        """
        for waiting_task_id in list(self.waiting_tasks):
            waiting_task = self.tasks.get(waiting_task_id)
            if not waiting_task:
                self.waiting_tasks.discard(waiting_task_id)
                continue
            
            if completed_task_id in waiting_task.dependencies:
                # Check if all dependencies are completed
                can_run = True
                for dep_id in waiting_task.dependencies:
                    dep_task = self.tasks.get(dep_id)
                    if not dep_task or dep_task.status != TaskStatus.COMPLETED.value:
                        can_run = False
                        break
                
                if can_run:
                    waiting_task.status = TaskStatus.PENDING.value
                    self.waiting_tasks.discard(waiting_task_id)
                    logger.info(f"Task {waiting_task_id} ({waiting_task.name}) dependencies satisfied, marked as pending")

# Create a singleton instance
task_manager = AsyncTaskManager()

