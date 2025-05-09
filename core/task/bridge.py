"""
Task system bridge for WiseFlow.

This module provides a bridge between the old and new task execution systems
to ensure consistent task state management and resource cleanup.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Callable, List, Set, Union, Awaitable

from core.task_manager import TaskManager, TaskStatus as OldTaskStatus, TaskPriority
from core.thread_pool_manager import ThreadPoolManager
from core.task.monitor import TaskMonitor, TaskStatus as NewTaskStatus

logger = logging.getLogger(__name__)

# Get singleton instances
task_manager = TaskManager()
thread_pool_manager = ThreadPoolManager()
task_monitor = TaskMonitor()

# Map between old and new task status values
STATUS_MAP_OLD_TO_NEW = {
    OldTaskStatus.PENDING: NewTaskStatus.PENDING,
    OldTaskStatus.RUNNING: NewTaskStatus.RUNNING,
    OldTaskStatus.COMPLETED: NewTaskStatus.COMPLETED,
    OldTaskStatus.FAILED: NewTaskStatus.FAILED,
    OldTaskStatus.CANCELLED: NewTaskStatus.CANCELLED,
    OldTaskStatus.WAITING: NewTaskStatus.PENDING  # Map WAITING to PENDING in new system
}

STATUS_MAP_NEW_TO_OLD = {
    NewTaskStatus.PENDING: OldTaskStatus.PENDING,
    NewTaskStatus.RUNNING: OldTaskStatus.RUNNING,
    NewTaskStatus.COMPLETED: OldTaskStatus.COMPLETED,
    NewTaskStatus.FAILED: OldTaskStatus.FAILED,
    NewTaskStatus.CANCELLED: OldTaskStatus.CANCELLED
}

class TaskBridge:
    """
    Bridge between old and new task systems.
    
    This class provides methods to ensure consistent task state management
    and resource cleanup between the old and new task systems.
    """
    
    _instance = None
    
    def __new__(cls):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(TaskBridge, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the task bridge."""
        if self._initialized:
            return
        
        self.task_mapping = {}  # Map between old and new task IDs
        self._initialized = True
        
        logger.info("Task bridge initialized")
    
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
        task_id: Optional[str] = None,
        use_old_system: bool = True
    ) -> str:
        """
        Register a task with both task systems.
        
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
            use_old_system: Whether to use the old task system for execution
            
        Returns:
            Task ID
        """
        # Register with the old task system
        old_task_id = task_manager.register_task(
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            dependencies=dependencies,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            task_id=task_id
        )
        
        # Register with the new task system
        new_task_id = task_monitor.register_task(
            task_id=old_task_id,
            task_type=name,
            description=f"Task {name} with priority {priority.name}",
            metadata={
                "priority": priority.name,
                "dependencies": dependencies or [],
                "max_retries": max_retries,
                "retry_delay": retry_delay,
                "timeout": timeout
            }
        )
        
        # Store mapping
        self.task_mapping[old_task_id] = new_task_id
        
        logger.info(f"Task registered with bridge: {old_task_id} ({name})")
        return old_task_id
    
    def start_task(self, task_id: str) -> bool:
        """
        Start a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Get task from old system
        task = task_manager.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found in old system")
            return False
        
        # Start task in new system
        new_task_id = self.task_mapping.get(task_id, task_id)
        task_monitor.start_task(new_task_id)
        
        logger.info(f"Task started: {task_id}")
        return True
    
    def update_task_progress(self, task_id: str, progress: float, message: Optional[str] = None) -> bool:
        """
        Update task progress.
        
        Args:
            task_id: Task ID
            progress: Progress value (0.0 to 1.0)
            message: Optional progress message
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Update progress in new system
        new_task_id = self.task_mapping.get(task_id, task_id)
        return task_monitor.update_task_progress(new_task_id, progress, message)
    
    def complete_task(self, task_id: str, result: Any = None) -> bool:
        """
        Mark a task as completed.
        
        Args:
            task_id: Task ID
            result: Task result
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Get task from old system
        task = task_manager.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found in old system")
            return False
        
        # Update task in old system
        task.status = OldTaskStatus.COMPLETED
        task.result = result
        task.completed_at = task_monitor.tasks[self.task_mapping.get(task_id, task_id)]["completed_at"]
        
        # Remove from running tasks
        task_manager.running_tasks.discard(task_id)
        task_manager.completed_tasks.add(task_id)
        
        # Complete task in new system
        new_task_id = self.task_mapping.get(task_id, task_id)
        task_monitor.complete_task(new_task_id, result)
        
        logger.info(f"Task completed: {task_id}")
        return True
    
    def fail_task(self, task_id: str, error: Union[str, Exception]) -> bool:
        """
        Mark a task as failed.
        
        Args:
            task_id: Task ID
            error: Error message or exception
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Get task from old system
        task = task_manager.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found in old system")
            return False
        
        # Update task in old system
        task.status = OldTaskStatus.FAILED
        task.error = error
        task.completed_at = task_monitor.tasks[self.task_mapping.get(task_id, task_id)]["completed_at"]
        
        # Remove from running tasks
        task_manager.running_tasks.discard(task_id)
        task_manager.failed_tasks.add(task_id)
        
        # Fail task in new system
        new_task_id = self.task_mapping.get(task_id, task_id)
        task_monitor.fail_task(new_task_id, error)
        
        logger.info(f"Task failed: {task_id}")
        return True
    
    def cancel_task(self, task_id: str, reason: Optional[str] = None) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: Task ID
            reason: Optional reason for cancellation
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Cancel task in old system
        result = task_manager.cancel_task(task_id)
        
        # Cancel task in new system
        new_task_id = self.task_mapping.get(task_id, task_id)
        task_monitor.cancel_task(new_task_id, reason)
        
        logger.info(f"Task cancelled: {task_id}")
        return result
    
    def get_task_status(self, task_id: str) -> Optional[OldTaskStatus]:
        """
        Get task status.
        
        Args:
            task_id: Task ID
            
        Returns:
            Optional[TaskStatus]: Task status if found, None otherwise
        """
        # Get status from old system
        return task_manager.get_task_status(task_id)
    
    def get_task_result(self, task_id: str) -> Any:
        """
        Get task result.
        
        Args:
            task_id: Task ID
            
        Returns:
            Any: Task result if found and completed, None otherwise
        """
        # Get result from old system
        return task_manager.get_task_result(task_id)
    
    def get_task_error(self, task_id: str) -> Optional[str]:
        """
        Get task error.
        
        Args:
            task_id: Task ID
            
        Returns:
            Optional[str]: Task error if found and failed, None otherwise
        """
        # Get error from old system
        task = task_manager.get_task(task_id)
        return str(task.error) if task and task.error else None
    
    def cleanup_task(self, task_id: str) -> bool:
        """
        Clean up task resources.
        
        Args:
            task_id: Task ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Clean up in old system
        task = task_manager.get_task(task_id)
        if task:
            task_manager._cleanup_task_resources(task)
        
        # Clean up in new system
        new_task_id = self.task_mapping.get(task_id, task_id)
        task_monitor.cleanup_task(new_task_id)
        
        # Remove from mapping
        if task_id in self.task_mapping:
            del self.task_mapping[task_id]
        
        logger.info(f"Task cleaned up: {task_id}")
        return True
    
    def cleanup_completed_tasks(self, max_age: float = 86400.0) -> int:
        """
        Clean up completed tasks older than max_age.
        
        Args:
            max_age: Maximum age of completed tasks in seconds
            
        Returns:
            int: Number of tasks cleaned up
        """
        # Clean up in new system
        cleaned_up = task_monitor.cleanup_completed_tasks(max_age)
        
        # Clean up in old system
        for task_id, task in list(task_manager.tasks.items()):
            if task.status in [OldTaskStatus.COMPLETED, OldTaskStatus.FAILED, OldTaskStatus.CANCELLED]:
                if task.completed_at and (datetime.now() - task.completed_at).total_seconds() > max_age:
                    self.cleanup_task(task_id)
        
        return cleaned_up

# Create a singleton instance
task_bridge = TaskBridge()

