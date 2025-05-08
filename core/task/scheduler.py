"""
Task scheduler for WiseFlow.

This module provides a task scheduler for executing tasks with priority and load balancing.
"""

import os
import time
import asyncio
import logging
import threading
import heapq
from typing import Dict, List, Set, Any, Optional, Callable, Awaitable, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum, auto

from core.config import config
from core.task_manager import TaskPriority, TaskStatus
from core.task.dependency_manager import DependencyManager, DependencyStatus
from core.utils.concurrency import AsyncLock, AsyncSemaphore, async_retry
from core.event_system import (
    EventType, Event, publish_sync,
    create_task_event
)

logger = logging.getLogger(__name__)

class SchedulerStrategy(Enum):
    """Scheduler strategies for task execution."""
    FIFO = auto()  # First in, first out
    PRIORITY = auto()  # Priority-based
    FAIR = auto()  # Fair scheduling with round-robin
    ADAPTIVE = auto()  # Adaptive scheduling based on resource usage

class TaskScheduler:
    """
    Task scheduler for WiseFlow.
    
    This class provides a scheduler for executing tasks with priority and load balancing.
    """
    
    def __init__(
        self,
        max_concurrent_tasks: int = None,
        strategy: SchedulerStrategy = SchedulerStrategy.PRIORITY,
        check_interval: float = 0.1,
        dependency_manager: Optional[DependencyManager] = None
    ):
        """
        Initialize the task scheduler.
        
        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks
            strategy: Scheduling strategy to use
            check_interval: Interval in seconds between scheduler checks
            dependency_manager: Dependency manager to use
        """
        self.max_concurrent_tasks = max_concurrent_tasks or config.get("MAX_CONCURRENT_TASKS", 4)
        self.strategy = strategy
        self.check_interval = check_interval
        self.dependency_manager = dependency_manager or DependencyManager()
        
        # Task queues
        self.task_queue = []  # Priority queue for tasks
        self.running_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.cancelled_tasks: Set[str] = set()
        
        # Task metadata
        self.task_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Locks and semaphores
        self.task_lock = AsyncLock()
        self.task_semaphore = AsyncSemaphore(self.max_concurrent_tasks)
        
        # Scheduler state
        self.is_running = False
        self.scheduler_task = None
        
        # Metrics
        self.metrics = {
            "tasks_scheduled": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_cancelled": 0,
            "total_execution_time": 0.0,
            "avg_execution_time": 0.0,
            "max_execution_time": 0.0,
            "min_execution_time": float('inf'),
            "last_check_time": None
        }
        self.metrics_lock = threading.RLock()
        
        # Load balancing
        self.load_balancing_enabled = config.get("LOAD_BALANCING_ENABLED", True)
        self.load_balancing_threshold = config.get("LOAD_BALANCING_THRESHOLD", 0.8)
        self.load_balancing_check_interval = config.get("LOAD_BALANCING_CHECK_INTERVAL", 60.0)
        self.last_load_balancing_check = time.time()
        
        # Task timeout handling
        self.timeout_check_interval = config.get("TIMEOUT_CHECK_INTERVAL", 10.0)
        self.last_timeout_check = time.time()
        
        logger.info(f"Task scheduler initialized with strategy {strategy.name}")
    
    async def schedule_task(
        self,
        task_id: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: List[str] = None,
        timeout: Optional[float] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Schedule a task for execution.
        
        Args:
            task_id: Unique identifier for the task
            func: Function to execute
            args: Arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
            priority: Priority of the task
            dependencies: List of task IDs that must complete before this task
            timeout: Timeout in seconds for the task
            metadata: Additional metadata for the task
            
        Returns:
            Task ID
        """
        async with self.task_lock:
            # Create task metadata
            task_meta = {
                "task_id": task_id,
                "func": func,
                "args": args,
                "kwargs": kwargs or {},
                "priority": priority,
                "dependencies": dependencies or [],
                "timeout": timeout,
                "metadata": metadata or {},
                "created_at": datetime.now(),
                "started_at": None,
                "completed_at": None,
                "result": None,
                "error": None,
                "status": TaskStatus.PENDING
            }
            
            # Add to task metadata
            self.task_metadata[task_id] = task_meta
            
            # Add to dependency manager
            try:
                self.dependency_manager.add_node(
                    task_id,
                    name=metadata.get("name", task_id) if metadata else task_id,
                    dependencies=dependencies
                )
            except ValueError:
                # Node already exists, update dependencies
                for dep_id in dependencies or []:
                    try:
                        self.dependency_manager.add_dependency(task_id, dep_id)
                    except ValueError:
                        # Dependency node doesn't exist, create it
                        self.dependency_manager.add_node(dep_id, name=dep_id)
                        self.dependency_manager.add_dependency(task_id, dep_id)
            
            # Check if task has dependencies
            if dependencies:
                # Check if all dependencies are satisfied
                all_satisfied = True
                for dep_id in dependencies:
                    try:
                        dep_status = self.dependency_manager.get_node_status(dep_id)
                        if dep_status != DependencyStatus.SATISFIED:
                            all_satisfied = False
                            break
                    except ValueError:
                        # Dependency node doesn't exist
                        all_satisfied = False
                        break
                
                if not all_satisfied:
                    # Task has dependencies that are not satisfied yet
                    logger.info(f"Task {task_id} is waiting for dependencies")
                    return task_id
            
            # Add to task queue based on strategy
            if self.strategy == SchedulerStrategy.PRIORITY:
                # Priority queue (lower value = higher priority)
                priority_value = 5 - priority.value  # Invert priority value
                heapq.heappush(self.task_queue, (priority_value, time.time(), task_id))
            elif self.strategy == SchedulerStrategy.FIFO:
                # FIFO queue
                heapq.heappush(self.task_queue, (0, time.time(), task_id))
            elif self.strategy == SchedulerStrategy.FAIR:
                # Fair scheduling (round-robin)
                # Use task count as priority to ensure fairness
                task_count = self.metrics["tasks_scheduled"] % 1000
                heapq.heappush(self.task_queue, (task_count, time.time(), task_id))
            elif self.strategy == SchedulerStrategy.ADAPTIVE:
                # Adaptive scheduling based on resource usage
                # Use a combination of priority and resource usage
                cpu_usage = os.getloadavg()[0] / os.cpu_count()
                priority_value = 5 - priority.value  # Invert priority value
                adaptive_priority = priority_value * (1 + cpu_usage)
                heapq.heappush(self.task_queue, (adaptive_priority, time.time(), task_id))
            
            # Update metrics
            with self.metrics_lock:
                self.metrics["tasks_scheduled"] += 1
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_CREATED,
                    task_id,
                    {"name": metadata.get("name", task_id) if metadata else task_id, "priority": priority.name}
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task created event: {e}")
            
            logger.info(f"Task scheduled: {task_id}")
            
            return task_id
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a scheduled or running task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        async with self.task_lock:
            # Check if task exists
            if task_id not in self.task_metadata:
                logger.warning(f"Task {task_id} not found")
                return False
            
            # Get task metadata
            task_meta = self.task_metadata[task_id]
            
            # Check if task is already completed or cancelled
            if task_meta["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                logger.warning(f"Task {task_id} is already {task_meta['status'].name}")
                return False
            
            # Cancel task
            if task_meta["status"] == TaskStatus.RUNNING:
                # Task is running, mark as cancelled
                # The task will be cancelled during execution
                task_meta["status"] = TaskStatus.CANCELLED
                self.running_tasks.discard(task_id)
                self.cancelled_tasks.add(task_id)
            elif task_meta["status"] == TaskStatus.PENDING:
                # Task is pending, remove from queue
                task_meta["status"] = TaskStatus.CANCELLED
                
                # Remove from queue (will be filtered out during execution)
                # Note: We don't actually remove it from the heap because that's expensive
                # Instead, we mark it as cancelled and filter it out when we pop from the heap
                
                self.cancelled_tasks.add(task_id)
            
            # Update task metadata
            task_meta["completed_at"] = datetime.now()
            
            # Update dependency manager
            try:
                self.dependency_manager.set_node_status(task_id, DependencyStatus.FAILED)
            except ValueError:
                pass
            
            # Update metrics
            with self.metrics_lock:
                self.metrics["tasks_cancelled"] += 1
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.TASK_CANCELLED,
                    task_id,
                    {"name": task_meta["metadata"].get("name", task_id) if task_meta["metadata"] else task_id}
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish task cancelled event: {e}")
            
            logger.info(f"Task cancelled: {task_id}")
            
            return True
    
    async def start(self):
        """Start the task scheduler."""
        if self.is_running:
            logger.warning("Task scheduler is already running")
            return
        
        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Task scheduler started")
    
    async def stop(self):
        """Stop the task scheduler."""
        if not self.is_running:
            logger.warning("Task scheduler is not running")
            return
        
        self.is_running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all running tasks
        async with self.task_lock:
            for task_id in list(self.running_tasks):
                await self.cancel_task(task_id)
        
        logger.info("Task scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        try:
            while self.is_running:
                # Check for tasks to execute
                await self._check_tasks()
                
                # Check for task timeouts
                if time.time() - self.last_timeout_check >= self.timeout_check_interval:
                    await self._check_timeouts()
                    self.last_timeout_check = time.time()
                
                # Check for load balancing
                if self.load_balancing_enabled and time.time() - self.last_load_balancing_check >= self.load_balancing_check_interval:
                    await self._check_load_balancing()
                    self.last_load_balancing_check = time.time()
                
                # Update metrics
                with self.metrics_lock:
                    self.metrics["last_check_time"] = datetime.now()
                
                # Sleep for a while
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            logger.info("Task scheduler loop cancelled")
        except Exception as e:
            logger.error(f"Error in task scheduler loop: {e}")
    
    async def _check_tasks(self):
        """Check for tasks to execute."""
        # Check if we can execute more tasks
        if len(self.running_tasks) >= self.max_concurrent_tasks:
            return
        
        # Check for ready tasks from dependency manager
        ready_tasks = self.dependency_manager.get_ready_nodes()
        for task_id in ready_tasks:
            if task_id in self.task_metadata and self.task_metadata[task_id]["status"] == TaskStatus.PENDING:
                # Schedule task for execution
                asyncio.create_task(self._execute_task(task_id))
        
        # Check task queue
        async with self.task_lock:
            while self.task_queue and len(self.running_tasks) < self.max_concurrent_tasks:
                # Get next task from queue
                try:
                    _, _, task_id = heapq.heappop(self.task_queue)
                except IndexError:
                    # Queue is empty
                    break
                
                # Check if task exists and is still pending
                if task_id not in self.task_metadata:
                    continue
                
                task_meta = self.task_metadata[task_id]
                if task_meta["status"] != TaskStatus.PENDING:
                    continue
                
                # Check if task has dependencies
                if task_meta["dependencies"]:
                    # Check if all dependencies are satisfied
                    all_satisfied = True
                    for dep_id in task_meta["dependencies"]:
                        try:
                            dep_status = self.dependency_manager.get_node_status(dep_id)
                            if dep_status != DependencyStatus.SATISFIED:
                                all_satisfied = False
                                break
                        except ValueError:
                            # Dependency node doesn't exist
                            all_satisfied = False
                            break
                    
                    if not all_satisfied:
                        # Task has dependencies that are not satisfied yet
                        # Put it back in the queue with a delay
                        heapq.heappush(self.task_queue, (0, time.time() + 1.0, task_id))
                        continue
                
                # Schedule task for execution
                asyncio.create_task(self._execute_task(task_id))
    
    async def _execute_task(self, task_id: str):
        """
        Execute a task.
        
        Args:
            task_id: ID of the task to execute
        """
        # Acquire semaphore to limit concurrent tasks
        await self.task_semaphore.acquire()
        
        try:
            async with self.task_lock:
                # Check if task exists and is still pending
                if task_id not in self.task_metadata:
                    return
                
                task_meta = self.task_metadata[task_id]
                if task_meta["status"] != TaskStatus.PENDING:
                    return
                
                # Mark task as running
                task_meta["status"] = TaskStatus.RUNNING
                task_meta["started_at"] = datetime.now()
                self.running_tasks.add(task_id)
                
                # Publish event
                try:
                    event = create_task_event(
                        EventType.TASK_STARTED,
                        task_id,
                        {"name": task_meta["metadata"].get("name", task_id) if task_meta["metadata"] else task_id}
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish task started event: {e}")
                
                logger.info(f"Task started: {task_id}")
            
            # Execute task
            start_time = time.time()
            result = None
            error = None
            
            try:
                # Execute task with timeout if specified
                if task_meta["timeout"]:
                    # Use asyncio.wait_for for timeout
                    result = await asyncio.wait_for(
                        self._call_task_func(task_meta["func"], task_meta["args"], task_meta["kwargs"]),
                        task_meta["timeout"]
                    )
                else:
                    # Execute without timeout
                    result = await self._call_task_func(task_meta["func"], task_meta["args"], task_meta["kwargs"])
                
                # Task completed successfully
                status = TaskStatus.COMPLETED
                self.completed_tasks.add(task_id)
                
                # Update dependency manager
                try:
                    self.dependency_manager.set_node_status(task_id, DependencyStatus.SATISFIED)
                except ValueError:
                    pass
                
                # Update metrics
                execution_time = time.time() - start_time
                with self.metrics_lock:
                    self.metrics["tasks_completed"] += 1
                    self.metrics["total_execution_time"] += execution_time
                    self.metrics["avg_execution_time"] = (
                        self.metrics["total_execution_time"] / self.metrics["tasks_completed"]
                    )
                    self.metrics["max_execution_time"] = max(
                        self.metrics["max_execution_time"], execution_time
                    )
                    self.metrics["min_execution_time"] = min(
                        self.metrics["min_execution_time"], execution_time
                    )
                
                # Publish event
                try:
                    event = create_task_event(
                        EventType.TASK_COMPLETED,
                        task_id,
                        {
                            "name": task_meta["metadata"].get("name", task_id) if task_meta["metadata"] else task_id,
                            "execution_time": execution_time
                        }
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish task completed event: {e}")
                
                logger.info(f"Task completed: {task_id} in {execution_time:.2f}s")
            except asyncio.TimeoutError:
                # Task timed out
                status = TaskStatus.FAILED
                error = f"Task timed out after {task_meta['timeout']} seconds"
                self.failed_tasks.add(task_id)
                
                # Update dependency manager
                try:
                    self.dependency_manager.set_node_status(task_id, DependencyStatus.FAILED)
                except ValueError:
                    pass
                
                # Update metrics
                execution_time = time.time() - start_time
                with self.metrics_lock:
                    self.metrics["tasks_failed"] += 1
                
                # Publish event
                try:
                    event = create_task_event(
                        EventType.TASK_FAILED,
                        task_id,
                        {
                            "name": task_meta["metadata"].get("name", task_id) if task_meta["metadata"] else task_id,
                            "error": error,
                            "execution_time": execution_time
                        }
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish task failed event: {e}")
                
                logger.warning(f"Task timed out: {task_id} after {execution_time:.2f}s")
            except asyncio.CancelledError:
                # Task was cancelled
                status = TaskStatus.CANCELLED
                error = "Task was cancelled"
                self.cancelled_tasks.add(task_id)
                
                # Update dependency manager
                try:
                    self.dependency_manager.set_node_status(task_id, DependencyStatus.FAILED)
                except ValueError:
                    pass
                
                # Update metrics
                execution_time = time.time() - start_time
                with self.metrics_lock:
                    self.metrics["tasks_cancelled"] += 1
                
                # Publish event
                try:
                    event = create_task_event(
                        EventType.TASK_CANCELLED,
                        task_id,
                        {
                            "name": task_meta["metadata"].get("name", task_id) if task_meta["metadata"] else task_id,
                            "execution_time": execution_time
                        }
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish task cancelled event: {e}")
                
                logger.info(f"Task cancelled: {task_id} after {execution_time:.2f}s")
                
                # Re-raise to propagate cancellation
                raise
            except Exception as e:
                # Task failed
                status = TaskStatus.FAILED
                error = str(e)
                self.failed_tasks.add(task_id)
                
                # Update dependency manager
                try:
                    self.dependency_manager.set_node_status(task_id, DependencyStatus.FAILED)
                except ValueError:
                    pass
                
                # Update metrics
                execution_time = time.time() - start_time
                with self.metrics_lock:
                    self.metrics["tasks_failed"] += 1
                
                # Publish event
                try:
                    event = create_task_event(
                        EventType.TASK_FAILED,
                        task_id,
                        {
                            "name": task_meta["metadata"].get("name", task_id) if task_meta["metadata"] else task_id,
                            "error": error,
                            "execution_time": execution_time
                        }
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish task failed event: {e}")
                
                logger.error(f"Task failed: {task_id} after {execution_time:.2f}s: {error}")
            
            # Update task metadata
            async with self.task_lock:
                if task_id in self.task_metadata:
                    task_meta = self.task_metadata[task_id]
                    task_meta["status"] = status
                    task_meta["completed_at"] = datetime.now()
                    task_meta["result"] = result
                    task_meta["error"] = error
                    self.running_tasks.discard(task_id)
        finally:
            # Release semaphore
            self.task_semaphore.release()
    
    async def _call_task_func(self, func: Callable, args: tuple, kwargs: dict) -> Any:
        """
        Call a task function.
        
        Args:
            func: Function to call
            args: Arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
            
        Returns:
            Result of the function call
        """
        if asyncio.iscoroutinefunction(func):
            # Function is already a coroutine
            return await func(*args, **kwargs)
        else:
            # Function is synchronous, run it in a thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    
    async def _check_timeouts(self):
        """Check for task timeouts."""
        now = datetime.now()
        
        async with self.task_lock:
            for task_id in list(self.running_tasks):
                if task_id not in self.task_metadata:
                    self.running_tasks.discard(task_id)
                    continue
                
                task_meta = self.task_metadata[task_id]
                if not task_meta["timeout"]:
                    continue
                
                # Check if task has timed out
                if task_meta["started_at"] and (now - task_meta["started_at"]).total_seconds() > task_meta["timeout"]:
                    # Task has timed out
                    logger.warning(f"Task {task_id} has timed out")
                    
                    # Cancel task
                    await self.cancel_task(task_id)
    
    async def _check_load_balancing(self):
        """Check for load balancing."""
        # Get current load
        cpu_load = os.getloadavg()[0] / os.cpu_count()
        
        if cpu_load > self.load_balancing_threshold:
            # System is under high load, reduce max concurrent tasks
            new_max = max(1, self.max_concurrent_tasks - 1)
            if new_max < self.max_concurrent_tasks:
                logger.info(f"Reducing max concurrent tasks from {self.max_concurrent_tasks} to {new_max} due to high load")
                self.max_concurrent_tasks = new_max
                self.task_semaphore = AsyncSemaphore(self.max_concurrent_tasks)
        elif cpu_load < self.load_balancing_threshold * 0.5:
            # System is under low load, increase max concurrent tasks
            new_max = min(os.cpu_count() * 2, self.max_concurrent_tasks + 1)
            if new_max > self.max_concurrent_tasks:
                logger.info(f"Increasing max concurrent tasks from {self.max_concurrent_tasks} to {new_max} due to low load")
                self.max_concurrent_tasks = new_max
                self.task_semaphore = AsyncSemaphore(self.max_concurrent_tasks)
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get the status of a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Status of the task, or None if the task doesn't exist
        """
        if task_id not in self.task_metadata:
            return None
        
        return self.task_metadata[task_id]["status"]
    
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """
        Get the result of a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Result of the task, or None if the task doesn't exist or hasn't completed
        """
        if task_id not in self.task_metadata:
            return None
        
        task_meta = self.task_metadata[task_id]
        if task_meta["status"] != TaskStatus.COMPLETED:
            return None
        
        return task_meta["result"]
    
    def get_task_error(self, task_id: str) -> Optional[str]:
        """
        Get the error of a failed task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Error message of the task, or None if the task doesn't exist or hasn't failed
        """
        if task_id not in self.task_metadata:
            return None
        
        task_meta = self.task_metadata[task_id]
        if task_meta["status"] != TaskStatus.FAILED:
            return None
        
        return task_meta["error"]
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get scheduler metrics.
        
        Returns:
            Dictionary of metrics
        """
        with self.metrics_lock:
            metrics = self.metrics.copy()
        
        # Add current task counts
        metrics.update({
            "pending_tasks": len([t for t in self.task_metadata.values() if t["status"] == TaskStatus.PENDING]),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "cancelled_tasks": len(self.cancelled_tasks),
            "total_tasks": len(self.task_metadata),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "strategy": self.strategy.name,
            "is_running": self.is_running
        })
        
        return metrics
    
    def clear_completed_tasks(self, max_age_seconds: int = 3600):
        """
        Clear completed, failed, and cancelled tasks from memory.
        
        Args:
            max_age_seconds: Maximum age of tasks to keep in seconds
        """
        now = datetime.now()
        count = 0
        
        # Get tasks to clear
        tasks_to_clear = []
        for task_id, task_meta in self.task_metadata.items():
            if task_meta["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                if task_meta["completed_at"] and (now - task_meta["completed_at"]).total_seconds() > max_age_seconds:
                    tasks_to_clear.append(task_id)
        
        # Clear tasks
        for task_id in tasks_to_clear:
            del self.task_metadata[task_id]
            self.completed_tasks.discard(task_id)
            self.failed_tasks.discard(task_id)
            self.cancelled_tasks.discard(task_id)
            count += 1
        
        if count > 0:
            logger.info(f"Cleared {count} old tasks")

# Create a singleton instance
task_scheduler = TaskScheduler()

