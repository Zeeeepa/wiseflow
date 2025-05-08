# WiseFlow Event System

## Overview

The WiseFlow Event System provides a centralized mechanism for communication between different components of the application. It follows a publish-subscribe pattern where components can publish events and others can subscribe to receive notifications.

## Key Features

- Thread-safe event publishing and subscription
- Support for both synchronous and asynchronous event handling
- Event history tracking
- Automatic cleanup of subscriptions to prevent memory leaks
- Configurable exception propagation
- Helper functions for creating common event types

## Event Types

The system defines several event types in the `EventType` enum:

- **System Events**: `SYSTEM_STARTUP`, `SYSTEM_SHUTDOWN`, `SYSTEM_ERROR`
- **Task Events**: `TASK_CREATED`, `TASK_STARTED`, `TASK_COMPLETED`, `TASK_FAILED`, `TASK_CANCELLED`
- **Focus Point Events**: `FOCUS_POINT_CREATED`, `FOCUS_POINT_UPDATED`, `FOCUS_POINT_DELETED`, `FOCUS_POINT_PROCESSED`
- **Data Events**: `DATA_COLLECTED`, `DATA_PROCESSED`, `DATA_EXPORTED`
- **Connector Events**: `CONNECTOR_INITIALIZED`, `CONNECTOR_ERROR`
- **Knowledge Graph Events**: `KNOWLEDGE_GRAPH_UPDATED`, `KNOWLEDGE_GRAPH_EXPORTED`
- **Insight Events**: `INSIGHT_GENERATED`
- **Resource Events**: `RESOURCE_WARNING`, `RESOURCE_CRITICAL`
- **Custom Events**: `CUSTOM`

## Basic Usage

### Subscribing to Events

```python
from core.event_system import EventType, subscribe, Event

# Subscribe to a specific event type
def handle_task_completed(event: Event):
    task_id = event.data.get("task_id")
    print(f"Task {task_id} completed")

subscribe(EventType.TASK_COMPLETED, handle_task_completed)

# Subscribe to all events
def log_all_events(event: Event):
    print(f"Event received: {event.event_type.name}")

subscribe(None, log_all_events)

# Subscribe with a source identifier (for later unsubscription)
subscribe(EventType.SYSTEM_ERROR, handle_system_error, source="error_handler")
```

### Publishing Events

```python
from core.event_system import EventType, Event, publish, publish_sync

# Publish an event asynchronously
async def notify_task_completed(task_id):
    event = Event(
        event_type=EventType.TASK_COMPLETED,
        data={"task_id": task_id},
        source="task_manager"
    )
    await publish(event)

# Publish an event synchronously
def notify_system_error(error):
    event = Event(
        event_type=EventType.SYSTEM_ERROR,
        data={"error": str(error)},
        source="system"
    )
    publish_sync(event)
```

### Using Helper Functions

```python
from core.event_system import create_task_event, create_system_error_event, publish_sync

# Create and publish a task event
task_event = create_task_event(
    event_type=EventType.TASK_STARTED,
    task_id="task-123",
    data={"name": "Data Processing Task"}
)
publish_sync(task_event)

# Create and publish a system error event
try:
    # Some code that might raise an exception
    result = 1 / 0
except Exception as e:
    error_event = create_system_error_event(e)
    publish_sync(error_event)
```

### Unsubscribing

```python
from core.event_system import EventType, unsubscribe, unsubscribe_by_source

# Unsubscribe a specific callback from an event type
unsubscribe(EventType.TASK_COMPLETED, handle_task_completed)

# Unsubscribe all callbacks from a specific source
unsubscribe_by_source("error_handler")
```

## Best Practices

### Memory Leak Prevention

To prevent memory leaks, always unsubscribe from events when a component is destroyed:

```python
class MyComponent:
    def __init__(self):
        self.source_id = "my_component_123"
        subscribe(EventType.TASK_COMPLETED, self.handle_task_completed, source=self.source_id)
    
    def handle_task_completed(self, event):
        # Handle the event
        pass
    
    def cleanup(self):
        # Unsubscribe all callbacks from this component
        unsubscribe_by_source(self.source_id)
```

### Error Handling

Configure how exceptions in event subscribers should be handled:

```python
from core.event_system import set_propagate_exceptions

# By default, exceptions are caught and logged
# To propagate exceptions (useful for debugging):
set_propagate_exceptions(True)

# To catch and log exceptions (better for production):
set_propagate_exceptions(False)
```

### Asynchronous Event Handling

When subscribing with an async callback, make sure to use it in an async context:

```python
async def async_event_handler(event):
    # Async processing
    await some_async_function()

# Subscribe the async handler
subscribe(EventType.DATA_COLLECTED, async_event_handler)

# When publishing, use the async publish function
await publish(event)
```

### Event History

The event system keeps a history of events that can be queried:

```python
from core.event_system import get_history, clear_history

# Get recent events of a specific type
task_events = get_history(EventType.TASK_COMPLETED, limit=10)

# Get all recent events
all_events = get_history(limit=100)

# Clear event history
clear_history()
```

## Configuration

The event system can be enabled or disabled globally:

```python
from core.event_system import enable, disable, is_enabled

# Check if the event system is enabled
if is_enabled():
    # Do something with events
    
# Disable the event system
disable()

# Enable the event system
enable()
```

You can also configure the maximum history size:

```python
from core.event_system import set_max_history_size

# Set the maximum number of events to keep in history
set_max_history_size(2000)
```

## Thread Safety

The event system is designed to be thread-safe. All operations that modify shared state are protected by locks. However, be careful when implementing event handlers that might modify shared state themselves.

## Performance Considerations

- Consider the performance impact of event handlers, especially for high-frequency events
- Use event filtering to process only relevant events
- For very high-frequency events, consider batching or sampling
- Be mindful of the event history size, as it can consume memory

## Debugging

To debug the event system, you can:

1. Enable exception propagation: `set_propagate_exceptions(True)`
2. Increase logging level for the event system: `logging.getLogger("core.event_system").setLevel(logging.DEBUG)`
3. Examine event history: `get_history()`
4. Check subscriber count: `get_subscriber_count()`

