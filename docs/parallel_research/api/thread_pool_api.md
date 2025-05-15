# Thread Pool Management API

The Thread Pool Management API provides functionality for executing tasks concurrently using a thread pool. It is a core component of WiseFlow's parallel processing capabilities and is used by the research system to execute tasks in parallel.

## Class: ThreadPoolManager

The `ThreadPoolManager` class is a singleton that manages a pool of threads for executing CPU-bound tasks concurrently.

### Initialization

The `ThreadPoolManager` is a singleton and should be accessed through the global instance:

```python
from core.thread_pool_manager import thread_pool_manager

# The manager is already initialized with default settings
# You can access it directly
max_workers = thread_pool_manager.max_workers
```

If you need to customize the manager in tests or specialized environments:

```python
import os
from core.thread_pool_manager import ThreadPoolManager
from core.config import config

# Override configuration
config.set("MAX_THREAD_WORKERS", 8)

# Create a new instance (will replace the singleton)
custom_manager = ThreadPoolManager()
```

### Methods

#### submit(func, *args, task_id=None, name="Unnamed Task", priority=TaskPriority.NORMAL, **kwargs)

Submits a task to the thread pool for execution.

**Parameters:**
- `func` (Callable): Function to execute
- `*args`: Arguments to pass to the function
- `task_id` (Optional[str]): Optional task ID, if not provided a new one will be generated
- `name` (str): Name of the task
- `priority` (TaskPriority): Priority of the task
- `**kwargs`: Keyword arguments to pass to the function

**Returns:**
- `str`: Task ID

**Example:**
```python
def process_data(data):
    # Process data
    return processed_data

# Submit a task
task_id = thread_pool_manager.submit(
    process_data,
    data,
    name="Process Research Data",
    priority=TaskPriority.HIGH
)

print(f"Task submitted with ID: {task_id}")
```

#### cancel(task_id)

Cancels a task.

**Parameters:**
- `task_id` (str): ID of the task to cancel

**Returns:**
- `bool`: True if the task was cancelled, False otherwise

**Example:**
```python
# Cancel a task
cancelled = thread_pool_manager.cancel(task_id)
if cancelled:
    print(f"Task {task_id} cancelled successfully")
else:
    print(f"Failed to cancel task {task_id}")
```

#### get_task(task_id)

Gets a task by ID.

**Parameters:**
- `task_id` (str): ID of the task to get

**Returns:**
- `Optional[Dict[str, Any]]`: Task dictionary or None if not found

**Example:**
```python
# Get task details
task = thread_pool_manager.get_task(task_id)
if task:
    print(f"Task name: {task['name']}")
    print(f"Task status: {task['status']}")
    print(f"Task created at: {task['created_at']}")
else:
    print(f"Task {task_id} not found")
```

#### get_task_status(task_id)

Gets the status of a task.

**Parameters:**
- `task_id` (str): ID of the task to get status for

**Returns:**
- `Optional[TaskStatus]`: Task status or None if task not found

**Example:**
```python
# Get task status
status = thread_pool_manager.get_task_status(task_id)
if status:
    print(f"Task status: {status}")
else:
    print(f"Task {task_id} not found")
```

#### get_task_result(task_id)

Gets the result of a task.

**Parameters:**
- `task_id` (str): ID of the task to get result for

**Returns:**
- `Any`: Task result or None if task not found or not completed

**Example:**
```python
# Get task result
result = thread_pool_manager.get_task_result(task_id)
if result is not None:
    print(f"Task result: {result}")
else:
    print(f"Task {task_id} not completed or not found")
```

#### get_task_error(task_id)

Gets the error of a failed task.

**Parameters:**
- `task_id` (str): ID of the task to get error for

**Returns:**
- `Optional[str]`: Task error or None if task not found or not failed

**Example:**
```python
# Get task error
error = thread_pool_manager.get_task_error(task_id)
if error:
    print(f"Task error: {error}")
else:
    print(f"Task {task_id} did not fail or not found")
```

#### get_all_tasks()

Gets all tasks.

**Returns:**
- `Dict[str, Dict[str, Any]]`: Dictionary of all tasks

**Example:**
```python
# Get all tasks
tasks = thread_pool_manager.get_all_tasks()
print(f"Total tasks: {len(tasks)}")
```

#### get_pending_tasks()

Gets all pending tasks.

**Returns:**
- `Dict[str, Dict[str, Any]]`: Dictionary of pending tasks

**Example:**
```python
# Get pending tasks
pending_tasks = thread_pool_manager.get_pending_tasks()
print(f"Pending tasks: {len(pending_tasks)}")
```

#### get_running_tasks()

Gets all running tasks.

**Returns:**
- `Dict[str, Dict[str, Any]]`: Dictionary of running tasks

**Example:**
```python
# Get running tasks
running_tasks = thread_pool_manager.get_running_tasks()
print(f"Running tasks: {len(running_tasks)}")
```

#### get_completed_tasks()

Gets all completed tasks.

**Returns:**
- `Dict[str, Dict[str, Any]]`: Dictionary of completed tasks

**Example:**
```python
# Get completed tasks
completed_tasks = thread_pool_manager.get_completed_tasks()
print(f"Completed tasks: {len(completed_tasks)}")
```

#### get_failed_tasks()

Gets all failed tasks.

**Returns:**
- `Dict[str, Dict[str, Any]]`: Dictionary of failed tasks

**Example:**
```python
# Get failed tasks
failed_tasks = thread_pool_manager.get_failed_tasks()
print(f"Failed tasks: {len(failed_tasks)}")
```

#### get_cancelled_tasks()

Gets all cancelled tasks.

**Returns:**
- `Dict[str, Dict[str, Any]]`: Dictionary of cancelled tasks

**Example:**
```python
# Get cancelled tasks
cancelled_tasks = thread_pool_manager.get_cancelled_tasks()
print(f"Cancelled tasks: {len(cancelled_tasks)}")
```

#### shutdown(wait=True)

Shuts down the thread pool.

**Parameters:**
- `wait` (bool): Whether to wait for pending tasks to complete

**Example:**
```python
# Shutdown the thread pool
thread_pool_manager.shutdown(wait=True)
print("Thread pool shut down")
```

## Enums

### TaskPriority

The `TaskPriority` enum defines the priority levels for tasks:

```python
class TaskPriority(Enum):
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL = auto()
```

### TaskStatus

The `TaskStatus` enum defines the possible status values for tasks:

```python
class TaskStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
```

## Task Dictionary

The task dictionary returned by various methods has the following structure:

```python
{
    "task_id": "unique-task-id",
    "name": "Task Name",
    "func": <function_reference>,
    "args": (arg1, arg2),
    "kwargs": {"key1": "value1", "key2": "value2"},
    "priority": TaskPriority.NORMAL,
    "status": TaskStatus.RUNNING,
    "created_at": datetime.datetime(2023, 1, 1, 12, 0, 0),
    "started_at": datetime.datetime(2023, 1, 1, 12, 0, 1),
    "completed_at": None,
    "result": None,
    "error": None
}
```

## Events

The Thread Pool Manager publishes events through the event system:

### Task Created Event

Published when a task is created:

```python
{
    "type": EventType.TASK_CREATED,
    "task_id": "unique-task-id",
    "data": {
        "name": "Task Name",
        "priority": "NORMAL"
    }
}
```

### Task Completed Event

Published when a task is completed:

```python
{
    "type": EventType.TASK_COMPLETED,
    "task_id": "unique-task-id",
    "data": {
        "name": "Task Name"
    }
}
```

### Task Failed Event

Published when a task fails:

```python
{
    "type": EventType.TASK_FAILED,
    "task_id": "unique-task-id",
    "data": {
        "name": "Task Name",
        "error": "Error message"
    }
}
```

## Configuration

The Thread Pool Manager is configured through the configuration system:

| Configuration Key | Type | Default | Description |
|------------------|------|---------|-------------|
| MAX_THREAD_WORKERS | int | os.cpu_count() or 4 | Maximum number of worker threads in the pool |

## Thread Safety

The Thread Pool Manager is thread-safe and can be accessed concurrently from multiple threads.

## Performance Considerations

- The thread pool is best suited for CPU-bound tasks
- For I/O-bound tasks, consider using the asyncio-based Task Manager instead
- The number of worker threads should be tuned based on the available CPU cores
- Too many worker threads can lead to excessive context switching and reduced performance

## See Also

- [Task Management API](./task_management_api.md)
- [Event System](../developer_guide/event_system.md)
- [Configuration System](../admin_guide/configuration.md)

