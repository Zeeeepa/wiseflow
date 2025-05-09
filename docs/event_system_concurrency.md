# Event System Concurrency Guide

This document provides guidance on using the WiseFlow event system with a focus on concurrency, thread safety, and avoiding common pitfalls.

## Overview of Improvements

The event system has been enhanced with the following improvements:

1. **Clear Separation of Async/Sync Paths**
   - Dedicated processing paths for synchronous and asynchronous callbacks
   - Proper event loop management when crossing async/sync boundaries
   - Safeguards against event loop conflicts

2. **Thread Safety Enhancements**
   - Thread-safe event handling with proper locking mechanisms
   - Worker thread for processing synchronous events
   - Queue-based event processing to prevent thread contention

3. **Deadlock Prevention**
   - Detection and prevention of circular event dependencies
   - Timeouts for event processing to prevent hanging
   - Locks are not held during callback execution

4. **Improved Event Loop Management**
   - Proper creation and management of event loops
   - Handling cases where no event loop is available
   - Prevention of event loop nesting issues

5. **Standardized Error Handling**
   - Consistent error handling for event callbacks
   - Proper logging for event handler errors
   - Automatic disabling of problematic subscribers after repeated failures
   - Configuration options for error propagation

## Best Practices

### Choosing Between Sync and Async

```python
from core.event_system import EventType, Event, subscribe, publish, publish_sync

# For synchronous callbacks
def sync_handler(event):
    # Process event synchronously
    print(f"Sync handling of {event}")

# For asynchronous callbacks
async def async_handler(event):
    # Process event asynchronously
    await some_async_operation()
    print(f"Async handling of {event}")

# Subscribe both types of handlers
subscribe(EventType.SYSTEM_STARTUP, sync_handler)
subscribe(EventType.SYSTEM_STARTUP, async_handler)

# Publishing events
event = Event(EventType.SYSTEM_STARTUP, {"version": "1.0.0"}, "my_component")

# For synchronous contexts
publish_sync(event)

# For asynchronous contexts
await publish(event)
```

### Avoiding Deadlocks

1. **Keep Callbacks Short**: Avoid long-running operations in event callbacks.

2. **Don't Hold Locks During Event Publishing**: Never hold locks when publishing events.

   ```python
   # BAD
   with my_lock:
       # Do something
       publish_sync(event)  # May deadlock if a callback tries to acquire my_lock
   
   # GOOD
   with my_lock:
       # Do something
   
   # Release the lock before publishing
   publish_sync(event)
   ```

3. **Be Careful with Nested Events**: Avoid complex chains of nested event publications.

   ```python
   # Potentially problematic if it creates circular dependencies
   def handler(event):
       # Process event
       publish_sync(another_event)  # Publishing from within a handler
   ```

4. **Use Timeouts**: The event system now has built-in timeouts to prevent hanging.

   ```python
   from core.event_system import set_timeout
   
   # Set a timeout for event processing (in seconds)
   set_timeout(2.0)
   ```

### Thread Safety

1. **Thread-Local State**: Be careful with thread-local state in callbacks.

2. **Synchronization**: Use proper synchronization for shared resources.

   ```python
   import threading
   
   # Thread-safe counter
   counter = {"value": 0}
   counter_lock = threading.Lock()
   
   def increment_counter(event):
       with counter_lock:
           counter["value"] += 1
   ```

3. **Avoid Blocking Operations**: Blocking operations can impact the entire event system.

### Error Handling

1. **Exception Propagation**: Configure whether exceptions should be propagated.

   ```python
   from core.event_system import set_propagate_exceptions
   
   # Propagate exceptions (for debugging)
   set_propagate_exceptions(True)
   
   # Catch and log exceptions (for production)
   set_propagate_exceptions(False)
   ```

2. **Graceful Error Handling**: Handle exceptions in your callbacks.

   ```python
   def robust_handler(event):
       try:
           # Process event
       except Exception as e:
           logger.error(f"Error processing event {event}: {e}")
   ```

## Advanced Usage

### Custom Event Types

You can extend the `EventType` enum with your own event types:

```python
from core.event_system import EventType, Event

# Define custom event types
class MyEventTypes(EventType):
    MY_CUSTOM_EVENT = auto()
    ANOTHER_CUSTOM_EVENT = auto()

# Create and publish custom events
event = Event(MyEventTypes.MY_CUSTOM_EVENT, {"custom_data": "value"}, "my_component")
publish_sync(event)
```

### Component Lifecycle Management

Properly manage subscriptions during component lifecycle:

```python
class MyComponent:
    def __init__(self):
        # Subscribe to events
        subscribe(EventType.SYSTEM_STARTUP, self.on_startup, source="MyComponent")
    
    def on_startup(self, event):
        # Handle startup event
        pass
    
    def cleanup(self):
        # Unsubscribe all callbacks from this component
        unsubscribe_by_source("MyComponent")
```

### Performance Monitoring

Monitor event system performance:

```python
from core.event_system import get_subscriber_count, get_history

# Get number of subscribers
count = get_subscriber_count(EventType.SYSTEM_STARTUP)
print(f"Number of subscribers: {count}")

# Get recent events
recent_events = get_history(limit=10)
for event in recent_events:
    print(f"Event: {event}")
```

## Troubleshooting

### Common Issues

1. **Events Not Being Processed**
   - Check if the event bus is enabled: `is_enabled()`
   - Verify that you've subscribed to the correct event type
   - Check for exceptions in your callbacks

2. **Deadlocks**
   - Look for circular event dependencies
   - Check if locks are being held during event publishing
   - Increase the timeout: `set_timeout(10.0)`

3. **Performance Issues**
   - Reduce the number of subscribers
   - Keep callbacks lightweight
   - Consider using a dedicated thread pool for heavy processing

### Debugging

Enable detailed logging to debug event system issues:

```python
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("core.event_system").setLevel(logging.DEBUG)
```

## Conclusion

The improved event system provides robust support for both synchronous and asynchronous event handling with built-in protections against common concurrency issues. By following these best practices, you can build reliable and efficient event-driven components in WiseFlow.

