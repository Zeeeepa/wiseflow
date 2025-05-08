# WiseFlow Resource Monitoring and Management System

This document provides an overview of the resource monitoring and management system in WiseFlow.

## Overview

The resource monitoring and management system in WiseFlow is responsible for:

1. Monitoring system resources (CPU, memory, disk)
2. Triggering alerts when resource thresholds are exceeded
3. Adjusting resource allocation based on system load
4. Ensuring proper cleanup of resources
5. Providing a dashboard for monitoring resource usage

## Components

### ResourceMonitor

The `ResourceMonitor` class in `core/resource_monitor.py` is the main component responsible for monitoring system resources. It:

- Periodically checks CPU, memory, and disk usage
- Maintains a history of resource usage
- Triggers alerts when thresholds are exceeded
- Provides methods for calculating optimal resource allocation

Key features:
- Multiple callback support for resource alerts
- Configurable thresholds for warnings and critical alerts
- Resource usage history for trend analysis
- Automatic recovery from monitoring errors

### ThreadPoolManager

The `ThreadPoolManager` class in `core/thread_pool_manager.py` manages a pool of worker threads for executing CPU-bound tasks. It:

- Manages a pool of worker threads with configurable min/max sizes
- Tracks resource usage of tasks
- Provides methods for adjusting worker count based on system load
- Ensures proper cleanup of resources when tasks are cancelled

Key features:
- Dynamic worker count adjustment
- Resource usage tracking for tasks
- Graceful shutdown with resource cleanup
- Task prioritization

### TaskManager

The `TaskManager` class in `core/task_manager.py` manages asynchronous tasks with dependencies. It:

- Schedules tasks based on priority and dependencies
- Tracks resource usage of tasks
- Provides methods for cancelling tasks with proper resource cleanup
- Handles task retries with exponential backoff

Key features:
- Task dependency management
- Resource cleanup handlers
- Task prioritization
- Automatic retry with exponential backoff
- Resource usage tracking

### Dashboard

The dashboard in `dashboard/resource_monitor.py` provides a web interface for monitoring resource usage and task status. It:

- Displays real-time resource usage
- Shows task status and resource usage
- Allows manual intervention for problematic tasks
- Provides configuration options for resource thresholds

## Resource Monitoring

The resource monitoring system checks the following resources:

### CPU Usage

- Warning threshold: Configurable (default: 72% - calculated as 90% * 0.8)
- Critical threshold: Configurable (default: 90%)

When CPU usage exceeds these thresholds, the system:
1. Logs a warning or critical alert
2. Publishes a resource event
3. Calls registered callbacks
4. Adjusts thread pool size if necessary

### Memory Usage

- Warning threshold: Configurable (default: 68% - calculated as 85% * 0.8)
- Critical threshold: Configurable (default: 85%)

When memory usage exceeds these thresholds, the system:
1. Logs a warning or critical alert
2. Publishes a resource event
3. Calls registered callbacks
4. Adjusts thread pool size if necessary

### Disk Usage

- Warning threshold: Configurable (default: 72% - calculated as 90% * 0.8)
- Critical threshold: Configurable (default: 90%)

When disk usage exceeds these thresholds, the system:
1. Logs a warning or critical alert
2. Publishes a resource event
3. Calls registered callbacks

## Resource Management

The resource management system ensures efficient use of system resources:

### Thread Pool Adjustment

The thread pool size is adjusted based on:
- Current CPU usage
- Current memory usage
- Number of pending tasks

The `calculate_optimal_thread_count` method in `ResourceMonitor` calculates the optimal number of worker threads based on current resource usage.

### Task Prioritization

Tasks are prioritized based on:
- Priority level (LOW, NORMAL, HIGH, CRITICAL)
- Dependencies
- Creation time

Higher priority tasks are executed first, and tasks with dependencies are only executed when all dependencies are completed.

### Resource Cleanup

Resources are cleaned up when:
- Tasks are cancelled
- Tasks fail
- The system is shut down

The `register_resource_cleanup_handler` method in `TaskManager` allows registering handlers for cleaning up resources when tasks are cancelled or fail.

## Configuration

The resource monitoring and management system can be configured through the following settings in `config.py`:

```python
# Resource monitoring
RESOURCE_CHECK_INTERVAL = 10.0  # Interval in seconds between resource checks
CPU_THRESHOLD = 90.0  # CPU usage threshold in percent
MEMORY_THRESHOLD = 85.0  # Memory usage threshold in percent
DISK_THRESHOLD = 90.0  # Disk usage threshold in percent
WARNING_THRESHOLD_FACTOR = 0.8  # Factor to multiply thresholds by for warnings

# Thread pool
MAX_THREAD_WORKERS = 8  # Maximum number of worker threads
MIN_THREAD_WORKERS = 2  # Minimum number of worker threads

# Task manager
MAX_CONCURRENT_TASKS = 4  # Maximum number of concurrent tasks

# Auto-shutdown
AUTO_SHUTDOWN_ENABLED = False  # Whether to enable auto-shutdown
AUTO_SHUTDOWN_IDLE_TIME = 3600  # Idle time in seconds before auto-shutdown
AUTO_SHUTDOWN_CHECK_INTERVAL = 300  # Interval in seconds between auto-shutdown checks
```

## Dashboard

The resource monitoring dashboard provides a web interface for monitoring resource usage and task status. It can be accessed at `http://localhost:5000` when running the dashboard server.

The dashboard provides:
- Real-time resource usage graphs
- Task status and resource usage
- Configuration options for resource thresholds
- Manual intervention for problematic tasks

## Best Practices

1. **Configure appropriate thresholds**: Set resource thresholds based on your system's capabilities and requirements.
2. **Register resource cleanup handlers**: Register handlers for cleaning up resources when tasks are cancelled or fail.
3. **Monitor the dashboard**: Regularly check the dashboard for resource usage trends and task status.
4. **Adjust thread pool size**: Adjust the thread pool size based on your system's capabilities and workload.
5. **Use task priorities**: Use appropriate task priorities to ensure critical tasks are executed first.
6. **Set task dependencies**: Use task dependencies to ensure tasks are executed in the correct order.
7. **Enable auto-shutdown**: Enable auto-shutdown for non-critical systems to save resources when idle.

## Troubleshooting

### High CPU Usage

If CPU usage is consistently high:
1. Check the number of concurrent tasks and thread pool size
2. Reduce the maximum number of concurrent tasks
3. Reduce the maximum number of worker threads
4. Increase the CPU threshold if your system can handle higher CPU usage

### High Memory Usage

If memory usage is consistently high:
1. Check for memory leaks in long-running tasks
2. Reduce the maximum number of concurrent tasks
3. Reduce the maximum number of worker threads
4. Increase the memory threshold if your system can handle higher memory usage

### Stalled Tasks

If tasks are stalling:
1. Check the task status in the dashboard
2. Check for deadlocks or infinite loops in task code
3. Set appropriate timeouts for tasks
4. Cancel stalled tasks manually through the dashboard

### Resource Cleanup Failures

If resources are not being cleaned up properly:
1. Check resource cleanup handlers
2. Ensure all resources have proper cleanup code
3. Add additional logging to track resource allocation and deallocation
4. Implement a periodic resource audit to detect leaks

