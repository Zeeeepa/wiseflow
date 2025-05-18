"""
Task manager for the unified task management system.

This module provides the TaskManager class for managing and executing tasks.
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, Callable, List, Union, Awaitable, Set, Tuple
from datetime import datetime

from core.task_management.task import Task, TaskStatus, TaskPriority, create_task_id
from core.task_management.executor import Executor, SequentialExecutor, ThreadPoolExecutor, AsyncExecutor
from core.task_management.exceptions import (
    TaskError,
    TaskDependencyError,
    TaskExecutionError,
    TaskNotFoundError,
    InvalidTaskStateError
)
from core.event_system import EventType, Event, publish_sync, create_task_event
from core.models.task_models import TaskRegistrationParams
from core.utils.validation import validate_input

logger = logging.getLogger(__name__)

class TaskManager:
    """
    Task manager for the unified task management system.
    
    This class provides functionality to manage and execute tasks using different
    execution strategies.
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
            cls._initialized = False
        return cls._instance
    
    def __init__(
        self,
        max_concurrent_tasks: int = 4,
        default_executor_type: str = "async"
    ):
        """
        Initialize the task manager.
        
        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks
            default_executor_type: Default executor type (sequential, thread_pool, or async)
        """
        if self._initialized:
            return
            
        self.max_concurrent_tasks = max_concurrent_tasks
        self.default_executor_type = default_executor_type
        
        # Create executors
        self.executors = {
            "sequential": SequentialExecutor(),
            "thread_pool": ThreadPoolExecutor(max_workers=max_concurrent_tasks),
            "async": AsyncExecutor(max_concurrency=max_concurrent_tasks)
        }
        
        # Task collections
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.cancelled_tasks: Set[str] = set()
        self.waiting_tasks: Set[str] = set()
        
        # Task execution tracking
        self.task_executors: Dict[str, str] = {}  # Maps task_id to executor_type
        
        # Scheduler state
        self.is_running = False
        self.scheduler_task = None
        self.task_lock = asyncio.Lock()
        
        self._initialized = True
        
        logger.info(f"Task manager initialized with {max_concurrent_tasks} max concurrent tasks")
    
    def register_task(
        self,
        name: str,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        kwargs: Optional[dict] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: Optional[List[str]] = None,
        max_retries: int = 0,
        retry_delay: float = 1.0,
        timeout: Optional[float] = None,
        description: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        executor_type: Optional[str] = None
    ) -> str:
        """
        Register a task with the task manager.
        
        Args:
            name: Name of the task
            func: Function to execute
            *args: Arguments to pass to the function
            task_id: Optional task ID, if not provided a new one will be generated
            kwargs: Keyword arguments to pass to the function
            priority: Priority of the task
            dependencies: List of task IDs that must complete before this task
            max_retries: Maximum number of retries if the task fails
            retry_delay: Delay in seconds between retries
            timeout: Timeout in seconds for the task
            description: Detailed description of the task
            tags: List of tags for categorizing the task
            metadata: Additional metadata for the task
            executor_type: Type of executor to use (sequential, thread_pool, or async)
            
        Returns:
            Task ID
            
        Raises:
            TaskDependencyError: If a dependency does not exist
        """
        # Validate parameters using Pydantic model
        params = TaskRegistrationParams(
            name=name,
            func=func,
            task_id=task_id,
            kwargs=kwargs or {},
            priority=priority,
            dependencies=dependencies or [],
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            description=description,
            tags=tags or [],
            metadata=metadata or {},
            executor_type=executor_type
        )
        
        # Validate the parameters
        validation_result = validate_input(params.dict(exclude={"func"}), TaskRegistrationParams.schema(exclude={"func"}))
        if not validation_result.is_valid:
            logger.error(f"Parameter validation failed: {validation_result.errors}")
            raise ValueError(f"Invalid parameters: {validation_result.errors}")
        
        # Generate a task ID if not provided
        if params.task_id is None:
            task_id = create_task_id()
        else:
            task_id = params.task_id
            
        # Check if task ID already exists
        if task_id in self.tasks:
            logger.warning(f"Task ID {task_id} already exists, generating a new one")
            task_id = create_task_id()
        
        # Check if dependencies exist
        if params.dependencies:
            for dep_id in params.dependencies:
                if dep_id not in self.tasks:
                    raise TaskDependencyError(
                        f"Dependency {dep_id} does not exist",
                        task_id=task_id
                    )
        
        # Create the task
        task = Task(
            task_id=task_id,
            name=params.name,
            func=params.func,
            args=args,
            kwargs=params.kwargs,
            priority=params.priority,
            dependencies=params.dependencies,
            max_retries=params.max_retries,
            retry_delay=params.retry_delay,
            timeout=params.timeout,
            description=params.description,
            tags=params.tags,
            metadata=params.metadata
        )
        
        # Store the task
        self.tasks[task_id] = task
        
        # Determine executor type
        executor_type = params.executor_type or self.default_executor_type
        if executor_type not in self.executors:
            logger.warning(f"Executor type {executor_type} not found, using default")
            executor_type = self.default_executor_type
        
        # Store executor type
        self.task_executors[task_id] = executor_type
        
        # Check if task has dependencies
        if task.dependencies:
            # Check if all dependencies are completed
            all_completed = True
            for dep_id in task.dependencies:
                dep_task = self.tasks.get(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    all_completed = False
                    break
            
            if not all_completed:
                task.status = TaskStatus.WAITING
                self.waiting_tasks.add(task_id)
        
        # Publish event
        try:
            event = create_task_event(
                EventType.TASK_CREATED,
                task_id,
                {
                    "name": task.name,
                    "priority": task.priority.name,
                    "dependencies": task.dependencies,
                    "executor_type": self.task_executors[task_id]
                }
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish task created event: {e}")
        
        logger.info(f"Task registered: {task_id} ({task.name})")
        return task_id
    
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
    
    def get_task_progress(self, task_id: str) -> Tuple[float, str]:
        """
        Get the progress of a task.
        
        Args:
            task_id: ID of the task to get progress for
            
        Returns:
            Tuple of (progress, progress_message) or (0.0, "") if task not found
        """
        task = self.tasks.get(task_id)
        if not task:
            return 0.0, ""
        return task.progress, task.progress_message
    
    def update_task_progress(self, task_id: str, progress: float, message: str = "") -> bool:
        """
        Update the progress of a task.
        
        Args:
            task_id: ID of the task to update progress for
            progress: Progress value between 0.0 and 1.0
            message: Optional progress message
            
        Returns:
            True if the task was updated, False otherwise
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        task.update_progress(progress, message)
        
        # Publish event
        try:
            event = create_task_event(
                EventType.TASK_PROGRESS,
                task_id,
                {
                    "name": task.name,
                    "progress": task.progress,
                    "progress_message": task.progress_message
                }
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish task progress event: {e}")
        
        return True
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """
        Get all tasks with a specific status.
        
        Args:
            status: Status to filter by
            
        Returns:
            List of tasks with the specified status
        """
        return [task for task in self.tasks.values() if task.status == status]
    
    def get_tasks_by_tag(self, tag: str) -> List[Task]:
        """
        Get all tasks with a specific tag.
        
        Args:
            tag: Tag to filter by
            
        Returns:
            List of tasks with the specified tag
        """
        return [task for task in self.tasks.values() if tag in task.tags]
    
    def get_tasks_by_metadata(self, key: str, value: Any) -> List[Task]:
        """
        Get all tasks with a specific metadata key-value pair.
        
        Args:
            key: Metadata key to filter by
            value: Metadata value to filter by
            
        Returns:
            List of tasks with the specified metadata
        """
        return [
            task for task in self.tasks.values()
            if key in task.metadata and task.metadata[key] == value
        ]
    
    async def execute_task(self, task_id: str, wait: bool = True) -> Any:
        """
        Execute a task.
        
        Args:
            task_id: ID of the task to execute
            wait: Whether to wait for the task to complete
            
        Returns:
            Task result if wait is True, None otherwise
            
        Raises:
            TaskNotFoundError: If the task is not found
            InvalidTaskStateError: If the task is not in a valid state for execution
            TaskExecutionError: If the task execution fails
        """
        task = self.tasks.get(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found", task_id=task_id)
        
        if task.status not in [TaskStatus.PENDING, TaskStatus.WAITING]:
            raise InvalidTaskStateError(
                f"Task {task_id} is in invalid state for execution: {task.status.name}",
                task_id=task_id
            )
        
        # Check if task has dependencies
        if task.dependencies:
            # Check if all dependencies are completed
            all_completed = True
            for dep_id in task.dependencies:
                dep_task = self.tasks.get(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    all_completed = False
                    break
            
            if not all_completed:
                task.status = TaskStatus.WAITING
                self.waiting_tasks.add(task_id)
                
                if wait:
                    # Wait for dependencies to complete
                    while not all(
                        self.tasks.get(dep_id) and self.tasks[dep_id].status == TaskStatus.COMPLETED
                        for dep_id in task.dependencies
                    ):
                        await asyncio.sleep(0.1)
                else:
                    return None
        
        # Update task status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.running_tasks.add(task_id)
        
        # Get executor
        executor_type = self.task_executors.get(task_id, self.default_executor_type)
        executor = self.executors[executor_type]
        
        # Publish event
        try:
            event = create_task_event(
                EventType.TASK_STARTED,
                task_id,
                {
                    "name": task.name,
                    "executor_type": executor_type
                }
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish task started event: {e}")
        
        logger.info(f"Task started: {task_id} ({task.name})")
        
        if wait:
            try:
                # Execute task and wait for result
                result = await executor.execute(task)
                
                # Update task
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.result = result
                task.progress = 1.0
                task.progress_message = "Task completed"
                
                # Update task sets
                self.running_tasks.discard(task_id)
                self.completed_tasks.add(task_id)
                
                # Publish event
                try:
                    event = create_task_event(
                        EventType.TASK_COMPLETED,
                        task_id,
                        {
                            "name": task.name,
                            "execution_time": (task.completed_at - task.started_at).total_seconds()
                        }
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish task completed event: {e}")
                
                logger.info(f"Task completed: {task_id} ({task.name})")
                
                # Check for waiting tasks that depend on this task
                await self._check_waiting_tasks()
                
                return result
            except asyncio.CancelledError:
                # Handle cancellation
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                task.error = asyncio.CancelledError("Task was cancelled")
                
                # Update task sets
                self.running_tasks.discard(task_id)
                self.cancelled_tasks.add(task_id)
                
                # Publish event
                try:
                    event = create_task_event(
                        EventType.TASK_CANCELLED,
                        task_id,
                        {
                            "name": task.name,
                            "reason": "cancelled"
                        }
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish task cancelled event: {e}")
                
                logger.info(f"Task cancelled: {task_id} ({task.name})")
                raise
            except Exception as e:
                # Handle other errors
                task.error = e
                
                # Check if we should retry
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.PENDING
                    self.running_tasks.discard(task_id)
                    
                    logger.warning(
                        f"Task {task_id} ({task.name}) failed, "
                        f"retrying ({task.retry_count}/{task.max_retries}): {e}"
                    )
                    
                    # Wait before retrying
                    retry_delay = task.retry_delay * (2 ** (task.retry_count - 1))  # Exponential backoff
                    await asyncio.sleep(retry_delay)
                    
                    # Retry the task
                    return await self.execute_task(task_id, wait=True)
                else:
                    # Mark task as failed
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now()
                    
                    # Update task sets
                    self.running_tasks.discard(task_id)
                    self.failed_tasks.add(task_id)
                    
                    # Publish event
                    try:
                        event = create_task_event(
                            EventType.TASK_FAILED,
                            task_id,
                            {
                                "name": task.name,
                                "error": str(e)
                            }
                        )
                        publish_sync(event)
                    except Exception as e:
                        logger.warning(f"Failed to publish task failed event: {e}")
                    
                    logger.error(f"Task failed: {task_id} ({task.name}): {e}")
                    raise TaskExecutionError(
                        f"Task {task_id} execution failed: {str(e)}",
                        task_id=task_id,
                        original_error=e
                    )
        else:
            # Execute task asynchronously
            asyncio.create_task(self._execute_task_async(task_id, executor))
            return None
    
    async def _execute_task_async(self, task_id: str, executor: Executor) -> None:
        """
        Execute a task asynchronously.
        
        Args:
            task_id: ID of the task to execute
            executor: Executor to use
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found for async execution")
            return
        
        try:
            # Execute task
            result = await executor.execute(task)
            
            # Update task
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            task.progress = 1.0
            task.progress_message = "Task completed"
            
            # Update task sets
            self.running_tasks.discard(task_id)
            self.completed_tasks.add(task_id)
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_COMPLETED,
                    task_id,
                    {
                        "name": task.name,
                        "execution_time": (task.completed_at - task.started_at).total_seconds()
                    }
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task completed event: {e}")
            
            logger.info(f"Task completed: {task_id} ({task.name})")
            
            # Check for waiting tasks that depend on this task
            await self._check_waiting_tasks()
        except asyncio.CancelledError:
            # Handle cancellation
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            task.error = asyncio.CancelledError("Task was cancelled")
            
            # Update task sets
            self.running_tasks.discard(task_id)
            self.cancelled_tasks.add(task_id)
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_CANCELLED,
                    task_id,
                    {
                        "name": task.name,
                        "reason": "cancelled"
                    }
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task cancelled event: {e}")
            
            logger.info(f"Task cancelled: {task_id} ({task.name})")
        except Exception as e:
            # Handle other errors
            task.error = e
            
            # Check if we should retry
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                self.running_tasks.discard(task_id)
                
                logger.warning(
                    f"Task {task_id} ({task.name}) failed, "
                    f"retrying ({task.retry_count}/{task.max_retries}): {e}"
                )
                
                # Wait before retrying
                retry_delay = task.retry_delay * (2 ** (task.retry_count - 1))  # Exponential backoff
                await asyncio.sleep(retry_delay)
                
                # Retry the task
                await self._execute_task_async(task_id, executor)
            else:
                # Mark task as failed
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                
                # Update task sets
                self.running_tasks.discard(task_id)
                self.failed_tasks.add(task_id)
                
                # Publish event
                try:
                    event = create_task_event(
                        EventType.TASK_FAILED,
                        task_id,
                        {
                            "name": task.name,
                            "error": str(e)
                        }
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish task failed event: {e}")
                
                logger.error(f"Task failed: {task_id} ({task.name}): {e}")
    
    async def _check_waiting_tasks(self) -> None:
        """Check for waiting tasks that can now run."""
        async with self.task_lock:
            for task_id in list(self.waiting_tasks):
                task = self.tasks.get(task_id)
                if not task:
                    self.waiting_tasks.discard(task_id)
                    continue
                
                # Check if all dependencies are completed
                all_completed = True
                for dep_id in task.dependencies:
                    dep_task = self.tasks.get(dep_id)
                    if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                        all_completed = False
                        break
                
                if all_completed:
                    task.status = TaskStatus.PENDING
                    self.waiting_tasks.discard(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found for cancellation")
            return False
        
        if task.status == TaskStatus.RUNNING:
            # Get executor
            executor_type = self.task_executors.get(task_id, self.default_executor_type)
            executor = self.executors[executor_type]
            
            # Cancel the task
            cancelled = await executor.cancel(task)
            
            if cancelled:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                task.error = asyncio.CancelledError("Task was cancelled")
                
                # Update task sets
                self.running_tasks.discard(task_id)
                self.cancelled_tasks.add(task_id)
                
                # Publish event
                try:
                    event = create_task_event(
                        EventType.TASK_CANCELLED,
                        task_id,
                        {
                            "name": task.name,
                            "reason": "cancelled by user"
                        }
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish task cancelled event: {e}")
                
                logger.info(f"Task cancelled: {task_id} ({task.name})")
                return True
            else:
                logger.warning(f"Failed to cancel task {task_id} ({task.name})")
                return False
        elif task.status in [TaskStatus.PENDING, TaskStatus.WAITING]:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            task.error = asyncio.CancelledError("Task was cancelled")
            
            # Update task sets
            if task.status == TaskStatus.WAITING:
                self.waiting_tasks.discard(task_id)
            self.cancelled_tasks.add(task_id)
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_CANCELLED,
                    task_id,
                    {
                        "name": task.name,
                        "reason": "cancelled by user"
                    }
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task cancelled event: {e}")
            
            logger.info(f"Task cancelled: {task_id} ({task.name})")
            return True
        else:
            logger.warning(f"Cannot cancel task {task_id} with status {task.status.name}")
            return False
    
    async def start(self) -> None:
        """Start the task manager."""
        if self.is_running:
            logger.warning("Task manager is already running")
            return
        
        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler())
        logger.info("Task manager started")
    
    async def stop(self) -> None:
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
            await self.cancel_task(task_id)
        
        # Shutdown all executors
        for executor in self.executors.values():
            await executor.shutdown(wait=False)
        
        logger.info("Task manager stopped")
    
    async def _scheduler(self) -> None:
        """Scheduler loop for the task manager."""
        try:
            while self.is_running:
                await self._schedule_tasks()
                await asyncio.sleep(0.1)  # Small delay to prevent CPU hogging
        except asyncio.CancelledError:
            logger.info("Task scheduler cancelled")
        except Exception as e:
            logger.error(f"Error in task scheduler: {e}")
    
    async def _schedule_tasks(self) -> None:
        """Schedule tasks for execution."""
        async with self.task_lock:
            # Check if we can run more tasks
            if len(self.running_tasks) >= self.max_concurrent_tasks:
                return
            
            # Check for waiting tasks that can now run
            await self._check_waiting_tasks()
            
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
                
                # Execute the task
                asyncio.create_task(self.execute_task(task_id, wait=False))
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get task manager metrics.
        
        Returns:
            Dictionary of metrics
        """
        executor_metrics = {
            name: executor.get_metrics()
            for name, executor in self.executors.items()
        }
        
        return {
            "is_running": self.is_running,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "default_executor_type": self.default_executor_type,
            "total_tasks": len(self.tasks),
            "pending_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "cancelled_tasks": len(self.cancelled_tasks),
            "waiting_tasks": len(self.waiting_tasks),
            "executors": executor_metrics
        }

# Create a singleton instance
task_manager = TaskManager()
