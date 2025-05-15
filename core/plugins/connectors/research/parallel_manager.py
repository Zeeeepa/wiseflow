#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parallel Manager for Research Operations.

This module provides a manager for handling parallel research operations,
including error handling, recovery, and resource management.
"""

import asyncio
import logging
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Union, cast

from core.utils.error_handling import WiseflowError, TaskError
from core.utils.error_manager import (
    ErrorManager, ErrorSeverity, RecoveryStrategy, error_manager, retry, with_error_handling
)
from core.utils.logging_config import logger, with_context

# Type variable for task result
T = TypeVar('T')

class TaskStatus(Enum):
    """Status of a parallel task."""
    
    # Task is pending execution
    PENDING = "pending"
    
    # Task is currently running
    RUNNING = "running"
    
    # Task completed successfully
    COMPLETED = "completed"
    
    # Task failed with an error
    FAILED = "failed"
    
    # Task was cancelled
    CANCELLED = "cancelled"
    
    # Task was skipped due to dependencies or conditions
    SKIPPED = "skipped"

class TaskPriority(Enum):
    """Priority levels for parallel tasks."""
    
    # Low priority task
    LOW = 0
    
    # Normal priority task
    NORMAL = 1
    
    # High priority task
    HIGH = 2
    
    # Critical priority task
    CRITICAL = 3

@dataclass
class ParallelTask:
    """
    Represents a task that can be executed in parallel.
    
    Attributes:
        id: Unique identifier for the task
        func: The function to execute
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function
        dependencies: List of task IDs that must complete before this task
        priority: Priority level for the task
        max_retries: Maximum number of retry attempts
        status: Current status of the task
        result: Result of the task execution
        error: Error that occurred during execution
        retry_count: Number of retry attempts
        start_time: Time when the task started
        end_time: Time when the task completed
    """
    
    id: str
    func: Callable
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    retry_count: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None

class ParallelExecutionError(WiseflowError):
    """Error raised when parallel execution fails."""
    pass

class TaskExecutionError(TaskError):
    """Error raised when a specific task execution fails."""
    pass

class DependencyError(TaskError):
    """Error raised when a task dependency fails."""
    pass

class ResourceExhaustionError(WiseflowError):
    """Error raised when resources are exhausted."""
    pass

class ParallelManager:
    """
    Manager for parallel research operations.
    
    This class provides methods for executing tasks in parallel with error handling,
    recovery, and resource management. It supports task dependencies, priorities,
    and automatic retries.
    """
    
    def __init__(
        self,
        max_workers: int = 10,
        max_queue_size: int = 100,
        default_timeout: float = 300.0
    ):
        """
        Initialize the parallel manager.
        
        Args:
            max_workers: Maximum number of worker threads/tasks
            max_queue_size: Maximum size of the task queue
            default_timeout: Default timeout for task execution in seconds
        """
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.default_timeout = default_timeout
        
        self.tasks: Dict[str, ParallelTask] = {}
        self.running_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.error_manager = error_manager
        self.logger = logger
    
    async def execute_all(
        self,
        timeout: Optional[float] = None,
        raise_on_failure: bool = False
    ) -> Dict[str, Any]:
        """
        Execute all registered tasks respecting dependencies and priorities.
        
        Args:
            timeout: Maximum time to wait for all tasks to complete
            raise_on_failure: Whether to raise an exception if any task fails
            
        Returns:
            Dictionary mapping task IDs to results
            
        Raises:
            ParallelExecutionError: If raise_on_failure is True and any task fails
            asyncio.TimeoutError: If the execution times out
        """
        if not self.tasks:
            return {}
        
        timeout = timeout or self.default_timeout * len(self.tasks)
        start_time = time.time()
        
        try:
            # Create a task for the execution manager
            execution_task = asyncio.create_task(self._execution_manager())
            
            # Wait for all tasks to complete or timeout
            await asyncio.wait_for(execution_task, timeout)
            
            # Check for failures
            if raise_on_failure and self.failed_tasks:
                failed_task_ids = ", ".join(self.failed_tasks)
                raise ParallelExecutionError(
                    f"Some tasks failed: {failed_task_ids}",
                    {"failed_tasks": list(self.failed_tasks)}
                )
            
            # Return results
            return {task_id: task.result for task_id, task in self.tasks.items() 
                   if task.status == TaskStatus.COMPLETED}
            
        except asyncio.TimeoutError:
            # Handle timeout
            self.logger.error(
                f"Parallel execution timed out after {timeout} seconds"
            )
            
            # Cancel running tasks
            for task_id in self.running_tasks:
                self.tasks[task_id].status = TaskStatus.CANCELLED
            
            if raise_on_failure:
                raise ParallelExecutionError(
                    f"Parallel execution timed out after {timeout} seconds",
                    {"timeout": timeout, "running_tasks": list(self.running_tasks)}
                )
            
            # Return partial results
            return {task_id: task.result for task_id, task in self.tasks.items() 
                   if task.status == TaskStatus.COMPLETED}
    
    async def _execution_manager(self):
        """
        Manage the execution of tasks respecting dependencies and priorities.
        """
        # Continue until all tasks are completed, failed, or cancelled
        while self._has_pending_tasks():
            # Get executable tasks (no pending dependencies)
            executable_tasks = self._get_executable_tasks()
            
            if not executable_tasks and self.running_tasks:
                # Wait for some running tasks to complete
                await asyncio.sleep(0.1)
                continue
            
            if not executable_tasks and not self.running_tasks:
                # No more tasks to execute and nothing is running
                break
            
            # Sort tasks by priority
            executable_tasks.sort(
                key=lambda task_id: self.tasks[task_id].priority.value,
                reverse=True
            )
            
            # Execute tasks up to max_workers
            available_workers = self.max_workers - len(self.running_tasks)
            for task_id in executable_tasks[:available_workers]:
                # Start the task
                asyncio.create_task(self._execute_task(task_id))
                
                # Mark as running
                self.tasks[task_id].status = TaskStatus.RUNNING
                self.running_tasks.add(task_id)
            
            # Wait a bit before checking again
            await asyncio.sleep(0.1)
    
    async def _execute_task(self, task_id: str):
        """
        Execute a single task with error handling and retries.
        
        Args:
            task_id: ID of the task to execute
        """
        task = self.tasks[task_id]
        task.start_time = time.time()
        
        try:
            # Execute the task
            if asyncio.iscoroutinefunction(task.func):
                # Async function
                task.result = await task.func(*task.args, **task.kwargs)
            else:
                # Sync function - run in executor
                loop = asyncio.get_event_loop()
                task.result = await loop.run_in_executor(
                    self.executor,
                    lambda: task.func(*task.args, **task.kwargs)
                )
            
            # Mark as completed
            task.status = TaskStatus.COMPLETED
            self.completed_tasks.add(task_id)
            
        except Exception as e:
            # Handle the error
            task.error = e
            task.retry_count += 1
            
            # Log the error
            self.logger.error(
                f"Task {task_id} failed: {e}",
                extra={"task_id": task_id, "error": str(e), "traceback": traceback.format_exc()}
            )
            
            # Check if we should retry
            if task.retry_count <= task.max_retries:
                # Reset for retry
                task.status = TaskStatus.PENDING
                self.logger.info(
                    f"Retrying task {task_id} (attempt {task.retry_count}/{task.max_retries})"
                )
            else:
                # Mark as failed
                task.status = TaskStatus.FAILED
                self.failed_tasks.add(task_id)
                
                # Handle the error with ErrorManager
                error_context = {
                    "task_id": task_id,
                    "function": task.func.__name__,
                    "args": str(task.args),
                    "kwargs": str(task.kwargs),
                    "retry_count": task.retry_count
                }
                
                self.error_manager.handle_error(
                    TaskExecutionError(
                        f"Task {task_id} failed after {task.retry_count} attempts",
                        {"task_id": task_id, "original_error": str(e)},
                        e
                    ),
                    error_context,
                    ErrorSeverity.MEDIUM,
                    RecoveryStrategy.NONE
                )
        
        finally:
            # Update task state
            task.end_time = time.time()
            self.running_tasks.remove(task_id)
    
    def _has_pending_tasks(self) -> bool:
        """
        Check if there are any pending tasks.
        
        Returns:
            True if there are pending tasks, False otherwise
        """
        return any(task.status == TaskStatus.PENDING for task in self.tasks.values())
    
    def _get_executable_tasks(self) -> List[str]:
        """
        Get tasks that can be executed (all dependencies satisfied).
        
        Returns:
            List of task IDs that can be executed
        """
        executable_tasks = []
        
        for task_id, task in self.tasks.items():
            if task.status != TaskStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            dependencies_satisfied = True
            for dep_id in task.dependencies:
                if dep_id not in self.tasks:
                    # Missing dependency
                    self.logger.warning(f"Task {task_id} has missing dependency: {dep_id}")
                    task.status = TaskStatus.FAILED
                    task.error = DependencyError(
                        f"Missing dependency: {dep_id}",
                        {"task_id": task_id, "dependency_id": dep_id}
                    )
                    self.failed_tasks.add(task_id)
                    dependencies_satisfied = False
                    break
                
                dep_status = self.tasks[dep_id].status
                
                if dep_status == TaskStatus.FAILED:
                    # Failed dependency
                    self.logger.warning(
                        f"Task {task_id} has failed dependency: {dep_id}"
                    )
                    task.status = TaskStatus.FAILED
                    task.error = DependencyError(
                        f"Dependency failed: {dep_id}",
                        {"task_id": task_id, "dependency_id": dep_id}
                    )
                    self.failed_tasks.add(task_id)
                    dependencies_satisfied = False
                    break
                
                if dep_status != TaskStatus.COMPLETED:
                    # Dependency not yet completed
                    dependencies_satisfied = False
                    break
            
            if dependencies_satisfied:
                executable_tasks.append(task_id)
        
        return executable_tasks
    
    def add_task(
        self,
        task_id: str,
        func: Callable,
        args: Tuple = (),
        kwargs: Dict[str, Any] = None,
        dependencies: List[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3
    ) -> str:
        """
        Add a task to the parallel manager.
        
        Args:
            task_id: Unique identifier for the task
            func: The function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            dependencies: List of task IDs that must complete before this task
            priority: Priority level for the task
            max_retries: Maximum number of retry attempts
            
        Returns:
            The task ID
            
        Raises:
            ValueError: If a task with the same ID already exists
        """
        if task_id in self.tasks:
            raise ValueError(f"Task with ID {task_id} already exists")
        
        if len(self.tasks) >= self.max_queue_size:
            raise ResourceExhaustionError(
                f"Task queue is full (max size: {self.max_queue_size})",
                {"current_size": len(self.tasks), "max_size": self.max_queue_size}
            )
        
        self.tasks[task_id] = ParallelTask(
            id=task_id,
            func=func,
            args=args,
            kwargs=kwargs or {},
            dependencies=dependencies or [],
            priority=priority,
            max_retries=max_retries
        )
        
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task if it's pending.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            return True
        
        return False
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get the status of a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            The task status or None if the task doesn't exist
        """
        if task_id not in self.tasks:
            return None
        
        return self.tasks[task_id].status
    
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """
        Get the result of a completed task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            The task result or None if the task doesn't exist or isn't completed
        """
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        
        if task.status != TaskStatus.COMPLETED:
            return None
        
        return task.result
    
    def get_task_error(self, task_id: str) -> Optional[Exception]:
        """
        Get the error of a failed task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            The task error or None if the task doesn't exist or didn't fail
        """
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        
        if task.status != TaskStatus.FAILED:
            return None
        
        return task.error
    
    def get_all_results(self) -> Dict[str, Any]:
        """
        Get results of all completed tasks.
        
        Returns:
            Dictionary mapping task IDs to results
        """
        return {
            task_id: task.result
            for task_id, task in self.tasks.items()
            if task.status == TaskStatus.COMPLETED
        }
    
    def get_all_errors(self) -> Dict[str, Exception]:
        """
        Get errors of all failed tasks.
        
        Returns:
            Dictionary mapping task IDs to errors
        """
        return {
            task_id: task.error
            for task_id, task in self.tasks.items()
            if task.status == TaskStatus.FAILED and task.error is not None
        }
    
    def reset(self):
        """Reset the parallel manager, clearing all tasks."""
        self.tasks.clear()
        self.running_tasks.clear()
        self.completed_tasks.clear()
        self.failed_tasks.clear()
    
    def __del__(self):
        """Clean up resources when the manager is deleted."""
        self.executor.shutdown(wait=False)

# Utility functions for working with the parallel manager

async def execute_in_parallel(
    functions: List[Callable],
    args_list: Optional[List[Tuple]] = None,
    kwargs_list: Optional[List[Dict[str, Any]]] = None,
    max_workers: int = 10,
    timeout: Optional[float] = None,
    raise_on_failure: bool = False
) -> List[Any]:
    """
    Execute multiple functions in parallel.
    
    Args:
        functions: List of functions to execute
        args_list: List of positional arguments for each function
        kwargs_list: List of keyword arguments for each function
        max_workers: Maximum number of worker threads/tasks
        timeout: Maximum time to wait for all functions to complete
        raise_on_failure: Whether to raise an exception if any function fails
        
    Returns:
        List of results in the same order as the functions
        
    Raises:
        ParallelExecutionError: If raise_on_failure is True and any function fails
    """
    if not functions:
        return []
    
    # Initialize args and kwargs if not provided
    if args_list is None:
        args_list = [()] * len(functions)
    if kwargs_list is None:
        kwargs_list = [{}] * len(functions)
    
    # Ensure all lists have the same length
    if len(functions) != len(args_list) or len(functions) != len(kwargs_list):
        raise ValueError(
            "functions, args_list, and kwargs_list must have the same length"
        )
    
    # Create a parallel manager
    manager = ParallelManager(max_workers=max_workers)
    
    # Add tasks
    for i, (func, args, kwargs) in enumerate(zip(functions, args_list, kwargs_list)):
        manager.add_task(
            task_id=f"task_{i}",
            func=func,
            args=args,
            kwargs=kwargs
        )
    
    # Execute all tasks
    results_dict = await manager.execute_all(
        timeout=timeout,
        raise_on_failure=raise_on_failure
    )
    
    # Collect results in the original order
    results = []
    for i in range(len(functions)):
        task_id = f"task_{i}"
        if task_id in results_dict:
            results.append(results_dict[task_id])
        else:
            # Task failed or was cancelled
            results.append(None)
    
    return results

@with_error_handling(
    error_types=[Exception],
    severity=ErrorSeverity.MEDIUM,
    recovery_strategy=RecoveryStrategy.NONE,
    notify=True,
    log_level="error",
    save_to_file=False
)
async def parallel_map(
    func: Callable,
    items: List[Any],
    max_workers: int = 10,
    timeout: Optional[float] = None,
    raise_on_failure: bool = False
) -> List[Any]:
    """
    Apply a function to each item in a list in parallel.
    
    Args:
        func: Function to apply to each item
        items: List of items to process
        max_workers: Maximum number of worker threads/tasks
        timeout: Maximum time to wait for all items to be processed
        raise_on_failure: Whether to raise an exception if any item fails
        
    Returns:
        List of results in the same order as the items
        
    Raises:
        ParallelExecutionError: If raise_on_failure is True and any item fails
    """
    if not items:
        return []
    
    # Create a list of functions (same function for each item)
    functions = [func] * len(items)
    
    # Create a list of args (each item as the first arg)
    args_list = [(item,) for item in items]
    
    # Execute in parallel
    return await execute_in_parallel(
        functions=functions,
        args_list=args_list,
        max_workers=max_workers,
        timeout=timeout,
        raise_on_failure=raise_on_failure
    )

