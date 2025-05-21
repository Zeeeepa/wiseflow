# WiseFlow Plugin System

## Overview

The WiseFlow plugin system allows you to extend the functionality of WiseFlow by adding new data sources, processing capabilities, and analysis methods. This document provides a comprehensive guide to understanding, using, and developing plugins for WiseFlow.

## Prerequisites

Before working with the WiseFlow plugin system, you should have:

- Basic understanding of Python programming
- Familiarity with WiseFlow core concepts
- WiseFlow installed and configured

## Plugin Types

WiseFlow supports three main types of plugins:

### Connector Plugins

Connector plugins allow WiseFlow to connect to and fetch data from external sources. Examples include:

- Web connectors for crawling websites
- API connectors for accessing external APIs
- Database connectors for querying databases
- File system connectors for accessing local files

### Processor Plugins

Processor plugins process and transform data fetched by connectors. Examples include:

- Text processors for cleaning and normalizing text
- Image processors for analyzing images
- Audio processors for transcribing audio
- Video processors for extracting information from videos

### Analyzer Plugins

Analyzer plugins analyze processed data to extract insights. Examples include:

- Entity analyzers for identifying entities in text
- Sentiment analyzers for determining sentiment
- Topic analyzers for identifying topics
- Trend analyzers for detecting trends over time

## Plugin Lifecycle

Plugins in WiseFlow go through the following lifecycle states:

1. **UNLOADED**: The plugin class is not yet loaded
2. **LOADED**: The plugin class is loaded but not initialized
3. **INITIALIZED**: The plugin is initialized but not necessarily active
4. **ACTIVE**: The plugin is initialized and enabled
5. **DISABLED**: The plugin is initialized but disabled
6. **ERROR**: The plugin encountered an error during loading or initialization
7. **UNINSTALLED**: The plugin has been uninstalled

## Using Plugins

### Installing Plugins

To install a plugin:

1. Place the plugin module in the appropriate directory:
   - Connector plugins: `core/plugins/connectors/`
   - Processor plugins: `core/plugins/processors/`
   - Analyzer plugins: `core/plugins/analyzers/`

2. Restart WiseFlow or reload the plugin system:

```python
from core.plugins import get_plugin_manager

# Get the plugin manager
plugin_manager = get_plugin_manager()

# Reload plugins
plugin_manager.load_all_plugins()
```

### Configuring Plugins

Plugins are configured through configuration dictionaries. The configuration options depend on the specific plugin.

Example configuration for a web connector plugin:

```python
config = {
    "url": "https://example.com",
    "depth": 2,
    "follow_links": True,
    "user_agent": "WiseFlow/1.0",
    "timeout": 30
}

# Configure the plugin
plugin_manager.initialize_plugin("web_connector", config)
```

### Using Plugins in WiseFlow

Once installed and configured, plugins can be used in WiseFlow:

1. **Connector Plugins**: Used when configuring data sources for focus points
2. **Processor Plugins**: Used in the data processing pipeline
3. **Analyzer Plugins**: Used when analyzing data for insights

Example of using a connector plugin:

```python
from core.plugins import get_plugin_manager

# Get the plugin manager
plugin_manager = get_plugin_manager()

# Get the connector plugin
connector = plugin_manager.get_plugin("web_connector")

# Connect to the data source
connector.connect()

# Fetch data
data = connector.fetch_data("query")

# Disconnect
connector.disconnect()
```

## Developing Plugins

### Plugin Base Classes

When developing a plugin, you should inherit from one of the base plugin classes:

- `BasePlugin`: The base class for all plugins
- `ConnectorPlugin`: The base class for connector plugins
- `ProcessorPlugin`: The base class for processor plugins
- `AnalyzerPlugin`: The base class for analyzer plugins

### Plugin Structure

A basic plugin structure looks like this:

```python
from core.plugins import BasePlugin

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

### Plugin Metadata

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
```

### Event Integration

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

### Resource Management

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

### Error Handling

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

## Best Practices

1. **Error Handling**: Always handle errors gracefully
2. **Resource Management**: Register resources for automatic cleanup
3. **Configuration Validation**: Validate plugin configuration
4. **Event Integration**: Use the event system for communication
5. **Security**: Be mindful of security implications
6. **Documentation**: Document your plugin thoroughly
7. **Testing**: Write tests for your plugin
8. **Version Compatibility**: Specify version compatibility requirements

## Troubleshooting

### Common Issues

**Problem**: Plugin fails to load

**Solution**: Check that the plugin class is properly defined and that the module can be imported.

**Problem**: Plugin initialization fails

**Solution**: Check the plugin's `initialize` method and ensure all dependencies are available.

**Problem**: Plugin configuration is invalid

**Solution**: Check the plugin's `validate_config` method and ensure the configuration meets the requirements.

## Related Topics

- [Plugin Manager API](../dev-guide/plugins/plugin-manager.md)
- [Event System](../dev-guide/architecture/event-system.md)
- [Error Handling](../dev-guide/architecture/error-handling.md)
- [Resource Management](../dev-guide/architecture/resource-management.md)

## Version Information

This documentation applies to WiseFlow version 3.9 and later.

