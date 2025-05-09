# WiseFlow Resource Monitor

## Overview

The WiseFlow Resource Monitor provides functionality to monitor system resources like CPU, memory, and disk usage. It helps ensure system stability by detecting when resource usage exceeds configurable thresholds and triggering appropriate actions.

## Key Features

- Monitoring of CPU, memory, and disk usage
- Configurable warning and critical thresholds
- Adaptive monitoring intervals based on system load
- Hysteresis to prevent threshold oscillation
- Event-based notification system
- Resource usage history tracking
- Callback registration for custom actions

## Basic Usage

### Starting and Stopping the Monitor

```python
from core.resource_monitor import resource_monitor

# Start the resource monitor
await resource_monitor.start()

# Stop the resource monitor
await resource_monitor.stop()
```

### Getting Resource Usage

```python
# Get current resource usage
usage = resource_monitor.get_resource_usage()

print(f"CPU: {usage['cpu']['percent']}%")
print(f"Memory: {usage['memory']['percent']}%")
print(f"Disk: {usage['disk']['percent']}%")
```

### Setting Thresholds

```python
# Set new thresholds
resource_monitor.set_thresholds(
    cpu=80.0,      # 80% CPU threshold
    memory=85.0,   # 85% memory threshold
    disk=90.0      # 90% disk threshold
)
```

### Registering Callbacks

```python
# Register a callback for CPU events
def handle_cpu_event(resource_type, value, threshold, is_critical):
    if is_critical:
        print(f"CRITICAL: CPU usage at {value}%!")
    else:
        print(f"WARNING: CPU usage at {value}%")

resource_monitor.register_callback('cpu', handle_cpu_event)

# Register a callback for all resource events
def handle_all_resources(resource_data):
    print(f"Resource update: CPU={resource_data['cpu']}%, Memory={resource_data['memory']}%")

resource_monitor.register_callback('all', handle_all_resources)
```

## Advanced Features

### Adaptive Monitoring

The resource monitor can adjust its check interval based on system load:

```python
# Enable adaptive monitoring
resource_monitor.set_adaptive_monitoring(True)

# Disable adaptive monitoring
resource_monitor.set_adaptive_monitoring(False)
```

When adaptive monitoring is enabled:
- The check interval decreases (more frequent checks) when resource usage is high
- The check interval increases (less frequent checks) when resource usage is low

### Resource History

You can access the history of resource usage:

```python
# Get all resource history
history = resource_monitor.get_resource_history()

# Get history for a specific resource
cpu_history = resource_monitor.get_resource_history(resource_type='cpu')

# Get limited history
recent_history = resource_monitor.get_resource_history(limit=10)
```

### Clearing History

```python
# Clear resource history
resource_monitor.clear_history()
```

## Configuration

The resource monitor can be configured through the application config:

```python
# In config.py or similar
config = {
    "RESOURCE_CHECK_INTERVAL": 10.0,  # Check interval in seconds
    "CPU_THRESHOLD": 90.0,            # CPU threshold in percent
    "MEMORY_THRESHOLD": 85.0,         # Memory threshold in percent
    "DISK_THRESHOLD": 90.0,           # Disk threshold in percent
    "ADAPTIVE_RESOURCE_MONITORING": True  # Enable adaptive monitoring
}
```

## Integration with Event System

The resource monitor integrates with the WiseFlow Event System to publish resource events:

- `EventType.RESOURCE_WARNING`: Published when resource usage exceeds warning threshold
- `EventType.RESOURCE_CRITICAL`: Published when resource usage exceeds critical threshold

You can subscribe to these events:

```python
from core.event_system import EventType, subscribe

def handle_resource_warning(event):
    resource_type = event.data['resource_type']
    value = event.data['value']
    threshold = event.data['threshold']
    print(f"Resource warning: {resource_type} at {value}% (threshold: {threshold}%)")

subscribe(EventType.RESOURCE_WARNING, handle_resource_warning)
```

## Performance Considerations

- The resource monitor is designed to have minimal impact on system performance
- Adaptive monitoring reduces overhead during normal operation
- Resource history is limited to prevent memory growth
- Hysteresis prevents rapid oscillation between states

## Best Practices

1. **Set appropriate thresholds**: Configure thresholds based on your application's requirements and system capabilities
2. **Use adaptive monitoring**: Enable adaptive monitoring to reduce overhead during normal operation
3. **Register specific callbacks**: Register callbacks for specific resources rather than all resources when possible
4. **Clean up callbacks**: Unregister callbacks when components are destroyed to prevent memory leaks
5. **Handle events asynchronously**: When responding to resource events, avoid blocking operations
6. **Monitor resource trends**: Use the resource history to identify trends and potential issues
7. **Properly shutdown**: Always call `stop()` when the application is shutting down

## Troubleshooting

If you encounter issues with the resource monitor:

1. Check the logs for error messages
2. Verify that the monitor is running: `resource_monitor.is_running`
3. Check the current thresholds: `resource_monitor.thresholds`
4. Examine the resource history: `resource_monitor.get_resource_history()`
5. Temporarily disable adaptive monitoring: `resource_monitor.set_adaptive_monitoring(False)`

