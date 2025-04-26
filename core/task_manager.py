import threading
import time
import logging
import schedule
import datetime
from typing import Dict, List, Callable, Optional, Any, Set, Tuple, Union
import uuid
from enum import Enum
from dataclasses import dataclass, field

from core.thread_pool_manager import ThreadPoolManager, TaskPriority, TaskStatus
from core.resource_monitor import ResourceMonitor

logger = logging.getLogger(__name__)


class TaskDependencyError(Exception):
    """Exception raised for task dependency issues."""
    pass


class TaskScheduleError(Exception):
    """Exception raised for task scheduling issues."""
    pass


@dataclass
class TaskDefinition:
    """Definition of a task that can be registered with the TaskManager."""
    id: str
    name: str
    func: Callable
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 0
    retry_delay: float = 1.0
    schedule: Optional[str] = None  # Cron-like schedule string
    enabled: bool = True
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class TaskHistory:
    """Record of a task execution."""
    task_id: str
    execution_id: str
    start_time: datetime.datetime
    end_time: Optional[datetime.datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    execution_time: Optional[float] = None


class TaskManager:
    """
    High-level task management system that handles task registration, scheduling,
    dependencies, and execution history.
    """
    
    def __init__(self, 
                 thread_pool: Optional[ThreadPoolManager] = None,
                 resource_monitor: Optional[ResourceMonitor] = None,
                 history_limit: int = 1000):
        """
        Initialize the task manager.
        
        Args:
            thread_pool: Optional ThreadPoolManager instance for task execution
            resource_monitor: Optional ResourceMonitor for system resource monitoring
            history_limit: Maximum number of task history entries to keep
        """
        # Create a thread pool if not provided
        if thread_pool is None:
            if resource_monitor is None:
                resource_monitor = ResourceMonitor()
                resource_monitor.start()
            
            thread_pool = ThreadPoolManager(
                min_workers=2,
                max_workers=10,
                resource_monitor=resource_monitor
            )
            thread_pool.start()
            self._owns_thread_pool = True
        else:
            self._owns_thread_pool = False
        
        self.thread_pool = thread_pool
        self.resource_monitor = resource_monitor
        
        # Task definitions and history
        self.tasks = {}  # type: Dict[str, TaskDefinition]
        self.history = []  # type: List[TaskHistory]
        self.history_limit = history_limit
        
        # Locks for thread safety
        self._tasks_lock = threading.RLock()
        self._history_lock = threading.RLock()
        
        # Scheduler for recurring tasks
        self._scheduler = schedule.Scheduler()
        self._scheduler_thread = None
        self._stop_event = threading.Event()
    
    def start(self):
        """Start the task manager and scheduler thread."""
        if self._scheduler_thread is None or not self._scheduler_thread.is_alive():
            self._stop_event.clear()
            self._scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self._scheduler_thread.start()
            logger.info("TaskManager scheduler started")
    
    def stop(self):
        """Stop the task manager and scheduler thread."""
        self._stop_event.set()
        
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=1.0)
        
        if self._owns_thread_pool:
            self.thread_pool.stop()
            if self.resource_monitor:
                self.resource_monitor.stop()
        
        logger.info("TaskManager stopped")
    
    def register_task(self, 
                      name: str,
                      func: Callable,
                      *args,
                      dependencies: Optional[List[str]] = None,
                      priority: TaskPriority = TaskPriority.NORMAL,
                      max_retries: int = 0,
                      retry_delay: float = 1.0,
                      schedule: Optional[str] = None,
                      enabled: bool = True,
                      description: str = "",
                      tags: Optional[List[str]] = None,
                      **kwargs) -> str:
        """
        Register a task with the task manager.
        
        Args:
            name: Name of the task
            func: Function to execute
            *args: Positional arguments for the function
            dependencies: List of task IDs that must complete before this task
            priority: Task priority level
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retry attempts in seconds
            schedule: Cron-like schedule string (e.g., "*/5 * * * *" for every 5 minutes)
            enabled: Whether the task is enabled
            description: Description of the task
            tags: List of tags for categorizing tasks
            **kwargs: Keyword arguments for the function
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        task_def = TaskDefinition(
            id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            dependencies=set(dependencies or []),
            priority=priority,
            max_retries=max_retries,
            retry_delay=retry_delay,
            schedule=schedule,
            enabled=enabled,
            description=description,
            tags=tags or []
        )
        
        with self._tasks_lock:
            # Validate dependencies
            for dep_id in task_def.dependencies:
                if dep_id not in self.tasks:
                    raise TaskDependencyError(f"Dependency task {dep_id} not found")
            
            self.tasks[task_id] = task_def
            
            # Set up scheduled execution if specified
            if schedule and enabled:
                self._schedule_task(task_def)
        
        logger.info(f"Registered task '{name}' with ID {task_id}")
        return task_id
    
    def update_task(self, 
                    task_id: str,
                    **kwargs) -> bool:
        """
        Update a registered task's properties.
        
        Args:
            task_id: ID of the task to update
            **kwargs: Task properties to update
            
        Returns:
            True if the task was updated, False if not found
        """
        with self._tasks_lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            # Update task properties
            for key, value in kwargs.items():
                if hasattr(task, key):
                    # Special handling for dependencies
                    if key == 'dependencies' and value is not None:
                        # Validate new dependencies
                        for dep_id in value:
                            if dep_id not in self.tasks:
                                raise TaskDependencyError(f"Dependency task {dep_id} not found")
                        setattr(task, key, set(value))
                    else:
                        setattr(task, key, value)
            
            # Update schedule if it changed
            if 'schedule' in kwargs or 'enabled' in kwargs:
                self._reschedule_task(task)
        
        return True
    
    def execute_task(self, 
                     task_id: str,
                     wait: bool = False,
                     timeout: Optional[float] = None) -> str:
        """
        Execute a registered task.
        
        Args:
            task_id: ID of the task to execute
            wait: Whether to wait for the task to complete
            timeout: Maximum time to wait in seconds
            
        Returns:
            Execution ID
        """
        with self._tasks_lock:
            if task_id not in self.tasks:
                raise ValueError(f"Task {task_id} not found")
            
            task = self.tasks[task_id]
            
            if not task.enabled:
                raise ValueError(f"Task {task_id} is disabled")
            
            # Check dependencies
            for dep_id in task.dependencies:
                dep_status = self._check_dependency_status(dep_id)
                if not dep_status:
                    raise TaskDependencyError(
                        f"Dependency task {dep_id} has not completed successfully"
                    )
        
        # Create a unique execution ID
        execution_id = str(uuid.uuid4())
        
        # Record the start in history
        history_entry = TaskHistory(
            task_id=task_id,
            execution_id=execution_id,
            start_time=datetime.datetime.now(),
            status=TaskStatus.PENDING
        )
        
        with self._history_lock:
            self.history.append(history_entry)
            self._trim_history()
        
        # Submit the task to the thread pool
        thread_task_id = self.thread_pool.submit(
            self._execute_task_wrapper,
            task_id,
            execution_id,
            priority=task.priority,
            max_retries=task.max_retries,
            retry_delay=task.retry_delay
        )
        
        # Wait for completion if requested
        if wait:
            self.thread_pool.wait_for_task(thread_task_id, timeout=timeout)
        
        return execution_id
    
    def execute_tasks(self, 
                      task_ids: List[str],
                      wait: bool = False,
                      timeout: Optional[float] = None) -> List[str]:
        """
        Execute multiple tasks, respecting dependencies.
        
        Args:
            task_ids: List of task IDs to execute
            wait: Whether to wait for all tasks to complete
            timeout: Maximum time to wait in seconds
            
        Returns:
            List of execution IDs
        """
        # Build dependency graph and execution order
        execution_order = self._build_execution_order(task_ids)
        
        # Execute tasks in order
        execution_ids = []
        for task_id in execution_order:
            execution_id = self.execute_task(task_id, wait=False)
            execution_ids.append(execution_id)
        
        # Wait for all tasks if requested
        if wait:
            start_time = time.time()
            for execution_id in execution_ids:
                remaining_time = None
                if timeout:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        break
                    remaining_time = timeout - elapsed
                
                self.wait_for_execution(execution_id, timeout=remaining_time)
        
        return execution_ids
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a scheduled task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False if not found or not scheduled
        """
        with self._tasks_lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            # Disable the task
            task.enabled = False
            
            # Remove from scheduler
            self._reschedule_task(task)
        
        return True
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dictionary with task status information or None if not found
        """
        with self._tasks_lock:
            if task_id not in self.tasks:
                return None
            
            task = self.tasks[task_id]
            
            # Get the most recent execution
            latest_execution = None
            with self._history_lock:
                for entry in reversed(self.history):
                    if entry.task_id == task_id:
                        latest_execution = entry
                        break
            
            return {
                'id': task.id,
                'name': task.name,
                'enabled': task.enabled,
                'schedule': task.schedule,
                'dependencies': list(task.dependencies),
                'priority': task.priority.name,
                'max_retries': task.max_retries,
                'latest_execution': {
                    'id': latest_execution.execution_id if latest_execution else None,
                    'status': latest_execution.status.name if latest_execution else None,
                    'start_time': latest_execution.start_time if latest_execution else None,
                    'end_time': latest_execution.end_time if latest_execution else None,
                    'execution_time': latest_execution.execution_time if latest_execution else None,
                } if latest_execution else None
            }
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a specific task execution.
        
        Args:
            execution_id: ID of the execution
            
        Returns:
            Dictionary with execution status information or None if not found
        """
        with self._history_lock:
            for entry in self.history:
                if entry.execution_id == execution_id:
                    return {
                        'execution_id': entry.execution_id,
                        'task_id': entry.task_id,
                        'status': entry.status.name,
                        'start_time': entry.start_time,
                        'end_time': entry.end_time,
                        'execution_time': entry.execution_time,
                        'result': entry.result,
                        'error': str(entry.error) if entry.error else None
                    }
        
        return None
    
    def get_task_history(self, 
                         task_id: Optional[str] = None,
                         limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the execution history for a task or all tasks.
        
        Args:
            task_id: Optional ID of the task to get history for
            limit: Maximum number of history entries to return
            
        Returns:
            List of dictionaries with execution history information
        """
        history_entries = []
        
        with self._history_lock:
            for entry in reversed(self.history):
                if task_id is None or entry.task_id == task_id:
                    history_entries.append({
                        'execution_id': entry.execution_id,
                        'task_id': entry.task_id,
                        'task_name': self.tasks[entry.task_id].name if entry.task_id in self.tasks else "Unknown",
                        'status': entry.status.name,
                        'start_time': entry.start_time,
                        'end_time': entry.end_time,
                        'execution_time': entry.execution_time,
                        'error': str(entry.error) if entry.error else None
                    })
                
                if len(history_entries) >= limit:
                    break
        
        return history_entries
    
    def wait_for_execution(self, 
                           execution_id: str,
                           timeout: Optional[float] = None) -> bool:
        """
        Wait for a specific task execution to complete.
        
        Args:
            execution_id: ID of the execution to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if the execution completed, False if it timed out
        """
        start_time = time.time()
        
        while True:
            status = self.get_execution_status(execution_id)
            
            if not status:
                return False
            
            if status['status'] in ['COMPLETED', 'FAILED', 'CANCELLED']:
                return True
            
            if timeout and time.time() - start_time > timeout:
                return False
            
            time.sleep(0.1)
    
    def list_tasks(self, 
                   enabled_only: bool = False,
                   tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all registered tasks.
        
        Args:
            enabled_only: Whether to only include enabled tasks
            tag: Optional tag to filter tasks by
            
        Returns:
            List of dictionaries with task information
        """
        tasks_list = []
        
        with self._tasks_lock:
            for task_id, task in self.tasks.items():
                if enabled_only and not task.enabled:
                    continue
                
                if tag and tag not in task.tags:
                    continue
                
                tasks_list.append({
                    'id': task.id,
                    'name': task.name,
                    'description': task.description,
                    'enabled': task.enabled,
                    'schedule': task.schedule,
                    'dependencies': list(task.dependencies),
                    'priority': task.priority.name,
                    'tags': task.tags
                })
        
        return tasks_list
    
    def _execute_task_wrapper(self, task_id: str, execution_id: str):
        """
        Wrapper function for executing a task and updating history.
        
        Args:
            task_id: ID of the task to execute
            execution_id: ID of this execution
            
        Returns:
            Task result
        """
        # Find the task and history entry
        with self._tasks_lock:
            if task_id not in self.tasks:
                raise ValueError(f"Task {task_id} not found")
            
            task = self.tasks[task_id]
        
        history_entry = None
        with self._history_lock:
            for entry in self.history:
                if entry.execution_id == execution_id:
                    history_entry = entry
                    break
        
        if not history_entry:
            logger.error(f"History entry for execution {execution_id} not found")
            return None
        
        # Update status to running
        history_entry.status = TaskStatus.RUNNING
        
        start_time = time.time()
        
        try:
            # Execute the task
            result = task.func(*task.args, **task.kwargs)
            
            # Update history with success
            execution_time = time.time() - start_time
            
            history_entry.status = TaskStatus.COMPLETED
            history_entry.result = result
            history_entry.end_time = datetime.datetime.now()
            history_entry.execution_time = execution_time
            
            return result
            
        except Exception as e:
            # Update history with failure
            execution_time = time.time() - start_time
            
            history_entry.status = TaskStatus.FAILED
            history_entry.error = e
            history_entry.end_time = datetime.datetime.now()
            history_entry.execution_time = execution_time
            
            logger.error(f"Task {task_id} execution {execution_id} failed: {e}")
            raise
    
    def _schedule_task(self, task: TaskDefinition):
        """
        Schedule a task for recurring execution.
        
        Args:
            task: TaskDefinition to schedule
        """
        if not task.schedule or not task.enabled:
            return
        
        try:
            # Parse the schedule string and set up the job
            schedule_parts = task.schedule.split()
            
            if len(schedule_parts) == 5:
                # Cron-like format: minute hour day month weekday
                minute, hour, day, month, weekday = schedule_parts
                
                job = self._scheduler.every()
                
                # Handle day of month
                if day != '*':
                    job = job.day(int(day))
                
                # Handle month
                if month != '*':
                    # Convert month number to name
                    month_names = [
                        'january', 'february', 'march', 'april', 'may', 'june',
                        'july', 'august', 'september', 'october', 'november', 'december'
                    ]
                    job = job.month(month_names[int(month) - 1])
                
                # Handle day of week
                if weekday != '*':
                    # Convert weekday number to name
                    weekday_names = [
                        'monday', 'tuesday', 'wednesday', 'thursday',
                        'friday', 'saturday', 'sunday'
                    ]
                    job = job.day_of_week(weekday_names[int(weekday) % 7])
                
                # Handle hour
                if hour != '*':
                    job = job.at(f"{hour.zfill(2)}:{minute.zfill(2)}")
                else:
                    # If hour is *, but minute is specific
                    if minute != '*':
                        # Schedule to run at that minute of every hour
                        job = job.hour.at(f":{minute.zfill(2)}")
                    else:
                        # Both hour and minute are *, run every minute
                        job = job.minute
                
                # Set the task to run
                job.do(self.execute_task, task.id)
                
                logger.info(f"Scheduled task '{task.name}' with cron schedule: {task.schedule}")
            else:
                raise ValueError(f"Invalid schedule format: {task.schedule}")
                
        except Exception as e:
            logger.error(f"Error scheduling task '{task.name}': {e}")
            raise TaskScheduleError(f"Error scheduling task: {e}")
    
    def _reschedule_task(self, task: TaskDefinition):
        """
        Update or remove a task's schedule.
        
        Args:
            task: TaskDefinition to reschedule
        """
        # Clear existing schedule for this task
        self._scheduler.clear(tag=task.id)
        
        # Set up new schedule if enabled
        if task.enabled and task.schedule:
            self._schedule_task(task)
    
    def _run_scheduler(self):
        """Run the scheduler in a loop."""
        while not self._stop_event.is_set():
            self._scheduler.run_pending()
            time.sleep(1)
    
    def _trim_history(self):
        """Trim the history list to the configured limit."""
        if len(self.history) > self.history_limit:
            self.history = self.history[-self.history_limit:]
    
    def _check_dependency_status(self, task_id: str) -> bool:
        """
        Check if a dependency task has completed successfully.
        
        Args:
            task_id: ID of the dependency task
            
        Returns:
            True if the task has completed successfully, False otherwise
        """
        # Find the most recent execution of the task
        with self._history_lock:
            for entry in reversed(self.history):
                if entry.task_id == task_id:
                    return entry.status == TaskStatus.COMPLETED
        
        return False
    
    def _build_execution_order(self, task_ids: List[str]) -> List[str]:
        """
        Build an execution order for tasks that respects dependencies.
        
        Args:
            task_ids: List of task IDs to execute
            
        Returns:
            List of task IDs in execution order
        """
        # Validate all tasks exist
        with self._tasks_lock:
            for task_id in task_ids:
                if task_id not in self.tasks:
                    raise ValueError(f"Task {task_id} not found")
            
            # Build dependency graph
            graph = {}
            for task_id in task_ids:
                task = self.tasks[task_id]
                graph[task_id] = list(task.dependencies)
            
            # Add dependencies of dependencies
            for task_id in list(graph.keys()):
                self._add_transitive_dependencies(graph, task_id)
            
            # Topological sort
            visited = set()
            temp_visited = set()
            order = []
            
            def visit(node):
                if node in temp_visited:
                    # Cycle detected
                    cycle_path = " -> ".join(temp_visited) + " -> " + node
                    raise TaskDependencyError(f"Circular dependency detected: {cycle_path}")
                
                if node not in visited:
                    temp_visited.add(node)
                    
                    for dep in graph.get(node, []):
                        visit(dep)
                    
                    temp_visited.remove(node)
                    visited.add(node)
                    order.append(node)
            
            for task_id in graph:
                if task_id not in visited:
                    visit(task_id)
            
            # Reverse to get correct execution order
            return list(reversed(order))
    
    def _add_transitive_dependencies(self, graph: Dict[str, List[str]], task_id: str):
        """
        Add transitive dependencies to the graph.
        
        Args:
            graph: Dependency graph
            task_id: Task ID to process
        """
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        
        for dep_id in task.dependencies:
            if dep_id not in graph:
                graph[dep_id] = list(self.tasks[dep_id].dependencies) if dep_id in self.tasks else []
                self._add_transitive_dependencies(graph, dep_id)


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create a resource monitor
    resource_monitor = ResourceMonitor(check_interval=2.0)
    resource_monitor.start()
    
    # Create a thread pool
    thread_pool = ThreadPoolManager(
        min_workers=2,
        max_workers=5,
        resource_monitor=resource_monitor
    )
    thread_pool.start()
    
    # Create a task manager
    task_manager = TaskManager(
        thread_pool=thread_pool,
        resource_monitor=resource_monitor
    )
    task_manager.start()
    
    try:
        # Example task functions
        def task_1():
            logger.info("Executing task 1")
            time.sleep(1)
            return "Task 1 result"
        
        def task_2():
            logger.info("Executing task 2")
            time.sleep(2)
            return "Task 2 result"
        
        def task_3(param):
            logger.info(f"Executing task 3 with param: {param}")
            time.sleep(1)
            return f"Task 3 result with {param}"
        
        # Register tasks
        task1_id = task_manager.register_task(
            name="Task 1",
            func=task_1,
            priority=TaskPriority.HIGH,
            description="Example task 1"
        )
        
        task2_id = task_manager.register_task(
            name="Task 2",
            func=task_2,
            dependencies=[task1_id],
            priority=TaskPriority.NORMAL,
            description="Example task 2 that depends on task 1"
        )
        
        task3_id = task_manager.register_task(
            name="Task 3",
            func=task_3,
            args=("test parameter",),
            dependencies=[task2_id],
            priority=TaskPriority.LOW,
            description="Example task 3 that depends on task 2",
            schedule="*/5 * * * *"  # Run every 5 minutes
        )
        
        # Execute tasks with dependencies
        logger.info("Executing tasks with dependencies...")
        execution_ids = task_manager.execute_tasks([task3_id], wait=True)
        
        # Print results
        for execution_id in execution_ids:
            status = task_manager.get_execution_status(execution_id)
            logger.info(f"Execution {execution_id} status: {status['status']}")
        
        # List all tasks
        tasks = task_manager.list_tasks()
        logger.info(f"Registered tasks: {len(tasks)}")
        
        # Let the scheduled task run a few times
        logger.info("Waiting for scheduled executions...")
        time.sleep(10)
        
        # Get task history
        history = task_manager.get_task_history()
        logger.info(f"Task execution history: {len(history)} entries")
        
    finally:
        # Stop everything
        task_manager.stop()
        thread_pool.stop()
        resource_monitor.stop()
