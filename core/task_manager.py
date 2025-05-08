"""
Task management module for WiseFlow.

This module provides functionality to manage and execute tasks asynchronously.
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
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    WAITING = auto()

class TaskDependencyError(Exception):
    """Error raised when a task dependency cannot be satisfied."""
    pass

def create_task_id() -> str:
    """Create a unique task ID."""
    return str(uuid.uuid4())

class Task:
    """
    Task class for the task manager.
    
    This class represents a task that can be executed asynchronously.
    """
    
    def __init__(
        self,
        task_id: str,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: List[str] = None,
        max_retries: int = 0,
        retry_delay: float = 1.0,
        timeout: Optional[float] = None,
        description: str = "",
        tags: List[str] = None
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
        """
        self.task_id = task_id
        self.name = name
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
        
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.retry_count = 0
        self.task_object = None
        self.resource_usage = {
            "cpu_time": 0,
            "memory_peak": 0
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the task to a dictionary.
        
        Returns:
            Dictionary representation of the task
        """
        return {
            "task_id": self.task_id,
            "name": self.name,
            "priority": self.priority.name,
            "status": self.status.name,
            "dependencies": self.dependencies,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error": str(self.error) if self.error else None,
            "description": self.description,
            "tags": self.tags,
            "resource_usage": self.resource_usage
        }

class TaskManager:
    """
    Task manager for WiseFlow.
    
    This class provides functionality to manage and execute tasks asynchronously.
    """
    
    _instance = None
    
    def __new__(cls):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the task manager."""
        if self._initialized:
            return
            
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.cancelled_tasks: Set[str] = set()
        self.waiting_tasks: Set[str] = set()
        
        self.max_concurrent_tasks = config.get("MAX_CONCURRENT_TASKS", 4)
        self.task_lock = asyncio.Lock()
        self.is_running = False
        self.scheduler_task = None
        
        # Resource tracking
        self.resource_cleanup_handlers = []
        
        self._initialized = True
        
        logger.info("Task manager initialized")
    
    def register_task(
        self,
        name: str,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: List[str] = None,
        max_retries: int = 0,
        retry_delay: float = 1.0,
        timeout: Optional[float] = None,
        task_id: Optional[str] = None,
        description: str = "",
        tags: List[str] = None
    ) -> str:
        """
        Register a task with the task manager.
        
        Args:
            name: Name of the task
            func: Function to execute
            *args: Arguments to pass to the function
            priority: Priority of the task
            dependencies: List of task IDs that must complete before this task
            max_retries: Maximum number of retries if the task fails
            retry_delay: Delay in seconds between retries
            timeout: Timeout in seconds for the task
            task_id: Optional task ID, if not provided a new one will be generated
            description: Description of the task
            tags: List of tags for the task
            
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
            kwargs={},
            priority=priority,
            dependencies=dependencies or [],
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            description=description,
            tags=tags or []
        )
        
        # Add task to manager
        self.tasks[task_id] = task
        
        # Check if task has dependencies
        if task.dependencies:
            # Check if all dependencies are completed
            can_run = True
            for dep_id in task.dependencies:
                dep_task = self.tasks.get(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    can_run = False
                    break
            
            if not can_run:
                task.status = TaskStatus.WAITING
                self.waiting_tasks.add(task_id)
        
        logger.info(f"Task registered: {task_id} ({name})")
        return task_id
    
    def register_resource_cleanup_handler(self, handler: Callable[[Task], None]) -> None:
        """
        Register a handler for cleaning up resources when a task is cancelled or fails.
        
        Args:
            handler: Function to call when a task is cancelled or fails
        """
        if handler not in self.resource_cleanup_handlers:
            self.resource_cleanup_handlers.append(handler)
    
    def _cleanup_task_resources(self, task: Task) -> None:
        """
        Clean up resources allocated to a task.
        
        Args:
            task: Task to clean up resources for
        """
        for handler in self.resource_cleanup_handlers:
            try:
                handler(task)
            except Exception as e:
                logger.error(f"Error in resource cleanup handler for task {task.task_id}: {e}")
    
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
        
        try:
            # Cleanup any allocated resources
            self._cleanup_task_resources(task)
            
            # Cancel the task
            if task.status == TaskStatus.RUNNING:
                if task.task_object and not task.task_object.done():
                    task.task_object.cancel()
                
                self.running_tasks.discard(task_id)
                self.cancelled_tasks.add(task_id)
            elif task.status == TaskStatus.PENDING:
                self.cancelled_tasks.add(task_id)
            elif task.status == TaskStatus.WAITING:
                self.waiting_tasks.discard(task_id)
                self.cancelled_tasks.add(task_id)
            else:
                logger.warning(f"Cannot cancel task {task_id} with status {task.status}")
                return False
            
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_CANCELLED,
                    task_id,
                    {"name": task.name, "reason": "cancelled"}
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task cancelled event: {e}")
            
            logger.info(f"Task cancelled: {task_id} ({task.name})")
            return True
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id: ID of the task to get
            
        Returns:
            Task object or None if not found
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
        return task.result if task and task.status == TaskStatus.COMPLETED else None
    
    def get_task_error(self, task_id: str) -> Optional[Exception]:
        """
        Get the error of a failed task.
        
        Args:
            task_id: ID of the task to get error for
            
        Returns:
            Task error or None if task not found or not failed
        """
        task = self.tasks.get(task_id)
        return task.error if task and task.status == TaskStatus.FAILED else None
    
    def get_all_tasks(self) -> Dict[str, Task]:
        """
        Get all tasks.
        
        Returns:
            Dictionary of all tasks
        """
        return self.tasks.copy()
    
    def get_pending_tasks(self) -> Dict[str, Task]:
        """
        Get all pending tasks.
        
        Returns:
            Dictionary of pending tasks
        """
        return {task_id: task for task_id, task in self.tasks.items() if task.status == TaskStatus.PENDING}
    
    def get_running_tasks(self) -> Dict[str, Task]:
        """
        Get all running tasks.
        
        Returns:
            Dictionary of running tasks
        """
        return {task_id: task for task_id, task in self.tasks.items() if task.status == TaskStatus.RUNNING}
    
    def get_completed_tasks(self) -> Dict[str, Task]:
        """
        Get all completed tasks.
        
        Returns:
            Dictionary of completed tasks
        """
        return {task_id: task for task_id, task in self.tasks.items() if task.status == TaskStatus.COMPLETED}
    
    def get_failed_tasks(self) -> Dict[str, Task]:
        """
        Get all failed tasks.
        
        Returns:
            Dictionary of failed tasks
        """
        return {task_id: task for task_id, task in self.tasks.items() if task.status == TaskStatus.FAILED}
    
    def get_cancelled_tasks(self) -> Dict[str, Task]:
        """
        Get all cancelled tasks.
        
        Returns:
            Dictionary of cancelled tasks
        """
        return {task_id: task for task_id, task in self.tasks.items() if task.status == TaskStatus.CANCELLED}
    
    def get_waiting_tasks(self) -> Dict[str, Task]:
        """
        Get all waiting tasks.
        
        Returns:
            Dictionary of waiting tasks
        """
        return {task_id: task for task_id, task in self.tasks.items() if task.status == TaskStatus.WAITING}
    
    def get_tasks_by_tag(self, tag: str) -> Dict[str, Task]:
        """
        Get tasks by tag.
        
        Args:
            tag: Tag to filter by
            
        Returns:
            Dictionary of tasks with the specified tag
        """
        return {task_id: task for task_id, task in self.tasks.items() if tag in task.tags}
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get task manager metrics.
        
        Returns:
            Dictionary of task manager metrics
        """
        return {
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "running_tasks": len(self.running_tasks),
            "waiting_tasks": len(self.waiting_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "cancelled_tasks": len(self.cancelled_tasks),
            "total_tasks": len(self.tasks),
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
            except Exception as e:
                logger.error(f"Error stopping task manager: {e}")
        
        # Cancel all running tasks
        for task_id in list(self.running_tasks):
            self.cancel_task(task_id)
        
        logger.info("Task manager stopped")
    
    def stop(self):
        """Synchronous version of stop."""
        if not self.is_running:
            logger.warning("Task manager is not running")
            return
        
        self.is_running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
        
        # Cancel all running tasks
        for task_id in list(self.running_tasks):
            self.cancel_task(task_id)
        
        logger.info("Task manager stopped")
    
    async def _scheduler(self):
        """Scheduler loop for the task manager."""
        try:
            while self.is_running:
                await self._schedule_tasks()
                await asyncio.sleep(0.1)  # Small delay to prevent CPU hogging
        except asyncio.CancelledError:
            logger.info("Task scheduler cancelled")
            raise  # Re-raise to properly handle cancellation
        except Exception as e:
            logger.error(f"Error in task scheduler: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            # Attempt to restart scheduler after a delay
            if self.is_running:
                logger.info("Attempting to restart task scheduler...")
                await asyncio.sleep(1.0)
                if self.is_running:  # Check again in case stop() was called during sleep
                    self.scheduler_task = asyncio.create_task(self._scheduler())
    
    async def _schedule_tasks(self):
        """Schedule tasks for execution."""
        async with self.task_lock:
            # Check if we can run more tasks
            if len(self.running_tasks) >= self.max_concurrent_tasks:
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
                    if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                        can_run = False
                        break
                
                if can_run:
                    task.status = TaskStatus.PENDING
                    self.waiting_tasks.discard(task_id)
            
            # Get pending tasks sorted by priority
            pending_tasks = sorted(
                [(task_id, task) for task_id, task in self.tasks.items() if task.status == TaskStatus.PENDING],
                key=lambda x: x[1].priority.value,
                reverse=True  # Higher priority first
            )
            
            # Schedule tasks up to max_concurrent_tasks
            for task_id, task in pending_tasks:
                if len(self.running_tasks) >= self.max_concurrent_tasks:
                    break
                
                # Start task
                task.status = TaskStatus.RUNNING
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
        import psutil
        import time
        import os
        
        try:
            # Get current process
            process = psutil.Process(os.getpid())
            
            # Record start time and initial memory usage
            start_time = time.time()
            start_memory = process.memory_info().rss
            
            # Execute task with timeout if specified
            if task.timeout:
                task.result = await asyncio.wait_for(self._call_task_func(task), task.timeout)
            else:
                task.result = await self._call_task_func(task)
            
            # Record end time and peak memory usage
            end_time = time.time()
            end_memory = process.memory_info().rss
            
            # Calculate resource usage
            cpu_time = end_time - start_time
            memory_peak = max(0, end_memory - start_memory)
            
            # Update task resource usage
            task.resource_usage = {
                "cpu_time": cpu_time,
                "memory_peak": memory_peak
            }
            
            # Mark task as completed
            task.status = TaskStatus.COMPLETED
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
            for waiting_task_id in list(self.waiting_tasks):
                waiting_task = self.tasks.get(waiting_task_id)
                if not waiting_task:
                    self.waiting_tasks.discard(waiting_task_id)
                    continue
                
                if task.task_id in waiting_task.dependencies:
                    # Check if all dependencies are completed
                    can_run = True
                    for dep_id in waiting_task.dependencies:
                        dep_task = self.tasks.get(dep_id)
                        if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                            can_run = False
                            break
                    
                    if can_run:
                        waiting_task.status = TaskStatus.PENDING
                        self.waiting_tasks.discard(waiting_task_id)
        except asyncio.TimeoutError:
            # Handle timeout
            task.error = asyncio.TimeoutError(f"Task timed out after {task.timeout} seconds")
            await self._handle_task_error(task)
        except asyncio.CancelledError:
            # Handle cancellation
            task.error = asyncio.CancelledError("Task was cancelled")
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            self.running_tasks.discard(task.task_id)
            self.cancelled_tasks.add(task.task_id)
            
            # Clean up resources
            self._cleanup_task_resources(task)
            
            logger.info(f"Task cancelled: {task.task_id} ({task.name})")
            raise  # Re-raise to properly handle cancellation
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
            return await task.func(*task.args, **task.kwargs)
        else:
            return task.func(*task.args, **task.kwargs)
    
    async def _handle_task_error(self, task: Task):
        """
        Handle a task error.
        
        Args:
            task: Task that failed
        """
        # Check if we should retry
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.PENDING
            self.running_tasks.discard(task.task_id)
            
            logger.warning(f"Task {task.task_id} ({task.name}) failed, retrying ({task.retry_count}/{task.max_retries}): {task.error}")
            
            # Wait before retrying
            await asyncio.sleep(task.retry_delay * (2 ** (task.retry_count - 1)))  # Exponential backoff
        else:
            # Mark task as failed
            task.status = TaskStatus.FAILED
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
            logger.debug(f"Traceback: {traceback.format_exc()}")
    
    def execute_task(self, task_id: str, wait: bool = False) -> str:
        """
        Execute a task.
        
        Args:
            task_id: ID of the task to execute
            wait: Whether to wait for the task to complete
            
        Returns:
            Execution ID (same as task_id)
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        if not self.is_running:
            # Start the task manager if it's not running
            asyncio.create_task(self.start())
        
        # If the task is waiting, check if it can run now
        if task.status == TaskStatus.WAITING:
            can_run = True
            for dep_id in task.dependencies:
                dep_task = self.tasks.get(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    can_run = False
                    break
            
            if can_run:
                task.status = TaskStatus.PENDING
                self.waiting_tasks.discard(task_id)
        
        # If wait is True, run the task synchronously
        if wait:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self._execute_task_sync(task))
        
        return task_id
    
    async def _execute_task_sync(self, task: Task) -> str:
        """
        Execute a task synchronously.
        
        Args:
            task: Task to execute
            
        Returns:
            Task ID
        """
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        try:
            # Execute task with timeout if specified
            if task.timeout:
                task.result = await asyncio.wait_for(self._call_task_func(task), task.timeout)
            else:
                task.result = await self._call_task_func(task)
            
            # Mark task as completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            logger.info(f"Task completed synchronously: {task.task_id} ({task.name})")
        except Exception as e:
            # Mark task as failed
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = e
            
            logger.error(f"Task failed synchronously: {task.task_id} ({task.name}): {e}")
        
        return task.task_id

# Create a singleton instance
task_manager = TaskManager()
