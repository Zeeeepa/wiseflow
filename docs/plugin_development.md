# WiseFlow Plugin Development Guide

This guide provides detailed information on how to develop plugins for WiseFlow. Plugins allow you to extend WiseFlow's functionality with custom connectors, processors, and analyzers.

## Table of Contents

- [Plugin System Overview](#plugin-system-overview)
- [Plugin Types](#plugin-types)
- [Creating a Plugin](#creating-a-plugin)
- [Plugin Registration](#plugin-registration)
- [Plugin Configuration](#plugin-configuration)
- [Testing Plugins](#testing-plugins)
- [Best Practices](#best-practices)
- [Examples](#examples)

## Plugin System Overview

WiseFlow's plugin system is designed to be modular and extensible. Plugins are Python classes that inherit from base classes provided by WiseFlow. The plugin system is managed by the `PluginManager` class, which handles plugin registration, loading, and lifecycle management.

### Plugin Lifecycle

1. **Registration**: Plugins are registered with the plugin manager
2. **Initialization**: Plugins are initialized with configuration parameters
3. **Execution**: Plugins are executed to perform their specific functions
4. **Cleanup**: Plugins are cleaned up when they are no longer needed

## Plugin Types

WiseFlow supports the following types of plugins:

### Connectors

Connectors are plugins that connect to data sources and collect data. They inherit from the `ConnectorBase` class and implement the `collect` method.

```python
from core.connectors import ConnectorBase, DataItem
from typing import List, Dict, Any, Optional

class CustomConnector(ConnectorBase):
    name = "custom_connector"
    description = "Custom data source connector"
    source_type = "custom"
    
    def initialize(self) -> bool:
        # Initialize the connector
        return True
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        # Collect data from the source
        # ...
        return data_items
    
    async def collect_with_retry(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        # Implement retry logic for more robust data collection
        # ...
        return await self.collect(params)
```

### Processors

Processors are plugins that process data collected by connectors. They inherit from the `ProcessorBase` class and implement the `process` method.

```python
from core.plugins.processors import ProcessorBase, ProcessedData
from core.connectors import DataItem
from typing import Dict, Any, Optional

class CustomProcessor(ProcessorBase):
    name = "custom_processor"
    description = "Custom content processor"
    content_types = ["text/plain", "text/html"]
    
    def process(self, data_item: DataItem, params: Dict[str, Any]) -> Optional[ProcessedData]:
        # Process the data item
        # ...
        return ProcessedData(
            processed_content=processed_content,
            metadata=metadata
        )
```

### Analyzers

Analyzers are plugins that analyze processed data to extract insights. They inherit from the `AnalyzerBase` class and implement the `analyze` method.

```python
from core.plugins.analyzers import AnalyzerBase, AnalysisResult
from typing import Dict, Any, List, Optional

class CustomAnalyzer(AnalyzerBase):
    name = "custom_analyzer"
    description = "Custom data analyzer"
    analysis_type = "custom"
    
    def analyze(self, data: List[Dict[str, Any]], params: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        # Analyze the data
        # ...
        return AnalysisResult(
            results=results,
            metadata=metadata
        )
```

## Creating a Plugin

To create a plugin, follow these steps:

1. Identify the type of plugin you want to create (connector, processor, or analyzer)
2. Create a new Python file in the appropriate directory:
   - Connectors: `core/plugins/connectors/`
   - Processors: `core/plugins/processors/`
   - Analyzers: `core/plugins/analyzers/`
3. Import the appropriate base class
4. Create a class that inherits from the base class
5. Implement the required methods
6. Add class attributes for plugin metadata

### Required Methods

#### Connectors

- `initialize()`: Initialize the connector
- `collect(params)`: Collect data from the source

#### Processors

- `process(data_item, params)`: Process a data item

#### Analyzers

- `analyze(data, params)`: Analyze data

### Plugin Metadata

All plugins should define the following class attributes:

- `name`: A unique name for the plugin
- `description`: A description of the plugin
- `version` (optional): The plugin version

Additionally, each plugin type has specific metadata:

#### Connectors

- `source_type`: The type of data source (e.g., "web", "github", "academic")

#### Processors

- `content_types`: A list of content types that the processor can handle (e.g., ["text/plain", "text/html"])

#### Analyzers

- `analysis_type`: The type of analysis performed (e.g., "entity", "trend", "pattern")

## Plugin Registration

Plugins are registered with the plugin manager when WiseFlow starts. There are two ways to register plugins:

### Automatic Registration

Plugins in the standard plugin directories are automatically discovered and registered by the plugin manager.

### Manual Registration

Plugins can also be registered manually using the `register_plugin` method of the `PluginManager` class:

```python
from core.plugins import PluginManager
from my_plugin import MyPlugin

plugin_manager = PluginManager()
plugin_manager.register_plugin(MyPlugin)
```

## Plugin Configuration

Plugins can be configured using configuration parameters. These parameters can be passed to the plugin during initialization or when the plugin is executed.

### Configuration During Initialization

```python
plugin = MyPlugin()
plugin.initialize(config={
    "param1": "value1",
    "param2": "value2"
})
```

### Configuration During Execution

```python
# For connectors
data_items = await connector.collect(params={
    "param1": "value1",
    "param2": "value2"
})

# For processors
processed_data = processor.process(data_item, params={
    "param1": "value1",
    "param2": "value2"
})

# For analyzers
analysis_result = analyzer.analyze(data, params={
    "param1": "value1",
    "param2": "value2"
})
```

## Testing Plugins

WiseFlow provides utilities for testing plugins. These utilities are located in the `tests` directory.

### Testing Connectors

```python
from tests.core.connectors import ConnectorTestCase

class TestMyConnector(ConnectorTestCase):
    connector_class = MyConnector
    
    def test_collect(self):
        # Test the collect method
        data_items = self.connector.collect(params={
            "param1": "value1",
            "param2": "value2"
        })
        self.assertIsNotNone(data_items)
        self.assertGreater(len(data_items), 0)
```

### Testing Processors

```python
from tests.core.processors import ProcessorTestCase
from core.connectors import DataItem

class TestMyProcessor(ProcessorTestCase):
    processor_class = MyProcessor
    
    def test_process(self):
        # Test the process method
        data_item = DataItem(
            content="Test content",
            content_type="text/plain",
            url="https://example.com",
            metadata={}
        )
        processed_data = self.processor.process(data_item, params={
            "param1": "value1",
            "param2": "value2"
        })
        self.assertIsNotNone(processed_data)
        self.assertIsNotNone(processed_data.processed_content)
```

### Testing Analyzers

```python
from tests.core.analyzers import AnalyzerTestCase

class TestMyAnalyzer(AnalyzerTestCase):
    analyzer_class = MyAnalyzer
    
    def test_analyze(self):
        # Test the analyze method
        data = [
            {"content": "Test content 1"},
            {"content": "Test content 2"}
        ]
        analysis_result = self.analyzer.analyze(data, params={
            "param1": "value1",
            "param2": "value2"
        })
        self.assertIsNotNone(analysis_result)
        self.assertIsNotNone(analysis_result.results)
```

## Best Practices

### Error Handling

Plugins should handle errors gracefully and provide meaningful error messages. Use try-except blocks to catch exceptions and log errors.

```python
import logging

logger = logging.getLogger(__name__)

class MyPlugin(ConnectorBase):
    # ...
    
    async def collect(self, params=None):
        try:
            # Collect data
            # ...
            return data_items
        except Exception as e:
            logger.error(f"Error collecting data: {e}")
            return []
```

### Logging

Plugins should use the logging module to log information, warnings, and errors. This helps with debugging and monitoring.

```python
import logging

logger = logging.getLogger(__name__)

class MyPlugin(ConnectorBase):
    # ...
    
    async def collect(self, params=None):
        logger.info(f"Collecting data with params: {params}")
        # ...
        logger.info(f"Collected {len(data_items)} data items")
        return data_items
```

### Documentation

Plugins should be well-documented with docstrings for all classes and methods. This helps users understand how to use the plugin.

```python
class MyPlugin(ConnectorBase):
    """
    My custom connector plugin.
    
    This plugin connects to a custom data source and collects data.
    """
    
    async def collect(self, params=None):
        """
        Collect data from the custom data source.
        
        Args:
            params: Optional parameters for data collection
                - url: The URL to collect data from
                - limit: The maximum number of items to collect
                
        Returns:
            A list of DataItem objects
        """
        # ...
        return data_items
```

### Type Hints

Plugins should use type hints to indicate the expected types of parameters and return values. This helps with static type checking and documentation.

```python
from typing import List, Dict, Any, Optional
from core.connectors import ConnectorBase, DataItem

class MyPlugin(ConnectorBase):
    # ...
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        # ...
        return data_items
```

## Examples

### Web Connector Example

```python
from core.connectors import ConnectorBase, DataItem
from core.utils.general_utils import isURL
from typing import List, Dict, Any, Optional
import aiohttp
import logging

logger = logging.getLogger(__name__)

class WebConnector(ConnectorBase):
    """
    Web connector for collecting data from web pages.
    
    This connector uses aiohttp to fetch web pages and extract content.
    """
    
    name = "web_connector"
    description = "Connector for web pages"
    source_type = "web"
    
    def initialize(self) -> bool:
        """
        Initialize the web connector.
        
        Returns:
            True if initialization is successful, False otherwise
        """
        logger.info("Initializing web connector")
        return True
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """
        Collect data from web pages.
        
        Args:
            params: Parameters for data collection
                - urls: List of URLs to collect data from
                - timeout: Timeout for HTTP requests (default: 60 seconds)
                
        Returns:
            A list of DataItem objects containing the web page content
        """
        if not params or "urls" not in params:
            logger.warning("No URLs provided for web connector")
            return []
        
        urls = params["urls"]
        timeout = params.get("timeout", 60)
        
        if not isinstance(urls, list):
            urls = [urls]
        
        data_items = []
        
        async with aiohttp.ClientSession() as session:
            for url in urls:
                if not isURL(url):
                    logger.warning(f"Invalid URL: {url}")
                    continue
                
                try:
                    async with session.get(url, timeout=timeout) as response:
                        if response.status == 200:
                            content = await response.text()
                            
                            # Create a DataItem
                            data_item = DataItem(
                                content=content,
                                content_type="text/html",
                                url=url,
                                metadata={
                                    "status_code": response.status,
                                    "headers": dict(response.headers),
                                    "title": self._extract_title(content)
                                }
                            )
                            
                            data_items.append(data_item)
                        else:
                            logger.warning(f"Failed to fetch URL {url}: {response.status}")
                except Exception as e:
                    logger.error(f"Error fetching URL {url}: {e}")
        
        logger.info(f"Collected {len(data_items)} data items from {len(urls)} URLs")
        return data_items
    
    def _extract_title(self, html_content: str) -> str:
        """
        Extract the title from HTML content.
        
        Args:
            html_content: HTML content
            
        Returns:
            The title of the web page, or an empty string if not found
        """
        import re
        
        title_match = re.search(r"<title>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
        if title_match:
            return title_match.group(1).strip()
        return ""
```

### Text Processor Example

```python
from core.plugins.processors import ProcessorBase, ProcessedData
from core.connectors import DataItem
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class TextProcessor(ProcessorBase):
    """
    Text processor for processing plain text content.
    
    This processor extracts information from plain text based on a focus point.
    """
    
    name = "text_processor"
    description = "Processor for plain text content"
    content_types = ["text/plain", "text/html"]
    
    def process(self, data_item: DataItem, params: Dict[str, Any]) -> Optional[ProcessedData]:
        """
        Process a text data item.
        
        Args:
            data_item: The data item to process
            params: Processing parameters
                - focus_point: The focus point for information extraction
                - explanation: Additional context for the focus point
                - prompts: List of prompts for the LLM
                
        Returns:
            A ProcessedData object containing the extracted information
        """
        if not data_item.content:
            logger.warning("Empty content in data item")
            return None
        
        focus_point = params.get("focus_point", "")
        explanation = params.get("explanation", "")
        prompts = params.get("prompts", [])
        
        if not focus_point:
            logger.warning("No focus point provided for text processor")
            return None
        
        try:
            # Extract information using LLM
            from core.agents.get_info import get_info
            
            infos = await get_info(
                [data_item.content],
                data_item.metadata.get("links", {}),
                prompts,
                data_item.metadata.get("author", ""),
                data_item.metadata.get("publish_date", ""),
                _logger=logger
            )
            
            # Create processed data
            return ProcessedData(
                processed_content=infos,
                metadata={
                    "focus_point": focus_point,
                    "explanation": explanation,
                    "url": data_item.url,
                    "content_type": data_item.content_type
                }
            )
        except Exception as e:
            logger.error(f"Error processing text data: {e}")
            return None
```

### Entity Analyzer Example

```python
from core.plugins.analyzers import AnalyzerBase, AnalysisResult
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class EntityAnalyzer(AnalyzerBase):
    """
    Entity analyzer for extracting entities from processed content.
    
    This analyzer identifies entities such as people, organizations, locations, etc.
    """
    
    name = "entity_analyzer"
    description = "Analyzer for entity extraction"
    analysis_type = "entity"
    
    def analyze(self, data: List[Dict[str, Any]], params: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Analyze processed content to extract entities.
        
        Args:
            data: List of processed content items
            params: Analysis parameters
                - entity_types: List of entity types to extract (default: ["person", "organization", "location"])
                - confidence_threshold: Minimum confidence score for entities (default: 0.7)
                
        Returns:
            An AnalysisResult object containing the extracted entities
        """
        if not data:
            logger.warning("No data provided for entity analyzer")
            return AnalysisResult(results=[], metadata={})
        
        entity_types = params.get("entity_types", ["person", "organization", "location"])
        confidence_threshold = params.get("confidence_threshold", 0.7)
        
        try:
            # Extract entities using NLP
            entities = []
            
            for item in data:
                content = item.get("content", "")
                if not content:
                    continue
                
                # Use NLP to extract entities
                item_entities = self._extract_entities(content, entity_types, confidence_threshold)
                
                # Add source information
                for entity in item_entities:
                    entity["source"] = item.get("url", "")
                    entity["source_title"] = item.get("url_title", "")
                
                entities.extend(item_entities)
            
            # Deduplicate entities
            unique_entities = self._deduplicate_entities(entities)
            
            logger.info(f"Extracted {len(unique_entities)} unique entities from {len(data)} content items")
            
            return AnalysisResult(
                results=unique_entities,
                metadata={
                    "entity_types": entity_types,
                    "confidence_threshold": confidence_threshold,
                    "total_entities": len(entities),
                    "unique_entities": len(unique_entities)
                }
            )
        except Exception as e:
            logger.error(f"Error analyzing entities: {e}")
            return AnalysisResult(results=[], metadata={"error": str(e)})
    
    def _extract_entities(self, content: str, entity_types: List[str], confidence_threshold: float) -> List[Dict[str, Any]]:
        """
        Extract entities from content using NLP.
        
        Args:
            content: The content to analyze
            entity_types: List of entity types to extract
            confidence_threshold: Minimum confidence score for entities
            
        Returns:
            A list of extracted entities
        """
        # This is a placeholder for actual NLP entity extraction
        # In a real implementation, you would use a library like spaCy or an LLM
        
        # Placeholder implementation
        entities = []
        
        # Add some dummy entities for demonstration
        if "person" in entity_types and "John Doe" in content:
            entities.append({
                "text": "John Doe",
                "type": "person",
                "confidence": 0.9
            })
        
        if "organization" in entity_types and "Acme Corp" in content:
            entities.append({
                "text": "Acme Corp",
                "type": "organization",
                "confidence": 0.85
            })
        
        if "location" in entity_types and "New York" in content:
            entities.append({
                "text": "New York",
                "type": "location",
                "confidence": 0.95
            })
        
        # Filter by confidence threshold
        return [entity for entity in entities if entity["confidence"] >= confidence_threshold]
    
    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate entities based on text and type.
        
        Args:
            entities: List of entities
            
        Returns:
            A list of deduplicated entities
        """
        unique_entities = {}
        
        for entity in entities:
            key = f"{entity['text']}|{entity['type']}"
            
            if key not in unique_entities or entity["confidence"] > unique_entities[key]["confidence"]:
                unique_entities[key] = entity
        
        return list(unique_entities.values())
```

These examples demonstrate how to create different types of plugins for WiseFlow. You can use them as a starting point for your own plugin development.

