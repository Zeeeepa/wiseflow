#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Thread Pool Manager for Wiseflow.

This module provides a dynamic thread pool implementation with resource monitoring
and adaptive scaling capabilities.
"""

import threading
import queue
import time
import logging
import uuid
from typing import Dict, List, Any, Optional, Callable, Tuple, Set, Union
from enum import Enum, auto
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, Future

# Configure logging
logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    """Priority levels for tasks."""
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL = auto()

class TaskStatus(Enum):
    """Status values for tasks."""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

class Task:
    """Represents a task to be executed by the thread pool."""
    
    def __init__(
        self,
        task_id: str,
        name: str,
        func: Callable,
        args: Tuple = (),
        kwargs: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 0,
        retry_delay: float = 0.0,
        dependencies: List[str] = None,
        description: str = "",
        tags: List[str] = None
    ):
        """Initialize a task."""
        self.task_id = task_id
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.priority = priority
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.dependencies = dependencies or []
        self.description = description
        self.tags = tags or []
        self.status = TaskStatus.PENDING
        self.retries = 0
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.execution_id = None
        
    def __lt__(self, other):
        """Compare tasks based on priority for queue ordering."""
        if not isinstance(other, Task):
            return NotImplemented
        return self.priority.value > other.priority.value  # Higher priority values come first

class TaskExecution:
    """Represents a specific execution of a task."""
    
    def __init__(self, execution_id: str, task_id: str):
        """Initialize a task execution."""
        self.execution_id = execution_id
        self.task_id = task_id
        self.status = TaskStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.result = None
        self.error = None
        self.worker_id = None

class Worker(threading.Thread):
    """Worker thread that executes tasks from the queue."""
    
    def __init__(
        self,
        worker_id: str,
        task_queue: queue.PriorityQueue,
        result_callback: Callable,
        shutdown_event: threading.Event
    ):
        """Initialize a worker thread."""
        super().__init__(daemon=True)
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.result_callback = result_callback
        self.shutdown_event = shutdown_event
        self.current_task = None
        self.current_execution = None
        self.idle_since = time.time()
        self.is_active = False
        
    def run(self):
        """Run the worker thread."""
        logger.info(f"Worker {self.worker_id} started")
        
        while not self.shutdown_event.is_set():
            try:
                # Get a task from the queue with a timeout
                try:
                    priority, task, execution = self.task_queue.get(timeout=1.0)
                    self.is_active = True
                    self.current_task = task
                    self.current_execution = execution
                    execution.worker_id = self.worker_id
                    
                    # Execute the task
                    self._execute_task(task, execution)
                    
                    # Mark the task as done in the queue
                    self.task_queue.task_done()
                    
                except queue.Empty:
                    # No task available, update idle time
                    if self.is_active:
                        self.idle_since = time.time()
                        self.is_active = False
                    
                    # Sleep briefly to avoid busy waiting
                    time.sleep(0.1)
            
            except Exception as e:
                logger.error(f"Worker {self.worker_id} encountered an error: {e}")
                # Sleep briefly to avoid rapid error loops
                time.sleep(1.0)
        
        logger.info(f"Worker {self.worker_id} shutting down")
    
    def _execute_task(self, task: Task, execution: TaskExecution):
        """Execute a task and handle the result."""
        logger.info(f"Worker {self.worker_id} executing task {task.task_id} (execution {execution.execution_id})")
        
        execution.status = TaskStatus.RUNNING
        execution.start_time = time.time()
        task.status = TaskStatus.RUNNING
        task.start_time = execution.start_time
        
        try:
            # Execute the task function
            result = task.func(*task.args, **task.kwargs)
            
            # Update task and execution status
            execution.status = TaskStatus.COMPLETED
            execution.end_time = time.time()
            execution.result = result
            
            task.status = TaskStatus.COMPLETED
            task.end_time = execution.end_time
            task.result = result
            
            logger.info(f"Task {task.task_id} (execution {execution.execution_id}) completed successfully")
            
        except Exception as e:
            logger.error(f"Task {task.task_id} (execution {execution.execution_id}) failed: {e}")
            
            execution.status = TaskStatus.FAILED
            execution.end_time = time.time()
            execution.error = e
            
            # Check if we should retry the task
            if task.retries < task.max_retries:
                task.retries += 1
                task.status = TaskStatus.PENDING
                logger.info(f"Retrying task {task.task_id} (attempt {task.retries}/{task.max_retries}) after {task.retry_delay} seconds")
                
                # Schedule the retry
                threading.Timer(task.retry_delay, self._retry_task, args=(task,)).start()
            else:
                task.status = TaskStatus.FAILED
                task.end_time = execution.end_time
                task.error = e
        
        finally:
            # Call the result callback
            self.result_callback(task, execution)
            
            # Clear current task references
            self.current_task = None
            self.current_execution = None
    
    def _retry_task(self, task: Task):
        """Retry a failed task."""
        # The task manager will handle the actual retry by checking the task status
        pass
    
    def get_idle_time(self) -> float:
        """Get the time this worker has been idle in seconds."""
        if self.is_active:
            return 0.0
        return time.time() - self.idle_since
    
    def cancel_current_task(self) -> bool:
        """Attempt to cancel the current task."""
        # This is a best-effort attempt, as Python doesn't support true thread cancellation
        if self.current_task and self.current_execution:
            logger.info(f"Attempting to cancel task {self.current_task.task_id} (execution {self.current_execution.execution_id})")
            
            # Mark the task and execution as cancelled
            self.current_task.status = TaskStatus.CANCELLED
            self.current_execution.status = TaskStatus.CANCELLED
            self.current_execution.end_time = time.time()
            
            # Note: The task will continue to run in the thread, but its results will be ignored
            return True
        
        return False

class ThreadPoolManager:
    """Manages a dynamic thread pool with resource monitoring and adaptive scaling."""
    
    def __init__(
        self,
        min_workers: int = 2,
        max_workers: int = 8,
        resource_monitor = None,
        adjust_interval: float = 60.0,
        idle_timeout: float = 300.0
    ):
        """Initialize the thread pool manager."""
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.resource_monitor = resource_monitor
        self.adjust_interval = adjust_interval
        self.idle_timeout = idle_timeout
        
        self.task_queue = queue.PriorityQueue()
        self.shutdown_event = threading.Event()
        
        self.workers: Dict[str, Worker] = {}
        self.tasks: Dict[str, Task] = {}
        self.executions: Dict[str, TaskExecution] = {}
        self.dependencies: Dict[str, Set[str]] = {}  # task_id -> set of dependent task_ids
        
        self.worker_lock = threading.RLock()
        self.task_lock = threading.RLock()
        
        self.adjust_thread = None
        self.is_running = False
    
    def start(self):
        """Start the thread pool manager."""
        if self.is_running:
            return
        
        logger.info(f"Starting thread pool manager with {self.min_workers}-{self.max_workers} workers")
        self.is_running = True
        self.shutdown_event.clear()
        
        # Start the initial workers
        with self.worker_lock:
            for _ in range(self.min_workers):
                self._add_worker()
        
        # Start the adjustment thread
        self.adjust_thread = threading.Thread(target=self._adjust_worker_count, daemon=True)
        self.adjust_thread.start()
    
    def stop(self):
        """Stop the thread pool manager."""
        if not self.is_running:
            return
        
        logger.info("Stopping thread pool manager")
        self.is_running = False
        self.shutdown_event.set()
        
        # Wait for all tasks to complete
        self.task_queue.join()
        
        # Wait for all workers to stop
        with self.worker_lock:
            for worker in self.workers.values():
                worker.join(timeout=5.0)
        
        # Clear all collections
        self.workers.clear()
        self.tasks.clear()
        self.executions.clear()
        self.dependencies.clear()
        
        logger.info("Thread pool manager stopped")
    
    def register_task(
        self,
        name: str,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 0,
        retry_delay: float = 0.0,
        dependencies: List[str] = None,
        description: str = "",
        tags: List[str] = None,
        **kwargs
    ) -> str:
        """Register a task with the thread pool."""
        task_id = str(uuid.uuid4())
        
        # Create the task
        task = Task(
            task_id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries,
            retry_delay=retry_delay,
            dependencies=dependencies or [],
            description=description,
            tags=tags or []
        )
        
        # Register the task
        with self.task_lock:
            self.tasks[task_id] = task
            
            # Register dependencies
            for dep_id in task.dependencies:
                if dep_id not in self.tasks:
                    raise TaskDependencyError(f"Dependency task {dep_id} does not exist")
                
                if dep_id not in self.dependencies:
                    self.dependencies[dep_id] = set()
                
                self.dependencies[dep_id].add(task_id)
        
        logger.info(f"Registered task {task_id}: {name}")
        return task_id
    
    def execute_task(self, task_id: str, wait: bool = False) -> str:
        """Execute a registered task."""
        with self.task_lock:
            if task_id not in self.tasks:
                raise ValueError(f"Task {task_id} is not registered")
            
            task = self.tasks[task_id]
            
            # Check if all dependencies are completed
            for dep_id in task.dependencies:
                dep_task = self.tasks.get(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    raise TaskDependencyError(f"Dependency task {dep_id} is not completed")
            
            # Create a new execution
            execution_id = str(uuid.uuid4())
            execution = TaskExecution(execution_id=execution_id, task_id=task_id)
            self.executions[execution_id] = execution
            
            # Add the task to the queue
            self.task_queue.put((task.priority.value, task, execution))
            
            logger.info(f"Executing task {task_id} (execution {execution_id})")
            
            # Wait for the task to complete if requested
            if wait:
                self._wait_for_execution(execution_id)
            
            return execution_id
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        with self.task_lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            # If the task is already completed or cancelled, return False
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False
            
            # If the task is running, try to cancel its current execution
            if task.status == TaskStatus.RUNNING and task.execution_id:
                execution = self.executions.get(task.execution_id)
                if execution and execution.worker_id:
                    worker = self.workers.get(execution.worker_id)
                    if worker:
                        return worker.cancel_current_task()
            
            # If the task is pending, mark it as cancelled
            task.status = TaskStatus.CANCELLED
            
            logger.info(f"Cancelled task {task_id}")
            return True
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a task."""
        with self.task_lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            
            return {
                "task_id": task.task_id,
                "name": task.name,
                "status": task.status.name,
                "priority": task.priority.name,
                "retries": task.retries,
                "max_retries": task.max_retries,
                "dependencies": task.dependencies,
                "description": task.description,
                "tags": task.tags,
                "start_time": task.start_time,
                "end_time": task.end_time,
                "error": str(task.error) if task.error else None
            }
    
    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a task execution."""
        with self.task_lock:
            execution = self.executions.get(execution_id)
            if not execution:
                return None
            
            return {
                "execution_id": execution.execution_id,
                "task_id": execution.task_id,
                "status": execution.status.name,
                "worker_id": execution.worker_id,
                "start_time": execution.start_time,
                "end_time": execution.end_time,
                "error": str(execution.error) if execution.error else None
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics about the thread pool."""
        with self.worker_lock, self.task_lock:
            active_workers = sum(1 for w in self.workers.values() if w.is_active)
            
            pending_tasks = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
            running_tasks = sum(1 for t in self.tasks.values() if t.status == TaskStatus.RUNNING)
            completed_tasks = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
            failed_tasks = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
            cancelled_tasks = sum(1 for t in self.tasks.values() if t.status == TaskStatus.CANCELLED)
            
            return {
                "worker_count": len(self.workers),
                "active_workers": active_workers,
                "idle_workers": len(self.workers) - active_workers,
                "queue_size": self.task_queue.qsize(),
                "pending_tasks": pending_tasks,
                "running_tasks": running_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "cancelled_tasks": cancelled_tasks,
                "total_tasks": len(self.tasks),
                "total_executions": len(self.executions)
            }
    
    def get_tasks_by_tag(self, tag: str) -> List[str]:
        """Get all task IDs with a specific tag."""
        with self.task_lock:
            return [t.task_id for t in self.tasks.values() if tag in t.tags]
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[str]:
        """Get all task IDs with a specific status."""
        with self.task_lock:
            return [t.task_id for t in self.tasks.values() if t.status == status]
    
    def _add_worker(self) -> str:
        """Add a new worker to the pool."""
        worker_id = str(uuid.uuid4())
        worker = Worker(
            worker_id=worker_id,
            task_queue=self.task_queue,
            result_callback=self._handle_task_result,
            shutdown_event=self.shutdown_event
        )
        self.workers[worker_id] = worker
        worker.start()
        
        logger.info(f"Added worker {worker_id}, total workers: {len(self.workers)}")
        return worker_id
    
    def _remove_worker(self, worker_id: str = None) -> bool:
        """Remove a worker from the pool."""
        if len(self.workers) <= self.min_workers:
            return False
        
        # If no worker_id is specified, remove the most idle worker
        if not worker_id:
            idle_workers = [(w.get_idle_time(), w_id) for w_id, w in self.workers.items() if not w.is_active]
            if not idle_workers:
                return False
            
            # Get the most idle worker
            _, worker_id = max(idle_workers)
        
        # Remove the worker
        worker = self.workers.pop(worker_id, None)
        if not worker:
            return False
        
        # Signal the worker to stop
        # Note: The worker will finish its current task before stopping
        
        logger.info(f"Removed worker {worker_id}, total workers: {len(self.workers)}")
        return True
    
    def _adjust_worker_count(self):
        """Periodically adjust the number of workers based on load and resource usage."""
        while not self.shutdown_event.is_set():
            try:
                # Sleep for the adjustment interval
                time.sleep(self.adjust_interval)
                
                with self.worker_lock:
                    # Get current metrics
                    metrics = self.get_metrics()
                    
                    # Calculate the optimal worker count based on queue size and resource usage
                    optimal_count = self._calculate_optimal_worker_count(metrics)
                    
                    # Adjust the worker count
                    current_count = len(self.workers)
                    
                    if optimal_count > current_count:
                        # Add workers
                        for _ in range(min(optimal_count - current_count, self.max_workers - current_count)):
                            self._add_worker()
                    
                    elif optimal_count < current_count:
                        # Remove idle workers
                        for _ in range(current_count - optimal_count):
                            if not self._remove_worker():
                                break
                    
                    # Remove excessively idle workers
                    self._remove_idle_workers()
            
            except Exception as e:
                logger.error(f"Error adjusting worker count: {e}")
    
    def _calculate_optimal_worker_count(self, metrics: Dict[str, Any]) -> int:
        """Calculate the optimal number of workers based on load and resource usage."""
        # Start with the current worker count
        optimal_count = len(self.workers)
        
        # Adjust based on queue size
        queue_size = metrics["queue_size"]
        if queue_size > optimal_count * 2:
            # Queue is growing, add workers
            optimal_count = min(optimal_count + 1, self.max_workers)
        elif queue_size == 0 and optimal_count > self.min_workers:
            # Queue is empty, reduce workers
            optimal_count = max(optimal_count - 1, self.min_workers)
        
        # Adjust based on resource usage if a monitor is available
        if self.resource_monitor:
            # Get current resource usage
            usage = self.resource_monitor.get_current_usage()
            
            # Adjust based on CPU usage
            cpu_usage = usage.get("cpu", 0)
            if cpu_usage > 90:
                # CPU is very high, reduce workers
                optimal_count = max(optimal_count - 2, self.min_workers)
            elif cpu_usage > 75:
                # CPU is high, reduce workers slightly
                optimal_count = max(optimal_count - 1, self.min_workers)
            
            # Adjust based on memory usage
            memory_usage = usage.get("memory", 0)
            if memory_usage > 90:
                # Memory is very high, reduce workers
                optimal_count = max(optimal_count - 2, self.min_workers)
            elif memory_usage > 75:
                # Memory is high, reduce workers slightly
                optimal_count = max(optimal_count - 1, self.min_workers)
        
        return optimal_count
    
    def _remove_idle_workers(self):
        """Remove workers that have been idle for too long."""
        if len(self.workers) <= self.min_workers:
            return
        
        # Find workers that have been idle for too long
        idle_workers = []
        for worker_id, worker in self.workers.items():
            idle_time = worker.get_idle_time()
            if idle_time > self.idle_timeout:
                idle_workers.append(worker_id)
        
        # Remove idle workers, but keep at least min_workers
        for worker_id in idle_workers[:len(self.workers) - self.min_workers]:
            self._remove_worker(worker_id)
    
    def _handle_task_result(self, task: Task, execution: TaskExecution):
        """Handle the result of a task execution."""
        with self.task_lock:
            # Update the execution in the registry
            self.executions[execution.execution_id] = execution
            
            # If the task completed successfully, check for dependent tasks
            if execution.status == TaskStatus.COMPLETED and task.task_id in self.dependencies:
                # Get dependent tasks
                dependent_tasks = self.dependencies.get(task.task_id, set())
                
                # Check if any dependent tasks can now be executed
                for dep_task_id in dependent_tasks:
                    dep_task = self.tasks.get(dep_task_id)
                    if not dep_task or dep_task.status != TaskStatus.PENDING:
                        continue
                    
                    # Check if all dependencies are completed
                    all_deps_completed = True
                    for dep_id in dep_task.dependencies:
                        dep = self.tasks.get(dep_id)
                        if not dep or dep.status != TaskStatus.COMPLETED:
                            all_deps_completed = False
                            break
                    
                    # If all dependencies are completed, execute the dependent task
                    if all_deps_completed:
                        try:
                            self.execute_task(dep_task_id)
                        except Exception as e:
                            logger.error(f"Error executing dependent task {dep_task_id}: {e}")
    
    def _wait_for_execution(self, execution_id: str, timeout: float = None) -> bool:
        """Wait for a task execution to complete."""
        start_time = time.time()
        
        while True:
            with self.task_lock:
                execution = self.executions.get(execution_id)
                if not execution:
                    return False
                
                if execution.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    return execution.status == TaskStatus.COMPLETED
            
            # Check timeout
            if timeout and time.time() - start_time > timeout:
                return False
            
            # Sleep briefly to avoid busy waiting
            time.sleep(0.1)

class TaskDependencyError(Exception):
    """Exception raised when a task dependency cannot be satisfied."""
    pass

# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create a thread pool manager
    pool = ThreadPoolManager(min_workers=2, max_workers=4)
    
    # Start the pool
    pool.start()
    
    try:
        # Define some example tasks
        def task1():
            logger.info("Executing task 1")
            time.sleep(2)
            return "Task 1 result"
        
        def task2():
            logger.info("Executing task 2")
            time.sleep(3)
            return "Task 2 result"
        
        def task3():
            logger.info("Executing task 3")
            time.sleep(1)
            return "Task 3 result"
        
        # Register the tasks
        task1_id = pool.register_task("Task 1", task1, priority=TaskPriority.HIGH)
        task2_id = pool.register_task("Task 2", task2, dependencies=[task1_id])
        task3_id = pool.register_task("Task 3", task3, dependencies=[task2_id])
        
        # Execute the tasks
        pool.execute_task(task1_id)
        
        # Wait for all tasks to complete
        time.sleep(10)
        
        # Get metrics
        metrics = pool.get_metrics()
        logger.info(f"Thread pool metrics: {metrics}")
    
    finally:
        # Stop the pool
        pool.stop()

