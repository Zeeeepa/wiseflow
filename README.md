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

## Installation

```bash
pip install -e .
```

## Usage

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

## Docker Deployment

```bash
docker-compose up -d
```

## License

MIT
