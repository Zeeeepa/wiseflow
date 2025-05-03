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

### Running the System

1. Start the API server:
   ```bash
   python api_server.py
   ```

2. Start the task processor:
   ```bash
   python core/run_task.py
   ```

3. Start the dashboard:
   ```bash
   python dashboard/main.py
   ```

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

## Plugin Development

WiseFlow can be extended with custom plugins for connectors, processors, and analyzers.

Example connector plugin:

```python
from core.connectors import ConnectorBase, DataItem

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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

