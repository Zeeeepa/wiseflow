"""
Task management module for WiseFlow.

This module provides functionality to manage and execute tasks asynchronously.
"""

import os
import time
import asyncio
import logging
import uuid
import threading
from typing import Dict, Any, Optional, Callable, List, Set, Union, Awaitable
from datetime import datetime
from enum import Enum, auto
from concurrent.futures import ThreadPoolExecutor

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
        self._future = None
        self._lock = asyncio.Lock()
    
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
            "tags": self.tags
        }
    
    async def cancel(self) -> bool:
        """
        Cancel the task if it's running.
        
        Returns:
            True if the task was cancelled, False otherwise
        """
        async with self._lock:
            if self.status == TaskStatus.RUNNING and self.task_object:
                if not self.task_object.done():
                    self.task_object.cancel()
                    return True
            return False

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
        
        # Thread pool for executing CPU-bound tasks
        self.thread_pool = ThreadPoolExecutor(
            max_workers=config.get("TASK_THREAD_POOL_SIZE", os.cpu_count() or 4),
            thread_name_prefix="task_worker"
        )
        
        # Task metrics
        self._metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_cancelled": 0,
            "total_execution_time": 0.0,
            "avg_execution_time": 0.0
        }
        self._metrics_lock = threading.RLock()
        
        self._initialized = True
        
        logger.info(f"Task manager initialized with max {self.max_concurrent_tasks} concurrent tasks")
    
    def register_task(
        self,
        name: str,
        func: Callable,
        *args,
        kwargs: dict = None,
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
            kwargs: Keyword arguments to pass to the function
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
            kwargs=kwargs or {},
            priority=priority,
            dependencies=dependencies or [],
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            description=description,
            tags=tags
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
                # Task has dependencies that are not completed yet
                task.status = TaskStatus.WAITING
                self.waiting_tasks.add(task_id)
                logger.info(f"Task {task_id} ({name}) is waiting for dependencies")
        
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
        
        logger.info(f"Task registered: {task_id} ({name})")
        return task_id
    
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
        
        if task.status == TaskStatus.RUNNING:
            # Create a task to cancel the running task
            asyncio.create_task(task.cancel())
            
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
        
        # Update metrics
        with self._metrics_lock:
            self._metrics["tasks_cancelled"] += 1
        
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
        Get all tasks with a specific tag.
        
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
            Dictionary of metrics
        """
        with self._metrics_lock:
            metrics = self._metrics.copy()
        
        # Add current task counts
        metrics.update({
            "pending_tasks": len(self.get_pending_tasks()),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "cancelled_tasks": len(self.cancelled_tasks),
            "waiting_tasks": len(self.waiting_tasks),
            "total_tasks": len(self.tasks)
        })
        
        return metrics
    
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
                    logger.info(f"Task {task_id} ({task.name}) is now ready to run")
            
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
        start_time = time.time()
        
        try:
            # Execute task with timeout if specified
            if task.timeout:
                task.result = await asyncio.wait_for(self._call_task_func(task), task.timeout)
            else:
                task.result = await self._call_task_func(task)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Mark task as completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            self.running_tasks.discard(task.task_id)
            self.completed_tasks.add(task.task_id)
            
            # Update metrics
            with self._metrics_lock:
                self._metrics["tasks_completed"] += 1
                self._metrics["total_execution_time"] += execution_time
                if self._metrics["tasks_completed"] > 0:
                    self._metrics["avg_execution_time"] = (
                        self._metrics["total_execution_time"] / self._metrics["tasks_completed"]
                    )
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_COMPLETED,
                    task.task_id,
                    {
                        "name": task.name,
                        "execution_time": execution_time
                    }
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task completed event: {e}")
            
            logger.info(f"Task completed: {task.task_id} ({task.name}) in {execution_time:.2f}s")
            
            # Check for waiting tasks that depend on this task
            await self._check_dependent_tasks(task.task_id)
        except asyncio.TimeoutError:
            # Handle timeout
            execution_time = time.time() - start_time
            task.error = asyncio.TimeoutError(f"Task timed out after {task.timeout} seconds")
            logger.warning(f"Task {task.task_id} ({task.name}) timed out after {task.timeout}s")
            await self._handle_task_error(task, execution_time)
        except asyncio.CancelledError:
            # Handle cancellation
            execution_time = time.time() - start_time
            task.error = asyncio.CancelledError("Task was cancelled")
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            self.running_tasks.discard(task.task_id)
            self.cancelled_tasks.add(task.task_id)
            
            # Update metrics
            with self._metrics_lock:
                self._metrics["tasks_cancelled"] += 1
            
            logger.info(f"Task cancelled: {task.task_id} ({task.name}) after {execution_time:.2f}s")
        except Exception as e:
            # Handle other errors
            execution_time = time.time() - start_time
            task.error = e
            logger.error(f"Task {task.task_id} ({task.name}) failed: {e}")
            await self._handle_task_error(task, execution_time)
    
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
    
    async def _handle_task_error(self, task: Task, execution_time: float):
        """
        Handle a task error.
        
        Args:
            task: Task that failed
            execution_time: Time spent executing the task before it failed
        """
        # Check if we should retry
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.PENDING
            self.running_tasks.discard(task.task_id)
            
            # Calculate retry delay with exponential backoff
            retry_delay = task.retry_delay * (2 ** (task.retry_count - 1))
            
            logger.warning(
                f"Task {task.task_id} ({task.name}) failed, retrying "
                f"({task.retry_count}/{task.max_retries}) in {retry_delay:.2f}s: {task.error}"
            )
            
            # Wait before retrying
            await asyncio.sleep(retry_delay)
        else:
            # Mark task as failed
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            self.running_tasks.discard(task.task_id)
            self.failed_tasks.add(task.task_id)
            
            # Update metrics
            with self._metrics_lock:
                self._metrics["tasks_failed"] += 1
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_FAILED,
                    task.task_id,
                    {
                        "name": task.name,
                        "error": str(task.error),
                        "execution_time": execution_time
                    }
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task failed event: {e}")
            
            logger.error(f"Task failed: {task.task_id} ({task.name}) after {execution_time:.2f}s: {task.error}")
    
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
                    if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                        can_run = False
                        break
                
                if can_run:
                    waiting_task.status = TaskStatus.PENDING
                    self.waiting_tasks.discard(waiting_task_id)
                    logger.info(f"Task {waiting_task_id} ({waiting_task.name}) is now ready to run")
    
    def cleanup_completed_tasks(self, max_age_seconds: int = 3600):
        """
        Clean up old completed, failed, and cancelled tasks.
        
        Args:
            max_age_seconds: Maximum age of tasks to keep in seconds
        """
        now = datetime.now()
        count = 0
        
        for task_id in list(self.completed_tasks):
            task = self.tasks.get(task_id)
            if not task:
                self.completed_tasks.discard(task_id)
                continue
            
            if task.completed_at and (now - task.completed_at).total_seconds() > max_age_seconds:
                del self.tasks[task_id]
                self.completed_tasks.discard(task_id)
                count += 1
        
        for task_id in list(self.failed_tasks):
            task = self.tasks.get(task_id)
            if not task:
                self.failed_tasks.discard(task_id)
                continue
            
            if task.completed_at and (now - task.completed_at).total_seconds() > max_age_seconds:
                del self.tasks[task_id]
                self.failed_tasks.discard(task_id)
                count += 1
        
        for task_id in list(self.cancelled_tasks):
            task = self.tasks.get(task_id)
            if not task:
                self.cancelled_tasks.discard(task_id)
                continue
            
            if task.completed_at and (now - task.completed_at).total_seconds() > max_age_seconds:
                del self.tasks[task_id]
                self.cancelled_tasks.discard(task_id)
                count += 1
        
        if count > 0:
            logger.info(f"Cleaned up {count} old tasks")

# Create a singleton instance
task_manager = TaskManager()
