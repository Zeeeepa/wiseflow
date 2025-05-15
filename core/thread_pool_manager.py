"""
Thread pool manager for WiseFlow.

This module provides a thread pool manager for executing tasks concurrently.
"""

import os
import logging
import uuid
import concurrent.futures




from typing import Dict, Any, Optional, Callable, List, Set

from datetime import datetime

from core.config import config
from core.task_manager import TaskPriority, TaskStatus
from core.resource_monitor import resource_monitor
from core.event_system import (
    EventType, publish_sync,
    create_task_event
)

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
            
        # Initialize configuration
        self.min_workers = config.get("MIN_THREAD_WORKERS", 2)
        self.max_workers = config.get("MAX_THREAD_WORKERS", os.cpu_count() or 4)
        self.initial_workers = config.get("INITIAL_THREAD_WORKERS", min(os.cpu_count() or 4, self.max_workers))
        self.adaptive_scaling = config.get("ADAPTIVE_THREAD_SCALING", True)
        self.scaling_interval = config.get("THREAD_SCALING_INTERVAL", 30.0)  # seconds
        self.cpu_threshold_scale_down = config.get("CPU_THRESHOLD_SCALE_DOWN", 75.0)
        self.cpu_threshold_scale_up = config.get("CPU_THRESHOLD_SCALE_UP", 30.0)
        self.memory_threshold_scale_down = config.get("MEMORY_THRESHOLD_SCALE_DOWN", 80.0)
        
        # Initialize thread pool
        self.current_workers = self.initial_workers
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.current_workers)
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.futures: Dict[str, concurrent.futures.Future] = {}
        
        # Initialize scaling
        self.scaling_task = None
        self.scaling_lock = threading.RLock()
        self.last_scaling_time = time.time()
        
        # Initialize metrics
        self.metrics = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "cancelled_tasks": 0,
            "task_times": [],
            "scaling_events": [],
            "worker_history": [(datetime.now(), self.current_workers)]
        }
        
        self._initialized = True
        
        # Start adaptive scaling if enabled
        if self.adaptive_scaling:
            self._start_adaptive_scaling()
        
        logger.info(f"Thread pool manager initialized with {self.current_workers} workers (min={self.min_workers}, max={self.max_workers})")
    
    def _start_adaptive_scaling(self):
        """Start adaptive scaling of the thread pool."""
        if self.scaling_task is not None:
            return
        
        def scaling_loop():
            while True:
                try:
                    self._adjust_thread_pool()
                    time.sleep(self.scaling_interval)
                except Exception as e:
                    logger.error(f"Error in thread pool scaling: {e}")
                    time.sleep(self.scaling_interval)
        
        self.scaling_task = threading.Thread(target=scaling_loop, daemon=True)
        self.scaling_task.start()
        logger.info("Adaptive thread pool scaling started")
    
    def _adjust_thread_pool(self):
        """Adjust the thread pool size based on system load."""
        with self.scaling_lock:
            # Check if enough time has passed since the last scaling
            current_time = time.time()
            if current_time - self.last_scaling_time < self.scaling_interval:
                return
            
            # Get current resource usage
            resource_usage = resource_monitor.get_resource_usage()
            cpu_percent = resource_usage["cpu"]["average"]
            memory_percent = resource_usage["memory"]["average"]
            
            # Get recommended thread count from resource monitor
            recommended_workers = resource_usage.get("recommended_thread_count")
            
            # Determine new worker count
            new_workers = self.current_workers
            
            if recommended_workers is not None:
                # Use recommended thread count if available
                new_workers = recommended_workers
            else:
                # Scale down if CPU or memory usage is high
                if cpu_percent > self.cpu_threshold_scale_down or memory_percent > self.memory_threshold_scale_down:
                    new_workers = max(self.min_workers, int(self.current_workers * 0.75))
                # Scale up if CPU usage is low and memory usage is acceptable
                elif cpu_percent < self.cpu_threshold_scale_up and memory_percent < self.memory_threshold_scale_down:
                    new_workers = min(self.max_workers, int(self.current_workers * 1.5))
            
            # Ensure worker count is within bounds
            new_workers = max(self.min_workers, min(self.max_workers, new_workers))
            
            # Only adjust if the worker count has changed
            if new_workers != self.current_workers:
                logger.info(f"Adjusting thread pool size from {self.current_workers} to {new_workers} workers (CPU: {cpu_percent:.1f}%, Memory: {memory_percent:.1f}%)")
                
                # Create a new executor with the new worker count
                new_executor = concurrent.futures.ThreadPoolExecutor(max_workers=new_workers)
                
                # Update the executor
                old_executor = self.executor
                self.executor = new_executor
                self.current_workers = new_workers
                
                # Record scaling event
                self.metrics["scaling_events"].append({
                    "timestamp": datetime.now(),
                    "old_workers": self.current_workers,
                    "new_workers": new_workers,
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent
                })
                
                # Record worker history
                self.metrics["worker_history"].append((datetime.now(), new_workers))
                
                # Limit history size
                if len(self.metrics["worker_history"]) > 100:
                    self.metrics["worker_history"] = self.metrics["worker_history"][-100:]
                
                # Shutdown the old executor without waiting for tasks to complete
                # (they will continue running)
                old_executor.shutdown(wait=False)
                
                # Update last scaling time
                self.last_scaling_time = current_time
    
    def submit(
        self,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        name: str = "Unnamed Task",
        priority: TaskPriority = TaskPriority.NORMAL,
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
            "status": TaskStatus.PENDING,
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None
        }
        
        # Add task to manager
        self.tasks[task_id] = task
        
        # Submit task to executor
        start_time = time.time()
        future = self.executor.submit(func, *args, **kwargs)
        self.futures[task_id] = future
        
        # Update task status
        task["status"] = TaskStatus.RUNNING
        task["started_at"] = datetime.now()
        
        # Add callback to handle completion
        future.add_done_callback(lambda f: self._handle_completion(task_id, f, start_time))
        
        # Update metrics
        self.metrics["total_tasks"] += 1
        
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
        return task_id
    
    def _handle_completion(self, task_id: str, future: concurrent.futures.Future, start_time: float):
        """
        Handle task completion.
        
        Args:
            task_id: ID of the task
            future: Future object for the task
            start_time: Time when the task was started
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return
        
        # Calculate task execution time
        execution_time = time.time() - start_time
        
        # Update metrics
        self.metrics["task_times"].append(execution_time)
        
        # Keep only the last 100 task times
        if len(self.metrics["task_times"]) > 100:
            self.metrics["task_times"] = self.metrics["task_times"][-100:]
        
        try:
            # Get result
            result = future.result()
            
            # Update task
            task["status"] = TaskStatus.COMPLETED
            task["completed_at"] = datetime.now()
            task["result"] = result
            
            # Update metrics
            self.metrics["completed_tasks"] += 1
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_COMPLETED,
                    task_id,
                    {"name": task["name"], "execution_time": execution_time}
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task completed event: {e}")
            
            logger.info(f"Task completed: {task_id} ({task['name']}) in {execution_time:.2f}s")
        except Exception as e:
            # Update task
            task["status"] = TaskStatus.FAILED
            task["completed_at"] = datetime.now()
            task["error"] = str(e)
            
            # Update metrics
            self.metrics["failed_tasks"] += 1
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_FAILED,
                    task_id,
                    {"name": task["name"], "error": str(e), "execution_time": execution_time}
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task failed event: {e}")
            
            logger.error(f"Task failed: {task_id} ({task['name']}): {e} in {execution_time:.2f}s")
    
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
                task["status"] = TaskStatus.CANCELLED
                task["completed_at"] = datetime.now()
            
            # Update metrics
            self.metrics["cancelled_tasks"] += 1
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_FAILED,
                    task_id,
                    {"name": task["name"] if task else "Unknown", "reason": "cancelled"}
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task cancelled event: {e}")
            
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
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
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
        return task["result"] if task and task["status"] == TaskStatus.COMPLETED else None
    
    def get_task_error(self, task_id: str) -> Optional[str]:
        """
        Get the error of a failed task.
        
        Args:
            task_id: ID of the task to get error for
            
        Returns:
            Task error or None if task not found or not failed
        """
        task = self.tasks.get(task_id)
        return task["error"] if task and task["status"] == TaskStatus.FAILED else None
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all tasks.
        
        Returns:
            Dictionary of all tasks
        """
        return self.tasks.copy()
    
    def get_pending_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all pending tasks.
        
        Returns:
            Dictionary of pending tasks
        """
        return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.PENDING}
    
    def get_running_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all running tasks.
        
        Returns:
            Dictionary of running tasks
        """
        return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.RUNNING}
    
    def get_completed_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all completed tasks.
        
        Returns:
            Dictionary of completed tasks
        """
        return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.COMPLETED}
    
    def get_failed_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all failed tasks.
        
        Returns:
            Dictionary of failed tasks
        """
        return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.FAILED}
    
    def get_cancelled_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all cancelled tasks.
        
        Returns:
            Dictionary of cancelled tasks
        """
        return {task_id: task for task_id, task in self.tasks.items() if task["status"] == TaskStatus.CANCELLED}
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Returns:
            Dictionary with performance metrics
        """
        metrics = self.metrics.copy()
        
        # Calculate average task time
        if metrics["task_times"]:
            metrics["average_task_time"] = sum(metrics["task_times"]) / len(metrics["task_times"])
        else:
            metrics["average_task_time"] = 0
        
        # Add current worker count
        metrics["current_workers"] = self.current_workers
        metrics["min_workers"] = self.min_workers
        metrics["max_workers"] = self.max_workers
        
        return metrics
    
    def set_worker_count(self, count: int) -> bool:
        """
        Manually set the worker count.
        
        Args:
            count: New worker count
            
        Returns:
            True if the worker count was changed, False otherwise
        """
        with self.scaling_lock:
            # Ensure count is within bounds
            count = max(self.min_workers, min(self.max_workers, count))
            
            # Only adjust if the worker count has changed
            if count != self.current_workers:
                logger.info(f"Manually adjusting thread pool size from {self.current_workers} to {count} workers")
                
                # Create a new executor with the new worker count
                new_executor = concurrent.futures.ThreadPoolExecutor(max_workers=count)
                
                # Update the executor
                old_executor = self.executor
                self.executor = new_executor
                self.current_workers = count
                
                # Record worker history
                self.metrics["worker_history"].append((datetime.now(), count))
                
                # Limit history size
                if len(self.metrics["worker_history"]) > 100:
                    self.metrics["worker_history"] = self.metrics["worker_history"][-100:]
                
                # Shutdown the old executor without waiting for tasks to complete
                # (they will continue running)
                old_executor.shutdown(wait=False)
                
                # Update last scaling time
                self.last_scaling_time = time.time()
                
                return True
            
            return False
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown the thread pool.
        
        Args:
            wait: Whether to wait for pending tasks to complete
        """
        # Stop adaptive scaling
        if self.scaling_task is not None:
            self.scaling_task = None
        
        # Shutdown the executor
        self.executor.shutdown(wait=wait)
        logger.info(f"Thread pool manager shutdown (wait={wait})")

# Create a singleton instance
thread_pool_manager = ThreadPoolManager()
