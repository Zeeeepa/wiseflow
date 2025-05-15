# Unified Task Management System

This module provides a consolidated task management system for WiseFlow that supports different execution strategies and provides a consistent API for task creation, monitoring, and cancellation.

## Overview

The task management system consists of the following components:

- **Task**: Represents a task that can be executed by the task manager.
- **TaskManager**: Manages and executes tasks using different execution strategies.
- **Executor**: Abstract base class for task executors.
  - **SequentialExecutor**: Executes tasks sequentially in the current thread.
  - **ThreadPoolExecutor**: Executes tasks concurrently using a thread pool.
  - **AsyncExecutor**: Executes tasks concurrently using asyncio tasks.
- **Exceptions**: Custom exceptions for the task management system.

## Usage

### Creating and Executing Tasks

```python
from core.task_management import TaskManager, TaskPriority

# Get the task manager instance
task_manager = TaskManager()

# Register a task
task_id = task_manager.register_task(
    name="My Task",
    func=my_function,
    arg1, arg2,
    kwargs={"param1": value1, "param2": value2},
    priority=TaskPriority.HIGH,
    dependencies=[other_task_id],
    max_retries=3,
    retry_delay=1.0,
    timeout=60.0,
    description="This is my task",
    tags=["tag1", "tag2"],
    metadata={"key1": "value1", "key2": "value2"},
    executor_type="async"  # or "sequential" or "thread_pool"
)

# Execute the task
await task_manager.execute_task(task_id, wait=True)  # Wait for the task to complete
# or
await task_manager.execute_task(task_id, wait=False)  # Execute the task asynchronously

# Get the task result
result = task_manager.get_task_result(task_id)

# Get the task status
status = task_manager.get_task_status(task_id)

# Cancel the task
await task_manager.cancel_task(task_id)
```

### Task Dependencies

Tasks can depend on other tasks. A task will only be executed when all its dependencies have completed successfully.

```python
# Register a task with dependencies
task_id = task_manager.register_task(
    name="Dependent Task",
    func=my_function,
    dependencies=[task_id1, task_id2]
)
```

### Task Progress

Tasks can report their progress, which can be used to provide feedback to users.

```python
# Update task progress
task_manager.update_task_progress(task_id, progress=0.5, message="Halfway done")

# Get task progress
progress, message = task_manager.get_task_progress(task_id)
```

### Task Metrics

The task manager provides metrics about the tasks it manages.

```python
# Get task manager metrics
metrics = task_manager.get_metrics()
```

## Integration with Event System

The task management system integrates with the event system to publish events when tasks are created, started, completed, failed, or cancelled.

```python
from core.event_system import subscribe

# Subscribe to task events
subscribe(EventType.TASK_CREATED, my_handler)
subscribe(EventType.TASK_STARTED, my_handler)
subscribe(EventType.TASK_COMPLETED, my_handler)
subscribe(EventType.TASK_FAILED, my_handler)
subscribe(EventType.TASK_CANCELLED, my_handler)
subscribe(EventType.TASK_PROGRESS, my_handler)
```

## Error Handling

The task management system provides comprehensive error handling, including retries for failed tasks and detailed error information.

```python
# Get task error
error = task_manager.get_task_error(task_id)
```

## Concurrency Control

The task manager limits the number of concurrent tasks to prevent overloading the system.

```python
# Create a task manager with a specific concurrency limit
task_manager = TaskManager(max_concurrent_tasks=10)
```

## Executor Types

The task management system supports different executor types:

- **sequential**: Executes tasks sequentially in the current thread.
- **thread_pool**: Executes tasks concurrently using a thread pool.
- **async**: Executes tasks concurrently using asyncio tasks.

```python
# Register a task with a specific executor type
task_id = task_manager.register_task(
    name="My Task",
    func=my_function,
    executor_type="async"  # or "sequential" or "thread_pool"
)
```

