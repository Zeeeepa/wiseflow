"""
Thread pool manager for handling concurrent tasks in Wiseflow.
"""

import os
import time
import threading
import queue
import logging
import asyncio
import concurrent.futures
from typing import Any, Callable, Dict, List, Optional, Union, Tuple
from enum import Enum
import uuid
import traceback

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Priority levels for tasks."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskStatus(Enum):
    """Status of a task."""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class Task:
    """Represents a task to be executed by the thread pool."""
    
    def __init__(
        self,
        func: Callable,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        task_id: Optional[str] = None,
        timeout: Optional[float] = None,
        callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None
    ):
        """Initialize a task.
        
        Args:
            func: Function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            priority: Priority level for the task
            task_id: Unique identifier for the task (generated if not provided)
            timeout: Maximum execution time in seconds (None for no timeout)
            callback: Function to call with the result when task completes
            error_callback: Function to call with the exception when task fails
        """
        self.func = func
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.priority = priority
        self.task_id = task_id or str(uuid.uuid4())
        self.timeout = timeout
        self.callback = callback
        self.error_callback = error_callback
        
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.thread = None
        self.future = None
        
    def __lt__(self, other):
        """Compare tasks based on priority for priority queue ordering."""
        if not isinstance(other, Task):
            return NotImplemented
        return self.priority.value > other.priority.value  # Higher priority value comes first


class ThreadPoolManager:
    """Manager for thread pools and async tasks."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(ThreadPoolManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        thread_name_prefix: str = 'wiseflow-worker',
        queue_size: int = 0,  # 0 means unlimited
        default_timeout: Optional[float] = None
    ):
        """Initialize the thread pool manager.
        
        Args:
            max_workers: Maximum number of worker threads (default: CPU count * 5)
            thread_name_prefix: Prefix for worker thread names
            queue_size: Maximum size of the task queue (0 for unlimited)
            default_timeout: Default timeout for tasks in seconds (None for no timeout)
        """
        if self._initialized:
            return
            
        self.max_workers = max_workers or min(32, os.cpu_count() * 5)
        self.thread_name_prefix = thread_name_prefix
        self.queue_size = queue_size
        self.default_timeout = default_timeout
        
        # Task queue with priority
        self.task_queue = queue.PriorityQueue(maxsize=queue_size)
        
        # Thread pool
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix=self.thread_name_prefix
        )
        
        # Task tracking
        self.tasks = {}  # task_id -> Task
        self.tasks_lock = threading.RLock()
        
        # Worker management
        self.worker_threads = []
        self.shutdown_event = threading.Event()
        
        # Start worker threads
        for _ in range(self.max_workers):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self.worker_threads.append(worker)
            
        # Async event loop
        self.loop = asyncio.new_event_loop()
        self.async_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.async_thread.start()
        
        self._initialized = True
        logger.info(f"ThreadPoolManager initialized with {self.max_workers} workers")
        
    def _worker_loop(self):
        """Worker thread loop for processing tasks from the queue."""
        while not self.shutdown_event.is_set():
            try:
                # Get task from queue with timeout to check shutdown periodically
                try:
                    priority_task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                    
                task = priority_task
                
                # Skip cancelled tasks
                if task.status == TaskStatus.CANCELLED:
                    self.task_queue.task_done()
                    continue
                    
                # Execute task
                self._execute_task(task)
                
                # Mark task as done in queue
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in worker thread: {str(e)}")
                logger.debug(traceback.format_exc())
                
    def _execute_task(self, task: Task):
        """Execute a task and handle results/errors.
        
        Args:
            task: Task to execute
        """
        # Update task status
        with self.tasks_lock:
            task.status = TaskStatus.RUNNING
            task.start_time = time.time()
            task.thread = threading.current_thread()
            
        try:
            # Execute with timeout if specified
            if task.timeout is not None:
                future = self.executor.submit(task.func, *task.args, **task.kwargs)
                task.future = future
                result = future.result(timeout=task.timeout)
            else:
                result = task.func(*task.args, **task.kwargs)
                
            # Update task with result
            with self.tasks_lock:
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.end_time = time.time()
                
            # Call callback if provided
            if task.callback:
                try:
                    task.callback(result)
                except Exception as e:
                    logger.error(f"Error in task callback: {str(e)}")
                    
        except concurrent.futures.TimeoutError:
            # Handle timeout
            with self.tasks_lock:
                task.status = TaskStatus.FAILED
                task.error = TimeoutError(f"Task timed out after {task.timeout} seconds")
                task.end_time = time.time()
                
            logger.warning(f"Task {task.task_id} timed out after {task.timeout} seconds")
            
            # Call error callback if provided
            if task.error_callback:
                try:
                    task.error_callback(task.error)
                except Exception as e:
                    logger.error(f"Error in task error callback: {str(e)}")
                    
        except Exception as e:
            # Handle other exceptions
            with self.tasks_lock:
                task.status = TaskStatus.FAILED
                task.error = e
                task.end_time = time.time()
                
            logger.error(f"Task {task.task_id} failed: {str(e)}")
            logger.debug(traceback.format_exc())
            
            # Call error callback if provided
            if task.error_callback:
                try:
                    task.error_callback(e)
                except Exception as e:
                    logger.error(f"Error in task error callback: {str(e)}")
                    
    def _run_async_loop(self):
        """Run the asyncio event loop in a separate thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        
    def submit(
        self,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        task_id: Optional[str] = None,
        timeout: Optional[float] = None,
        callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None,
        **kwargs
    ) -> str:
        """Submit a task to the thread pool.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            priority: Priority level for the task
            task_id: Unique identifier for the task (generated if not provided)
            timeout: Maximum execution time in seconds (None for no timeout)
            callback: Function to call with the result when task completes
            error_callback: Function to call with the exception when task fails
            **kwargs: Keyword arguments for the function
            
        Returns:
            str: Task ID
        """
        # Create task
        task = Task(
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            task_id=task_id,
            timeout=timeout or self.default_timeout,
            callback=callback,
            error_callback=error_callback
        )
        
        # Register task
        with self.tasks_lock:
            self.tasks[task.task_id] = task
            
        # Add to queue
        self.task_queue.put(task)
        
        return task.task_id
        
    async def submit_async(
        self,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        task_id: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """Submit a task to the thread pool and await its result.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            priority: Priority level for the task
            task_id: Unique identifier for the task (generated if not provided)
            timeout: Maximum execution time in seconds (None for no timeout)
            **kwargs: Keyword arguments for the function
            
        Returns:
            Any: Task result
            
        Raises:
            Exception: If the task fails
        """
        # Create future for async result
        future = self.loop.create_future()
        
        def on_complete(result):
            self.loop.call_soon_threadsafe(future.set_result, result)
            
        def on_error(error):
            self.loop.call_soon_threadsafe(future.set_exception, error)
            
        # Submit task with callbacks
        task_id = self.submit(
            func,
            *args,
            priority=priority,
            task_id=task_id,
            timeout=timeout,
            callback=on_complete,
            error_callback=on_error,
            **kwargs
        )
        
        # Wait for result
        return await future
        
    def run_async(self, coro):
        """Run a coroutine in the async event loop.
        
        Args:
            coro: Coroutine to run
            
        Returns:
            concurrent.futures.Future: Future for the coroutine result
        """
        return asyncio.run_coroutine_threadsafe(coro, self.loop)
        
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Optional[Task]: Task object if found, None otherwise
        """
        with self.tasks_lock:
            return self.tasks.get(task_id)
            
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the status of a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Optional[TaskStatus]: Task status if found, None otherwise
        """
        task = self.get_task(task_id)
        return task.status if task else None
        
    def get_task_result(self, task_id: str) -> Any:
        """Get the result of a completed task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Any: Task result
            
        Raises:
            ValueError: If task not found
            RuntimeError: If task not completed
            Exception: If task failed
        """
        task = self.get_task(task_id)
        
        if not task:
            raise ValueError(f"Task {task_id} not found")
            
        if task.status == TaskStatus.PENDING or task.status == TaskStatus.RUNNING:
            raise RuntimeError(f"Task {task_id} not completed yet")
            
        if task.status == TaskStatus.FAILED:
            raise task.error or RuntimeError(f"Task {task_id} failed")
            
        if task.status == TaskStatus.CANCELLED:
            raise RuntimeError(f"Task {task_id} was cancelled")
            
        return task.result
        
    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> bool:
        """Wait for a task to complete.
        
        Args:
            task_id: Task ID
            timeout: Maximum time to wait in seconds (None for no timeout)
            
        Returns:
            bool: True if task completed, False if timed out
        """
        task = self.get_task(task_id)
        
        if not task:
            raise ValueError(f"Task {task_id} not found")
            
        start_time = time.time()
        
        while task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            time.sleep(0.1)
            
            if timeout is not None and time.time() - start_time > timeout:
                return False
                
        return True
        
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task if possible.
        
        Args:
            task_id: Task ID
            
        Returns:
            bool: True if task was cancelled, False otherwise
        """
        with self.tasks_lock:
            task = self.tasks.get(task_id)
            
            if not task:
                return False
                
            if task.status != TaskStatus.PENDING and task.status != TaskStatus.RUNNING:
                return False
                
            # Cancel future if available
            if task.future and not task.future.done():
                task.future.cancel()
                
            # Update task status
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                task.end_time = time.time()
                return True
                
            # For running tasks, we can't reliably cancel them
            # Just mark as cancelled and let them complete
            task.status = TaskStatus.CANCELLED
            task.end_time = time.time()
            
            return True
            
    def shutdown(self, wait: bool = True):
        """Shutdown the thread pool manager.
        
        Args:
            wait: Whether to wait for all tasks to complete
        """
        logger.info("Shutting down ThreadPoolManager")
        
        # Signal workers to stop
        self.shutdown_event.set()
        
        # Wait for workers to finish if requested
        if wait:
            for worker in self.worker_threads:
                worker.join(timeout=5.0)
                
        # Shutdown executor
        self.executor.shutdown(wait=wait)
        
        # Stop async loop
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.async_thread.join(timeout=5.0)
        
        logger.info("ThreadPoolManager shutdown complete")
        
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the thread pool.
        
        Returns:
            Dict[str, Any]: Statistics
        """
        with self.tasks_lock:
            total_tasks = len(self.tasks)
            pending_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.PENDING)
            running_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.RUNNING)
            completed_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED)
            failed_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.FAILED)
            cancelled_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.CANCELLED)
            
            queue_size = self.task_queue.qsize()
            
            return {
                'max_workers': self.max_workers,
                'active_workers': running_tasks,
                'queue_size': queue_size,
                'total_tasks': total_tasks,
                'pending_tasks': pending_tasks,
                'running_tasks': running_tasks,
                'completed_tasks': completed_tasks,
                'failed_tasks': failed_tasks,
                'cancelled_tasks': cancelled_tasks
            }
            
    def cleanup_completed_tasks(self, max_age: float = 3600.0):
        """Clean up completed tasks older than max_age.
        
        Args:
            max_age: Maximum age of completed tasks in seconds
        """
        current_time = time.time()
        
        with self.tasks_lock:
            to_remove = []
            
            for task_id, task in self.tasks.items():
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    if task.end_time and current_time - task.end_time > max_age:
                        to_remove.append(task_id)
                        
            for task_id in to_remove:
                del self.tasks[task_id]
                
            return len(to_remove)


# Global instance
thread_pool_manager = ThreadPoolManager()

