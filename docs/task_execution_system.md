# WiseFlow Task Execution System

This document provides an overview of the task execution and concurrency management system in WiseFlow.

## Overview

WiseFlow uses a task execution system to manage and execute tasks asynchronously. The system consists of several components:

1. **Task Manager**: Manages task execution, dependencies, and state.
2. **Thread Pool Manager**: Provides a thread pool for executing CPU-bound tasks concurrently.
3. **Task Monitor**: Tracks task execution and status.
4. **Task Bridge**: Provides a bridge between the old and new task execution systems.

## Task Lifecycle

A task in WiseFlow goes through the following lifecycle:

1. **Creation**: A task is created with a unique ID, name, function to execute, and optional parameters.
2. **Registration**: The task is registered with the task manager and added to the pending tasks queue.
3. **Scheduling**: The task scheduler selects tasks from the pending queue based on priority and dependencies.
4. **Execution**: The task is executed by the task manager or thread pool manager.
5. **Completion**: The task completes successfully, fails, or is cancelled.
6. **Cleanup**: Resources allocated to the task are cleaned up.

## Task Status

A task can have one of the following statuses:

- **PENDING**: The task is waiting to be executed.
- **RUNNING**: The task is currently being executed.
- **COMPLETED**: The task has completed successfully.
- **FAILED**: The task has failed due to an error.
- **CANCELLED**: The task has been cancelled.
- **WAITING**: The task is waiting for its dependencies to complete.

## Task Dependencies

Tasks can have dependencies on other tasks. A task will not be executed until all its dependencies have completed successfully. If a dependency fails, the task will also fail.

## Task Priority

Tasks can have one of the following priority levels:

- **LOW**: Low priority tasks are executed last.
- **NORMAL**: Normal priority tasks are executed after high and critical priority tasks.
- **HIGH**: High priority tasks are executed after critical priority tasks.
- **CRITICAL**: Critical priority tasks are executed first.

## Task Execution

Tasks can be executed in one of two ways:

1. **Asynchronous Execution**: Tasks are executed asynchronously using asyncio.
2. **Thread Pool Execution**: CPU-bound tasks are executed in a thread pool.

## Task Bridge

The task bridge provides a unified interface to both the old and new task execution systems. It ensures consistent task state management and resource cleanup between the two systems.

## Error Handling

The task execution system includes robust error handling to ensure that tasks fail gracefully and resources are properly cleaned up. If a task fails, it can be retried a configurable number of times with exponential backoff.

## Resource Management

The task execution system includes resource management to ensure that resources allocated to tasks are properly cleaned up. This includes:

1. **Thread Pool Management**: The thread pool manager ensures that threads are properly managed and cleaned up.
2. **Task Resource Tracking**: Resources allocated to tasks are tracked and cleaned up when the task completes.
3. **Memory Management**: The system includes memory management to prevent memory leaks in long-running tasks.

## Concurrency Management

The task execution system includes concurrency management to prevent race conditions and deadlocks. This includes:

1. **Task Locking**: Tasks are locked during state transitions to prevent race conditions.
2. **Dependency Management**: Task dependencies are managed to prevent deadlocks.
3. **Resource Locking**: Resources are locked during access to prevent race conditions.

## Best Practices

When using the task execution system, follow these best practices:

1. **Use the Task Bridge**: Use the task bridge to ensure consistent task state management and resource cleanup.
2. **Register Resources**: Register resources allocated to tasks for proper cleanup.
3. **Handle Errors**: Handle errors in task execution and provide meaningful error messages.
4. **Set Timeouts**: Set timeouts for tasks to prevent them from running indefinitely.
5. **Use Dependencies**: Use task dependencies to ensure tasks are executed in the correct order.
6. **Clean Up Resources**: Clean up resources allocated to tasks when they complete.
7. **Monitor Task Status**: Monitor task status to detect and handle failures.
8. **Use Appropriate Priority**: Use appropriate priority levels for tasks based on their importance.
9. **Limit Concurrent Tasks**: Limit the number of concurrent tasks to prevent resource exhaustion.
10. **Use Exponential Backoff**: Use exponential backoff for task retries to prevent overloading the system.

## Example Usage

```python
from core.task import task_bridge
from core.task_manager import TaskPriority

# Register a task
task_id = task_bridge.register_task(
    name="Example Task",
    func=my_function,
    args=(arg1, arg2),
    kwargs={"key": "value"},
    priority=TaskPriority.NORMAL,
    dependencies=[dependency_task_id],
    max_retries=3,
    retry_delay=1.0,
    timeout=60.0
)

# Start the task
task_bridge.start_task(task_id)

# Update task progress
task_bridge.update_task_progress(task_id, 0.5, "Halfway done")

# Complete the task
task_bridge.complete_task(task_id, result)

# Or fail the task
task_bridge.fail_task(task_id, error)

# Or cancel the task
task_bridge.cancel_task(task_id)

# Get task status
status = task_bridge.get_task_status(task_id)

# Get task result
result = task_bridge.get_task_result(task_id)

# Get task error
error = task_bridge.get_task_error(task_id)

# Clean up task resources
task_bridge.cleanup_task(task_id)
```

