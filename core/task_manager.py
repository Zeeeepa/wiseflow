"""
Task management module for WiseFlow.

This module provides functionality to manage and execute tasks asynchronously.
This is a compatibility layer that delegates to the unified task management system.
"""

import os
import time
import asyncio
import logging
import uuid
import warnings
from typing import Dict, Any, Optional, Callable, List, Set, Union, Awaitable
from datetime import datetime
from enum import Enum, auto

warnings.warn(
    "core.task_manager is deprecated and will be removed in a future version. "
    "Use core.task_management.task_manager instead.",
    DeprecationWarning,
    stacklevel=2
)

from core.config import config
from core.event_system import (
    EventType, Event, publish_sync,
    create_task_event
)

# Import the unified task management system
from core.task_management import (
    Task as UnifiedTask,
    TaskManager as UnifiedTaskManager,
    TaskPriority as UnifiedTaskPriority,
    TaskStatus as UnifiedTaskStatus,
    TaskDependencyError as UnifiedTaskDependencyError
)

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
    This is a compatibility class that wraps the unified Task class.
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
        timeout: Optional[float] = None
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
        
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.retry_count = 0
        self.task_object = None
    
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
            "error": str(self.error) if self.error else None
        }

class TaskManager:
    """
    Task manager for WiseFlow.
    
    This class provides functionality to manage and execute tasks asynchronously.
    This is a compatibility class that delegates to the unified task management system.
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
        
        # Initialize the unified task manager
        self.unified_manager = UnifiedTaskManager(
            max_concurrent_tasks=self.max_concurrent_tasks,
            default_executor_type="async"
        )
        
        self._initialized = True
        
        logger.info("Task manager initialized")
    
    def register_task(
        self,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: List[str] = None,
        max_retries: int = 0,
        retry_delay: float = 1.0,
        timeout: Optional[float] = None,
        task_id: Optional[str] = None
    ) -> str:
        """
        Register a task with the task manager.
        
        Args:
            name: Name of the task
            func: Function to execute
            args: Arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
            priority: Priority of the task
            dependencies: List of task IDs that must complete before this task
            max_retries: Maximum number of retries if the task fails
            retry_delay: Delay in seconds between retries
            timeout: Timeout in seconds for the task
            task_id: Optional task ID, if not provided a new one will be generated
            
        Returns:
            Task ID
        """
        task_id = task_id or create_task_id()
        
        # Map priority to unified priority
        unified_priority = UnifiedTaskPriority.NORMAL
        if priority == TaskPriority.LOW:
            unified_priority = UnifiedTaskPriority.LOW
        elif priority == TaskPriority.HIGH:
            unified_priority = UnifiedTaskPriority.HIGH
        elif priority == TaskPriority.CRITICAL:
            unified_priority = UnifiedTaskPriority.CRITICAL
        
        try:
            # Register with unified task manager
            unified_task_id = self.unified_manager.register_task(
                name=name,
                func=func,
                *args,
                task_id=task_id,
                kwargs=kwargs,
                priority=unified_priority,
                dependencies=dependencies,
                max_retries=max_retries,
                retry_delay=retry_delay,
                timeout=timeout,
                metadata={"legacy_task": True}
            )
            
            # Create legacy task object for compatibility
            task = Task(
                task_id=task_id,
                name=name,
                func=func,
                args=args,
                kwargs=kwargs,
                priority=priority,
                dependencies=dependencies,
                max_retries=max_retries,
                retry_delay=retry_delay,
                timeout=timeout
            )
            
            # Add task to manager
            self.tasks[task_id] = task
            
            logger.info(f"Task registered: {task_id} ({name})")
            return task_id
            
        except UnifiedTaskDependencyError as e:
            # Convert to legacy exception
            raise TaskDependencyError(str(e))
    
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
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                
                # Update task sets
                self.running_tasks.discard(task_id)
                self.cancelled_tasks.add(task_id)
        
        return result
    
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
        unified_status = self.unified_manager.get_task_status(task_id)
        if unified_status is None:
            return None
        
        # Map unified status to legacy status
        status_map = {
            UnifiedTaskStatus.PENDING: TaskStatus.PENDING,
            UnifiedTaskStatus.RUNNING: TaskStatus.RUNNING,
            UnifiedTaskStatus.COMPLETED: TaskStatus.COMPLETED,
            UnifiedTaskStatus.FAILED: TaskStatus.FAILED,
            UnifiedTaskStatus.CANCELLED: TaskStatus.CANCELLED,
            UnifiedTaskStatus.WAITING: TaskStatus.WAITING
        }
        
        return status_map.get(unified_status, TaskStatus.PENDING)
    
    def get_task_result(self, task_id: str) -> Any:
        """
        Get the result of a task.
        
        Args:
            task_id: ID of the task to get result for
            
        Returns:
            Task result or None if task not found or not completed
        """
        return self.unified_manager.get_task_result(task_id)
    
    def get_task_error(self, task_id: str) -> Optional[Exception]:
        """
        Get the error of a failed task.
        
        Args:
            task_id: ID of the task to get error for
            
        Returns:
            Task error or None if task not found or not failed
        """
        return self.unified_manager.get_task_error(task_id)
    
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
    
    async def start(self):
        """Start the task manager."""
        if self.is_running:
            logger.warning("Task manager is already running")
            return
        
        self.is_running = True
        
        # Start the unified task manager
        await self.unified_manager.start()
        
        logger.info("Task manager started")
    
    async def stop(self):
        """Stop the task manager."""
        if not self.is_running:
            logger.warning("Task manager is not running")
            return
        
        self.is_running = False
        
        # Stop the unified task manager
        await self.unified_manager.stop()
        
        logger.info("Task manager stopped")
    
    async def execute_task(self, task_id: str, wait: bool = True) -> Any:
        """
        Execute a task.
        
        Args:
            task_id: ID of the task to execute
            wait: Whether to wait for the task to complete
            
        Returns:
            Task result if wait is True, otherwise None
        """
        return await self.unified_manager.execute_task(task_id, wait)

# Create a singleton instance
task_manager = TaskManager()
