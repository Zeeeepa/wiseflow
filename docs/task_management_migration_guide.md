# Task Management Migration Guide

## Overview

This guide provides instructions for migrating from the deprecated task management systems (`TaskManager` and `ThreadPoolManager`) to the new consolidated `AsyncTaskManager` system.

## Why Migrate?

The new `AsyncTaskManager` system offers several advantages:

1. **Unified Interface**: A single, consistent API for all task management needs
2. **Improved Concurrency**: Better handling of concurrent tasks with proper locking mechanisms
3. **Enhanced Error Handling**: Standardized error handling across all task execution paths
4. **Better Resource Management**: Proper cleanup of resources when tasks are cancelled or fail
5. **Dependency Management**: Improved handling of task dependencies
6. **Monitoring and Metrics**: Better visibility into task execution status and performance

## Migration Steps

### 1. Update Imports

Replace imports from the deprecated modules with imports from the new module:

```python
# Old imports
from core.task_manager import TaskManager, TaskPriority, TaskStatus
from core.thread_pool_manager import ThreadPoolManager

# New imports
from core.task import (
    AsyncTaskManager, Task, TaskPriority, TaskStatus,
    TaskDependencyError, create_task_id, task_manager
)
```

### 2. Replace TaskManager Usage

Replace usage of the old `TaskManager` with the new `AsyncTaskManager`:

```python
# Old code
from core.task_manager import TaskManager
task_manager = TaskManager()

# New code
from core.task import AsyncTaskManager, task_manager
# Or use the singleton instance directly
from core.task import task_manager
```

### 3. Replace ThreadPoolManager Usage

Replace usage of the old `ThreadPoolManager` with the new `AsyncTaskManager`:

```python
# Old code
from core.thread_pool_manager import ThreadPoolManager
thread_pool = ThreadPoolManager()
task_id = thread_pool.submit(func, *args, **kwargs)

# New code
from core.task import task_manager
task_id = task_manager.register_task("Task Name", func, *args, **kwargs)
execution_id = task_manager.execute_task(task_id)
```

### 4. Update Task Registration and Execution

The new `AsyncTaskManager` separates task registration from task execution:

```python
# Old code (TaskManager)
task_id = task_manager.register_task(
    name="My Task",
    func=my_function,
    args=(arg1, arg2),
    kwargs={"param1": value1},
    priority=TaskPriority.HIGH
)

# New code
task_id = task_manager.register_task(
    name="My Task",
    func=my_function,
    arg1, arg2,  # Args are passed directly
    priority=TaskPriority.HIGH,
    param1=value1  # Kwargs are passed directly
)
execution_id = task_manager.execute_task(task_id)
```

### 5. Update Task Dependencies

The new `AsyncTaskManager` has improved support for task dependencies:

```python
# Old code
task_id2 = task_manager.register_task(
    name="Dependent Task",
    func=dependent_function,
    dependencies=[task_id1]
)

# New code
task_id2 = task_manager.register_task(
    name="Dependent Task",
    func=dependent_function,
    dependencies=[task_id1]
)
# The task will automatically execute when dependencies complete
execution_id = task_manager.execute_task(task_id2)
```

### 6. Update Error Handling

The new `AsyncTaskManager` provides standardized error handling:

```python
# Old code
try:
    result = task_manager.get_task_result(task_id)
    if not result:
        error = task_manager.get_task_error(task_id)
        if error:
            handle_error(error)
except Exception as e:
    handle_exception(e)

# New code
try:
    result = task_manager.get_task_result(task_id)
    if not result:
        error = task_manager.get_task_error(task_id)
        if error:
            handle_error(error)
except TaskError as e:
    # TaskError provides more context about the failure
    handle_task_error(e)
except Exception as e:
    handle_exception(e)
```

### 7. Update Resource Management

The new `AsyncTaskManager` provides better resource management:

```python
# Old code
try:
    # Manual resource management
    resource = acquire_resource()
    task_id = task_manager.register_task(
        name="Resource Task",
        func=resource_function,
        args=(resource,)
    )
    # Need to manually release resource when task completes
    if task_manager.get_task_status(task_id) == TaskStatus.COMPLETED:
        release_resource(resource)
except Exception as e:
    release_resource(resource)
    handle_exception(e)

# New code
# Resource cleanup is handled automatically
task_id = task_manager.register_task(
    name="Resource Task",
    func=resource_function_with_cleanup,
    resource
)
execution_id = task_manager.execute_task(task_id)
```

## API Reference

### AsyncTaskManager

The main class for task management.

#### Methods

- `register_task(name, func, *args, **kwargs)`: Register a task
- `execute_task(task_id, wait=False)`: Execute a registered task
- `cancel_task(task_id)`: Cancel a task
- `get_task(task_id)`: Get a task by ID
- `get_task_status(task_id)`: Get the status of a task
- `get_task_result(task_id)`: Get the result of a task
- `get_task_error(task_id)`: Get the error of a failed task
- `get_tasks_by_status(status)`: Get all tasks with a specific status
- `get_tasks_by_focus(focus_id)`: Get all tasks associated with a specific focus point
- `get_tasks_by_tag(tag)`: Get all tasks with a specific tag
- `get_metrics()`: Get metrics about the task manager
- `start()`: Start the task manager
- `stop()`: Stop the task manager
- `shutdown(wait=True)`: Shutdown the task manager

### Task

The class representing a task.

#### Properties

- `task_id`: Unique identifier for the task
- `name`: Name of the task
- `func`: Function to execute
- `args`: Arguments to pass to the function
- `kwargs`: Keyword arguments to pass to the function
- `priority`: Priority of the task
- `dependencies`: List of task IDs that must complete before this task
- `status`: Status of the task
- `result`: Result of the task
- `error`: Error of the task
- `created_at`: When the task was created
- `started_at`: When the task was started
- `completed_at`: When the task was completed

## Troubleshooting

### Task Not Executing

If a task is not executing, check the following:

1. Make sure you called `execute_task` after registering the task
2. Check if the task has dependencies that haven't completed yet
3. Check if the task manager is running (`task_manager.is_running`)
4. Check if the maximum number of concurrent tasks has been reached

### Task Failing

If a task is failing, check the following:

1. Get the error using `task_manager.get_task_error(task_id)`
2. Check if the task has exceeded its maximum number of retries
3. Check if the task has timed out
4. Check if the task was cancelled

### Resource Leaks

If you're experiencing resource leaks, check the following:

1. Make sure you're properly cleaning up resources in your task functions
2. Consider using context managers for resource management
3. Implement a custom `_cleanup_task_resources` method if needed

## Need Help?

If you need help migrating to the new task management system, please contact the WiseFlow development team.

