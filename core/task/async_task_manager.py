#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AsyncTaskManager compatibility layer for WiseFlow.

This module provides a compatibility layer for the AsyncTaskManager referenced in
run_task_new.py, delegating to the unified task management system.
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, Callable, List, Union, Awaitable, Set

from core.task_management import (
    Task as UnifiedTask,
    TaskManager as UnifiedTaskManager,
    TaskPriority,
    TaskStatus
)

logger = logging.getLogger(__name__)

def create_task_id() -> str:
    """Create a unique task ID."""
    return str(uuid.uuid4())

class Task:
    """
    Task class for the AsyncTaskManager.
    
    This is a compatibility class that wraps the unified Task class.
    """
    
    def __init__(
        self,
        task_id: str,
        focus_id: str,
        function: Callable,
        args: tuple = (),
        auto_shutdown: bool = False
    ):
        """
        Initialize a task.
        
        Args:
            task_id: Unique identifier for the task
            focus_id: ID of the focus point
            function: Function to execute
            args: Arguments to pass to the function
            auto_shutdown: Whether to shut down after task completion
        """
        self.task_id = task_id
        self.focus_id = focus_id
        self.function = function
        self.args = args
        self.auto_shutdown = auto_shutdown
        
        # Status tracking
        self.status = "pending"
        self.result = None
        self.error = None

class AsyncTaskManager:
    """
    Async task manager compatibility class.
    
    This class provides a compatibility layer for the AsyncTaskManager referenced in
    run_task_new.py, delegating to the unified task management system.
    """
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize the async task manager.
        
        Args:
            max_workers: Maximum number of concurrent tasks
        """
        self.max_workers = max_workers
        self.unified_manager = UnifiedTaskManager(
            max_concurrent_tasks=max_workers,
            default_executor_type="async"
        )
        self.tasks: Dict[str, Task] = {}
        
        logger.info(f"AsyncTaskManager initialized with {max_workers} max workers")
    
    async def submit_task(self, task: Task) -> str:
        """
        Submit a task for execution.
        
        Args:
            task: Task to execute
            
        Returns:
            Task ID
        """
        logger.info(f"Submitting task {task.task_id} to AsyncTaskManager")
        
        # Store the task
        self.tasks[task.task_id] = task
        
        # Update task status
        task.status = "running"
        
        # Register with unified task manager
        unified_task_id = self.unified_manager.register_task(
            name=f"Task {task.task_id} (focus: {task.focus_id})",
            func=task.function,
            *task.args,
            task_id=task.task_id,
            priority=TaskPriority.NORMAL,
            executor_type="async",
            metadata={
                "focus_id": task.focus_id,
                "auto_shutdown": task.auto_shutdown,
                "legacy_task": True
            }
        )
        
        # Execute the task
        await self.unified_manager.execute_task(unified_task_id)
        
        return task.task_id
    
    def get_tasks_by_focus(self, focus_id: str) -> List[Task]:
        """
        Get tasks by focus ID.
        
        Args:
            focus_id: Focus ID to filter by
            
        Returns:
            List of tasks for the focus ID
        """
        return [task for task in self.tasks.values() if task.focus_id == focus_id]
    
    async def shutdown(self, wait: bool = True):
        """
        Shut down the task manager.
        
        Args:
            wait: Whether to wait for pending tasks to complete
        """
        logger.info("Shutting down AsyncTaskManager")
        await self.unified_manager.stop()

