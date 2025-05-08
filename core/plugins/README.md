# Wiseflow Plugin System

This document provides comprehensive documentation for the Wiseflow plugin system, including how to develop, install, and use plugins.

## Overview

The Wiseflow plugin system allows for extending the functionality of the application through plugins. There are three main types of plugins:

1. **Connector Plugins**: Connect to external data sources and fetch data
2. **Processor Plugins**: Process data from various sources
3. **Analyzer Plugins**: Analyze processed data to extract insights

## Plugin Lifecycle

Plugins in Wiseflow go through the following lifecycle states:

1. **UNLOADED**: The plugin class is not yet loaded
2. **LOADED**: The plugin class is loaded but not initialized
3. **INITIALIZED**: The plugin is initialized but not necessarily active
4. **ACTIVE**: The plugin is initialized and enabled
5. **DISABLED**: The plugin is initialized but disabled
6. **ERROR**: The plugin encountered an error during loading or initialization
7. **UNINSTALLED**: The plugin has been uninstalled

## Creating a Plugin

To create a plugin, you need to create a Python class that inherits from one of the base plugin classes:

### Base Plugin Structure

```python
from core.plugins import BasePlugin, PluginState

class MyPlugin(BasePlugin):
    name = "my_plugin"
    version = "1.0.0"
    description = "My custom plugin"
    
    def __init__(self, config=None):
        super().__init__(config)
        # Custom initialization code
    
    def initialize(self) -> bool:
        # Initialize the plugin
        # Return True if initialization was successful, False otherwise
        return True
    
    def shutdown(self) -> bool:
        # Clean up resources
        # Return True if shutdown was successful, False otherwise
        return True
    
    def validate_config(self) -> bool:
        # Validate the plugin configuration
        # Return True if configuration is valid, False otherwise
        return True
```

### Connector Plugin Example

```python
from core.plugins import ConnectorPlugin
from typing import Dict, Any

class MyConnector(ConnectorPlugin):
    name = "my_connector"
    version = "1.0.0"
    description = "My custom connector plugin"
    
    def initialize(self) -> bool:
        # Initialize the connector
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
from core.plugins import ProcessorPlugin
from typing import Any

class MyProcessor(ProcessorPlugin):
    name = "my_processor"
    version = "1.0.0"
    description = "My custom processor plugin"
    
    def initialize(self) -> bool:
        # Initialize the processor
        return True
    
    def process(self, data: Any, **kwargs) -> Any:
        # Process the input data
        return data
```

### Analyzer Plugin Example

```python
from core.plugins import AnalyzerPlugin
from typing import Dict, Any

class MyAnalyzer(AnalyzerPlugin):
    name = "my_analyzer"
    version = "1.0.0"
    description = "My custom analyzer plugin"
    
    def initialize(self) -> bool:
        # Initialize the analyzer
        return True
    
    def analyze(self, data: Any, **kwargs) -> Dict[str, Any]:
        # Analyze the input data
        return {"analysis": "sample analysis"}
```

## Plugin Metadata

Plugins can include metadata to provide additional information:

```python
from core.plugins import BasePlugin, PluginMetadata, PluginSecurityLevel

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
        return True
```

## Event Integration

Plugins can subscribe to system events:

```python
from core.plugins import BasePlugin
from core.event_system import EventType, Event

class MyPlugin(BasePlugin):
    name = "my_plugin"
    
    def initialize(self) -> bool:
        # Subscribe to system events
        self._subscribe_to_event(EventType.SYSTEM_STARTUP, self._handle_system_startup)
        self._subscribe_to_event(EventType.SYSTEM_SHUTDOWN, self._handle_system_shutdown)
        return True
    
    def _handle_system_startup(self, event: Event) -> None:
        # Handle system startup event
        print(f"System started: {event.data}")
    
    def _handle_system_shutdown(self, event: Event) -> None:
        # Handle system shutdown event
        print(f"System shutting down: {event.data}")
```

## Resource Management

Plugins should properly manage resources:

```python
from core.plugins import BasePlugin

class MyPlugin(BasePlugin):
    name = "my_plugin"
    
    def initialize(self) -> bool:
        # Open a file resource
        self.file = open("data.txt", "w")
        
        # Register the resource for automatic cleanup
        self._register_resource("file", self.file)
        
        return True
    
    def shutdown(self) -> bool:
        # Resources will be automatically cleaned up
        # But you can also manually clean up if needed
        return super().shutdown()
```

## Error Handling

Plugins should handle errors gracefully:

```python
from core.plugins import BasePlugin
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
```

## Plugin Configuration

Plugins can be configured through a configuration dictionary:

```python
from core.plugins import BasePlugin

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

## Plugin Installation

To install a plugin:

1. Place the plugin module in the `core/plugins` directory or a subdirectory
2. The plugin will be automatically discovered and loaded when the system starts
3. You can also manually load and initialize plugins using the plugin manager

## Plugin Security

The plugin system includes security measures:

1. **Module Restrictions**: Certain modules are restricted to prevent security issues
2. **File Hashing**: Plugin files are hashed to detect modifications
3. **Security Levels**: Plugins can have different security levels

## Version Compatibility

Plugins can specify version compatibility requirements:

1. **Minimum System Version**: The minimum system version required
2. **Maximum System Version**: The maximum system version supported
3. **Dependencies**: Other plugins that this plugin depends on

## Plugin Manager API

The plugin manager provides the following API:

- `load_plugin(plugin_name)`: Load a plugin by name
- `load_all_plugins()`: Load all available plugins
- `initialize_plugin(plugin_name, config)`: Initialize a plugin
- `initialize_all_plugins(configs)`: Initialize all loaded plugins
- `get_plugin(plugin_name)`: Get a plugin by name
- `get_all_plugins()`: Get all initialized plugins
- `get_plugins_by_type(plugin_type)`: Get plugins by type
- `shutdown_plugin(plugin_name)`: Shutdown a plugin
- `shutdown_all_plugins()`: Shutdown all initialized plugins
- `reload_plugin(plugin_name, config)`: Reload a plugin
- `enable_plugin(plugin_name)`: Enable a plugin
- `disable_plugin(plugin_name)`: Disable a plugin

## Best Practices

1. **Error Handling**: Always handle errors gracefully
2. **Resource Management**: Register resources for automatic cleanup
3. **Configuration Validation**: Validate plugin configuration
4. **Event Integration**: Use the event system for communication
5. **Security**: Be mindful of security implications
6. **Documentation**: Document your plugin thoroughly
7. **Testing**: Write tests for your plugin
8. **Version Compatibility**: Specify version compatibility requirements

