"""
Pydantic models for task management.

This module defines the Pydantic models used for task management operations.
"""

from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from core.task_management.task_manager import TaskPriority


class TaskRegistrationParams(BaseModel):
    """Parameters for registering tasks with the task manager."""
    
    name: str = Field(..., description="Name of the task")
    func: Callable = Field(..., description="Function to execute")
    task_id: Optional[str] = Field(None, description="Optional task ID, if not provided a new one will be generated")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="Keyword arguments to pass to the function")
    priority: TaskPriority = Field(TaskPriority.NORMAL, description="Priority of the task")
    dependencies: List[str] = Field(default_factory=list, description="List of task IDs that must complete before this task")
    max_retries: int = Field(0, description="Maximum number of retries if the task fails")
    retry_delay: float = Field(1.0, description="Delay in seconds between retries")
    timeout: Optional[float] = Field(None, description="Timeout in seconds for the task")
    description: str = Field("", description="Detailed description of the task")
    tags: List[str] = Field(default_factory=list, description="List of tags for categorizing the task")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for the task")
    executor_type: Optional[str] = Field(None, description="Type of executor to use (sequential, thread_pool, or async)")

