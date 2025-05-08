# WiseFlow Plugin System

This document provides guidelines and documentation for developing plugins for the WiseFlow system.

## Table of Contents

1. [Introduction](#introduction)
2. [Plugin Types](#plugin-types)
3. [Creating a Plugin](#creating-a-plugin)
4. [Plugin Lifecycle](#plugin-lifecycle)
5. [Resource Management](#resource-management)
6. [Error Handling](#error-handling)
7. [Dependencies](#dependencies)
8. [Best Practices](#best-practices)

## Introduction

The WiseFlow plugin system allows you to extend the functionality of the application by creating custom plugins. Plugins can be used to add new data sources, processing capabilities, and analysis tools.

## Plugin Types

WiseFlow supports three types of plugins:

1. **Connector Plugins**: Used to connect to external data sources and fetch data.
2. **Processor Plugins**: Used to process and transform data.
3. **Analyzer Plugins**: Used to analyze data and extract insights.

## Creating a Plugin

To create a plugin, you need to create a Python class that inherits from one of the base plugin classes:

- `BasePlugin`: Base class for all plugins.
- `ConnectorPlugin`: Base class for connector plugins.
- `ProcessorPlugin`: Base class for processor plugins.
- `AnalyzerPlugin`: Base class for analyzer plugins.

### Example: Creating a Connector Plugin

```python
from core.plugins import ConnectorPlugin

class MyConnector(ConnectorPlugin):
    """My custom connector plugin."""
    
    name = "my_connector"
    description = "My custom connector plugin"
    version = "1.0.0"
    
    def __init__(self, config=None):
        """Initialize the connector."""
        super().__init__(config)
        # Initialize your connector-specific attributes here
    
    def initialize(self) -> bool:
        """Initialize the connector."""
        # Perform initialization tasks here
        self.initialized = True
        return True
    
    def connect(self) -> bool:
        """Connect to the data source."""
        # Connect to your data source here
        return True
    
    def fetch_data(self, query: str, **kwargs) -> dict:
        """Fetch data from the source."""
        # Fetch data from your data source here
        return {"data": "example data"}
    
    def disconnect(self) -> bool:
        """Disconnect from the data source."""
        # Disconnect from your data source here
        return True
```

### Example: Creating a Processor Plugin

```python
from core.plugins import ProcessorPlugin

class MyProcessor(ProcessorPlugin):
    """My custom processor plugin."""
    
    name = "my_processor"
    description = "My custom processor plugin"
    version = "1.0.0"
    
    def __init__(self, config=None):
        """Initialize the processor."""
        super().__init__(config)
        # Initialize your processor-specific attributes here
    
    def initialize(self) -> bool:
        """Initialize the processor."""
        # Perform initialization tasks here
        self.initialized = True
        return True
    
    def process(self, data, **kwargs) -> dict:
        """Process the input data."""
        # Process your data here
        return {"processed_data": data}
```

### Example: Creating an Analyzer Plugin

```python
from core.plugins import AnalyzerPlugin

class MyAnalyzer(AnalyzerPlugin):
    """My custom analyzer plugin."""
    
    name = "my_analyzer"
    description = "My custom analyzer plugin"
    version = "1.0.0"
    
    def __init__(self, config=None):
        """Initialize the analyzer."""
        super().__init__(config)
        # Initialize your analyzer-specific attributes here
    
    def initialize(self) -> bool:
        """Initialize the analyzer."""
        # Perform initialization tasks here
        self.initialized = True
        return True
    
    def analyze(self, data, **kwargs) -> dict:
        """Analyze the input data."""
        # Analyze your data here
        return {"analysis_results": data}
```

## Plugin Lifecycle

Plugins have a lifecycle that consists of the following stages:

1. **Loading**: The plugin class is loaded from a module.
2. **Registration**: The plugin class is registered with the plugin manager.
3. **Initialization**: The plugin is initialized with its configuration.
4. **Usage**: The plugin is used to perform its specific function.
5. **Shutdown**: The plugin is shut down and resources are released.

### Loading and Registration

Plugins are automatically loaded and registered when the plugin system is initialized. You don't need to manually register your plugin.

### Initialization

Plugins are initialized when they are first used or when the plugin system is initialized. The `initialize` method is called to perform initialization tasks.

```python
def initialize(self) -> bool:
    """Initialize the plugin."""
    # Perform initialization tasks here
    self.initialized = True
    return True
```

### Usage

Plugins are used by calling their specific methods:

- Connector plugins: `connect`, `fetch_data`, `disconnect`
- Processor plugins: `process`
- Analyzer plugins: `analyze`

### Shutdown

Plugins are shut down when the plugin system is shut down or when the plugin is explicitly shut down. The `shutdown` method is called to release resources.

```python
def shutdown(self) -> bool:
    """Shutdown the plugin."""
    # Release resources here
    self.initialized = False
    return True
```

## Resource Management

Plugins should properly manage their resources to prevent memory leaks and other issues. The `BasePlugin` class provides methods for registering and releasing resources:

```python
# Register a resource
self._register_resource("my_resource", resource_object)

# Register a shared resource
self._register_resource("shared_resource", shared_resource, shared=True)

# Release a resource
self._release_resource("my_resource")

# Release all resources
self._release_all_resources()
```

The plugin system also provides a resource monitor that can be used to track resource usage:

```python
from core.plugins.utils import get_resource_monitor

# Get the resource monitor
monitor = get_resource_monitor()

# Register a resource
resource_id = monitor.register_resource("my_plugin", "connection", connection_object)

# Unregister a resource
monitor.unregister_resource(resource_id)

# Get resource statistics
stats = monitor.get_resource_stats()
```

## Error Handling

Plugins should handle errors properly and provide meaningful error messages. The plugin system provides custom exception classes for different types of errors:

```python
from core.plugins.exceptions import (
    PluginError,
    PluginInitializationError,
    PluginValidationError,
    PluginInterfaceError,
    PluginLoadError,
    PluginDependencyError,
    PluginResourceError
)

# Raise a plugin error
raise PluginError("Something went wrong")

# Raise a specific error
raise PluginInitializationError("my_plugin", "Failed to initialize plugin")
```

## Dependencies

Plugins can depend on other plugins. Dependencies are automatically resolved when plugins are initialized. You can register dependencies using the `register_dependency` function:

```python
from core.plugins.loader import register_dependency

# Register a dependency
register_dependency("my_plugin", "dependency_plugin")
```

## Best Practices

Here are some best practices for developing plugins:

1. **Follow the Interface**: Implement all required methods for your plugin type.
2. **Handle Errors**: Properly handle errors and provide meaningful error messages.
3. **Manage Resources**: Properly register and release resources to prevent memory leaks.
4. **Document Your Plugin**: Provide clear documentation for your plugin.
5. **Test Your Plugin**: Write tests for your plugin to ensure it works correctly.
6. **Use Configuration**: Use configuration to make your plugin configurable.
7. **Validate Configuration**: Validate the configuration to ensure it's valid.
8. **Use Logging**: Use logging to provide information about your plugin's operation.
9. **Handle Dependencies**: Properly handle dependencies on other plugins.
10. **Clean Up**: Properly clean up resources when your plugin is shut down.

