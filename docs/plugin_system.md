# Wiseflow Plugin System

The Wiseflow plugin system provides a flexible and extensible framework for adding new functionality to the application. This document describes how the plugin system works and how to create new plugins.

## Overview

The plugin system consists of the following components:

- **Base Plugin Classes**: Abstract base classes that define the interface for different types of plugins
- **Plugin Manager**: A class that handles plugin discovery, loading, initialization, and management
- **Plugin Registry**: A registry that keeps track of available plugins by type
- **Plugin Loader**: Utility functions for loading and accessing plugins

## Plugin Types

Wiseflow supports the following types of plugins:

1. **Connector Plugins**: Plugins that connect to external data sources and fetch data
2. **Processor Plugins**: Plugins that process and transform data
3. **Analyzer Plugins**: Plugins that analyze data and extract insights

## Plugin Lifecycle

Plugins go through the following lifecycle:

1. **Discovery**: The plugin manager discovers available plugins in the plugin directory
2. **Loading**: The plugin manager loads plugin classes from discovered modules
3. **Registration**: Plugin classes are registered in the plugin registry by type
4. **Initialization**: Plugin instances are created and initialized with configuration
5. **Usage**: Plugins are used by the application to perform tasks
6. **Shutdown**: Plugins are shut down when no longer needed

## Creating a New Plugin

To create a new plugin, follow these steps:

1. Choose the appropriate base class for your plugin:
   - `ConnectorPlugin` for data source connectors
   - `ProcessorPlugin` for data processors
   - `AnalyzerPlugin` for data analyzers

2. Create a new Python file in the appropriate directory:
   - `core/plugins/connectors/` for connector plugins
   - `core/plugins/processors/` for processor plugins
   - `core/plugins/analyzers/` for analyzer plugins

3. Implement the required methods for your plugin type:
   - For connector plugins: `connect()`, `fetch_data()`, `disconnect()`
   - For processor plugins: `process()`
   - For analyzer plugins: `analyze()`

4. Register your plugin in the appropriate `__init__.py` file

### Example: Creating a Connector Plugin

```python
from core.plugins.base import ConnectorPlugin

class MyConnector(ConnectorPlugin):
    """Connector for my data source."""
    
    name = "my_connector"
    description = "Fetches data from my data source"
    version = "1.0.0"
    
    def __init__(self, config=None):
        super().__init__(config)
        # Initialize your connector
        
    def initialize(self) -> bool:
        # Initialize your connector
        self.initialized = True
        return True
        
    def connect(self) -> bool:
        # Connect to your data source
        return True
        
    def fetch_data(self, query, **kwargs) -> dict:
        # Fetch data from your data source
        return {"data": "your data"}
        
    def disconnect(self) -> bool:
        # Disconnect from your data source
        return True
```

### Example: Creating a Processor Plugin

```python
from core.plugins.base import ProcessorPlugin

class MyProcessor(ProcessorPlugin):
    """Processor for my data."""
    
    name = "my_processor"
    description = "Processes my data"
    version = "1.0.0"
    
    def __init__(self, config=None):
        super().__init__(config)
        # Initialize your processor
        
    def initialize(self) -> bool:
        # Initialize your processor
        self.initialized = True
        return True
        
    def process(self, data, **kwargs) -> dict:
        # Process your data
        return {"processed_data": "your processed data"}
```

### Example: Creating an Analyzer Plugin

```python
from core.plugins.base import AnalyzerPlugin

class MyAnalyzer(AnalyzerPlugin):
    """Analyzer for my data."""
    
    name = "my_analyzer"
    description = "Analyzes my data"
    version = "1.0.0"
    
    def __init__(self, config=None):
        super().__init__(config)
        # Initialize your analyzer
        
    def initialize(self) -> bool:
        # Initialize your analyzer
        self.initialized = True
        return True
        
    def analyze(self, data, **kwargs) -> dict:
        # Analyze your data
        return {"analysis_results": "your analysis results"}
```

## Registering a Plugin

To register your plugin, add it to the appropriate `__init__.py` file:

```python
# For connector plugins (in core/plugins/connectors/__init__.py)
from core.plugins.base import ConnectorPlugin, plugin_manager
from core.plugins.connectors.my_connector import MyConnector

# Register the connector
plugin_manager.register_connector('my_connector', MyConnector)

# For processor plugins (in core/plugins/processors/__init__.py)
from core.plugins.base import ProcessorPlugin, plugin_manager
from core.plugins.processors.my_processor import MyProcessor

# Register the processor
plugin_manager.register_processor('my_processor', MyProcessor)

# For analyzer plugins (in core/plugins/analyzers/__init__.py)
from core.plugins.base import AnalyzerPlugin, plugin_manager
from core.plugins.analyzers.my_analyzer import MyAnalyzer

# Register the analyzer
plugin_manager.register_analyzer('my_analyzer', MyAnalyzer)
```

## Plugin Configuration

Plugins can be configured using a configuration dictionary. The configuration can be provided in the following ways:

1. **In the plugin configuration file**: `core/plugins/config.json`
2. **When initializing the plugin**: `plugin_manager.initialize_plugin('my_plugin', config)`
3. **When using the plugin**: `plugin.process(data, config_param=value)`

### Example Configuration

```json
{
  "my_connector": {
    "api_key": "your_api_key",
    "base_url": "https://api.example.com",
    "timeout": 30
  },
  "my_processor": {
    "max_items": 100,
    "normalize": true
  },
  "my_analyzer": {
    "threshold": 0.5,
    "max_results": 10
  }
}
```

## Using Plugins

To use plugins in your code, you can use the plugin manager or the plugin loader:

```python
from core.plugins import plugin_manager
from core.plugins.loader import get_plugin, get_processor, get_analyzer, get_connector

# Using the plugin manager
connector = plugin_manager.get_plugin('my_connector')
result = connector.fetch_data('my_query')

# Using the plugin loader
processor = get_processor('my_processor')
processed_data = processor.process(result)

analyzer = get_analyzer('my_analyzer')
analysis = analyzer.analyze(processed_data)
```

## Plugin Dependencies

If your plugin depends on other plugins, you can specify the dependencies in your plugin class:

```python
class MyPlugin(ProcessorPlugin):
    name = "my_plugin"
    description = "My plugin with dependencies"
    version = "1.0.0"
    dependencies = ["other_plugin"]
    
    def initialize(self) -> bool:
        # Check if dependencies are available
        from core.plugins import plugin_manager
        for dep in self.dependencies:
            if not plugin_manager.get_plugin(dep):
                logger.error(f"Dependency {dep} not found")
                return False
        
        self.initialized = True
        return True
```

## Error Handling

Plugins should handle errors gracefully and provide meaningful error messages. Use the logging module to log errors and warnings:

```python
import logging

logger = logging.getLogger(__name__)

class MyPlugin(ProcessorPlugin):
    # ...
    
    def process(self, data, **kwargs):
        try:
            # Process data
            return result
        except Exception as e:
            logger.error(f"Error processing data: {str(e)}")
            return {"error": str(e)}
```

## Testing Plugins

To test your plugins, you can create unit tests that initialize and use your plugins:

```python
import unittest
from core.plugins.base import plugin_manager

class MyPluginTest(unittest.TestCase):
    def setUp(self):
        self.plugin = plugin_manager.get_plugin('my_plugin')
        if not self.plugin:
            self.plugin = MyPlugin()
            self.plugin.initialize()
    
    def test_process(self):
        result = self.plugin.process({"test": "data"})
        self.assertIn("processed_data", result)
```

## Troubleshooting

If you encounter issues with your plugins, check the following:

1. **Plugin Discovery**: Make sure your plugin is in the correct directory and is a valid Python module
2. **Plugin Registration**: Make sure your plugin is registered in the appropriate `__init__.py` file
3. **Plugin Initialization**: Make sure your plugin's `initialize()` method returns `True` and sets `self.initialized = True`
4. **Plugin Usage**: Make sure you're using the correct plugin type and methods
5. **Plugin Configuration**: Make sure your plugin's configuration is valid and complete
6. **Plugin Dependencies**: Make sure all dependencies are available and initialized

## Best Practices

1. **Keep plugins focused**: Each plugin should do one thing well
2. **Handle errors gracefully**: Catch exceptions and provide meaningful error messages
3. **Document your plugins**: Provide clear documentation for your plugins
4. **Test your plugins**: Write unit tests for your plugins
5. **Use configuration**: Make your plugins configurable
6. **Follow naming conventions**: Use consistent naming for your plugins
7. **Use type hints**: Use type hints to make your code more readable and maintainable

