# WiseFlow Plugin System

The WiseFlow Plugin System provides a flexible and extensible way to add new functionality to the WiseFlow platform. This document explains how to use and develop plugins for WiseFlow.

## Overview

The plugin system allows you to:

- Add new data processors for different types of content
- Add new analyzers for extracting insights from processed data
- Configure plugins through a centralized configuration system
- Dynamically load and reload plugins at runtime

## Plugin Types

WiseFlow supports the following types of plugins:

1. **Processors**: Transform raw data into structured, processed data
2. **Analyzers**: Extract insights and patterns from processed data

## Using Plugins

### Loading Plugins

To load and use plugins in your code:

```python
from core.plugins.loader import load_all_plugins, get_processor, get_analyzer

# Load all available plugins
plugins = load_all_plugins()

# Get a specific processor
text_processor = get_processor("text_processor")

# Get a specific analyzer
entity_analyzer = get_analyzer("entity_analyzer")

# Get all processors
all_processors = get_all_processors()

# Get all analyzers
all_analyzers = get_all_analyzers()
```

### Using Processors

Processors transform raw data into structured, processed data:

```python
from core.connectors import DataItem

# Create a data item
data_item = DataItem(
    source_id="example-1",
    content="Example content",
    metadata={"author": "Example Author"},
    url="https://example.com/article1",
    content_type="text"
)

# Process the data
processed_data = text_processor.process(
    data_item,
    params={
        "focus_point": "AI language models",
        "explanation": "Information about AI language models",
        "prompts": [
            "System prompt",
            "User prompt",
            "Model name"
        ]
    }
)
```

### Using Analyzers

Analyzers extract insights from processed data:

```python
# Analyze the processed data
analysis_result = entity_analyzer.analyze(processed_data)

# Access the analysis content
entities = analysis_result.analysis_content["entities"]
relationships = analysis_result.analysis_content["relationships"]
```

## Developing Plugins

### Creating a Processor Plugin

To create a new processor plugin:

1. Create a new Python file in the `core/plugins/processors` directory
2. Define a class that inherits from `ProcessorBase`
3. Implement the required methods

Example:

```python
from core.plugins.processors import ProcessorBase, ProcessedData
from core.connectors import DataItem

class MyProcessor(ProcessorBase):
    """Custom processor for specific data."""
    
    name: str = "my_processor"
    description: str = "Custom processor for specific data"
    processor_type: str = "custom"
    
    def __init__(self, config=None):
        super().__init__(config)
        # Initialize any resources
        
    def process(self, data_item: DataItem, params=None) -> ProcessedData:
        # Process the data item
        processed_content = self._process_data(data_item.content)
        
        # Return processed data
        return ProcessedData(
            original_item=data_item,
            processed_content=processed_content,
            metadata={"processor": self.name}
        )
        
    def initialize(self) -> bool:
        # Perform any necessary initialization
        return True
        
    def _process_data(self, content):
        # Custom processing logic
        return content
```

### Creating an Analyzer Plugin

To create a new analyzer plugin:

1. Create a new Python file in the `core/plugins/analyzers` directory
2. Define a class that inherits from `AnalyzerBase`
3. Implement the required methods

Example:

```python
from core.plugins.analyzers import AnalyzerBase, AnalysisResult
from core.plugins.processors import ProcessedData

class MyAnalyzer(AnalyzerBase):
    """Custom analyzer for specific insights."""
    
    name: str = "my_analyzer"
    description: str = "Custom analyzer for specific insights"
    analyzer_type: str = "custom"
    
    def __init__(self, config=None):
        super().__init__(config)
        # Initialize any resources
        
    def analyze(self, processed_data: ProcessedData, params=None) -> AnalysisResult:
        # Analyze the processed data
        analysis_content = self._analyze_data(processed_data.processed_content)
        
        # Return analysis result
        return AnalysisResult(
            processed_data=processed_data,
            analysis_content=analysis_content,
            metadata={"analyzer": self.name}
        )
        
    def initialize(self) -> bool:
        # Perform any necessary initialization
        return True
        
    def _analyze_data(self, content):
        # Custom analysis logic
        return {"insights": []}
```

## Plugin Configuration

Plugins can be configured through the `config.json` file in the `core/plugins` directory:

```json
{
  "my_processor": {
    "option1": "value1",
    "option2": 42
  },
  "my_analyzer": {
    "model": "gpt-3.5-turbo",
    "max_tokens": 1000
  }
}
```

Access configuration in your plugin:

```python
def __init__(self, config=None):
    super().__init__(config)
    self.option1 = self.config.get("option1", "default")
    self.option2 = self.config.get("option2", 0)
```

## Plugin Discovery

The plugin system automatically discovers plugins in the following locations:

- `core/plugins/*.py`: General plugins
- `core/plugins/processors/*.py`: Processor plugins
- `core/plugins/analyzers/*.py`: Analyzer plugins

Plugins are loaded based on their directory structure, so placing a plugin in the correct directory automatically registers it with the appropriate type.

## Best Practices

1. **Descriptive Names**: Use clear, descriptive names for your plugins
2. **Error Handling**: Implement robust error handling in your plugins
3. **Documentation**: Document your plugin's purpose, parameters, and behavior
4. **Configuration**: Make your plugin configurable through the configuration system
5. **Testing**: Write tests for your plugins to ensure they work correctly

## Example

See the `examples/plugin_example.py` file for a complete example of using the plugin system.
