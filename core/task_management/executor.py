"""
Task executors for the unified task management system.

This module provides different execution strategies for tasks.
"""

import asyncio
import concurrent.futures
import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List, Union, Awaitable, Tuple

from core.task_management.task import Task, TaskStatus
from core.task_management.exceptions import TaskExecutionError, TaskTimeoutError

logger = logging.getLogger(__name__)

class Executor(ABC):
    """
    Abstract base class for task executors.
    
    Task executors are responsible for executing tasks using different strategies.
    """
    
    @abstractmethod
    async def execute(self, task: Task) -> Any:
        """
        Execute a task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result of the task execution
            
        Raises:
            TaskExecutionError: If the task execution fails
        """
        pass
    
    @abstractmethod
    async def cancel(self, task: Task) -> bool:
        """
        Cancel a task.
        
        Args:
            task: Task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        pass
    
    @abstractmethod
    async def shutdown(self, wait: bool = True) -> None:
        """
        Shut down the executor.
        
        Args:
            wait: Whether to wait for pending tasks to complete
        """
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get executor metrics.
        
        Returns:
            Dictionary of metrics
        """
        pass

class SequentialExecutor(Executor):
    """
    Sequential executor for tasks.
    
    This executor executes tasks sequentially in the current thread.
    """
    
    def __init__(self):
        """Initialize the sequential executor."""
        self.running_task = None
        self.cancelled = False
    
    async def execute(self, task: Task) -> Any:
        """
        Execute a task sequentially.
        
        Args:
            task: Task to execute
            
        Returns:
            Result of the task execution
            
        Raises:
            TaskExecutionError: If the task execution fails
        """
        self.running_task = task
        self.cancelled = False
        
        try:
            # Check if the task has been cancelled
            if self.cancelled:
                raise asyncio.CancelledError("Task was cancelled")
            
            # Execute the task
            if asyncio.iscoroutinefunction(task.func):
                if task.timeout:
                    result = await asyncio.wait_for(
                        task.func(*task.args, **task.kwargs),
                        timeout=task.timeout
                    )
                else:
                    result = await task.func(*task.args, **task.kwargs)
            else:
                if task.timeout:
                    # Run synchronous function in a thread pool with timeout
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            task.func,
                            *task.args,
                            **task.kwargs
                        ),
                        timeout=task.timeout
                    )
                else:
                    # Run synchronous function directly
                    result = task.func(*task.args, **task.kwargs)
            
            return result
        except asyncio.TimeoutError:
            raise TaskTimeoutError(
                f"Task {task.task_id} timed out after {task.timeout} seconds",
                task_id=task.task_id
            )
        except asyncio.CancelledError:
            logger.info(f"Task {task.task_id} was cancelled")
            raise
        except Exception as e:
            raise TaskExecutionError(
                f"Task {task.task_id} execution failed: {str(e)}",
                task_id=task.task_id,
                original_error=e
            )
        finally:
            self.running_task = None
    
    async def cancel(self, task: Task) -> bool:
        """
        Cancel a task.
        
        Args:
            task: Task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        if self.running_task and self.running_task.task_id == task.task_id:
            self.cancelled = True
            return True
        return False
    
    async def shutdown(self, wait: bool = True) -> None:
        """
        Shut down the executor.
        
        Args:
            wait: Whether to wait for pending tasks to complete
        """
        if self.running_task and not wait:
            await self.cancel(self.running_task)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get executor metrics.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "executor_type": "sequential",
            "running_task": self.running_task.task_id if self.running_task else None,
            "is_idle": self.running_task is None
        }

class ThreadPoolExecutor(Executor):
    """
    Thread pool executor for tasks.
    
    This executor executes tasks concurrently using a thread pool.
    """
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize the thread pool executor.
        
        Args:
            max_workers: Maximum number of worker threads
        """
        self.max_workers = max_workers or (os.cpu_count() or 4)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        self.futures: Dict[str, concurrent.futures.Future] = {}
    
    async def execute(self, task: Task) -> Any:
        """
        Execute a task in the thread pool.
        
        Args:
            task: Task to execute
            
        Returns:
            Result of the task execution
            
        Raises:
            TaskExecutionError: If the task execution fails
        """
        loop = asyncio.get_event_loop()
        
        try:
            # Execute the task
            if asyncio.iscoroutinefunction(task.func):
                # For coroutines, we need to run them in the event loop
                if task.timeout:
                    future = asyncio.ensure_future(
                        asyncio.wait_for(
                            task.func(*task.args, **task.kwargs),
                            timeout=task.timeout
                        )
                    )
                else:
                    future = asyncio.ensure_future(
                        task.func(*task.args, **task.kwargs)
                    )
                
                self.futures[task.task_id] = future
                result = await future
            else:
                # For regular functions, we can use the thread pool
                if task.timeout:
                    future = asyncio.ensure_future(
                        asyncio.wait_for(
                            loop.run_in_executor(
                                self.executor,
                                task.func,
                                *task.args,
                                **task.kwargs
                            ),
                            timeout=task.timeout
                        )
                    )
                else:
                    future = asyncio.ensure_future(
                        loop.run_in_executor(
                            self.executor,
                            task.func,
                            *task.args,
                            **task.kwargs
                        )
                    )
                
                self.futures[task.task_id] = future
                result = await future
            
            return result
        except asyncio.TimeoutError:
            raise TaskTimeoutError(
                f"Task {task.task_id} timed out after {task.timeout} seconds",
                task_id=task.task_id
            )
        except asyncio.CancelledError:
            logger.info(f"Task {task.task_id} was cancelled")
            raise
        except Exception as e:
            raise TaskExecutionError(
                f"Task {task.task_id} execution failed: {str(e)}",
                task_id=task.task_id,
                original_error=e
            )
        finally:
            if task.task_id in self.futures:
                del self.futures[task.task_id]
    
    async def cancel(self, task: Task) -> bool:
        """
        Cancel a task.
        
        Args:
            task: Task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        future = self.futures.get(task.task_id)
        if future and not future.done():
            future.cancel()
            return True
        return False
    
    async def shutdown(self, wait: bool = True) -> None:
        """
        Shut down the executor.
        
        Args:
            wait: Whether to wait for pending tasks to complete
        """
        if not wait:
            # Cancel all running tasks
            for future in self.futures.values():
                if not future.done():
                    future.cancel()
        
        # Shutdown the executor
        self.executor.shutdown(wait=wait)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get executor metrics.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "executor_type": "thread_pool",
            "max_workers": self.max_workers,
            "active_workers": len(self.futures),
            "is_idle": len(self.futures) == 0
        }

class AsyncExecutor(Executor):
    """
    Asynchronous executor for tasks.
    
    This executor executes tasks concurrently using asyncio tasks.
    """
    
    def __init__(self, max_concurrency: int = 10):
        """
        Initialize the async executor.
        
        Args:
            max_concurrency: Maximum number of concurrent tasks
        """
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.tasks: Dict[str, asyncio.Task] = {}
    
    async def execute(self, task: Task) -> Any:
        """
        Execute a task asynchronously.
        
        Args:
            task: Task to execute
            
        Returns:
            Result of the task execution
            
        Raises:
            TaskExecutionError: If the task execution fails
        """
        async with self.semaphore:
            try:
                # Execute the task
                if asyncio.iscoroutinefunction(task.func):
                    if task.timeout:
                        async_task = asyncio.create_task(
                            asyncio.wait_for(
                                task.func(*task.args, **task.kwargs),
                                timeout=task.timeout
                            )
                        )
                    else:
                        async_task = asyncio.create_task(
                            task.func(*task.args, **task.kwargs)
                        )
                    
                    self.tasks[task.task_id] = async_task
                    result = await async_task
                else:
                    # For regular functions, we need to run them in a thread
                    loop = asyncio.get_event_loop()
                    if task.timeout:
                        async_task = asyncio.create_task(
                            asyncio.wait_for(
                                loop.run_in_executor(
                                    None,
                                    task.func,
                                    *task.args,
                                    **task.kwargs
                                ),
                                timeout=task.timeout
                            )
                        )
                    else:
                        async_task = asyncio.create_task(
                            loop.run_in_executor(
                                None,
                                task.func,
                                *task.args,
                                **task.kwargs
                            )
                        )
                    
                    self.tasks[task.task_id] = async_task
                    result = await async_task
                
                return result
            except asyncio.TimeoutError:
                raise TaskTimeoutError(
                    f"Task {task.task_id} timed out after {task.timeout} seconds",
                    task_id=task.task_id
                )
            except asyncio.CancelledError:
                logger.info(f"Task {task.task_id} was cancelled")
                raise
            except Exception as e:
                raise TaskExecutionError(
                    f"Task {task.task_id} execution failed: {str(e)}",
                    task_id=task.task_id,
                    original_error=e
                )
            finally:
                if task.task_id in self.tasks:
                    del self.tasks[task.task_id]
    
    async def cancel(self, task: Task) -> bool:
        """
        Cancel a task.
        
        Args:
            task: Task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        async_task = self.tasks.get(task.task_id)
        if async_task and not async_task.done():
            async_task.cancel()
            return True
        return False
    
    async def shutdown(self, wait: bool = True) -> None:
        """
        Shut down the executor.
        
        Args:
            wait: Whether to wait for pending tasks to complete
        """
        if not wait:
            # Cancel all running tasks
            for async_task in self.tasks.values():
                if not async_task.done():
                    async_task.cancel()
        
        if wait and self.tasks:
            # Wait for all tasks to complete
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get executor metrics.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "executor_type": "async",
            "max_concurrency": self.max_concurrency,
            "active_tasks": len(self.tasks),
            "is_idle": len(self.tasks) == 0,
            "available_slots": self.semaphore._value
        }

