# Wiseflow Project Restructuring Plan

## Current Issues
1. Duplicate functionality across modules
2. Overly complex directory structure
3. Similar code in different locations
4. Redundant files (e.g., multiple resource monitors)
5. Inconsistent module organization

## New Structure

```
wiseflow/
├── api/                      # API-related code
│   ├── server.py             # Main API server
│   └── client.py             # API client for external use
├── core/                     # Core functionality
│   ├── analysis/             # Analysis and knowledge processing
│   │   ├── entities.py       # Entity definitions and operations
│   │   ├── knowledge_graph.py # Knowledge graph functionality
│   │   ├── patterns.py       # Pattern recognition
│   │   └── trends.py         # Trend analysis
│   ├── connectors/           # Data source connectors
│   │   ├── base.py           # Base connector class
│   │   ├── web.py            # Web connector
│   │   ├── github.py         # GitHub connector
│   │   ├── academic.py       # Academic connector
│   │   └── youtube.py        # YouTube connector
│   ├── extraction/           # Data extraction functionality
│   │   ├── crawler.py        # Web crawling functionality
│   │   ├── scraper.py        # Content scraping
│   │   └── processor.py      # Content processing
│   ├── llm/                  # LLM integration
│   │   ├── base.py           # Base LLM functionality
│   │   ├── openai.py         # OpenAI integration
│   │   └── specialized.py    # Specialized prompting
│   ├── plugins/              # Plugin system
│   │   ├── base.py           # Base plugin functionality
│   │   ├── registry.py       # Plugin registry
│   │   └── loader.py         # Plugin loading
│   └── utils/                # Utility functions
│       ├── export.py         # Export functionality
│       ├── io.py             # I/O utilities
│       └── general.py        # General utilities
├── dashboard/                # Dashboard functionality
│   ├── ui/                   # UI components
│   └── visualization/        # Visualization components
├── system/                   # System management
│   ├── resource_monitor.py   # Resource monitoring
│   ├── task_manager.py       # Task management
│   └── thread_pool.py        # Thread pool management
├── tests/                    # Tests
└── examples/                 # Example usage
```

## Consolidation Plan

### 1. Merge Duplicate Functionality
- Consolidate `core/resource_monitor.py` and `dashboard/resource_monitor.py` into `system/resource_monitor.py`
- Merge `core/task/__init__.py`, `core/task_manager.py`, and related task functionality into `system/task_manager.py`
- Combine `core/thread_pool_manager.py` with task execution into `system/thread_pool.py`
- Merge `core/analysis/__init__.py` and `core/knowledge/graph.py` into `core/analysis/entities.py` and `core/analysis/knowledge_graph.py`
- Consolidate `core/crawl4ai` modules into `core/extraction/` with simplified structure
- Merge `core/utils/general_utils.py` and `dashboard/general_utils.py` into `core/utils/general.py`

### 2. Remove Redundant Files
- Remove `core/run_task_new.py` and keep only the updated `run_task.py`
- Remove duplicate crawler implementations
- Remove redundant utility files

### 3. Simplify Module Structure
- Flatten the directory structure where possible
- Reduce nesting levels
- Group related functionality together

### 4. Improve Code Organization
- Ensure consistent naming conventions
- Improve import structure
- Add clear module docstrings
- Ensure proper dependency management

## Implementation Steps
1. Create the new directory structure
2. Move and merge files according to the plan
3. Update imports across the codebase
4. Test functionality to ensure nothing is broken
5. Update documentation to reflect the new structure

