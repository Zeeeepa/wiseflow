# Auto-Shutdown Mechanism

The auto-shutdown mechanism in WiseFlow is designed to automatically shut down the application when certain conditions are met. This helps conserve resources and ensures that the application doesn't continue running unnecessarily.

## Features

The auto-shutdown mechanism includes the following features:

1. **Task Completion Detection**: Automatically shuts down the application when all tasks with auto-shutdown enabled are complete.
2. **Resource Usage Monitoring**: Monitors CPU, memory, disk, and network usage, and can trigger a shutdown when resource usage exceeds configured thresholds.
3. **Idle Task Detection**: Detects and optionally terminates tasks that have been running for too long without making progress.
4. **Graceful Shutdown**: Ensures that all resources are properly released and tasks are completed or cancelled before shutting down.

## Configuration

The auto-shutdown mechanism can be configured through the `ResourceMonitor` class. Here's an example configuration:

```python
config = {
    "enabled": True,                # Enable/disable the resource monitor
    "check_interval": 300,          # Check every 5 minutes
    "idle_timeout": 3600,           # 1 hour of inactivity
    "resource_limits": {
        "cpu_percent": 90,          # 90% CPU usage
        "memory_percent": 85,       # 85% memory usage
        "disk_percent": 90          # 90% disk usage
    },
    "notification": {
        "enabled": True,
        "events": ["shutdown", "resource_warning", "task_stalled"]
    },
    "auto_shutdown": {
        "enabled": True,
        "idle_timeout": 3600,       # 1 hour of inactivity
        "resource_threshold": True, # Enable resource threshold checks
        "completion_detection": True # Enable task completion detection
    }
}

# Initialize the resource monitor
resource_monitor = initialize_resource_monitor(task_manager, config)
resource_monitor.start()
```

## Usage

### Enabling Auto-Shutdown for Tasks

To enable auto-shutdown for a task, set the `auto_shutdown` parameter to `True` when creating the task:

```python
task = Task(
    task_id=task_id,
    focus_id="my_focus",
    function=my_function,
    args=(arg1, arg2),
    kwargs={"param1": value1},
    auto_shutdown=True  # Enable auto-shutdown
)
```

When all tasks with auto-shutdown enabled are complete, the application will automatically shut down.

### Manual Shutdown

You can also manually trigger a shutdown using the `request_shutdown` method:

```python
from core.task.monitor import get_resource_monitor

# Get the resource monitor
monitor = get_resource_monitor()

# Request shutdown
monitor.request_shutdown()
```

## Events and Notifications

The auto-shutdown mechanism can log events and send notifications for the following events:

- `shutdown`: When the application is shutting down
- `resource_warning`: When resource usage exceeds configured thresholds
- `task_stalled`: When a task has been running for too long without making progress

Events are logged to the application log and can also be stored in a database if a PocketBase connector is provided.

## Testing

You can test the auto-shutdown mechanism using the provided test script:

```bash
python test_auto_shutdown.py
```

This script creates a task manager, submits a task with auto-shutdown enabled, and monitors the system resources. If the auto-shutdown mechanism is working correctly, the application should exit automatically after the task completes.

## Troubleshooting

If the auto-shutdown mechanism is not working as expected, check the following:

1. Make sure the resource monitor is enabled and started.
2. Check that at least one task has auto-shutdown enabled.
3. Verify that the task completes successfully.
4. Check the application logs for any errors or warnings.
5. Ensure that the resource limits are set appropriately for your system.

## Implementation Details

The auto-shutdown mechanism is implemented in the `core.task.monitor` module. The main components are:

- `ResourceMonitor`: Monitors system resources and manages auto-shutdown
- `monitor_resources`: Monitors system resources and returns current usage
- `check_task_status`: Checks the status of a specific task
- `detect_idle_tasks`: Detects idle tasks that have been running for too long
- `shutdown_task`: Shuts down a specific task
- `configure_shutdown_settings`: Configures auto-shutdown settings
- `shutdown_resources`: Shuts down all resources and exits the application
