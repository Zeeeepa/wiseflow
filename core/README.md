# WiseFlow Core Module

This directory contains the core functionality of WiseFlow, an LLM-based information extraction and analysis system.

## Code Organization

The core module is organized into the following components:

### Configuration

- `config.py`: Central configuration module that manages all environment variables and settings.

### LLM Integration

- `llms/`: Contains wrappers for different LLM providers.
  - `litellm_wrapper.py`: Wrapper for the LiteLLM library.
  - `openai_wrapper.py`: Wrapper for the OpenAI API.
  - `advanced/`: Advanced LLM integration with specialized prompting strategies.

### Data Collection

- `crawl4ai/`: Web crawling and content extraction.
- `connectors/`: Connectors for different data sources (web, GitHub, academic, etc.).
- `scrapers/`: Custom scrapers for specific websites.

### Data Processing

- `analysis/`: Data analysis modules.
  - `data_mining.py`: Extract insights from collected information.
  - `entity_extraction.py`: Extract named entities from text.
  - `entity_linking.py`: Link extracted entities to knowledge bases.
  - `multimodal_analysis.py`: Process multimodal content (text + images).
  - `pattern_recognition.py`: Identify patterns in data.
  - `trend_analysis.py`: Analyze trends over time.

### Knowledge Management

- `knowledge/`: Knowledge representation and management.
  - `graph.py`: Knowledge graph construction and querying.
- `references/`: Reference management.
  - `reference_extractor.py`: Extract references from text.
  - `reference_indexer.py`: Index references for retrieval.
  - `reference_linker.py`: Link references to content.

### Task Management

- `task/`: Task configuration and management.
- `task_manager.py`: Manage and schedule tasks.
- `thread_pool_manager.py`: Manage thread pools for concurrent execution.

### Plugin System

- `plugins/`: Plugin system for extending functionality.
  - `base.py`: Base classes for plugins.
  - `loader.py`: Plugin loading and management.
  - `analyzers/`: Plugins for data analysis.
  - `connectors/`: Plugins for data collection.
  - `processors/`: Plugins for data processing.

### Agents

- `agents/`: Autonomous agents for specific tasks.
  - `get_info.py`: Agent for extracting information.
  - `insights.py`: Agent for generating insights.

### Export

- `export/`: Export functionality for different formats.
  - `formats/`: Different export formats (CSV, JSON, PDF, etc.).
  - `webhook.py`: Webhook integration for exporting data.

### Utilities

- `utils/`: Utility functions and classes.
  - `general_utils.py`: General utility functions.
  - `pb_api.py`: PocketBase API client.

## Usage

The core module is designed to be used as a library by other components of WiseFlow, such as the API server and dashboard. It can also be used directly for scripting and automation.

### Environment Variables

The core module uses environment variables for configuration. These can be set in a `.env` file in the core directory. See `config.py` for a list of available configuration options.

### Example

```python
from core.config import get_config
from core.llms.litellm_wrapper import LiteLLMWrapper
from core.general_process import main_process

# Get configuration
config = get_config()

# Initialize LLM wrapper
llm = LiteLLMWrapper(default_model=config["PRIMARY_MODEL"])

# Process a focus point
await main_process(focus, sites)
```

## Development

When developing new features or fixing bugs, please follow these guidelines:

1. Use the centralized configuration in `config.py` instead of accessing environment variables directly.
2. Follow the plugin architecture for extending functionality.
3. Use async/await for I/O-bound operations.
4. Add appropriate error handling and logging.
5. Write tests for new functionality.

