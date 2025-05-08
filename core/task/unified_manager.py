"""
Unified Task Manager for WiseFlow.

This module provides a unified interface for task management, bridging the gap
between the old and new task management systems.
"""

import os
import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, Callable, List, Set, Union, Awaitable
from datetime import datetime
from enum import Enum, auto

from core.config import config
from core.task_manager import TaskManager as OldTaskManager
from core.thread_pool_manager import ThreadPoolManager
from core.task.monitor import TaskMonitor, TaskStatus
from core.event_system import (
    EventType, Event, publish_sync,
    create_task_event
)
from core.utils.error_handling import handle_exceptions, TaskError

logger = logging.getLogger(__name__)

class UnifiedTaskManager:
    """
    Unified Task Manager for WiseFlow.
    
    This class provides a unified interface for task management, bridging the gap
    between the old and new task management systems.
    """
    
    _instance = None
    
    def __new__(cls):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(UnifiedTaskManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the unified task manager."""
        if self._initialized:
            return
            
        # Initialize the old task manager
        self.old_task_manager = OldTaskManager()
        
        # Initialize the thread pool manager
        self.thread_pool = ThreadPoolManager()
        
        # Initialize the task monitor
        self.task_monitor = TaskMonitor()
        
        # Configuration
        self.use_new_system = config.get("USE_NEW_TASK_SYSTEM", True)
        
        self._initialized = True
        
        logger.info("Unified task manager initialized")
    
    async def register_task(
        self,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: str = "NORMAL",
        dependencies: List[str] = None,
        max_retries: int = 0,
        retry_delay: float = 1.0,
        timeout: Optional[float] = None,
        task_id: Optional[str] = None,
        task_type: str = "default",
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
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
            task_type: Type of task (for new system)
            description: Description of the task (for new system)
            metadata: Additional metadata for the task (for new system)
            
        Returns:
            Task ID
        """
        task_id = task_id or str(uuid.uuid4())
        
        if self.use_new_system:
            # Register with the new system
            self.task_monitor.register_task(
                task_id=task_id,
                task_type=task_type,
                description=description or name,
                metadata=metadata or {}
            )
        else:
            # Register with the old system
            from core.task_manager import TaskPriority
            priority_enum = getattr(TaskPriority, priority, TaskPriority.NORMAL)
            
            self.old_task_manager.register_task(
                name=name,
                func=func,
                args=args,
                kwargs=kwargs or {},
                priority=priority_enum,
                dependencies=dependencies or [],
                max_retries=max_retries,
                retry_delay=retry_delay,
                timeout=timeout,
                task_id=task_id
            )
        
        logger.info(f"Registered task {task_id} ({name})")
        return task_id
    
    async def execute_task(self, task_id: str, wait: bool = False) -> Union[str, Any]:
        """
        Execute a task.
        
        Args:
            task_id: ID of the task to execute
            wait: Whether to wait for the task to complete
            
        Returns:
            If wait is True, returns the task result, otherwise returns the task ID
        """
        if self.use_new_system:
            # Execute with the new system
            self.task_monitor.start_task(task_id)
            
            # Get task info
            task_info = self.task_monitor.get_task_info(task_id)
            if not task_info:
                logger.error(f"Task {task_id} not found")
                return task_id
            
            # Submit to thread pool
            self.thread_pool.submit(
                self._execute_task_wrapper,
                task_id,
                task_id=task_id,
                name=task_info.get('description', f"Task {task_id}")
            )
            
            if wait:
                # Wait for task to complete
                while True:
                    status = self.task_monitor.get_task_status(task_id)
                    if status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
                        break
                    await asyncio.sleep(0.1)
                
                # Return result
                return self.task_monitor.get_task_result(task_id)
        else:
            # Execute with the old system
            if wait:
                return await self.old_task_manager.execute_task(task_id)
            else:
                asyncio.create_task(self.old_task_manager.execute_task(task_id))
        
        return task_id
    
    def _execute_task_wrapper(self, task_id: str):
        """
        Wrapper function to execute a task.
        
        Args:
            task_id: ID of the task to execute
        """
        try:
            # Get task info
            task_info = self.task_monitor.get_task_info(task_id)
            if not task_info:
                logger.error(f"Task {task_id} not found")
                return
            
            # Execute task function
            func = task_info.get('metadata', {}).get('func')
            args = task_info.get('metadata', {}).get('args', ())
            kwargs = task_info.get('metadata', {}).get('kwargs', {})
            
            if not func:
                logger.error(f"Task {task_id} has no function to execute")
                self.task_monitor.fail_task(task_id, "No function to execute")
                return
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Mark task as completed
            self.task_monitor.complete_task(task_id, result)
            
            return result
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            self.task_monitor.fail_task(task_id, str(e))
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        if self.use_new_system:
            # Cancel with the new system
            return self.task_monitor.cancel_task(task_id, "Cancelled by user")
        else:
            # Cancel with the old system
            return self.old_task_manager.cancel_task(task_id)
    
    async def get_task_status(self, task_id: str) -> Optional[str]:
        """
        Get the status of a task.
        
        Args:
            task_id: ID of the task to get status for
            
        Returns:
            Task status or None if task not found
        """
        if self.use_new_system:
            # Get status from the new system
            return self.task_monitor.get_task_status(task_id)
        else:
            # Get status from the old system
            status = self.old_task_manager.get_task_status(task_id)
            return status.name if status else None
    
    async def get_task_result(self, task_id: str) -> Any:
        """
        Get the result of a task.
        
        Args:
            task_id: ID of the task to get result for
            
        Returns:
            Task result or None if task not found or not completed
        """
        if self.use_new_system:
            # Get result from the new system
            return self.task_monitor.get_task_result(task_id)
        else:
            # Get result from the old system
            return self.old_task_manager.get_task_result(task_id)
    
    async def get_task_error(self, task_id: str) -> Optional[str]:
        """
        Get the error of a failed task.
        
        Args:
            task_id: ID of the task to get error for
            
        Returns:
            Task error or None if task not found or not failed
        """
        if self.use_new_system:
            # Get error from the new system
            return self.task_monitor.get_task_error(task_id)
        else:
            # Get error from the old system
            task = self.old_task_manager.get_task(task_id)
            return str(task.error) if task and task.error else None
    
    async def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all tasks.
        
        Returns:
            Dictionary of all tasks
        """
        if self.use_new_system:
            # Get tasks from the new system
            return self.task_monitor.get_all_tasks()
        else:
            # Get tasks from the old system
            tasks = {}
            for task_id, task in self.old_task_manager.tasks.items():
                tasks[task_id] = task.to_dict()
            return tasks
    
    async def get_tasks_by_status(self, status: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all tasks with a specific status.
        
        Args:
            status: Task status
            
        Returns:
            Dictionary of tasks with the specified status
        """
        if self.use_new_system:
            # Get tasks from the new system
            return self.task_monitor.get_tasks_by_status(status)
        else:
            # Get tasks from the old system
            from core.task_manager import TaskStatus as OldTaskStatus
            status_enum = getattr(OldTaskStatus, status, None)
            if not status_enum:
                return {}
            
            tasks = {}
            for task_id, task in self.old_task_manager.tasks.items():
                if task.status == status_enum:
                    tasks[task_id] = task.to_dict()
            return tasks
    
    async def get_tasks_by_type(self, task_type: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all tasks of a specific type.
        
        Args:
            task_type: Task type
            
        Returns:
            Dictionary of tasks of the specified type
        """
        if self.use_new_system:
            # Get tasks from the new system
            return self.task_monitor.get_tasks_by_type(task_type)
        else:
            # The old system doesn't have task types
            return {}
    
    async def get_tasks_by_focus(self, focus_id: str) -> List[Dict[str, Any]]:
        """
        Get all tasks for a specific focus.
        
        Args:
            focus_id: Focus ID
            
        Returns:
            List of tasks for the specified focus
        """
        all_tasks = await self.get_all_tasks()
        
        focus_tasks = []
        for task_id, task_info in all_tasks.items():
            metadata = task_info.get('metadata', {})
            if isinstance(metadata, dict) and metadata.get('focus_id') == focus_id:
                focus_tasks.append(task_info)
            
        return focus_tasks
    
    async def cleanup_completed_tasks(self, max_age: float = 86400.0) -> int:
        """
        Clean up completed tasks older than max_age.
        
        Args:
            max_age: Maximum age of completed tasks in seconds
            
        Returns:
            Number of tasks cleaned up
        """
        if self.use_new_system:
            # Clean up with the new system
            return self.task_monitor.cleanup_completed_tasks(max_age)
        else:
            # The old system doesn't have a cleanup method
            # Implement a basic cleanup
            cleaned_up = 0
            current_time = datetime.now()
            
            for task_id, task in list(self.old_task_manager.tasks.items()):
                if task.status in [OldTaskStatus.COMPLETED, OldTaskStatus.FAILED, OldTaskStatus.CANCELLED]:
                    if task.completed_at and (current_time - task.completed_at).total_seconds() > max_age:
                        # Remove task
                        del self.old_task_manager.tasks[task_id]
                        cleaned_up += 1
            
            logger.info(f"Cleaned up {cleaned_up} completed tasks from old system")
            return cleaned_up
    
    async def shutdown(self):
        """Shutdown the task manager."""
        if self.use_new_system:
            # No explicit shutdown for the task monitor
            pass
        else:
            # Shutdown the old system
            await self.old_task_manager.stop()
        
        # Shutdown the thread pool
        self.thread_pool.shutdown(wait=True)
        
        logger.info("Unified task manager shutdown")

# Create a singleton instance
unified_task_manager = UnifiedTaskManager()

