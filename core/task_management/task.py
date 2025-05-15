"""
Task definition for the unified task management system.

This module provides the Task class and related enums for the task management system.
"""

import uuid
from enum import Enum, auto
from typing import Dict, Any, Optional, Callable, List, Union, Awaitable
from datetime import datetime

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

def create_task_id() -> str:
    """Create a unique task ID."""
    return str(uuid.uuid4())

class Task:
    """
    Task class for the unified task management system.
    
    This class represents a task that can be executed by the task manager.
    """
    
    def __init__(
        self,
        task_id: Optional[str] = None,
        name: str = "Unnamed Task",
        func: Optional[Callable] = None,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: Optional[List[str]] = None,
        max_retries: int = 0,
        retry_delay: float = 1.0,
        timeout: Optional[float] = None,
        description: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a task.
        
        Args:
            task_id: Unique identifier for the task (generated if not provided)
            name: Name of the task
            func: Function to execute
            args: Arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
            priority: Priority of the task
            dependencies: List of task IDs that must complete before this task
            max_retries: Maximum number of retries if the task fails
            retry_delay: Delay in seconds between retries
            timeout: Timeout in seconds for the task
            description: Detailed description of the task
            tags: List of tags for categorizing the task
            metadata: Additional metadata for the task
        """
        self.task_id = task_id or create_task_id()
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
        self.metadata = metadata or {}
        
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.retry_count = 0
        self.progress = 0.0
        self.progress_message = ""
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
            "progress": self.progress,
            "progress_message": self.progress_message,
            "description": self.description,
            "tags": self.tags,
            "metadata": self.metadata,
            "error": str(self.error) if self.error else None
        }
    
    def update_progress(self, progress: float, message: str = ""):
        """
        Update the progress of the task.
        
        Args:
            progress: Progress value between 0.0 and 1.0
            message: Optional progress message
        """
        self.progress = max(0.0, min(1.0, progress))
        self.progress_message = message
    
    def is_ready(self, completed_tasks: List[str]) -> bool:
        """
        Check if the task is ready to run.
        
        Args:
            completed_tasks: List of completed task IDs
            
        Returns:
            True if all dependencies are satisfied, False otherwise
        """
        return all(dep in completed_tasks for dep in self.dependencies)
    
    def __str__(self) -> str:
        """String representation of the task."""
        return f"Task({self.task_id}, {self.name}, {self.status.name})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the task."""
        return (
            f"Task(task_id={self.task_id}, name={self.name}, "
            f"status={self.status.name}, priority={self.priority.name})"
        )

