# WiseFlow Plugin Development Guide

This guide provides comprehensive instructions for developing plugins for the WiseFlow platform.

## Table of Contents

1. [Introduction](#introduction)
2. [Plugin Types](#plugin-types)
3. [Plugin Lifecycle](#plugin-lifecycle)
4. [Creating a Basic Plugin](#creating-a-basic-plugin)
5. [Plugin Metadata](#plugin-metadata)
6. [Configuration Management](#configuration-management)
7. [Error Handling](#error-handling)
8. [Resource Management](#resource-management)
9. [Event Integration](#event-integration)
10. [Security Considerations](#security-considerations)
11. [Dependency Management](#dependency-management)
12. [Testing Plugins](#testing-plugins)
13. [Best Practices](#best-practices)
14. [Advanced Topics](#advanced-topics)
15. [Troubleshooting](#troubleshooting)

## Introduction

The WiseFlow plugin system allows developers to extend the platform's functionality through custom plugins. Plugins can add new data sources, processing capabilities, and analysis tools to the platform.

## Plugin Types

WiseFlow supports three main types of plugins:

1. **Connector Plugins**: Connect to external data sources and fetch data
   - Example: GitHub connector, YouTube connector
   - Base class: `ConnectorPlugin`

2. **Processor Plugins**: Process data from various sources
   - Example: Text processor, Image processor
   - Base class: `ProcessorPlugin`

3. **Analyzer Plugins**: Analyze processed data to extract insights
   - Example: Entity analyzer, Trend analyzer
   - Base class: `AnalyzerPlugin`

## Plugin Lifecycle

Plugins in WiseFlow go through the following lifecycle states:

1. **UNLOADED**: The plugin class is not yet loaded
2. **LOADED**: The plugin class is loaded but not initialized
3. **INITIALIZED**: The plugin is initialized but not necessarily active
4. **ACTIVE**: The plugin is initialized and enabled
5. **DISABLED**: The plugin is initialized but disabled
6. **ERROR**: The plugin encountered an error during loading or initialization
7. **UNINSTALLED**: The plugin has been uninstalled

## Creating a Basic Plugin

To create a basic plugin, you need to create a Python class that inherits from one of the base plugin classes.

### Basic Plugin Structure

```python
from core.plugins.base import BasePlugin

class MyPlugin(BasePlugin):
    name = "my_plugin"
    version = "1.0.0"
    description = "My custom plugin"
    
    def __init__(self, config=None):
        super().__init__(config)
        # Custom initialization code
    
    def initialize(self) -> bool:
        # Initialize the plugin
        self.initialized = True
        return True
    
    def shutdown(self) -> bool:
        # Clean up resources
        self.initialized = False
        return True
    
    def validate_config(self) -> bool:
        # Validate the plugin configuration
        return True
```

### Connector Plugin Example

```python
from core.plugins.base import ConnectorPlugin
from typing import Dict, Any

class MyConnector(ConnectorPlugin):
    name = "my_connector"
    version = "1.0.0"
    description = "My custom connector plugin"
    
    def initialize(self) -> bool:
        # Initialize the connector
        self.initialized = True
        return True
    
    def connect(self) -> bool:
        # Connect to the data source
        return True
    
    def fetch_data(self, query: str, **kwargs) -> Dict[str, Any]:
        # Fetch data from the source
        return {"data": "sample data"}
    
    def disconnect(self) -> bool:
        # Disconnect from the data source
        return True
```

### Processor Plugin Example

```python
from core.plugins.base import ProcessorPlugin
from typing import Any

class MyProcessor(ProcessorPlugin):
    name = "my_processor"
    version = "1.0.0"
    description = "My custom processor plugin"
    
    def initialize(self) -> bool:
        # Initialize the processor
        self.initialized = True
        return True
    
    def process(self, data: Any, **kwargs) -> Any:
        # Process the input data
        return data
```

### Analyzer Plugin Example

```python
from core.plugins.base import AnalyzerPlugin
from typing import Dict, Any

class MyAnalyzer(AnalyzerPlugin):
    name = "my_analyzer"
    version = "1.0.0"
    description = "My custom analyzer plugin"
    
    def initialize(self) -> bool:
        # Initialize the analyzer
        self.initialized = True
        return True
    
    def analyze(self, data: Any, **kwargs) -> Dict[str, Any]:
        # Analyze the input data
        return {"analysis": "sample analysis"}
```

## Plugin Metadata

Plugins can include metadata to provide additional information:

```python
from core.plugins.base import BasePlugin, PluginMetadata, PluginSecurityLevel

class MyPlugin(BasePlugin):
    name = "my_plugin"
    version = "1.0.0"
    description = "My custom plugin"
    
    def __init__(self, config=None):
        super().__init__(config)
        self.metadata = PluginMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
            author="Your Name",
            website="https://example.com",
            license="MIT",
            min_system_version="4.0.0",
            max_system_version="5.0.0",
            dependencies={"another_plugin": ">=1.0.0"},
            security_level=PluginSecurityLevel.MEDIUM
        )
    
    def initialize(self) -> bool:
        self.initialized = True
        return True
```

## Configuration Management

Plugins can be configured through a configuration dictionary:

```python
from core.plugins.base import BasePlugin

class MyPlugin(BasePlugin):
    name = "my_plugin"
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # Get configuration values with defaults
        self.api_key = self.config.get("api_key", "")
        self.timeout = self.config.get("timeout", 30)
    
    def validate_config(self) -> bool:
        # Validate required configuration
        if not self.api_key:
            return False
        return True
```

## Error Handling

Plugins should handle errors gracefully:

```python
from core.plugins.base import BasePlugin
from core.plugins.errors import PluginError, PluginInitError
from core.utils.error_handling import handle_exceptions

class MyPlugin(BasePlugin):
    name = "my_plugin"
    
    @handle_exceptions(
        error_types=[Exception],
        default_message="Failed to process data",
        log_error=True
    )
    def process_data(self, data):
        # Process data with automatic error handling
        return data
    
    def initialize(self) -> bool:
        try:
            # Initialization code
            if some_condition:
                raise PluginInitError(self.name, "Failed to initialize plugin")
            self.initialized = True
            return True
        except Exception as e:
            self.error = str(e)
            return False
```

## Resource Management

Plugins should properly manage resources:

```python
from core.plugins.base import BasePlugin

class MyPlugin(BasePlugin):
    name = "my_plugin"
    
    def initialize(self) -> bool:
        # Open a file resource
        self.file = open("data.txt", "w")
        
        # Register the resource for automatic cleanup
        self._register_resource("file", self.file)
        
        # Create a thread
        self.thread = threading.Thread(target=self._background_task)
        self._register_resource("thread", self.thread)
        self.thread.start()
        
        self.initialized = True
        return True
    
    def shutdown(self) -> bool:
        # Resources will be automatically cleaned up
        # But you can also manually clean up if needed
        if hasattr(self, "file") and self.file:
            self.file.close()
            self.file = None
        
        return super().shutdown()
```

## Event Integration

Plugins can subscribe to system events:

```python
from core.plugins.base import BasePlugin
from core.event_system import EventType, Event

class MyPlugin(BasePlugin):
    name = "my_plugin"
    
    def initialize(self) -> bool:
        # Subscribe to system events
        self._subscribe_to_event(EventType.SYSTEM_STARTUP, self._handle_system_startup)
        self._subscribe_to_event(EventType.SYSTEM_SHUTDOWN, self._handle_system_shutdown)
        
        self.initialized = True
        return True
    
    def _handle_system_startup(self, event: Event) -> None:
        # Handle system startup event
        print(f"System started: {event.data}")
    
    def _handle_system_shutdown(self, event: Event) -> None:
        # Handle system shutdown event
        print(f"System shutting down: {event.data}")
    
    def shutdown(self) -> bool:
        # Unsubscribe from all events
        self._unsubscribe_from_all_events()
        
        self.initialized = False
        return True
```

## Security Considerations

Plugins should follow security best practices:

1. **Avoid Dangerous Modules**: Don't import restricted modules like `subprocess`, `socket`, etc.
2. **Validate Input**: Always validate input data before processing
3. **Avoid Dangerous Functions**: Don't use `eval()`, `exec()`, or similar functions
4. **Handle Secrets Securely**: Don't hardcode API keys or passwords
5. **Respect Security Levels**: Use the appropriate security level for your plugin

```python
from core.plugins.base import BasePlugin, PluginSecurityLevel

class MyPlugin(BasePlugin):
    name = "my_plugin"
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # Set security level
        self.metadata.security_level = PluginSecurityLevel.HIGH
    
    def process_data(self, data):
        # Validate input
        if not isinstance(data, dict):
            raise ValueError("Input must be a dictionary")
        
        # Process data securely
        return data
```

## Dependency Management

Plugins can declare dependencies on other plugins:

```python
from core.plugins.base import BasePlugin, PluginMetadata

class MyPlugin(BasePlugin):
    name = "my_plugin"
    version = "1.0.0"
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # Declare dependencies
        self.metadata = PluginMetadata(
            name=self.name,
            version=self.version,
            dependencies={
                "text_processor": ">=1.0.0",
                "entity_analyzer": ">=2.0.0,<3.0.0"
            }
        )
    
    def initialize(self) -> bool:
        # Get dependent plugins
        from core.plugins.loader import get_plugin
        
        self.text_processor = get_plugin("text_processor")
        self.entity_analyzer = get_plugin("entity_analyzer")
        
        if not self.text_processor or not self.entity_analyzer:
            return False
        
        self.initialized = True
        return True
```

## Testing Plugins

Plugins should be thoroughly tested:

```python
import unittest
from core.plugins.base import BasePlugin

class TestMyPlugin(unittest.TestCase):
    def setUp(self):
        # Create plugin instance
        self.plugin = MyPlugin({"api_key": "test_key"})
    
    def tearDown(self):
        # Clean up
        if self.plugin.initialized:
            self.plugin.shutdown()
    
    def test_initialization(self):
        # Test initialization
        result = self.plugin.initialize()
        self.assertTrue(result)
        self.assertTrue(self.plugin.initialized)
    
    def test_process_data(self):
        # Test data processing
        self.plugin.initialize()
        result = self.plugin.process_data({"test": "data"})
        self.assertIsNotNone(result)
```

## Best Practices

1. **Error Handling**: Always handle errors gracefully
2. **Resource Management**: Register resources for automatic cleanup
3. **Configuration Validation**: Validate plugin configuration
4. **Event Integration**: Use the event system for communication
5. **Security**: Be mindful of security implications
6. **Documentation**: Document your plugin thoroughly
7. **Testing**: Write tests for your plugin
8. **Version Compatibility**: Specify version compatibility requirements
9. **Performance**: Optimize performance-critical code
10. **Isolation**: Ensure your plugin doesn't interfere with other plugins

## Advanced Topics

### Thread Safety

Ensure your plugin is thread-safe:

```python
import threading

class MyPlugin(BasePlugin):
    def __init__(self, config=None):
        super().__init__(config)
        self.lock = threading.RLock()
    
    def process_data(self, data):
        with self.lock:
            # Thread-safe processing
            return processed_data
```

### Caching

Implement caching for expensive operations:

```python
class MyConnector(ConnectorPlugin):
    def __init__(self, config=None):
        super().__init__(config)
        self.cache = {}
        self.cache_timeout = self.config.get("cache_timeout", 300)
    
    def fetch_data(self, query, **kwargs):
        # Check cache
        if query in self.cache and time.time() - self.cache[query]["timestamp"] < self.cache_timeout:
            return self.cache[query]["data"]
        
        # Fetch data
        data = self._fetch_from_source(query)
        
        # Update cache
        self.cache[query] = {
            "data": data,
            "timestamp": time.time()
        }
        
        return data
```

### Background Tasks

Implement background tasks for maintenance operations:

```python
import threading
import time

class MyPlugin(BasePlugin):
    def initialize(self):
        # Start background thread
        self.stop_background = threading.Event()
        self.background_thread = threading.Thread(target=self._background_task)
        self.background_thread.daemon = True
        self._register_resource("thread", self.background_thread)
        self.background_thread.start()
        
        self.initialized = True
        return True
    
    def _background_task(self):
        while not self.stop_background.is_set():
            try:
                # Perform maintenance operations
                self._clean_cache()
            except Exception as e:
                logger.error(f"Error in background task: {e}")
            
            # Sleep for a while
            self.stop_background.wait(60.0)
    
    def shutdown(self):
        # Stop background thread
        if hasattr(self, "stop_background"):
            self.stop_background.set()
        
        return super().shutdown()
```

## Troubleshooting

### Common Issues

1. **Plugin Not Loading**
   - Check for syntax errors in your plugin code
   - Ensure your plugin class inherits from the correct base class
   - Check for circular dependencies

2. **Initialization Failures**
   - Check your initialization code for errors
   - Ensure all required dependencies are available
   - Validate your configuration properly

3. **Resource Leaks**
   - Register all resources with `_register_resource`
   - Implement proper cleanup in `shutdown`
   - Use context managers for resources when possible

4. **Security Violations**
   - Avoid importing restricted modules
   - Don't use dangerous functions like `eval` or `exec`
   - Follow security best practices

### Debugging Tips

1. **Enable Debug Logging**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Check Plugin Status**
   ```python
   from core.plugins.loader import get_plugin
   plugin = get_plugin("my_plugin")
   print(plugin.get_status())
   ```

3. **Inspect Plugin Errors**
   ```python
   plugin = get_plugin("my_plugin")
   if plugin.error:
       print(f"Plugin error: {plugin.error}")
   ```

4. **Test in Isolation**
   - Create a simple test script that loads and initializes your plugin
   - Test each method individually
   - Use a debugger to step through the code

