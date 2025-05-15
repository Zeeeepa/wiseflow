# Unified Task Management System

This directory contains the unified task management system for WiseFlow, which consolidates multiple task management implementations into a single, consistent API.

## Overview

The unified task management system provides a flexible and robust way to manage and execute tasks with different execution strategies, dependencies, and error handling. It replaces the following legacy implementations:

- `TaskManager` in `core/task_manager.py`
- `ThreadPoolManager` in `core/thread_pool_manager.py`
- Task handling in `core/run_task.py` and `core/run_task_new.py`
- `AsyncTaskManager` in `core/task/`

## Components

The unified task management system consists of the following components:

### Task

The `Task` class represents a task that can be executed by the task manager. It includes:

- Task metadata (ID, name, description, tags)
- Execution parameters (function, arguments, priority, dependencies)
- Retry configuration (max retries, retry delay)
- Status tracking (status, result, error, progress)

### TaskManager

The `TaskManager` class manages and executes tasks. It provides:

- Task registration and execution
- Dependency management
- Concurrency control
- Progress tracking
- Error handling and retries

### Executors

The system supports different execution strategies through executor classes:

- `SequentialExecutor`: Executes tasks sequentially in the current thread
- `ThreadPoolExecutor`: Executes tasks concurrently using a thread pool
- `AsyncExecutor`: Executes tasks concurrently using asyncio tasks

### Exceptions

The system defines specific exception types for different error scenarios:

- `TaskError`: Base class for all task-related errors
- `TaskDependencyError`: Error when a task dependency cannot be satisfied
- `TaskCancellationError`: Error when a task is cancelled
- `TaskTimeoutError`: Error when a task times out
- `TaskExecutionError`: Error when a task execution fails

## Usage

Here's a basic example of how to use the unified task management system:

```python
from core.task_management import TaskManager, TaskPriority

# Create a task manager
task_manager = TaskManager(max_concurrent_tasks=4)

# Register a task
task_id = task_manager.register_task(
    name="My Task",
    func=my_function,
    arg1, arg2,
    kwargs={"param": "value"},
    priority=TaskPriority.HIGH,
    max_retries=3,
    retry_delay=1.0,
    timeout=60.0,
    description="This is my task",
    tags=["tag1", "tag2"]
)

# Execute the task
result = await task_manager.execute_task(task_id)

# Get task status
status = task_manager.get_task_status(task_id)

# Get task result
result = task_manager.get_task_result(task_id)

# Cancel a task
cancelled = await task_manager.cancel_task(task_id)
```

## Compatibility Layer

For backward compatibility, the system includes compatibility layers for the legacy task management implementations:

- `core/task_manager.py`: Provides a compatibility layer for the legacy `TaskManager`
- `core/thread_pool_manager.py`: Provides a compatibility layer for the legacy `ThreadPoolManager`
- `core/task/async_task_manager.py`: Provides a compatibility layer for the legacy `AsyncTaskManager`

These compatibility layers delegate to the unified task management system while maintaining the legacy APIs.

## Migration

To migrate from the legacy task management implementations to the unified system:

1. Import from the unified system instead of the legacy implementations:

```python
# Legacy imports
from core.task_manager import TaskManager, Task, TaskPriority, TaskStatus

# New imports
from core.task_management import TaskManager, Task, TaskPriority, TaskStatus
```

2. Update task registration and execution code to use the unified API:

```python
# Legacy code
task_id = task_manager.register_task(
    name="My Task",
    func=my_function,
    args=(arg1, arg2),
    kwargs={"param": "value"},
    priority=TaskPriority.HIGH
)

# New code
task_id = task_manager.register_task(
    name="My Task",
    func=my_function,
    arg1, arg2,
    kwargs={"param": "value"},
    priority=TaskPriority.HIGH,
    description="This is my task",
    tags=["tag1", "tag2"]
)
```

3. Use the unified task manager's execute_task method:

```python
# Legacy code
task_manager.start()

# New code
await task_manager.start()
result = await task_manager.execute_task(task_id)
```

## Benefits

The unified task management system provides several benefits over the legacy implementations:

- **Consistency**: A single, consistent API for all task management needs
- **Flexibility**: Support for different execution strategies (sequential, thread pool, async)
- **Robustness**: Comprehensive error handling and retry mechanisms
- **Scalability**: Better concurrency control and resource management
- **Maintainability**: Cleaner code organization and separation of concerns

