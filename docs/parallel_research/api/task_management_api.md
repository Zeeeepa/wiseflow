# Task Management API

The Task Management API provides functionality to manage and execute tasks asynchronously. It is a core component of WiseFlow's parallel processing capabilities and is used by the research system to manage complex task workflows with dependencies.

## Class: TaskManager

The `TaskManager` class is a singleton that manages asynchronous tasks with support for dependencies, priorities, retries, and timeouts.

### Initialization

The `TaskManager` is a singleton and should be accessed through the global instance:

```python
from core.task_manager import task_manager

# The manager is already initialized with default settings
# You can access it directly
max_concurrent_tasks = task_manager.max_concurrent_tasks
```

If you need to customize the manager in tests or specialized environments:

```python
import asyncio
from core.task_manager import TaskManager
from core.config import config

# Override configuration
config.set("MAX_CONCURRENT_TASKS", 8)

# Create a new instance (will replace the singleton)
custom_manager = TaskManager()

# Start the manager
asyncio.run(custom_manager.start())
```

### Methods

#### register_task(name, func, args=(), kwargs=None, priority=TaskPriority.NORMAL, dependencies=None, max_retries=0, retry_delay=1.0, timeout=None, task_id=None)

Registers a task with the task manager.

**Parameters:**
- `name` (str): Name of the task
- `func` (Callable): Function to execute
- `args` (tuple): Arguments to pass to the function
- `kwargs` (dict): Keyword arguments to pass to the function
- `priority` (TaskPriority): Priority of the task
- `dependencies` (List[str]): List of task IDs that must complete before this task
- `max_retries` (int): Maximum number of retries if the task fails
- `retry_delay` (float): Delay in seconds between retries
- `timeout` (Optional[float]): Timeout in seconds for the task
- `task_id` (Optional[str]): Optional task ID, if not provided a new one will be generated

**Returns:**
- `str`: Task ID

**Example:**
```python
async def process_data(data):
    # Process data asynchronously
    return processed_data

# Register a task
task_id = task_manager.register_task(
    name="Process Research Data",
    func=process_data,
    args=(data,),
    priority=TaskPriority.HIGH,
    max_retries=3,
    retry_delay=2.0,
    timeout=60.0
)

print(f"Task registered with ID: {task_id}")
```

#### cancel_task(task_id)

Cancels a task.

**Parameters:**
- `task_id` (str): ID of the task to cancel

**Returns:**
- `bool`: True if the task was cancelled, False otherwise

**Example:**
```python
# Cancel a task
cancelled = task_manager.cancel_task(task_id)
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
- `Optional[Task]`: Task object or None if not found

**Example:**
```python
# Get task details
task = task_manager.get_task(task_id)
if task:
    print(f"Task name: {task.name}")
    print(f"Task status: {task.status}")
    print(f"Task created at: {task.created_at}")
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
status = task_manager.get_task_status(task_id)
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
result = task_manager.get_task_result(task_id)
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
- `Optional[Exception]`: Task error or None if task not found or not failed

**Example:**
```python
# Get task error
error = task_manager.get_task_error(task_id)
if error:
    print(f"Task error: {error}")
else:
    print(f"Task {task_id} did not fail or not found")
```

#### get_all_tasks()

Gets all tasks.

**Returns:**
- `Dict[str, Task]`: Dictionary of all tasks

**Example:**
```python
# Get all tasks
tasks = task_manager.get_all_tasks()
print(f"Total tasks: {len(tasks)}")
```

#### get_pending_tasks()

Gets all pending tasks.

**Returns:**
- `Dict[str, Task]`: Dictionary of pending tasks

**Example:**
```python
# Get pending tasks
pending_tasks = task_manager.get_pending_tasks()
print(f"Pending tasks: {len(pending_tasks)}")
```

#### get_running_tasks()

Gets all running tasks.

**Returns:**
- `Dict[str, Task]`: Dictionary of running tasks

**Example:**
```python
# Get running tasks
running_tasks = task_manager.get_running_tasks()
print(f"Running tasks: {len(running_tasks)}")
```

#### get_completed_tasks()

Gets all completed tasks.

**Returns:**
- `Dict[str, Task]`: Dictionary of completed tasks

**Example:**
```python
# Get completed tasks
completed_tasks = task_manager.get_completed_tasks()
print(f"Completed tasks: {len(completed_tasks)}")
```

#### get_failed_tasks()

Gets all failed tasks.

**Returns:**
- `Dict[str, Task]`: Dictionary of failed tasks

**Example:**
```python
# Get failed tasks
failed_tasks = task_manager.get_failed_tasks()
print(f"Failed tasks: {len(failed_tasks)}")
```

#### get_cancelled_tasks()

Gets all cancelled tasks.

**Returns:**
- `Dict[str, Task]`: Dictionary of cancelled tasks

**Example:**
```python
# Get cancelled tasks
cancelled_tasks = task_manager.get_cancelled_tasks()
print(f"Cancelled tasks: {len(cancelled_tasks)}")
```

#### get_waiting_tasks()

Gets all waiting tasks.

**Returns:**
- `Dict[str, Task]`: Dictionary of waiting tasks

**Example:**
```python
# Get waiting tasks
waiting_tasks = task_manager.get_waiting_tasks()
print(f"Waiting tasks: {len(waiting_tasks)}")
```

#### async start()

Starts the task manager.

**Example:**
```python
import asyncio

# Start the task manager
asyncio.create_task(task_manager.start())
```

#### async stop()

Stops the task manager.

**Example:**
```python
import asyncio

# Stop the task manager
await task_manager.stop()
```

## Class: Task

The `Task` class represents a task that can be executed asynchronously.

### Attributes

- `task_id` (str): Unique identifier for the task
- `name` (str): Name of the task
- `func` (Callable): Function to execute
- `args` (tuple): Arguments to pass to the function
- `kwargs` (dict): Keyword arguments to pass to the function
- `priority` (TaskPriority): Priority of the task
- `dependencies` (List[str]): List of task IDs that must complete before this task
- `max_retries` (int): Maximum number of retries if the task fails
- `retry_delay` (float): Delay in seconds between retries
- `timeout` (Optional[float]): Timeout in seconds for the task
- `status` (TaskStatus): Current status of the task
- `result` (Any): Result of the task (if completed)
- `error` (Exception): Error that occurred (if failed)
- `created_at` (datetime): When the task was created
- `started_at` (datetime): When the task started executing
- `completed_at` (datetime): When the task completed
- `retry_count` (int): Number of retries attempted
- `task_object` (asyncio.Task): Asyncio task object

### Methods

#### to_dict()

Converts the task to a dictionary.

**Returns:**
- `Dict[str, Any]`: Dictionary representation of the task

**Example:**
```python
task = task_manager.get_task(task_id)
task_dict = task.to_dict()
print(task_dict)
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
    WAITING = auto()
```

## Exceptions

### TaskDependencyError

Error raised when a task dependency cannot be satisfied.

**Example:**
```python
try:
    task_id = task_manager.register_task(
        name="Task with Invalid Dependency",
        func=process_data,
        dependencies=["non-existent-task-id"]
    )
except TaskDependencyError as e:
    print(f"Dependency error: {e}")
```

## Events

The Task Manager publishes events through the event system:

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

### Task Started Event

Published when a task starts executing:

```python
{
    "type": EventType.TASK_STARTED,
    "task_id": "unique-task-id",
    "data": {
        "name": "Task Name"
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

### Task Cancelled Event

Published when a task is cancelled:

```python
{
    "type": EventType.TASK_FAILED,
    "task_id": "unique-task-id",
    "data": {
        "name": "Task Name",
        "reason": "cancelled"
    }
}
```

## Configuration

The Task Manager is configured through the configuration system:

| Configuration Key | Type | Default | Description |
|------------------|------|---------|-------------|
| MAX_CONCURRENT_TASKS | int | 4 | Maximum number of tasks that can run concurrently |

## Task Dependencies

The Task Manager supports task dependencies, allowing you to create complex task workflows:

```python
# Register a task that will produce data
data_task_id = task_manager.register_task(
    name="Fetch Research Data",
    func=fetch_data
)

# Register a dependent task that will process the data
process_task_id = task_manager.register_task(
    name="Process Research Data",
    func=process_data,
    dependencies=[data_task_id]
)

# The process_data task will only run after the fetch_data task completes successfully
```

## Task Retries

The Task Manager supports automatic retries for failed tasks:

```python
# Register a task with retry configuration
task_id = task_manager.register_task(
    name="Unreliable API Call",
    func=call_external_api,
    max_retries=3,
    retry_delay=2.0  # 2 seconds between retries
)

# The task will be retried up to 3 times if it fails
# The retry delay will increase exponentially (2s, 4s, 8s)
```

## Task Timeouts

The Task Manager supports timeouts for tasks:

```python
# Register a task with a timeout
task_id = task_manager.register_task(
    name="Long-running Task",
    func=long_running_function,
    timeout=60.0  # 60 seconds timeout
)

# The task will be cancelled if it doesn't complete within 60 seconds
```

## Thread Safety

The Task Manager is designed to be used in an asyncio environment and is not thread-safe. All interactions with the Task Manager should be done from the same event loop.

## Performance Considerations

- The Task Manager is best suited for I/O-bound tasks
- For CPU-bound tasks, consider using the Thread Pool Manager instead
- The number of concurrent tasks should be tuned based on the nature of the tasks
- Tasks with dependencies can create complex execution graphs, which may impact scheduling efficiency

## See Also

- [Thread Pool Management API](./thread_pool_api.md)
- [Event System](../developer_guide/event_system.md)
- [Configuration System](../admin_guide/configuration.md)

