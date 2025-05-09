"""
Thread pool optimization utilities for WiseFlow.

This module provides functions to optimize thread pool management in WiseFlow.
"""

import os
import time
import asyncio
import logging
import uuid
import concurrent.futures
from typing import Dict, Any, Optional, Callable, List, Set, Union, Awaitable
from datetime import datetime
from enum import Enum, auto
import threading
import psutil

logger = logging.getLogger(__name__)

class AdaptiveThreadPoolManager:
    """
    Adaptive thread pool manager for WiseFlow.
    
    This class provides a thread pool that adapts to system load and workload.
    """
    
    _instance = None
    
    def __new__(cls):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(AdaptiveThreadPoolManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the adaptive thread pool manager."""
        if self._initialized:
            return
            
        # Initial configuration
        self.min_workers = max(2, os.cpu_count() or 4)
        self.max_workers = max(8, (os.cpu_count() or 4) * 2)
        self.current_workers = self.min_workers
        
        # Create executor with initial size
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.current_workers)
        
        # Task tracking
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.futures: Dict[str, concurrent.futures.Future] = {}
        self.active_tasks = 0
        
        # Monitoring
        self.last_adjustment_time = time.time()
        self.adjustment_interval = 30  # seconds
        self.cpu_threshold_high = 80  # percent
        self.cpu_threshold_low = 20  # percent
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_load, daemon=True)
        self.monitor_thread.start()
        
        self._initialized = True
        
        logger.info(f"Adaptive thread pool manager initialized with {self.current_workers} workers")
    
    def _monitor_load(self):
        """Monitor system load and adjust thread pool size."""
        while True:
            try:
                # Sleep first to allow initial tasks to be submitted
                time.sleep(self.adjustment_interval)
                
                # Check if adjustment is needed
                now = time.time()
                if now - self.last_adjustment_time < self.adjustment_interval:
                    continue
                
                # Get CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                
                # Get active tasks count
                active_tasks = self.active_tasks
                
                # Decide if adjustment is needed
                if cpu_percent > self.cpu_threshold_high and self.current_workers > self.min_workers:
                    # High CPU usage, reduce workers
                    self._adjust_pool_size(max(self.min_workers, self.current_workers - 1))
                elif cpu_percent < self.cpu_threshold_low and active_tasks > self.current_workers * 0.8 and self.current_workers < self.max_workers:
                    # Low CPU usage but high task count, increase workers
                    self._adjust_pool_size(min(self.max_workers, self.current_workers + 1))
                
                self.last_adjustment_time = now
            except Exception as e:
                logger.error(f"Error in thread pool monitor: {e}")
    
    def _adjust_pool_size(self, new_size: int):
        """
        Adjust the thread pool size.
        
        Args:
            new_size: New pool size
        """
        if new_size == self.current_workers:
            return
        
        logger.info(f"Adjusting thread pool size from {self.current_workers} to {new_size}")
        
        # Create new executor
        new_executor = concurrent.futures.ThreadPoolExecutor(max_workers=new_size)
        
        # Replace executor
        old_executor = self.executor
        self.executor = new_executor
        self.current_workers = new_size
        
        # Shutdown old executor without waiting for tasks to complete
        # (they will continue running)
        old_executor.shutdown(wait=False)
    
    def submit(
        self,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        name: str = "Unnamed Task",
        priority: int = 0,
        **kwargs
    ) -> str:
        """
        Submit a task to the thread pool.
        
        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            task_id: Optional task ID, if not provided a new one will be generated
            name: Name of the task
            priority: Priority of the task (higher is more important)
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
            "status": "pending",
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None
        }
        
        # Add task to manager
        self.tasks[task_id] = task
        
        # Submit task to executor
        future = self.executor.submit(self._execute_task, task_id, func, *args, **kwargs)
        self.futures[task_id] = future
        
        # Update task status
        task["status"] = "running"
        task["started_at"] = datetime.now()
        
        # Increment active tasks
        self.active_tasks += 1
        
        # Add callback to handle completion
        future.add_done_callback(lambda f: self._handle_completion(task_id, f))
        
        logger.info(f"Task submitted to thread pool: {task_id} ({name})")
        return task_id
    
    def _execute_task(self, task_id: str, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a task with proper error handling.
        
        Args:
            task_id: Task ID
            func: Function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Function result
        """
        try:
            # Execute the function
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            raise
    
    def _handle_completion(self, task_id: str, future: concurrent.futures.Future):
        """
        Handle task completion.
        
        Args:
            task_id: ID of the task
            future: Future object for the task
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return
        
        # Decrement active tasks
        self.active_tasks -= 1
        
        try:
            # Get result
            result = future.result()
            
            # Update task
            task["status"] = "completed"
            task["completed_at"] = datetime.now()
            task["result"] = result
            
            logger.info(f"Task completed: {task_id} ({task['name']})")
        except Exception as e:
            # Update task
            task["status"] = "failed"
            task["completed_at"] = datetime.now()
            task["error"] = str(e)
            
            logger.error(f"Task failed: {task_id} ({task['name']}): {e}")
    
    def cancel(self, task_id: str) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        future = self.futures.get(task_id)
        if not future:
            logger.warning(f"Task {task_id} not found")
            return False
        
        # Cancel future
        result = future.cancel()
        
        if result:
            # Update task
            task = self.tasks.get(task_id)
            if task:
                task["status"] = "cancelled"
                task["completed_at"] = datetime.now()
                
                # Decrement active tasks if it was running
                if task.get("status") == "running":
                    self.active_tasks -= 1
            
            logger.info(f"Task cancelled: {task_id}")
        
        return result
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a task by ID.
        
        Args:
            task_id: ID of the task to get
            
        Returns:
            Task dictionary or None if not found
        """
        return self.tasks.get(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[str]:
        """
        Get the status of a task.
        
        Args:
            task_id: ID of the task to get status for
            
        Returns:
            Task status or None if task not found
        """
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
        task = self.tasks.get(task_id)
        return task["result"] if task and task["status"] == "completed" else None
    
    def get_task_error(self, task_id: str) -> Optional[str]:
        """
        Get the error of a failed task.
        
        Args:
            task_id: ID of the task to get error for
            
        Returns:
            Task error or None if task not found or not failed
        """
        task = self.tasks.get(task_id)
        return task["error"] if task and task["status"] == "failed" else None
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all tasks.
        
        Returns:
            Dictionary of all tasks
        """
        return self.tasks.copy()
    
    def get_tasks_by_status(self, status: str) -> Dict[str, Dict[str, Any]]:
        """
        Get tasks by status.
        
        Args:
            status: Status to filter by
            
        Returns:
            Dictionary of tasks with the specified status
        """
        return {task_id: task for task_id, task in self.tasks.items() if task["status"] == status}
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown the thread pool.
        
        Args:
            wait: Whether to wait for pending tasks to complete
        """
        self.executor.shutdown(wait=wait)
        logger.info(f"Thread pool manager shutdown (wait={wait})")

# Create a singleton instance
adaptive_thread_pool_manager = AdaptiveThreadPoolManager()

