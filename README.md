# Wiseflow

AI-powered information extraction tool that uses large language models to mine relevant information from various sources based on user-defined focus points.

## Overview

Wiseflow is designed as a "wide search" system that collects broad information from various sources, as opposed to "deep search" systems that focus on answering specific questions. The key features include:

1. **Web Crawling**: Uses Crawl4ai to extract content from websites
2. **LLM-based Information Extraction**: Processes content using large language models to extract relevant information
3. **Focus Points**: User-defined topics of interest that guide information extraction
4. **PocketBase Database**: Stores extracted information and configuration
5. **Scheduling System**: Periodically crawls sources based on configured frequencies
6. **Plugin Architecture**: Supports extensibility through plugins for different data sources and processors

## New Directory Structure

The project has been restructured for better organization and maintainability:

```
wiseflow/
├── task_management/     # Task scheduling and execution
├── resource_monitoring/ # System resource monitoring
├── connectors/          # Data source connectors
│   ├── web/
│   ├── github/
│   ├── academic/
│   ├── youtube/
│   └── code_search/
├── analysis/            # Data analysis components
│   ├── entity_extraction/
│   ├── entity_linking/
│   ├── trend_analysis/
│   └── knowledge_graph/
├── plugins/             # Plugin system
│   ├── processors/
│   └── analyzers/
├── api/                 # API server and client
├── utils/               # Utility functions
└── config/              # Configuration
```

## Migration

To migrate from the old structure to the new structure, run the migration script:

```bash
python migrate_to_new_structure.py
```

This script will:
1. Create the new directory structure
2. Copy files from the old structure to the new structure
3. Create necessary __init__.py files
4. Create setup.py for package installation

After migration, you can install the package in development mode:

```bash
pip install -e .
```

## Installation

### From Source

```bash
git clone https://github.com/Zeeeepa/wiseflow.git
cd wiseflow
pip install -e .
```

### Using Docker

```bash
docker-compose up -d
```

## Usage

### Basic Usage

```python
from wiseflow.task_management.run_task import process_focus_task
from wiseflow.utils.pb_api import PbTalker

# Initialize PocketBase client
pb = PbTalker()

# Get focus points
focus_points = pb.read('focus_points', filter='activated=True')
sites = pb.read('sites')

# Process a focus point
for focus in focus_points:
    focus_sites = [s for s in sites if s['id'] in focus.get('sites', [])]
    process_focus_task(focus, focus_sites)
```

### Running the API Server

```bash
python -m wiseflow.api.api_server
```

### Using the Task Manager

```python
from wiseflow.task_management.task_manager import TaskManager
from wiseflow.task_management.thread_pool_manager import ThreadPoolManager, TaskPriority
from wiseflow.resource_monitoring.resource_monitor import ResourceMonitor

# Initialize components
resource_monitor = ResourceMonitor()
thread_pool = ThreadPoolManager(resource_monitor=resource_monitor)
task_manager = TaskManager(thread_pool=thread_pool)

# Start components
resource_monitor.start()
thread_pool.start()
task_manager.start()

# Register and execute a task
def my_task(arg1, arg2):
    print(f"Processing {arg1} and {arg2}")
    return f"{arg1}_{arg2}"

task_id = task_manager.register_task(
    name="My Task",
    func=my_task,
    "value1",
    "value2",
    priority=TaskPriority.HIGH
)

execution_id = task_manager.execute_task(task_id)

# Stop components
task_manager.stop()
thread_pool.stop()
resource_monitor.stop()
```

## Configuration

Wiseflow uses environment variables for configuration. You can set these in a `.env` file or directly in your environment.

### Core Configuration

- `PB_API_BASE`: PocketBase API base URL (default: "http://localhost:8090")
- `PB_API_AUTH`: PocketBase authentication credentials in the format "email|password"
- `MAX_CONCURRENT_TASKS`: Maximum number of concurrent tasks (default: 4)
- `AUTO_SHUTDOWN_ENABLED`: Whether to enable auto-shutdown (default: false)
- `AUTO_SHUTDOWN_IDLE_TIME`: Idle time in seconds before auto-shutdown (default: 3600)

### LLM Configuration

- `LLM_API_KEY`: API key for the LLM service
- `LLM_API_BASE`: Base URL for the LLM service
- `PRIMARY_MODEL`: Primary LLM model to use
- `SECONDARY_MODEL`: Secondary LLM model to use
- `LLM_CONCURRENT_NUMBER`: Number of concurrent LLM requests (default: 1)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

