# Task Management and Concurrency Best Practices

This document outlines best practices for task management and concurrency in the Wiseflow project.

## Task Management Architecture

Wiseflow uses a unified task management system that provides a consistent interface for managing asynchronous tasks. The system consists of the following components:

1. **Unified Task Manager**: A facade that provides a consistent API for task management, bridging the gap between the old and new task management systems.
2. **Task Monitor**: Tracks task execution and status.
3. **Thread Pool Manager**: Manages a pool of worker threads for executing CPU-bound tasks concurrently.
4. **Task Manager**: Manages and executes tasks asynchronously.

## Best Practices

### Task Creation and Execution

1. **Use the Unified Task Manager**: Always use the `unified_task_manager` for creating and executing tasks to ensure consistent behavior.

```python
from core.task.unified_manager import unified_task_manager

# Register a task
task_id = await unified_task_manager.register_task(
    name="My Task",
    func=my_function,
    args=(arg1, arg2),
    kwargs={"param1": value1},
    task_type="my_task_type",
    description="Description of my task",
    metadata={"key": "value"}
)

# Execute the task
await unified_task_manager.execute_task(task_id)
```

2. **Provide Descriptive Task Names**: Always provide descriptive names for tasks to make debugging easier.

3. **Use Task Types**: Categorize tasks by type to make it easier to filter and manage them.

4. **Include Metadata**: Include relevant metadata with tasks to provide context for debugging and monitoring.

### Concurrency Control

1. **Limit Concurrency**: Use semaphores to limit concurrency when processing multiple items:

```python
# Create a semaphore to limit concurrency
semaphore = asyncio.Semaphore(concurrency_limit)

# Process items with limited concurrency
async def process_item(item):
    async with semaphore:
        # Process the item
        ...

# Create tasks for all items
tasks = [process_item(item) for item in items]

# Wait for all tasks to complete
await asyncio.gather(*tasks)
```

2. **Avoid Blocking Operations**: Use asynchronous operations whenever possible to avoid blocking the event loop.

3. **Use Thread Pool for CPU-Bound Tasks**: Use the thread pool for CPU-bound tasks to avoid blocking the event loop:

```python
# Submit a CPU-bound task to the thread pool
result = await unified_task_manager.thread_pool.submit(
    cpu_bound_function,
    *args,
    **kwargs
)
```

4. **Monitor Resource Usage**: Monitor CPU and memory usage to adjust concurrency dynamically.

### Error Handling

1. **Use Try-Except Blocks**: Always use try-except blocks to handle exceptions in task functions:

```python
async def my_task_function(*args, **kwargs):
    try:
        # Task logic
        ...
        return result
    except Exception as e:
        logger.error(f"Error in task: {e}")
        # Handle the error or re-raise
        raise
```

2. **Log Errors**: Log all errors with sufficient context to aid debugging.

3. **Use Task Retries**: Configure tasks with appropriate retry settings for transient errors:

```python
task_id = await unified_task_manager.register_task(
    name="My Task",
    func=my_function,
    max_retries=3,
    retry_delay=5.0
)
```

4. **Implement Circuit Breakers**: Use circuit breakers to prevent cascading failures when external services are unavailable.

### Resource Management

1. **Clean Up Resources**: Always clean up resources when tasks complete:

```python
try:
    # Acquire resources
    resource = acquire_resource()
    
    # Use the resource
    result = use_resource(resource)
    
    return result
finally:
    # Release the resource
    release_resource(resource)
```

2. **Use Context Managers**: Use context managers for resource management when possible:

```python
async with acquire_resource() as resource:
    # Use the resource
    result = use_resource(resource)
    
    return result
```

3. **Implement Timeouts**: Use timeouts to prevent tasks from running indefinitely:

```python
try:
    # Execute task with timeout
    result = await asyncio.wait_for(my_coroutine(), timeout=30.0)
    return result
except asyncio.TimeoutError:
    logger.error("Task timed out")
    # Handle timeout
    raise
```

4. **Clean Up Completed Tasks**: Periodically clean up completed tasks to free up memory:

```python
# Clean up completed tasks older than 24 hours
cleaned_up = await unified_task_manager.cleanup_completed_tasks(86400.0)
logger.info(f"Cleaned up {cleaned_up} completed tasks")
```

### Task Dependencies

1. **Use Task Dependencies**: Use task dependencies to ensure tasks are executed in the correct order:

```python
# Register a task with dependencies
task_id = await unified_task_manager.register_task(
    name="My Task",
    func=my_function,
    dependencies=[dependency_task_id]
)
```

2. **Avoid Circular Dependencies**: Ensure there are no circular dependencies between tasks.

3. **Use Task Graphs**: For complex task dependencies, use a task graph to visualize and manage dependencies.

### Monitoring and Debugging

1. **Log Task Lifecycle Events**: Log task creation, execution, completion, and failure events.

2. **Monitor Task Queues**: Monitor the size of task queues to detect bottlenecks.

3. **Track Task Execution Time**: Track the execution time of tasks to identify performance issues.

4. **Use Task IDs for Correlation**: Use task IDs to correlate logs and events across the system.

## Transitioning from Old to New Task Management System

The Wiseflow project is transitioning from an old task management system to a new one. The `unified_task_manager` provides a consistent interface during this transition.

To control which system is used, set the `USE_NEW_TASK_SYSTEM` configuration option:

```python
# In your configuration file
config = {
    "USE_NEW_TASK_SYSTEM": True  # Use the new task management system
}
```

## Conclusion

Following these best practices will help ensure that task management and concurrency in the Wiseflow project is reliable, efficient, and maintainable. Always use the `unified_task_manager` for task management to ensure consistent behavior across the system.

