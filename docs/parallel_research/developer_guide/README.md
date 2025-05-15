# Developer Guide for Parallel Research

This developer guide provides comprehensive information for developers who want to extend, customize, or integrate with WiseFlow's parallel research capabilities.

## Table of Contents

1. [Getting Started](./getting_started.md)
2. [API Reference](../api/README.md)
3. [Extension Points](./extension_points.md)
4. [Creating Custom Research Modes](./custom_research_modes.md)
5. [Integrating New Search APIs](./integrating_search_apis.md)
6. [Developing Custom Plugins](./developing_plugins.md)
7. [Testing and Debugging](./testing_debugging.md)
8. [Performance Optimization](./performance_optimization.md)
9. [Code Examples](./code_examples.md)
10. [Best Practices](./best_practices.md)

## Introduction

WiseFlow's parallel research capabilities are designed to be extensible and customizable. This guide will help you understand the architecture, extension points, and best practices for developing with the parallel research system.

## Key Concepts

### Research Connector

The Research Connector is the main entry point for the research API. It provides methods for performing research on topics and continuing research based on previous results. The connector supports multiple research modes and search APIs.

```python
from core.plugins.connectors.research_connector import ResearchConnector
from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI

# Create configuration
config = Configuration(
    research_mode=ResearchMode.MULTI_AGENT,
    search_api=SearchAPI.TAVILY
)

# Initialize the research connector
connector = ResearchConnector(config)

# Perform research
results = connector.research("Artificial Intelligence in Healthcare")
```

### Research Graphs

Research Graphs define the workflow for different research modes. Each graph is implemented as a LangGraph StateGraph with nodes for different stages of the research process.

```python
from langgraph.graph import StateGraph
from core.plugins.connectors.research.state import ReportState

# Create a simple research graph
graph = StateGraph(ReportState)

# Add nodes
graph.add_node("generate_queries", generate_queries)
graph.add_node("execute_searches", execute_searches)
graph.add_node("write_report", write_report)

# Add edges
graph.add_edge(START, "generate_queries")
graph.add_edge("generate_queries", "execute_searches")
graph.add_edge("execute_searches", "write_report")
graph.add_edge("write_report", END)

# Compile the graph
graph = graph.compile()
```

### Thread Pool and Task Management

WiseFlow provides two systems for parallel processing:

1. **Thread Pool Manager**: For CPU-bound tasks using threads.
2. **Task Manager**: For I/O-bound tasks using asyncio.

```python
from core.thread_pool_manager import thread_pool_manager
from core.task_manager import task_manager, TaskPriority

# Submit a CPU-bound task to the thread pool
task_id = thread_pool_manager.submit(
    cpu_bound_function,
    arg1, arg2,
    name="CPU-bound Task",
    priority=TaskPriority.HIGH
)

# Register an I/O-bound task with the task manager
async def io_bound_function(arg1, arg2):
    # Async I/O operations
    pass

task_id = task_manager.register_task(
    name="I/O-bound Task",
    func=io_bound_function,
    args=(arg1, arg2),
    priority=TaskPriority.HIGH
)
```

### Plugin System

WiseFlow's plugin system allows you to extend the functionality of the research system:

```python
from core.plugins.base import Plugin
from core.plugins.connectors import ConnectorPlugin

class CustomSearchConnector(ConnectorPlugin):
    """Custom search connector plugin."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.name = "custom_search"
        
    def search(self, query, **kwargs):
        """Perform a search using the custom search API."""
        # Implementation
        pass
```

## Extension Points

WiseFlow provides several extension points for customizing the parallel research system:

1. **Custom Research Modes**: Create new research modes by implementing custom research graphs.
2. **Search API Integrations**: Integrate with new search APIs by implementing search API adapters.
3. **Custom Plugins**: Extend functionality through the plugin system.
4. **Custom LLM Providers**: Integrate with new LLM providers for research tasks.

For more information, see the [Extension Points](./extension_points.md) guide.

## Development Environment

To set up a development environment for working with WiseFlow's parallel research system:

1. Clone the WiseFlow repository:
   ```
   git clone https://github.com/Zeeeepa/wiseflow.git
   cd wiseflow
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. Set up environment variables:
   ```
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. Run the development server:
   ```
   python api_server.py
   ```

5. In another terminal, run the dashboard:
   ```
   cd dashboard
   python main.py
   ```

## Testing

WiseFlow includes a comprehensive test suite for the parallel research system:

```
# Run all tests
pytest tests/

# Run specific test modules
pytest tests/core/plugins/connectors/test_research_connector.py

# Run tests with coverage
pytest --cov=core.plugins.connectors.research tests/
```

For more information about testing, see the [Testing and Debugging](./testing_debugging.md) guide.

## Best Practices

When developing with WiseFlow's parallel research system, follow these best practices:

1. **Use Configuration Objects**: Always use Configuration objects for configuring research tasks.
2. **Handle Errors Gracefully**: Implement proper error handling for research tasks.
3. **Optimize Parallel Processing**: Configure parallel workers based on the nature of the tasks.
4. **Test Thoroughly**: Write comprehensive tests for custom components.
5. **Document Extensions**: Document custom extensions and plugins.

For more detailed best practices, see the [Best Practices](./best_practices.md) guide.

## Examples

For code examples of common development tasks, see the [Code Examples](./code_examples.md) guide.

## Contributing

We welcome contributions to improve WiseFlow's parallel research capabilities. Please see the [Contributing Guide](./contributing.md) for more information.

