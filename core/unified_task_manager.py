"""
Unified task management module for WiseFlow.

This module provides a unified task management system that combines functionality
from both task_manager.py and thread_pool_manager.py.
"""

import os
import asyncio
import logging
import uuid
import concurrent.futures
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
    """Task status states."""
    PENDING = auto()
    WAITING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    TIMEOUT = auto()

class Task:
    """
    Task class for both synchronous and asynchronous task execution.
    
    Attributes:
        task_id: Unique identifier for the task
        name: Name of the task
        function: Function to execute
        args: Arguments to pass to the function
        kwargs: Keyword arguments to pass to the function
        priority: Priority of the task
        dependencies: List of task IDs that must complete before this task
        status: Current status of the task
        result: Result of the task execution
        error: Error that occurred during task execution
        created_at: Time when the task was created
        started_at: Time when the task execution started
        completed_at: Time when the task execution completed
        timeout: Maximum time (in seconds) the task is allowed to run
        auto_shutdown: Whether to automatically shut down after completion
        tags: List of tags associated with the task
        metadata: Additional metadata for the task
        task_object: The actual task object (Future or Task)
    """
    
    def __init__(
        self,
        task_id: Optional[str] = None,
        name: Optional[str] = None,
        function: Optional[Callable] = None,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        auto_shutdown: bool = False,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a task.
        
        Args:
            task_id: Unique identifier for the task (generated if not provided)
            name: Name of the task (defaults to function name)
            function: Function to execute
            args: Arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
            priority: Priority of the task
            dependencies: List of task IDs that must complete before this task
            timeout: Maximum time (in seconds) the task is allowed to run
            auto_shutdown: Whether to automatically shut down after completion
            tags: List of tags associated with the task
            metadata: Additional metadata for the task
        """
        self.task_id = task_id or str(uuid.uuid4())
        self.name = name or (function.__name__ if function else "unnamed_task")
        self.function = function
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.priority = priority
        self.dependencies = dependencies or []
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.timeout = timeout
        self.auto_shutdown = auto_shutdown
        self.tags = tags or []
        self.metadata = metadata or {}
        self.task_object = None
    
    def __str__(self) -> str:
        """String representation of the task."""
        return f"Task({self.task_id}, {self.name}, {self.status.name})"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status.name,
            "priority": self.priority.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "dependencies": self.dependencies,
            "timeout": self.timeout,
            "auto_shutdown": self.auto_shutdown,
            "tags": self.tags,
            "metadata": self.metadata
        }

class UnifiedTaskManager:
    """
    Unified task manager that combines functionality from TaskManager and ThreadPoolManager.
    
    This class provides both synchronous and asynchronous task execution capabilities.
    """
    
    def __init__(
        self,
        max_workers: int = None,
        thread_name_prefix: str = "wiseflow-worker"
    ):
        """
        Initialize the unified task manager.
        
        Args:
            max_workers: Maximum number of worker threads (default: CPU count * 2)
            thread_name_prefix: Prefix for worker thread names
        """
        # Set default max_workers if not provided
        if max_workers is None:
            max_workers = os.cpu_count() * 2
        
        # Initialize thread pool
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=thread_name_prefix
        )
        
        # Task storage
        self.tasks = {}
        self.pending_tasks = set()
        self.waiting_tasks = set()
        self.running_tasks = set()
        self.completed_tasks = set()
        self.failed_tasks = set()
        self.cancelled_tasks = set()
        self.timeout_tasks = set()
        
        # Task execution tracking
        self.task_executions = {}
        
        # Shutdown flag
        self.is_shutdown = False
        
        logger.info(f"Initialized UnifiedTaskManager with {max_workers} workers")
    
    def register_task(
        self,
        function: Callable,
        args: tuple = None,
        kwargs: dict = None,
        task_id: str = None,
        name: str = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: List[str] = None,
        timeout: float = None,
        auto_shutdown: bool = False,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Register a task for execution.
        
        Args:
            function: Function to execute
            args: Arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
            task_id: Unique identifier for the task (generated if not provided)
            name: Name of the task (defaults to function name)
            priority: Priority of the task
            dependencies: List of task IDs that must complete before this task
            timeout: Maximum time (in seconds) the task is allowed to run
            auto_shutdown: Whether to automatically shut down after completion
            tags: List of tags associated with the task
            metadata: Additional metadata for the task
            
        Returns:
            Task ID
        """
        # Create task
        task = Task(
            task_id=task_id,
            name=name or function.__name__,
            function=function,
            args=args,
            kwargs=kwargs,
            priority=priority,
            dependencies=dependencies,
            timeout=timeout,
            auto_shutdown=auto_shutdown,
            tags=tags,
            metadata=metadata
        )
        
        # Add task to manager
        self.tasks[task.task_id] = task
        self.pending_tasks.add(task.task_id)
        
        # Publish event
        try:
            event = create_task_event(
                EventType.TASK_REGISTERED,
                task.task_id,
                {"name": task.name}
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish task registered event: {e}")
        
        logger.info(f"Task registered: {task.task_id} ({task.name})")
        return task.task_id
    
    def execute_task(self, task_id: str, wait: bool = False) -> Optional[str]:
        """
        Execute a registered task.
        
        Args:
            task_id: ID of the task to execute
            wait: Whether to wait for the task to complete
            
        Returns:
            Execution ID if successful, None otherwise
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return None
        
        # Check if task is already running
        if task.status == TaskStatus.RUNNING:
            logger.warning(f"Task {task_id} is already running")
            return None
        
        # Check if task is already completed
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            logger.warning(f"Task {task_id} is already {task.status.name}")
            return None
        
        # Check dependencies
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task:
                logger.warning(f"Dependency {dep_id} not found for task {task_id}")
                task.status = TaskStatus.FAILED
                task.error = TaskError(f"Dependency {dep_id} not found")
                self.pending_tasks.discard(task_id)
                self.failed_tasks.add(task_id)
                return None
            
            if dep_task.status != TaskStatus.COMPLETED:
                logger.warning(f"Dependency {dep_id} not completed for task {task_id}")
                task.status = TaskStatus.WAITING
                self.pending_tasks.discard(task_id)
                self.waiting_tasks.add(task_id)
                return None
        
        # Generate execution ID
        execution_id = str(uuid.uuid4())
        
        # Update task status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.pending_tasks.discard(task_id)
        self.waiting_tasks.discard(task_id)
        self.running_tasks.add(task_id)
        
        # Determine if function is async
        is_async = asyncio.iscoroutinefunction(task.function)
        
        # Execute task
        try:
            if is_async:
                # For async functions, create an asyncio task
                loop = asyncio.get_event_loop()
                task_obj = loop.create_task(self._execute_async_task(task))
                task.task_object = task_obj
                
                if wait:
                    # Wait for task to complete
                    loop.run_until_complete(task_obj)
            else:
                # For sync functions, submit to thread pool
                future = self.thread_pool.submit(
                    self._execute_sync_task, task
                )
                task.task_object = future
                
                if wait:
                    # Wait for task to complete
                    future.result()
            
            # Store execution
            self.task_executions[execution_id] = {
                "task_id": task_id,
                "started_at": task.started_at,
                "is_async": is_async
            }
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_STARTED,
                    task_id,
                    {"name": task.name, "execution_id": execution_id}
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task started event: {e}")
            
            logger.info(f"Task started: {task_id} ({task.name})")
            return execution_id
            
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            task.status = TaskStatus.FAILED
            task.error = e
            task.completed_at = datetime.now()
            self.running_tasks.discard(task_id)
            self.failed_tasks.add(task_id)
            return None
    
    def _execute_sync_task(self, task: Task) -> Any:
        """
        Execute a synchronous task.
        
        Args:
            task: Task to execute
            
        Returns:
            Task result
        """
        try:
            # Execute function
            result = task.function(*task.args, **task.kwargs)
            
            # Update task status
            task.status = TaskStatus.COMPLETED
            task.result = result
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
            
            # Check waiting tasks
            self._check_waiting_tasks()
            
            # Check auto shutdown
            if task.auto_shutdown:
                logger.info(f"Auto shutdown triggered by task {task.task_id}")
                self.stop()
            
            return result
            
        except Exception as e:
            # Update task status
            task.status = TaskStatus.FAILED
            task.error = e
            task.completed_at = datetime.now()
            self.running_tasks.discard(task.task_id)
            self.failed_tasks.add(task_id)
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_FAILED,
                    task.task_id,
                    {"name": task.name, "error": str(e)}
                )
                publish_sync(event)
            except Exception as ex:
                logger.warning(f"Failed to publish task failed event: {ex}")
            
            logger.error(f"Task failed: {task.task_id} ({task.name}) - {e}")
            
            # Check waiting tasks
            self._check_waiting_tasks()
            
            # Re-raise exception
            raise
    
    async def _execute_async_task(self, task: Task) -> Any:
        """
        Execute an asynchronous task.
        
        Args:
            task: Task to execute
            
        Returns:
            Task result
        """
        try:
            # Execute function
            result = await task.function(*task.args, **task.kwargs)
            
            # Update task status
            task.status = TaskStatus.COMPLETED
            task.result = result
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
            
            # Check waiting tasks
            self._check_waiting_tasks()
            
            # Check auto shutdown
            if task.auto_shutdown:
                logger.info(f"Auto shutdown triggered by task {task.task_id}")
                self.stop()
            
            return result
            
        except Exception as e:
            # Update task status
            task.status = TaskStatus.FAILED
            task.error = e
            task.completed_at = datetime.now()
            self.running_tasks.discard(task.task_id)
            self.failed_tasks.add(task_id)
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_FAILED,
                    task.task_id,
                    {"name": task.name, "error": str(e)}
                )
                publish_sync(event)
            except Exception as ex:
                logger.warning(f"Failed to publish task failed event: {ex}")
            
            logger.error(f"Task failed: {task.task_id} ({task.name}) - {e}")
            
            # Check waiting tasks
            self._check_waiting_tasks()
            
            # Re-raise exception
            raise
    
    def _check_waiting_tasks(self) -> None:
        """Check waiting tasks to see if their dependencies are satisfied."""
        for task_id in list(self.waiting_tasks):
            task = self.tasks.get(task_id)
            if not task:
                self.waiting_tasks.discard(task_id)
                continue
            
            # Check if all dependencies are completed
            all_deps_completed = True
            for dep_id in task.dependencies:
                dep_task = self.tasks.get(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    all_deps_completed = False
                    break
            
            if all_deps_completed:
                # Move task back to pending
                task.status = TaskStatus.PENDING
                self.waiting_tasks.discard(task_id)
                self.pending_tasks.add(task_id)
                
                # Publish event
                try:
                    event = create_task_event(
                        EventType.TASK_READY,
                        task_id,
                        {"name": task.name}
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish task ready event: {e}")
                
                logger.info(f"Task ready: {task_id} ({task.name})")
    
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
                if task.task_object:
                    if hasattr(task.task_object, 'cancel'):
                        task.task_object.cancel()
                    elif hasattr(task.task_object, 'done') and not task.task_object.done():
                        task.task_object.cancel()
                
                self.running_tasks.discard(task_id)
            elif task.status == TaskStatus.PENDING:
                self.pending_tasks.discard(task_id)
            elif task.status == TaskStatus.WAITING:
                self.waiting_tasks.discard(task_id)
                
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            self.cancelled_tasks.add(task_id)
            
            # Publish event
            event = create_task_event(
                EventType.TASK_CANCELLED,
                task_id,
                {"name": task.name, "reason": "cancelled by user"}
            )
            publish_sync(event)
            
            logger.info(f"Task cancelled: {task_id} ({task.name})")
            return True
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False
    
    def _cleanup_task_resources(self, task: Task) -> None:
        """
        Clean up resources allocated for a task.
        
        Args:
            task: Task to clean up
        """
        # Implement resource cleanup logic here
        pass
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id: ID of the task to get
            
        Returns:
            Task if found, None otherwise
        """
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Task]:
        """
        Get all tasks.
        
        Returns:
            List of all tasks
        """
        return list(self.tasks.values())
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """
        Get tasks by status.
        
        Args:
            status: Status to filter by
            
        Returns:
            List of tasks with the specified status
        """
        task_ids = set()
        if status == TaskStatus.PENDING:
            task_ids = self.pending_tasks
        elif status == TaskStatus.WAITING:
            task_ids = self.waiting_tasks
        elif status == TaskStatus.RUNNING:
            task_ids = self.running_tasks
        elif status == TaskStatus.COMPLETED:
            task_ids = self.completed_tasks
        elif status == TaskStatus.FAILED:
            task_ids = self.failed_tasks
        elif status == TaskStatus.CANCELLED:
            task_ids = self.cancelled_tasks
        elif status == TaskStatus.TIMEOUT:
            task_ids = self.timeout_tasks
        
        return [self.tasks[task_id] for task_id in task_ids if task_id in self.tasks]
    
    def get_tasks_by_tag(self, tag: str) -> List[Task]:
        """
        Get tasks by tag.
        
        Args:
            tag: Tag to filter by
            
        Returns:
            List of tasks with the specified tag
        """
        return [task for task in self.tasks.values() if tag in task.tags]
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get task manager metrics.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "total_tasks": len(self.tasks),
            "pending_tasks": len(self.pending_tasks),
            "waiting_tasks": len(self.waiting_tasks),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "cancelled_tasks": len(self.cancelled_tasks),
            "timeout_tasks": len(self.timeout_tasks)
        }
    
    def stop(self) -> None:
        """Stop the task manager and clean up resources."""
        if self.is_shutdown:
            return
        
        logger.info("Shutting down UnifiedTaskManager...")
        
        # Cancel all running tasks
        for task_id in list(self.running_tasks):
            self.cancel_task(task_id)
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        self.is_shutdown = True
        logger.info("UnifiedTaskManager shutdown complete")
    
    async def submit_task(self, task: Task) -> str:
        """
        Submit a task for execution (async compatibility method).
        
        Args:
            task: Task to submit
            
        Returns:
            Task ID
        """
        # Register task if not already registered
        if task.task_id not in self.tasks:
            self.tasks[task.task_id] = task
            self.pending_tasks.add(task.task_id)
        
        # Execute task
        execution_id = self.execute_task(task.task_id)
        return task.task_id
    
    async def shutdown(self) -> None:
        """Shutdown the task manager (async compatibility method)."""
        self.stop()

# Create a singleton instance
unified_task_manager = UnifiedTaskManager()

# For backward compatibility
TaskManager = UnifiedTaskManager
thread_pool_manager = unified_task_manager
