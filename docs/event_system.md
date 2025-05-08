# WiseFlow Event System

## Overview

The WiseFlow Event System provides a centralized mechanism for communication between different components of the application. It follows a publish-subscribe pattern where components can publish events and others can subscribe to receive notifications.

## Key Features

- Thread-safe event handling
- Support for both synchronous and asynchronous event processing
- Automatic event history management with configurable retention
- Efficient memory usage with automatic pruning
- Configurable exception handling
- Support for source-based subscription management

## Event Types

The system defines various event types for different aspects of the application:

```python
class EventType(Enum):
    # System events
    SYSTEM_STARTUP = auto()
    SYSTEM_SHUTDOWN = auto()
    SYSTEM_ERROR = auto()
    
    # Task events
    TASK_CREATED = auto()
    TASK_STARTED = auto()
    TASK_COMPLETED = auto()
    TASK_FAILED = auto()
    TASK_CANCELLED = auto()
    
    # Focus point events
    FOCUS_POINT_CREATED = auto()
    FOCUS_POINT_UPDATED = auto()
    FOCUS_POINT_DELETED = auto()
    FOCUS_POINT_PROCESSED = auto()
    
    # Data events
    DATA_COLLECTED = auto()
    DATA_PROCESSED = auto()
    DATA_EXPORTED = auto()
    
    # Connector events
    CONNECTOR_INITIALIZED = auto()
    CONNECTOR_ERROR = auto()
    
    # Knowledge graph events
    KNOWLEDGE_GRAPH_UPDATED = auto()
    KNOWLEDGE_GRAPH_EXPORTED = auto()
    
    # Insight events
    INSIGHT_GENERATED = auto()
    
    # Resource events
    RESOURCE_WARNING = auto()
    RESOURCE_CRITICAL = auto()
    
    # Custom event
    CUSTOM = auto()
```

## Basic Usage

### Publishing Events

You can publish events either synchronously or asynchronously:

```python
from core.event_system import EventType, Event, publish, publish_sync

# Create an event
event = Event(EventType.TASK_CREATED, {"task_id": "123"}, "task_manager")

# Publish asynchronously
await publish(event)

# Or publish synchronously
publish_sync(event)
```

### Subscribing to Events

You can subscribe to specific event types or all events:

```python
from core.event_system import EventType, subscribe

# Subscribe to a specific event type
def handle_task_created(event):
    print(f"Task created: {event.data['task_id']}")

subscribe(EventType.TASK_CREATED, handle_task_created)

# Subscribe to all events
def log_all_events(event):
    print(f"Event received: {event}")

subscribe(None, log_all_events)
```

### Asynchronous Event Handlers

You can use async functions as event handlers:

```python
from core.event_system import EventType, subscribe

# Async event handler
async def handle_task_created(event):
    await some_async_operation()
    print(f"Task created: {event.data['task_id']}")

subscribe(EventType.TASK_CREATED, handle_task_created)
```

### Unsubscribing

You can unsubscribe specific callbacks or all callbacks from a source:

```python
from core.event_system import EventType, unsubscribe, unsubscribe_by_source

# Unsubscribe a specific callback
unsubscribe(EventType.TASK_CREATED, handle_task_created)

# Unsubscribe all callbacks from a source
unsubscribe_by_source("my_component")
```

## Advanced Features

### Event History

The event system keeps a history of events that can be queried:

```python
from core.event_system import get_history, clear_history, prune_history
from datetime import datetime, timedelta

# Get all events (up to limit)
all_events = get_history(limit=100)

# Get events of a specific type
task_events = get_history(EventType.TASK_CREATED, limit=50)

# Get events since a specific time
recent_events = get_history(since=datetime.now() - timedelta(hours=1))

# Clear all event history
clear_history()

# Prune events older than a specific time
prune_history(older_than=datetime.now() - timedelta(days=1))
```

### Configuration

The event system can be enabled or disabled globally:

```python
from core.event_system import enable, disable, is_enabled

# Check if the event system is enabled
if is_enabled():
    print("Event system is enabled")

# Disable the event system
disable()

# Enable the event system
enable()
```

### Exception Handling

You can configure how exceptions in event handlers are handled:

```python
from core.event_system import set_propagate_exceptions

# By default, exceptions are caught and logged
set_propagate_exceptions(False)

# To propagate exceptions (useful for debugging)
set_propagate_exceptions(True)
```

### History Management

You can configure how event history is managed:

```python
from core.event_system import set_max_history_size, set_history_retention_period
from datetime import timedelta

# Set maximum number of events to keep in history
set_max_history_size(2000)

# Set retention period for events
set_history_retention_period(timedelta(days=7))
```

## Thread Safety

The event system is designed to be thread-safe. All operations that modify shared state are protected by locks. However, be careful when implementing event handlers that might modify shared state themselves.

Event handlers are executed concurrently using a thread pool for synchronous handlers and asyncio tasks for asynchronous handlers. This allows for efficient processing of events even when there are many subscribers.

## Performance Considerations

- The event system uses a thread pool for handling synchronous event callbacks to prevent blocking the main thread
- Event history is automatically pruned to prevent memory leaks
- You can configure the maximum history size and retention period to control memory usage
- For high-volume event scenarios, consider using more specific event subscriptions rather than subscribing to all events

## Debugging

To debug the event system, you can:

1. Enable exception propagation: `set_propagate_exceptions(True)`
2. Increase logging level for the event system: `logging.getLogger("core.event_system").setLevel(logging.DEBUG)`
3. Examine event history: `get_history()`

## Shutdown

When shutting down the application, it's important to properly shut down the event system:

```python
from core.event_system import shutdown

# Shutdown the event system
shutdown()
```

This ensures that all resources are properly cleaned up, including the thread pool used for event processing.

## Best Practices

1. **Use specific event types**: Subscribe to specific event types rather than all events when possible
2. **Clean up subscriptions**: Unsubscribe when components are destroyed to prevent memory leaks
3. **Keep handlers lightweight**: Event handlers should be quick to execute; for heavy processing, spawn a separate task
4. **Use source identifiers**: When subscribing, provide a source identifier to make bulk unsubscription easier
5. **Handle exceptions**: Make sure event handlers properly handle exceptions to prevent disrupting the event system
6. **Use async handlers for I/O**: For handlers that perform I/O operations, use async handlers to prevent blocking
7. **Properly shutdown**: Always call `shutdown()` when the application is shutting down
