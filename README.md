# WiseFlow

Use LLMs to dig out what you care about from massive amounts of information and a variety of sources daily.

## Overview

WiseFlow is a powerful information extraction and analysis system that leverages Large Language Models (LLMs) to process and extract insights from various data sources. It helps users focus on what matters most by filtering through massive amounts of information.

## Key Features

- **Information Extraction**: Extract relevant information from various content types (text, HTML, markdown, code, academic papers, videos)
- **Multi-step Reasoning**: Perform complex reasoning on extracted information
- **Cross-source Analysis**: Analyze information across multiple sources to identify patterns and connections
- **Knowledge Graph Construction**: Build and maintain knowledge graphs from extracted information
- **Reference Support**: Provide contextual understanding with reference materials
- **Plugin System**: Extend functionality with custom plugins for connectors, processors, and analyzers
- **API Integration**: Integrate with other systems through a RESTful API
- **Dashboard**: Visualize insights and manage focus points through a web dashboard

## System Architecture

WiseFlow is organized into several core components:

### Core Components

- **Imports Module** (`core/imports.py`): Centralizes imports to avoid circular dependencies
- **Configuration Module** (`core/config.py`): Manages configuration settings
- **Initialization Module** (`core/initialize.py`): Handles system initialization and shutdown
- **Task Management** (`core/task_manager.py`, `core/thread_pool_manager.py`): Manages concurrent task execution
- **Resource Monitoring** (`core/resource_monitor.py`): Monitors system resources
- **LLM Integration** (`core/llms/`): Integrates with language models
- **Plugin System** (`core/plugins/`): Provides extensibility through plugins
- **Connectors** (`core/connectors/`): Connects to various data sources
- **Analysis** (`core/analysis/`): Analyzes extracted information
- **Knowledge Graph** (`core/knowledge/`): Builds and maintains knowledge graphs
- **References** (`core/references/`): Manages reference materials
- **Export** (`core/export/`): Exports data in various formats

### API Server

The API server (`api_server.py`) provides a RESTful API for integrating with other systems. It includes endpoints for:

- Content processing
- Batch processing
- Webhook management
- Integration with other systems

### Dashboard

The dashboard (`dashboard/`) provides a web interface for:

- Managing focus points
- Visualizing insights
- Configuring data sources
- Monitoring system status

## Code Organization

The codebase is organized as follows:

```
wiseflow/
├── api_server.py                # API server
├── core/                        # Core components
│   ├── agents/                  # Agent implementations
│   ├── analysis/                # Analysis modules
│   ├── api/                     # API client
│   ├── config.py                # Configuration management
│   ├── connectors/              # Data source connectors
│   ├── crawl4ai/                # Web crawling functionality
│   ├── export/                  # Export functionality
│   ├── general_process.py       # Main processing logic
│   ├── imports.py               # Centralized imports
│   ├── initialize.py            # System initialization
│   ├── knowledge/               # Knowledge graph functionality
│   ├── llms/                    # LLM integration
│   ├── plugins/                 # Plugin system
│   ├── references/              # Reference management
│   ├── resource_monitor.py      # Resource monitoring
│   ├── run_task.py              # Task execution
│   ├── scrapers/                # Web scraping functionality
│   ├── task/                    # Task management
│   ├── task_manager.py          # Task manager
│   ├── thread_pool_manager.py   # Thread pool management
│   └── utils/                   # Utility functions
├── dashboard/                   # Web dashboard
│   ├── backend.py               # Dashboard backend
│   ├── main.py                  # Dashboard main entry point
│   ├── plugins/                 # Dashboard plugins
│   ├── routes.py                # Dashboard routes
│   └── visualization/           # Visualization components
├── examples/                    # Example usage
└── tests/                       # Tests
```

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Required Python packages (see `requirements.txt`)
- Access to an LLM API (OpenAI, Anthropic, etc.)
- PocketBase for database storage (optional, can be replaced with other storage solutions)

## Dependencies

WiseFlow uses a modular dependency management approach to ensure compatibility and prevent runtime errors:

- `requirements.txt`: Main entry point that includes base requirements
- `requirements-base.txt`: Core dependencies required for basic functionality
- `requirements-optional.txt`: Optional dependencies for extended features
- `requirements-dev.txt`: Dependencies needed for development and testing

Module-specific requirements:
- `weixin_mp/requirements.txt`: Dependencies specific to the WeChat Mini Program module
- `core/requirements.txt`: Dependencies specific to the core module

For detailed information about dependencies, see [DEPENDENCIES.md](DEPENDENCIES.md).

### Dependency Management

WiseFlow includes a dependency management script to help maintain dependencies:

```bash
# Check for outdated packages
python scripts/dependency_check.py --check-outdated

# Find unused dependencies
python scripts/dependency_check.py --find-unused

# Find missing dependencies
python scripts/dependency_check.py --find-missing

# Validate version constraints
python scripts/dependency_check.py --validate-versions

# Run all checks
python scripts/dependency_check.py --all
```

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Zeeeepa/wiseflow.git
   cd wiseflow
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

   Key environment variables to configure:
   - `LLM_API_KEY`: Your API key for the LLM provider
   - `LLM_API_BASE`: Base URL for the LLM API (if using a custom endpoint)
   - `PRIMARY_MODEL`: Primary LLM model to use
   - `SECONDARY_MODEL`: Secondary LLM model for specific tasks
   - `VL_MODEL`: Vision-language model for multimodal analysis
   - `LLM_CONCURRENT_NUMBER`: Maximum number of concurrent LLM requests
   - `PROJECT_DIR`: Directory for storing project files
   - `VERBOSE`: Enable verbose logging
   - `MAX_CONCURRENT_TASKS`: Maximum number of concurrent tasks
   - `AUTO_SHUTDOWN_ENABLED`: Enable automatic shutdown when idle
   - `AUTO_SHUTDOWN_IDLE_TIME`: Idle time before automatic shutdown (seconds)
   - `ENABLE_MULTIMODAL`: Enable multimodal analysis
   - `ENABLE_KNOWLEDGE_GRAPH`: Enable knowledge graph construction
   - `ENABLE_INSIGHTS`: Enable insight generation
   - `ENABLE_REFERENCES`: Enable reference support
   - `ENABLE_EVENT_SYSTEM`: Enable event system
   - `WISEFLOW_API_KEY`: API key for the WiseFlow API

### Running the System

#### Quick Start (Recommended)

The easiest way to run WiseFlow is to use the unified launcher script:

1. On Linux/macOS:
   ```bash
   # Make the script executable
   chmod +x wiseflow.sh
   
   # Run WiseFlow
   ./wiseflow.sh
   ```

2. On Windows:
   ```cmd
   wiseflow.bat
   ```

The launcher script will:
- Create a virtual environment if it doesn't exist
- Install all required dependencies
- Create a `.env` file from `.env.example` if it doesn't exist
- Start all required components (PocketBase, API server, task processor, and dashboard)
- Open the dashboard in your default web browser

#### Command-line Options

The launcher script supports several command-line options:

```bash
# Don't start the PocketBase database (if you're using an external database)
./wiseflow.sh --no-db

# Don't start the API server
./wiseflow.sh --no-api

# Don't start the task processor
./wiseflow.sh --no-task

# Don't start the dashboard
./wiseflow.sh --no-dashboard

# Don't open the dashboard in a browser
./wiseflow.sh --no-browser

# Specify a custom environment file
./wiseflow.sh --env-file /path/to/.env
```

#### Manual Startup (Advanced)

If you prefer to start the components manually:

1. Start the PocketBase database:
   ```bash
   cd pb
   ./pocketbase serve --http=0.0.0.0:8090 --dir=./pb_data
   ```

2. Start the API server:
   ```bash
   python api_server.py
   ```

3. Start the task processor:
   ```bash
   python core/run_task.py
   ```

4. Start the dashboard:
   ```bash
   python dashboard/main.py
   ```

### Configuration Options

WiseFlow can be configured through environment variables or a configuration file. Key configuration options include:

#### LLM Configuration
- `LLM_API_KEY`: API key for the LLM provider
- `LLM_API_BASE`: Base URL for the LLM API
- `PRIMARY_MODEL`: Primary LLM model to use
- `SECONDARY_MODEL`: Secondary LLM model for specific tasks
- `VL_MODEL`: Vision-language model for multimodal analysis
- `LLM_CONCURRENT_NUMBER`: Maximum number of concurrent LLM requests

#### System Configuration
- `PROJECT_DIR`: Directory for storing project files
- `VERBOSE`: Enable verbose logging
- `MAX_CONCURRENT_TASKS`: Maximum number of concurrent tasks
- `AUTO_SHUTDOWN_ENABLED`: Enable automatic shutdown when idle
- `AUTO_SHUTDOWN_IDLE_TIME`: Idle time before automatic shutdown (seconds)

#### Feature Flags
- `ENABLE_MULTIMODAL`: Enable multimodal analysis
- `ENABLE_KNOWLEDGE_GRAPH`: Enable knowledge graph construction
- `ENABLE_INSIGHTS`: Enable insight generation
- `ENABLE_REFERENCES`: Enable reference support
- `ENABLE_EVENT_SYSTEM`: Enable event system

## API Usage

The WiseFlow API provides endpoints for processing content, managing webhooks, and integrating with other systems.

Example API request:

```python
import requests
import json

url = "http://localhost:8000/api/v1/process"
headers = {
    "Content-Type": "application/json",
    "X-API-Key": "your-api-key"
}
data = {
    "content": "Your content here...",
    "focus_point": "What information to extract",
    "explanation": "Additional context",
    "content_type": "text/plain",
    "use_multi_step_reasoning": True
}

response = requests.post(url, headers=headers, data=json.dumps(data))
result = response.json()
print(result)
```

For more detailed API documentation, see the [API Integration Guide](docs/api_integration.md).

## Plugin Development

WiseFlow can be extended with custom plugins for connectors, processors, and analyzers.

### Plugin Types

- **Connectors**: Connect to data sources (web, GitHub, academic papers, etc.)
- **Processors**: Process content from different sources
- **Analyzers**: Analyze processed content to extract insights

### Example Connector Plugin

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
    
    def collect(self, params=None) -> List[DataItem]:
        # Collect data from the source
        # ...
        return data_items
```

### Example Processor Plugin

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

For more information on plugin development, see the [Plugin Development Guide](docs/plugin_development.md).

## Advanced Features

### Knowledge Graph

WiseFlow can build and maintain knowledge graphs from extracted information. The knowledge graph can be used to:

- Identify relationships between entities
- Discover patterns and trends
- Provide contextual understanding
- Visualize connections

### Reference Support

WiseFlow supports using reference materials to provide contextual understanding when processing content. References can be:

- Documents
- Websites
- Code repositories
- Academic papers

### Multimodal Analysis

WiseFlow supports multimodal analysis, allowing it to process:

- Text
- Images
- Videos
- Code
- Structured data

## Troubleshooting

For common issues and solutions, see the [Troubleshooting Guide](TROUBLESHOOTING.md).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Run tests:
   ```bash
   pytest
   ```

### Coding Standards

- Follow PEP 8 style guidelines
- Write docstrings for all functions, classes, and modules
- Add type hints to function signatures
- Write unit tests for new functionality

## License

This project is licensed under the MIT License - see the LICENSE file for details.
