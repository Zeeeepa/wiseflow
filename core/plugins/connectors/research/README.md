# Parallel Research Manager

This module provides a manager for executing parallel research tasks in WiseFlow.

## Overview

The parallel research manager allows multiple research tasks to be executed concurrently, with each task using either the standard research workflow or the multi-agent approach. It integrates with the unified task management system to provide a consistent API for task creation, monitoring, and cancellation.

## Components

- **ParallelResearchManager**: Manages and executes parallel research tasks.
- **Configuration**: Configuration for research tasks.
- **Research Workflows**:
  - **Standard Research Workflow**: A graph-based workflow for research tasks.
  - **Multi-Agent Research Workflow**: A multi-agent approach to research tasks.

## Usage

### Creating and Executing Research Tasks

```python
from core.plugins.connectors.research.parallel_manager import parallel_research_manager
from core.plugins.connectors.research.configuration import Configuration
from core.task_management import TaskPriority

# Create a research task
task_id = await parallel_research_manager.create_research_task(
    topic="Artificial Intelligence",
    config=Configuration(
        search_api="exa",
        number_of_queries=5,
        max_search_depth=3
    ),
    use_multi_agent=True,
    priority=TaskPriority.HIGH,
    tags=["ai", "research"],
    metadata={"source": "user_request"}
)

# Execute the task
await parallel_research_manager.task_manager.execute_task(task_id, wait=False)

# Get research ID from task ID
research_id = None
for rid, research in parallel_research_manager.active_research.items():
    if research["task_id"] == task_id:
        research_id = rid
        break

# Get research status
status = parallel_research_manager.get_research_status(research_id)

# Get research result
result = parallel_research_manager.get_research_result(research_id)

# Cancel research
await parallel_research_manager.cancel_research(research_id)
```

### Research Metrics

The parallel research manager provides metrics about the research tasks it manages.

```python
# Get research metrics
metrics = parallel_research_manager.get_metrics()
```

## API Integration

The parallel research manager is integrated with the API server to provide endpoints for managing research tasks.

### API Endpoints

- `POST /api/v1/research`: Create a new research task.
- `GET /api/v1/research`: Get all research tasks.
- `GET /api/v1/research/active`: Get all active research tasks.
- `GET /api/v1/research/metrics`: Get research metrics.
- `GET /api/v1/research/{research_id}`: Get a research task.
- `GET /api/v1/research/{research_id}/result`: Get the result of a research task.
- `POST /api/v1/research/{research_id}/cancel`: Cancel a research task.

## Dashboard Integration

The parallel research manager is also integrated with the dashboard to provide a user interface for managing research tasks.

### Dashboard Endpoints

- `POST /research`: Create a new research task.
- `GET /research`: Get all research tasks.
- `GET /research/active`: Get all active research tasks.
- `GET /research/metrics`: Get research metrics.
- `GET /research/{research_id}`: Get a research task.
- `GET /research/{research_id}/result`: Get the result of a research task.
- `POST /research/{research_id}/cancel`: Cancel a research task.
- `POST /research/{research_id}/visualize`: Create a visualization for a research result.

## Visualization

The dashboard provides visualizations for research results, including knowledge graphs and trend visualizations.

```python
# Create a knowledge graph visualization
visualization = visualize_knowledge_graph(
    result.sections.sections,
    config={}
)

# Create a trend visualization
visualization = visualize_trend(
    result.sections.sections,
    config={}
)
```

## Concurrency Control

The parallel research manager limits the number of concurrent research tasks to prevent overloading the system.

```python
# Create a parallel research manager with a specific concurrency limit
parallel_research_manager = ParallelResearchManager(max_concurrent_research=5)
```

## Integration with Event System

The parallel research manager integrates with the event system to publish events when research tasks are created, started, completed, failed, or cancelled.

```python
from core.event_system import subscribe

# Subscribe to research events
subscribe(EventType.RESEARCH_CREATED, my_handler)
subscribe(EventType.RESEARCH_STARTED, my_handler)
subscribe(EventType.RESEARCH_COMPLETED, my_handler)
subscribe(EventType.RESEARCH_FAILED, my_handler)
subscribe(EventType.RESEARCH_CANCELLED, my_handler)
```

