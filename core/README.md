# WiseFlow Core Module

This directory contains the core functionality of the WiseFlow system, which is designed to extract and process information from various sources using LLMs.

## Key Components

- **Task Management**: A unified task management system that supports both synchronous and asynchronous execution of tasks with dependency management.
- **Event System**: A publish-subscribe event system for communication between components.
- **Resource Monitoring**: Monitors system resources like CPU, memory, and disk usage.
- **Connection Pool**: Manages connections to external services with support for rate limiting and circuit breaking.
- **Cache Manager**: Provides caching for expensive operations with different backends and invalidation strategies.
- **Dependency Injection**: A container for managing service dependencies throughout the application.
- **Error Handling**: Centralized error handling and logging.
- **Configuration**: Centralized configuration management.

## Architecture

The core module follows a layered architecture:

1. **Domain Layer**: Contains the business logic and domain models.
2. **Application Layer**: Orchestrates the domain layer and provides services to the API layer.
3. **Infrastructure Layer**: Provides implementations for external services and repositories.
4. **API Layer**: Exposes the application functionality through REST APIs.

## Task Management

The task management system supports:

- Task dependencies
- Task priorities
- Task cancellation
- Task retries
- Task timeouts
- Different execution strategies (sequential, thread pool, async)

## Event System

The event system supports:

- Event publishing and subscribing
- Event history
- Event filtering
- Asynchronous event handling

## Resource Monitoring

The resource monitor:

- Monitors CPU, memory, and disk usage
- Triggers alerts when thresholds are exceeded
- Provides resource usage history
- Calculates resource trends

## Connection Pool

The connection pool:

- Manages connections to external services
- Implements rate limiting
- Implements circuit breaking
- Provides fallback mechanisms
- Monitors service health

## Cache Manager

The cache manager supports:

- Different cache backends (memory, disk, Redis)
- Different invalidation strategies (TTL, LRU, LFU)
- Namespace-based cache organization
- Cache statistics

## Dependency Injection

The DI container supports:

- Service registration
- Service resolution
- Singleton, transient, and scoped lifetimes
- Factory functions
- Scoped service disposal

## Usage

The core module is designed to be used by other modules in the WiseFlow system. It provides a set of services and utilities that can be used to build higher-level functionality.

Example:

```python
from core.imports import (
    config,
    wiseflow_logger,
    TaskManager,
    Event,
    EventType,
    publish
)

# Create a task manager
task_manager = TaskManager()

# Register a task
task_id = task_manager.register_task(
    name="My Task",
    func=my_function,
    args=(arg1, arg2),
    kwargs={"key": "value"},
    priority=TaskPriority.HIGH
)

# Execute the task
result = await task_manager.execute_task(task_id, wait=True)

# Publish an event
event = Event(EventType.CUSTOM, {"key": "value"}, "my_component")
await publish(event)
```

