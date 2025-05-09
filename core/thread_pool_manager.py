"""
Thread pool manager for WiseFlow.

This module provides a thread pool manager for executing tasks concurrently.
"""

import os
import time
import asyncio
import logging
import uuid
import threading
import concurrent.futures
import queue
from typing import Dict, Any, Optional, Callable, List, Set, Union, Awaitable, Tuple
from datetime import datetime
from enum import Enum, auto

from core.config import config
from core.task_manager import TaskPriority, TaskStatus
from core.event_system import (
    EventType, Event, publish_sync,
    create_task_event
)
from core.utils.error_handling import handle_exceptions, TaskError

logger = logging.getLogger(__name__)

class ThreadPoolManager:
    """
    Thread pool manager for WiseFlow.
    
    This class provides a thread pool for executing CPU-bound tasks concurrently.
    """
    
    _instance = None
    
    def __new__(cls):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(ThreadPoolManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the thread pool manager."""
        if self._initialized:
            return
        
        # Configure thread pool size
        self.min_workers = config.get("MIN_THREAD_WORKERS", max(2, os.cpu_count() // 2))
        self.max_workers = config.get("MAX_THREAD_WORKERS", os.cpu_count() or 4)
        
        # Create thread pool with adaptive sizing
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="wiseflow_worker"
        )
        
        # Task tracking
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.futures: Dict[str, concurrent.futures.Future] = {}
        
        # Task queue for prioritization
        self.task_queue = queue.PriorityQueue()
        
        # Locks for thread safety
        self._tasks_lock = threading.RLock()
        self._metrics_lock = threading.RLock()
        
        # Metrics tracking
        self._metrics = {
            "tasks_submitted": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_cancelled": 0,
            "total_execution_time": 0.0,
            "avg_execution_time": 0.0,
            "queue_size_history": [],
            "active_workers_history": []
        }
        
        # Worker management
        self._active_workers = 0
        self._worker_lock = threading.RLock()
        
        # Start monitoring thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_thread_pool,
            name="thread_pool_monitor",
            daemon=True
        )
        self._monitor_thread.start()
        
        self._initialized = True
        
        logger.info(f"Thread pool manager initialized with {self.min_workers}-{self.max_workers} workers")
    
    def submit(
        self,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        name: str = "Unnamed Task",
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Submit a task to the thread pool.
        
        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            task_id: Optional task ID, if not provided a new one will be generated
            name: Name of the task
            priority: Priority of the task
            timeout: Timeout in seconds for the task
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Task ID
        """
        task_id = task_id or str(uuid.uuid4())
        
        # Create task
        task = {
            "task_id": task_id,
            "name": name,
            "func": func,
            "args": args,
            "kwargs": kwargs,
            "priority": priority,
            "timeout": timeout,
            "status": TaskStatus.PENDING,
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None
        }
        
        # Add task to manager with lock protection
        with self._tasks_lock:
            self.tasks[task_id] = task
        
        # Update metrics
        with self._metrics_lock:
            self._metrics["tasks_submitted"] += 1
        
        # Add to priority queue
        # Lower priority value means higher priority
        self.task_queue.put((5 - priority.value, time.time(), task_id))
        
        # Publish event
        try:
            event = create_task_event(
                EventType.TASK_CREATED,
                task_id,
                {"name": name, "priority": priority.name}
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish task created event: {e}")
        
        logger.info(f"Task submitted to thread pool: {task_id} ({name})")
        
        # Start task execution in a separate thread
        threading.Thread(
            target=self._process_task_queue,
            name=f"task_processor_{task_id}",
            daemon=True
        ).start()
        
        return task_id
    
    def _process_task_queue(self):
        """Process the task queue and execute tasks."""
        try:
            # Check if we can get a task from the queue
            try:
                # Non-blocking get with timeout
                _, _, task_id = self.task_queue.get(block=True, timeout=0.1)
            except queue.Empty:
                return
            
            # Get the task
            with self._tasks_lock:
                task = self.tasks.get(task_id)
                if not task:
                    self.task_queue.task_done()
                    return
                
                # Check if task is still pending
                if task["status"] != TaskStatus.PENDING:
                    self.task_queue.task_done()
                    return
                
                # Mark task as running
                task["status"] = TaskStatus.RUNNING
                task["started_at"] = datetime.now()
            
            # Increment active workers count
            with self._worker_lock:
                self._active_workers += 1
            
            # Submit task to executor
            start_time = time.time()
            
            if task["timeout"]:
                # Create a future with timeout
                future = self.executor.submit(self._execute_with_timeout, task["func"], task["timeout"], *task["args"], **task["kwargs"])
            else:
                # Create a future without timeout
                future = self.executor.submit(task["func"], *task["args"], **task["kwargs"])
            
            # Store future
            with self._tasks_lock:
                self.futures[task_id] = future
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_STARTED,
                    task_id,
                    {"name": task["name"]}
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task started event: {e}")
            
            logger.info(f"Task started: {task_id} ({task['name']})")
            
            # Add callback to handle completion
            future.add_done_callback(
                lambda f: self._handle_completion(task_id, f, start_time)
            )
            
            # Mark task as done in the queue
            self.task_queue.task_done()
        except Exception as e:
            logger.error(f"Error processing task queue: {e}")
            # Decrement active workers count if we failed before submitting
            with self._worker_lock:
                self._active_workers -= 1
    
    def _execute_with_timeout(self, func, timeout, *args, **kwargs):
        """Execute a function with a timeout."""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Function timed out after {timeout} seconds")
        
        # Set timeout alarm
        original_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))
        
        try:
            # Execute function
            return func(*args, **kwargs)
        finally:
            # Reset alarm and restore original handler
            signal.alarm(0)
            signal.signal(signal.SIGALRM, original_handler)
    
    def _handle_completion(self, task_id: str, future: concurrent.futures.Future, start_time: float):
        """
        Handle task completion.
        
        Args:
            task_id: ID of the task
            future: Future object for the task
            start_time: Time when the task was started
        """
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Decrement active workers count
        with self._worker_lock:
            self._active_workers -= 1
        
        # Get the task
        with self._tasks_lock:
            task = self.tasks.get(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found")
                return
        
        try:
            # Get result
            result = future.result()
            
            # Update task
            with self._tasks_lock:
                task["status"] = TaskStatus.COMPLETED
                task["completed_at"] = datetime.now()
                task["result"] = result
            
            # Update metrics
            with self._metrics_lock:
                self._metrics["tasks_completed"] += 1
                self._metrics["total_execution_time"] += execution_time
                if self._metrics["tasks_completed"] > 0:
                    self._metrics["avg_execution_time"] = (
                        self._metrics["total_execution_time"] / self._metrics["tasks_completed"]
                    )
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_COMPLETED,
                    task_id,
                    {
                        "name": task["name"],
                        "execution_time": execution_time
                    }
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task completed event: {e}")
            
            logger.info(f"Task completed: {task_id} ({task['name']}) in {execution_time:.2f}s")
        except concurrent.futures.CancelledError:
            # Task was cancelled
            with self._tasks_lock:
                task["status"] = TaskStatus.CANCELLED
                task["completed_at"] = datetime.now()
                task["error"] = "Task was cancelled"
            
            # Update metrics
            with self._metrics_lock:
                self._metrics["tasks_cancelled"] += 1
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_CANCELLED,
                    task_id,
                    {
                        "name": task["name"],
                        "execution_time": execution_time
                    }
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task cancelled event: {e}")
            
            logger.info(f"Task cancelled: {task_id} ({task['name']}) after {execution_time:.2f}s")
        except Exception as e:
            # Task failed
            with self._tasks_lock:
                task["status"] = TaskStatus.FAILED
                task["completed_at"] = datetime.now()
                task["error"] = str(e)
            
            # Update metrics
            with self._metrics_lock:
                self._metrics["tasks_failed"] += 1
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_FAILED,
                    task_id,
                    {
                        "name": task["name"],
                        "error": str(e),
                        "execution_time": execution_time
                    }
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task failed event: {e}")
            
            logger.error(f"Task failed: {task_id} ({task['name']}) after {execution_time:.2f}s: {e}")
    
    def cancel(self, task_id: str) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        with self._tasks_lock:
            future = self.futures.get(task_id)
            task = self.tasks.get(task_id)
            
            if not future or not task:
                logger.warning(f"Task {task_id} not found")
                return False
            
            # Only cancel if the task is still running
            if task["status"] != TaskStatus.RUNNING:
                logger.warning(f"Cannot cancel task {task_id} with status {task['status']}")
                return False
            
            # Cancel future
            result = future.cancel()
            
            if result:
                # Update task
                task["status"] = TaskStatus.CANCELLED
                task["completed_at"] = datetime.now()
                
                # Update metrics
                with self._metrics_lock:
                    self._metrics["tasks_cancelled"] += 1
                
                # Publish event
                try:
                    event = create_task_event(
                        EventType.TASK_CANCELLED,
                        task_id,
                        {"name": task["name"], "reason": "cancelled"}
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish task cancelled event: {e}")
                
                logger.info(f"Task cancelled: {task_id} ({task['name']})")
            
            return result
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a task by ID.
        
        Args:
            task_id: ID of the task to get
            
        Returns:
            Task dictionary or None if not found
        """
        with self._tasks_lock:
            return self.tasks.get(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get the status of a task.
        
        Args:
            task_id: ID of the task to get status for
            
        Returns:
            Task status or None if task not found
        """
        with self._tasks_lock:
            task = self.tasks.get(task_id)
            return task["status"] if task else None
    
    def get_task_result(self, task_id: str) -> Any:
        """
        Get the result of a task.
        
        Args:
            task_id: ID of the task to get result for
            
        Returns:
            Task result or None if task not found or not completed
        """
        with self._tasks_lock:
            task = self.tasks.get(task_id)
            return task["result"] if task and task["status"] == TaskStatus.COMPLETED else None
    
    def get_task_error(self, task_id: str) -> Optional[str]:
        """
        Get the error of a failed task.
        
        Args:
            task_id: ID of the task to get error for
            
        Returns:
            Task error or None if task not found or not failed
        """
        with self._tasks_lock:
            task = self.tasks.get(task_id)
            return task["error"] if task and task["status"] == TaskStatus.FAILED else None
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all tasks.
        
        Returns:
            Dictionary of all tasks
        """
        with self._tasks_lock:
            return self.tasks.copy()
    
    def get_pending_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all pending tasks.
        
        Returns:
            Dictionary of pending tasks
        """
        with self._tasks_lock:
            return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.PENDING}
    
    def get_running_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all running tasks.
        
        Returns:
            Dictionary of running tasks
        """
        with self._tasks_lock:
            return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.RUNNING}
    
    def get_completed_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all completed tasks.
        
        Returns:
            Dictionary of completed tasks
        """
        with self._tasks_lock:
            return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.COMPLETED}
    
    def get_failed_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all failed tasks.
        
        Returns:
            Dictionary of failed tasks
        """
        with self._tasks_lock:
            return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.FAILED}
    
    def get_cancelled_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all cancelled tasks.
        
        Returns:
            Dictionary of cancelled tasks
        """
        with self._tasks_lock:
            return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.CANCELLED}
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get thread pool metrics.
        
        Returns:
            Dictionary of metrics
        """
        with self._metrics_lock:
            metrics = self._metrics.copy()
        
        # Add current task counts
        with self._tasks_lock:
            metrics.update({
                "pending_tasks": len([t for t in self.tasks.values() if t["status"] == TaskStatus.PENDING]),
                "running_tasks": len([t for t in self.tasks.values() if t["status"] == TaskStatus.RUNNING]),
                "completed_tasks": len([t for t in self.tasks.values() if t["status"] == TaskStatus.COMPLETED]),
                "failed_tasks": len([t for t in self.tasks.values() if t["status"] == TaskStatus.FAILED]),
                "cancelled_tasks": len([t for t in self.tasks.values() if t["status"] == TaskStatus.CANCELLED]),
                "total_tasks": len(self.tasks)
            })
        
        # Add thread pool metrics
        with self._worker_lock:
            metrics.update({
                "worker_count": self.executor._max_workers,
                "active_workers": self._active_workers,
                "queue_size": self.task_queue.qsize()
            })
        
        return metrics
    
    def _monitor_thread_pool(self):
        """Monitor thread pool and adjust size if needed."""
        while True:
            try:
                # Sleep for a while
                time.sleep(30)
                
                # Get current metrics
                metrics = self.get_metrics()
                
                # Update history
                with self._metrics_lock:
                    self._metrics["queue_size_history"].append(metrics["queue_size"])
                    self._metrics["active_workers_history"].append(metrics["active_workers"])
                    
                    # Keep history size limited
                    if len(self._metrics["queue_size_history"]) > 10:
                        self._metrics["queue_size_history"] = self._metrics["queue_size_history"][-10:]
                    if len(self._metrics["active_workers_history"]) > 10:
                        self._metrics["active_workers_history"] = self._metrics["active_workers_history"][-10:]
                
                # Calculate average queue size and active workers
                avg_queue_size = sum(self._metrics["queue_size_history"]) / len(self._metrics["queue_size_history"])
                avg_active_workers = sum(self._metrics["active_workers_history"]) / len(self._metrics["active_workers_history"])
                
                # Log current status
                logger.debug(
                    f"Thread pool status: workers={metrics['worker_count']}, "
                    f"active={metrics['active_workers']} (avg={avg_active_workers:.1f}), "
                    f"queue={metrics['queue_size']} (avg={avg_queue_size:.1f})"
                )
                
                # Adjust thread pool size if needed
                self._adjust_thread_pool_size(avg_queue_size, avg_active_workers)
                
                # Clean up old tasks
                self._cleanup_old_tasks()
            except Exception as e:
                logger.error(f"Error in thread pool monitor: {e}")
    
    def _adjust_thread_pool_size(self, avg_queue_size: float, avg_active_workers: float):
        """
        Adjust thread pool size based on workload.
        
        Args:
            avg_queue_size: Average queue size
            avg_active_workers: Average number of active workers
        """
        # Get current worker count
        current_workers = self.executor._max_workers
        
        # Calculate optimal worker count
        if avg_queue_size > 5 and current_workers < self.max_workers:
            # Increase worker count if queue is growing
            new_workers = min(current_workers + 2, self.max_workers)
            if new_workers > current_workers:
                logger.info(f"Increasing thread pool size from {current_workers} to {new_workers} workers")
                self._resize_thread_pool(new_workers)
        elif avg_queue_size < 2 and avg_active_workers < current_workers * 0.5 and current_workers > self.min_workers:
            # Decrease worker count if workers are idle
            new_workers = max(current_workers - 1, self.min_workers)
            if new_workers < current_workers:
                logger.info(f"Decreasing thread pool size from {current_workers} to {new_workers} workers")
                self._resize_thread_pool(new_workers)
    
    def _resize_thread_pool(self, new_size: int):
        """
        Resize the thread pool.
        
        Args:
            new_size: New thread pool size
        """
        # Create a new executor with the new size
        new_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=new_size,
            thread_name_prefix="wiseflow_worker"
        )
        
        # Shutdown old executor without waiting for tasks to complete
        # (they will continue running in the background)
        self.executor.shutdown(wait=False)
        
        # Replace executor
        self.executor = new_executor
    
    def _cleanup_old_tasks(self, max_age_seconds: int = 3600):
        """
        Clean up old completed, failed, and cancelled tasks.
        
        Args:
            max_age_seconds: Maximum age of tasks to keep in seconds
        """
        now = datetime.now()
        count = 0
        
        with self._tasks_lock:
            for task_id in list(self.tasks.keys()):
                task = self.tasks[task_id]
                
                # Skip tasks that are still running or pending
                if task["status"] in [TaskStatus.RUNNING, TaskStatus.PENDING]:
                    continue
                
                # Remove old completed, failed, and cancelled tasks
                if task["completed_at"] and (now - task["completed_at"]).total_seconds() > max_age_seconds:
                    del self.tasks[task_id]
                    if task_id in self.futures:
                        del self.futures[task_id]
                    count += 1
        
        if count > 0:
            logger.info(f"Cleaned up {count} old tasks")
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown the thread pool.
        
        Args:
            wait: Whether to wait for pending tasks to complete
        """
        # Cancel all running tasks if not waiting
        if not wait:
            with self._tasks_lock:
                for task_id, task in self.tasks.items():
                    if task["status"] == TaskStatus.RUNNING:
                        future = self.futures.get(task_id)
                        if future and not future.done():
                            future.cancel()
        
        # Shutdown executor
        self.executor.shutdown(wait=wait)
        
        logger.info(f"Thread pool manager shutdown (wait={wait})")
    
    def stop(self):
        """Stop the thread pool manager."""
        self.shutdown(wait=False)

# Create a singleton instance
thread_pool_manager = ThreadPoolManager()
