import threading
import queue
import time
import logging
from typing import Dict, List, Callable, Optional, Any, Tuple, Union
from enum import Enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from core.resource_monitor import ResourceMonitor

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    """Priority levels for tasks in the thread pool."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskStatus(Enum):
    """Status values for tasks in the thread pool."""
    PENDING = 0
    RUNNING = 1
    COMPLETED = 2
    FAILED = 3
    CANCELLED = 4


@dataclass
class Task:
    """Represents a task to be executed by the thread pool."""
    id: str
    func: Callable
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None
    retries: int = 0
    max_retries: int = 0
    retry_delay: float = 1.0
    
    def __lt__(self, other):
        """Compare tasks based on priority for the priority queue."""
        if not isinstance(other, Task):
            return NotImplemented
        return self.priority.value > other.priority.value


class ThreadPoolManager:
    """
    A thread pool manager that handles task scheduling, execution, and monitoring.
    Features priority-based scheduling, dynamic pool sizing, and task status tracking.
    """
    
    def __init__(self, 
                 min_workers: int = 2,
                 max_workers: int = 10,
                 resource_monitor: Optional[ResourceMonitor] = None,
                 adjust_interval: float = 30.0):
        """
        Initialize the thread pool manager.
        
        Args:
            min_workers: Minimum number of worker threads
            max_workers: Maximum number of worker threads
            resource_monitor: Optional ResourceMonitor instance for dynamic sizing
            adjust_interval: Time in seconds between worker count adjustments
        """
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.resource_monitor = resource_monitor
        self.adjust_interval = adjust_interval
        
        # Task queue with priority
        self.task_queue = queue.PriorityQueue()
        
        # Worker management
        self.workers = []
        self.worker_count = 0
        self.active_workers = 0
        self._worker_lock = threading.RLock()
        
        # Task tracking
        self.tasks = {}
        self._tasks_lock = threading.RLock()
        
        # Control flags
        self._stop_event = threading.Event()
        self._adjust_thread = None
        
        # Metrics
        self.metrics = {
            'tasks_submitted': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_cancelled': 0,
            'total_execution_time': 0.0,
            'avg_execution_time': 0.0,
            'max_execution_time': 0.0,
            'min_execution_time': float('inf'),
        }
        self._metrics_lock = threading.RLock()
    
    def start(self):
        """Start the thread pool and worker adjustment thread."""
        if self._stop_event.is_set():
            self._stop_event.clear()
        
        # Start initial workers
        self._adjust_worker_count(self.min_workers)
        
        # Start the adjustment thread if we have a resource monitor
        if self.resource_monitor and not self._adjust_thread:
            self._adjust_thread = threading.Thread(
                target=self._adjust_workers_periodically, 
                daemon=True
            )
            self._adjust_thread.start()
            logger.info("ThreadPoolManager started with dynamic worker adjustment")
        else:
            logger.info(f"ThreadPoolManager started with {self.min_workers} workers")
    
    def stop(self, wait_for_tasks: bool = True, timeout: Optional[float] = None):
        """
        Stop the thread pool.
        
        Args:
            wait_for_tasks: If True, wait for all tasks to complete
            timeout: Maximum time to wait for tasks to complete
        """
        if wait_for_tasks:
            # Wait for the task queue to empty
            start_time = time.time()
            while not self.task_queue.empty():
                if timeout and time.time() - start_time > timeout:
                    logger.warning("Timeout waiting for tasks to complete")
                    break
                time.sleep(0.1)
        
        # Signal all threads to stop
        self._stop_event.set()
        
        # Wait for all worker threads to finish
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=1.0 if timeout is None else min(1.0, timeout))
        
        # Clear the worker list
        with self._worker_lock:
            self.workers = []
            self.worker_count = 0
            self.active_workers = 0
        
        logger.info("ThreadPoolManager stopped")
    
    def submit(self, 
               func: Callable, 
               *args, 
               priority: TaskPriority = TaskPriority.NORMAL,
               max_retries: int = 0,
               retry_delay: float = 1.0,
               **kwargs) -> str:
        """
        Submit a task to the thread pool.
        
        Args:
            func: The function to execute
            *args: Positional arguments for the function
            priority: Task priority level
            max_retries: Maximum number of retry attempts if the task fails
            retry_delay: Delay in seconds between retry attempts
            **kwargs: Keyword arguments for the function
            
        Returns:
            Task ID that can be used to check status or cancel the task
        """
        task_id = str(uuid.uuid4())
        
        task = Task(
            id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries,
            retry_delay=retry_delay
        )
        
        # Store the task for tracking
        with self._tasks_lock:
            self.tasks[task_id] = task
        
        # Add to the priority queue
        self.task_queue.put(task)
        
        # Update metrics
        with self._metrics_lock:
            self.metrics['tasks_submitted'] += 1
        
        # Ensure we have enough workers
        self._ensure_min_workers()
        
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False if it couldn't be cancelled
        """
        with self._tasks_lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                
                # Can only cancel pending tasks
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED
                    
                    # Update metrics
                    with self._metrics_lock:
                        self.metrics['tasks_cancelled'] += 1
                    
                    return True
        
        return False
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get the current status of a task.
        
        Args:
            task_id: ID of the task to check
            
        Returns:
            TaskStatus enum value or None if task not found
        """
        with self._tasks_lock:
            if task_id in self.tasks:
                return self.tasks[task_id].status
        return None
    
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """
        Get the result of a completed task.
        
        Args:
            task_id: ID of the task to get the result for
            
        Returns:
            Task result or None if task not found or not completed
        """
        with self._tasks_lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status == TaskStatus.COMPLETED:
                    return task.result
        return None
    
    def get_task_error(self, task_id: str) -> Optional[Exception]:
        """
        Get the error from a failed task.
        
        Args:
            task_id: ID of the task to get the error for
            
        Returns:
            Exception object or None if task not found or not failed
        """
        with self._tasks_lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status == TaskStatus.FAILED:
                    return task.error
        return None
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current thread pool metrics.
        
        Returns:
            Dictionary with various performance metrics
        """
        with self._metrics_lock:
            metrics = self.metrics.copy()
        
        # Add current state information
        metrics.update({
            'worker_count': self.worker_count,
            'active_workers': self.active_workers,
            'queue_size': self.task_queue.qsize(),
            'pending_tasks': sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING),
            'running_tasks': sum(1 for t in self.tasks.values() if t.status == TaskStatus.RUNNING),
        })
        
        return metrics
    
    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for a specific task to complete.
        
        Args:
            task_id: ID of the task to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if the task completed, False if it timed out or wasn't found
        """
        start_time = time.time()
        
        while True:
            status = self.get_task_status(task_id)
            
            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return True
            
            if status is None:
                # Task not found
                return False
            
            if timeout and time.time() - start_time > timeout:
                # Timeout reached
                return False
            
            # Sleep briefly to avoid busy waiting
            time.sleep(0.1)
    
    def wait_all(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all submitted tasks to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if all tasks completed, False if timeout occurred
        """
        start_time = time.time()
        
        while True:
            with self._tasks_lock:
                active_tasks = sum(1 for t in self.tasks.values() 
                                  if t.status in [TaskStatus.PENDING, TaskStatus.RUNNING])
            
            if active_tasks == 0:
                return True
            
            if timeout and time.time() - start_time > timeout:
                return False
            
            # Sleep briefly to avoid busy waiting
            time.sleep(0.1)
    
    def _worker(self):
        """Worker thread function that processes tasks from the queue."""
        while not self._stop_event.is_set():
            try:
                # Try to get a task with a timeout to allow for checking the stop event
                try:
                    task = self.task_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                # Update active worker count
                with self._worker_lock:
                    self.active_workers += 1
                
                # Process the task if it's not cancelled
                if task.status != TaskStatus.CANCELLED:
                    self._process_task(task)
                
                # Mark the task as done in the queue
                self.task_queue.task_done()
                
                # Update active worker count
                with self._worker_lock:
                    self.active_workers -= 1
                
            except Exception as e:
                logger.error(f"Error in worker thread: {e}")
                with self._worker_lock:
                    self.active_workers -= 1
        
        # Thread is exiting, update the count
        with self._worker_lock:
            self.worker_count -= 1
    
    def _process_task(self, task: Task):
        """
        Process a single task, handling retries and updating status.
        
        Args:
            task: The Task object to process
        """
        # Update task status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        try:
            # Execute the task
            start_time = time.time()
            result = task.func(*task.args, **task.kwargs)
            execution_time = time.time() - start_time
            
            # Update task with success result
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.execution_time = execution_time
            task.completed_at = datetime.now()
            
            # Update metrics
            with self._metrics_lock:
                self.metrics['tasks_completed'] += 1
                self.metrics['total_execution_time'] += execution_time
                self.metrics['avg_execution_time'] = (
                    self.metrics['total_execution_time'] / self.metrics['tasks_completed']
                )
                self.metrics['max_execution_time'] = max(
                    self.metrics['max_execution_time'], execution_time
                )
                if execution_time < self.metrics['min_execution_time']:
                    self.metrics['min_execution_time'] = execution_time
            
        except Exception as e:
            # Task failed
            task.error = e
            task.retries += 1
            
            # Check if we should retry
            if task.retries <= task.max_retries:
                logger.info(f"Task {task.id} failed, retrying ({task.retries}/{task.max_retries}): {e}")
                
                # Reset status to pending for retry
                task.status = TaskStatus.PENDING
                
                # Wait for the retry delay
                time.sleep(task.retry_delay)
                
                # Put the task back in the queue
                self.task_queue.put(task)
            else:
                # Max retries reached, mark as failed
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                
                # Update metrics
                with self._metrics_lock:
                    self.metrics['tasks_failed'] += 1
                
                logger.error(f"Task {task.id} failed after {task.retries} retries: {e}")
    
    def _ensure_min_workers(self):
        """Ensure we have at least the minimum number of workers running."""
        with self._worker_lock:
            if self.worker_count < self.min_workers:
                self._adjust_worker_count(self.min_workers)
    
    def _adjust_worker_count(self, target_count: int):
        """
        Adjust the number of worker threads to the target count.
        
        Args:
            target_count: Desired number of worker threads
        """
        with self._worker_lock:
            target_count = max(self.min_workers, min(target_count, self.max_workers))
            
            # Add workers if needed
            while self.worker_count < target_count:
                worker = threading.Thread(target=self._worker, daemon=True)
                worker.start()
                self.workers.append(worker)
                self.worker_count += 1
                logger.debug(f"Added worker thread, count: {self.worker_count}")
            
            # Note: We don't remove workers directly; they'll exit when the stop event is set
            # or naturally when there are no more tasks
    
    def _adjust_workers_periodically(self):
        """Periodically adjust the number of workers based on system load."""
        while not self._stop_event.is_set():
            try:
                if self.resource_monitor:
                    # Get the optimal thread count from the resource monitor
                    optimal_count = self.resource_monitor.calculate_optimal_thread_count()
                    
                    # Adjust based on queue size and current active workers
                    queue_size = self.task_queue.qsize()
                    
                    if queue_size > optimal_count:
                        # More tasks than optimal threads, increase workers
                        target_count = min(self.max_workers, optimal_count + queue_size // 2)
                    elif queue_size == 0 and self.active_workers < self.min_workers:
                        # No tasks and few active workers, reduce to minimum
                        target_count = self.min_workers
                    else:
                        # Otherwise use the optimal count
                        target_count = optimal_count
                    
                    # Apply the adjustment
                    self._adjust_worker_count(target_count)
                    
                    logger.debug(f"Adjusted worker count to {target_count} (optimal: {optimal_count}, "
                                f"queue: {queue_size}, active: {self.active_workers})")
            
            except Exception as e:
                logger.error(f"Error adjusting worker count: {e}")
            
            # Wait for the next adjustment interval
            self._stop_event.wait(self.adjust_interval)


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create a resource monitor
    resource_monitor = ResourceMonitor(check_interval=2.0)
    resource_monitor.start()
    
    # Create a thread pool manager
    pool = ThreadPoolManager(
        min_workers=2,
        max_workers=10,
        resource_monitor=resource_monitor,
        adjust_interval=5.0
    )
    
    # Start the pool
    pool.start()
    
    # Example task function
    def example_task(task_id, sleep_time):
        logger.info(f"Task {task_id} started, will sleep for {sleep_time}s")
        time.sleep(sleep_time)
        logger.info(f"Task {task_id} completed")
        return f"Result from task {task_id}"
    
    # Submit some tasks with different priorities
    task_ids = []
    for i in range(10):
        # Alternate between priorities
        if i % 3 == 0:
            priority = TaskPriority.HIGH
        elif i % 3 == 1:
            priority = TaskPriority.NORMAL
        else:
            priority = TaskPriority.LOW
        
        # Submit the task
        task_id = pool.submit(
            example_task, 
            i, 
            sleep_time=1.0,
            priority=priority,
            max_retries=2
        )
        task_ids.append(task_id)
        logger.info(f"Submitted task {i} with ID {task_id} and priority {priority}")
    
    # Wait for all tasks to complete
    pool.wait_all()
    
    # Print results
    for task_id in task_ids:
        result = pool.get_task_result(task_id)
        logger.info(f"Task {task_id} result: {result}")
    
    # Print metrics
    metrics = pool.get_metrics()
    logger.info(f"Thread pool metrics: {metrics}")
    
    # Stop the pool and resource monitor
    pool.stop()
    resource_monitor.stop()
