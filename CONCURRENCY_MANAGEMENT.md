# Concurrency Management System

This document provides an overview of the concurrency management system implemented in Wiseflow. The system is designed to improve resource utilization, error handling, and task scheduling through a comprehensive approach to managing concurrent operations.

## Components

The concurrency management system consists of three main components:

1. **Resource Monitor** - Tracks system resources and provides optimization guidance
2. **Thread Pool Manager** - Manages worker threads with priority-based scheduling
3. **Task Manager** - Provides high-level task management with dependencies and scheduling

### 1. Resource Monitor

The `ResourceMonitor` class tracks CPU, memory, disk, and IO usage to ensure optimal resource utilization.

#### Key Features:
- Real-time monitoring of system resources
- Configurable thresholds for resource constraints
- Callback system for resource events
- Historical metrics tracking
- Optimal thread count calculation based on system load

#### Example Usage:

```python
from resource_monitor import ResourceMonitor

# Create and start a resource monitor
monitor = ResourceMonitor(
    check_interval=5.0,
    cpu_threshold=80.0,
    memory_threshold=80.0
)

# Define a callback for resource alerts
def resource_alert(resource_type, current_value, threshold):
    print(f"Alert: {resource_type} usage at {current_value:.1f}% (threshold: {threshold}%)")

# Register the callback
monitor.add_callback(resource_alert)

# Start monitoring
monitor.start()

# Get current resource usage
usage = monitor.get_current_usage()
print(f"CPU: {usage['cpu']:.1f}%, Memory: {usage['memory']:.1f}%")

# Calculate optimal thread count
optimal_threads = monitor.calculate_optimal_thread_count()
print(f"Optimal thread count: {optimal_threads}")

# Stop monitoring when done
monitor.stop()
```

### 2. Thread Pool Manager

The `ThreadPoolManager` class provides a robust thread pool implementation with advanced features for task execution.

#### Key Features:
- Priority-based task scheduling
- Dynamic worker pool size adjustment based on system resources
- Task cancellation and status tracking
- Comprehensive metrics and monitoring
- Task retry policies with configurable retry counts and delays

#### Example Usage:

```python
from thread_pool_manager import ThreadPoolManager, TaskPriority
from resource_monitor import ResourceMonitor

# Create a resource monitor
resource_monitor = ResourceMonitor()
resource_monitor.start()

# Create a thread pool manager
pool = ThreadPoolManager(
    min_workers=2,
    max_workers=10,
    resource_monitor=resource_monitor
)

# Start the pool
pool.start()

# Define a task function
def example_task(task_id, sleep_time):
    print(f"Task {task_id} started")
    time.sleep(sleep_time)
    print(f"Task {task_id} completed")
    return f"Result from task {task_id}"

# Submit tasks with different priorities
task_id = pool.submit(
    example_task, 
    1, 
    sleep_time=2.0,
    priority=TaskPriority.HIGH,
    max_retries=2
)

# Wait for a specific task to complete
pool.wait_for_task(task_id)

# Get the task result
result = pool.get_task_result(task_id)
print(f"Task result: {result}")

# Get pool metrics
metrics = pool.get_metrics()
print(f"Thread pool metrics: {metrics}")

# Stop the pool when done
pool.stop()
```

### 3. Task Manager

The `TaskManager` class provides high-level task management with support for dependencies, scheduling, and execution history.

#### Key Features:
- Task registration and scheduling with cron-like syntax
- Task dependencies and ordering
- Task retry policies with configurable retry counts and delays
- Task status tracking and history
- Support for scheduled tasks

#### Example Usage:

```python
from task_manager import TaskManager
from thread_pool_manager import ThreadPoolManager, TaskPriority
from resource_monitor import ResourceMonitor

# Create a resource monitor
resource_monitor = ResourceMonitor()
resource_monitor.start()

# Create a thread pool
thread_pool = ThreadPoolManager(
    resource_monitor=resource_monitor
)
thread_pool.start()

# Create a task manager
task_manager = TaskManager(
    thread_pool=thread_pool,
    resource_monitor=resource_monitor
)
task_manager.start()

# Define task functions
def task_1():
    print("Executing task 1")
    time.sleep(1)
    return "Task 1 result"

def task_2():
    print("Executing task 2")
    time.sleep(2)
    return "Task 2 result"

# Register tasks
task1_id = task_manager.register_task(
    name="Task 1",
    func=task_1,
    priority=TaskPriority.HIGH
)

task2_id = task_manager.register_task(
    name="Task 2",
    func=task_2,
    dependencies=[task1_id],  # Task 2 depends on Task 1
    priority=TaskPriority.NORMAL
)

# Execute tasks with dependencies
execution_ids = task_manager.execute_tasks([task2_id], wait=True)

# Get task history
history = task_manager.get_task_history()
print(f"Task execution history: {len(history)} entries")

# Stop the task manager when done
task_manager.stop()
```

## Integration with Existing Code

The concurrency management system has been integrated with the existing Wiseflow codebase, particularly in `run_task.py`. The integration includes:

1. Initializing the resource monitor, thread pool, and task manager
2. Registering focus points as tasks with the task manager
3. Setting up task dependencies for insight generation
4. Implementing resource monitoring callbacks
5. Maintaining backward compatibility with the existing task management system

## Benefits

The concurrency management system provides several benefits:

1. **Improved Resource Utilization**
   - Dynamic thread pool sizing based on system load
   - Optimal resource allocation for tasks

2. **Better Error Handling**
   - Robust retry mechanisms for failed tasks
   - Comprehensive error tracking and reporting

3. **Enhanced Monitoring**
   - Real-time monitoring of system resources
   - Detailed metrics on task execution

4. **Priority-Based Scheduling**
   - Critical tasks are executed first
   - Better control over task execution order

5. **Support for Complex Workflows**
   - Task dependencies ensure proper execution order
   - Scheduled tasks with cron-like syntax

## Future Enhancements

Potential future enhancements to the concurrency management system include:

1. **Distributed Task Execution**
   - Support for executing tasks across multiple machines
   - Load balancing between nodes

2. **Advanced Scheduling**
   - More sophisticated scheduling algorithms
   - Support for time windows and blackout periods

3. **Task Profiling**
   - Automatic profiling of task resource usage
   - Performance optimization recommendations

4. **Web Interface**
   - Real-time monitoring dashboard
   - Task management UI

5. **Workflow Designer**
   - Visual editor for creating task workflows
   - Support for complex dependency graphs

## Requirements

The concurrency management system requires the following dependencies:

- Python 3.7+
- `psutil` for system resource monitoring
- `schedule` for task scheduling

These dependencies have been added to the `requirements.txt` file.
