"""
Pydantic models for research operations.

This module defines the Pydantic models used for research operations.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.task_management.task_manager import TaskPriority


class ResearchTaskParams(BaseModel):
    """Parameters for creating research tasks."""
    
    topic: str = Field(..., description="Research topic to investigate")
    config: Optional[Dict[str, Any]] = Field(None, description="Research configuration settings")
    use_multi_agent: bool = Field(False, description="Whether to use the multi-agent approach")
    priority: TaskPriority = Field(TaskPriority.NORMAL, description="Priority of the task")
    tags: List[str] = Field(default_factory=lambda: ["research"], description="List of tags for categorizing the task")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for the task")

