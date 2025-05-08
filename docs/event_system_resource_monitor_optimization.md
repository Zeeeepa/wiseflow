# Event System and Resource Monitor Optimization

This document outlines the optimizations made to the event system and resource monitor components in the Wiseflow project to prevent runtime errors and improve performance.

## Event System Optimizations

### Memory Management Improvements

1. **Weak References for Callbacks**
   - Implemented `weakref.WeakKeyDictionary` to store callback sources
   - Prevents memory leaks when callbacks are not properly unsubscribed
   - Automatically cleans up references when objects are garbage collected

2. **Improved Unsubscribe Mechanism**
   - Enhanced `unsubscribe_by_source` to use the weak reference dictionary
   - More reliable cleanup of event subscriptions

### Asynchronous Event Handling

1. **Task-based Async Execution**
   - Implemented proper task creation and gathering for async callbacks
   - Prevents blocking the event loop during event publishing
   - Improved error handling for async callbacks

2. **Safe Callback Execution**
   - Added dedicated methods for safely calling callbacks with proper error handling
   - Separated sync and async callback handling logic
   - Consistent error handling across both synchronous and asynchronous contexts

### Error Handling and Resilience

1. **Improved Exception Handling**
   - Better isolation of exceptions in event subscribers
   - Prevents cascading failures when one subscriber fails
   - Configurable exception propagation

2. **Thread Safety Enhancements**
   - Improved locking mechanism to prevent race conditions
   - Better protection of shared data structures

## Resource Monitor Optimizations

### Performance Improvements

1. **Efficient Data Structures**
   - Replaced lists with `collections.deque` for history tracking
   - Fixed-size collections with O(1) append and pop operations
   - Reduced memory usage and improved performance

2. **Optimized Resource Checking**
   - Reduced CPU usage during resource checks
   - Implemented smarter sampling intervals
   - Added averaging to smooth out spikes and prevent false alarms

### Enhanced Monitoring Capabilities

1. **Consecutive Threshold Violations**
   - Added tracking of consecutive threshold violations
   - Prevents alert fatigue from transient spikes
   - Only triggers alerts after sustained resource pressure

2. **Expanded Resource Metrics**
   - Added more detailed resource information
   - Better history tracking with timestamps
   - Improved resource usage reporting

3. **Configurable Thresholds**
   - Added method to dynamically update thresholds
   - Allows runtime adjustment of monitoring sensitivity

### Thread Safety and Error Handling

1. **Improved Thread Safety**
   - Added proper locking for all shared data structures
   - Prevents race conditions during history updates and resource checks

2. **Enhanced Error Handling**
   - Better isolation of errors during resource checks
   - Prevents monitoring failures from affecting the entire system
   - Automatic recovery from transient errors

## System Initialization Improvements

1. **Resource Event Handling**
   - Added dedicated handler for resource events
   - Implements appropriate actions based on resource type and severity

2. **Improved Configuration**
   - Better configuration of resource monitor during initialization
   - More flexible threshold settings

## Performance Impact

These optimizations result in:

1. **Reduced Memory Usage**
   - Fewer memory leaks from unmanaged event subscriptions
   - More efficient data structures for history tracking

2. **Lower CPU Overhead**
   - More efficient event publishing
   - Optimized resource checking

3. **Improved Reliability**
   - Better error handling and recovery
   - Reduced chance of cascading failures

4. **Enhanced Monitoring**
   - More accurate resource usage tracking
   - Better alerting with fewer false positives

## Usage Examples

### Event System

```python
from core.event_system import EventType, Event, subscribe, publish_sync

# Subscribe to events with a source identifier
def handle_system_event(event):
    print(f"Received system event: {event}")

subscribe(EventType.SYSTEM_STARTUP, handle_system_event, source="my_component")

# Publish an event
event = Event(EventType.SYSTEM_STARTUP, {"version": "1.0.0"}, "system")
publish_sync(event)

# Later, unsubscribe all callbacks from the source
from core.event_system import unsubscribe_by_source
unsubscribe_by_source("my_component")
```

### Resource Monitor

```python
from core.resource_monitor import resource_monitor

# Get current resource usage
usage = resource_monitor.get_resource_usage()
print(f"CPU: {usage['cpu']['percent']}%, Memory: {usage['memory']['percent']}%")

# Get resource history
history = resource_monitor.get_resource_usage_history(limit=10)
print(f"CPU history: {history['cpu']}")

# Update thresholds
resource_monitor.set_thresholds(
    cpu_threshold=85.0,
    memory_threshold=80.0,
    disk_threshold=90.0,
    warning_threshold_factor=0.8
)
```

