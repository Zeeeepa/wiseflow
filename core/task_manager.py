"""
Task management module for WiseFlow.

This module provides functionality to manage and execute tasks asynchronously.
"""

import os
import time
import asyncio
import logging
import uuid
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
            timeout=timeout
        )
        
        # Add task to manager
        self.tasks[task_id] = task
        
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
                    {"name": task.name, "reason": "cancelled by user"}
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task cancelled event: {e}")
            
            logger.info(f"Task cancelled: {task_id} ({task.name})")
            return True
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False
    
    def _cleanup_task_resources(self, task: Task) -> None:
        """
        Clean up resources allocated to a task.
        
        Args:
            task: Task to clean up resources for
        """
        # Implement resource cleanup logic here
        # This is a placeholder for actual resource cleanup
        pass

# Create a singleton instance
task_manager = TaskManager()
