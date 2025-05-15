# Parallel Research Developer Guide

## Architecture Overview

The parallel research system in WiseFlow is designed to execute multiple research tasks concurrently while maintaining system stability and resource efficiency. This guide provides detailed information for developers who want to understand, use, or extend the parallel research capabilities.

## Core Components

### ParallelResearchManager

The `ParallelResearchManager` is the central component that manages parallel research tasks. It's implemented as a singleton to ensure consistent state across the application.

**Location**: `core/plugins/connectors/research/parallel_manager.py`

**Key Responsibilities**:
- Managing concurrent research tasks
- Enforcing concurrency limits
- Tracking research task status and results
- Integrating with the unified task management system
- Publishing events for research task lifecycle

**Class Diagram**:

```
ParallelResearchManager
├── Properties
│   ├── max_concurrent_research: int
│   ├── active_research: Dict[str, Dict]
│   ├── completed_research: Dict[str, Dict]
│   └── task_manager: TaskManager
├── Methods
│   ├── create_research_task()
│   ├── execute_research_task()
│   ├── cancel_research()
│   ├── get_research_status()
│   ├── get_research_result()
│   ├── get_all_research()
│   ├── get_active_research()
│   ├── get_completed_research()
│   └── get_metrics()
```

### Research Workflows

WiseFlow supports two research workflow implementations:

1. **Standard Research Workflow**: A graph-based workflow for research tasks
   - **Location**: `core/plugins/connectors/research/graph_workflow.py`
   - **Implementation**: Uses a directed graph to represent the research workflow

2. **Multi-Agent Research Workflow**: A multi-agent approach to research tasks
   - **Location**: `core/plugins/connectors/research/multi_agent.py`
   - **Implementation**: Uses multiple specialized agents to conduct research

### Configuration

The `Configuration` class provides a structured way to configure research tasks.

**Location**: `core/plugins/connectors/research/configuration.py`

**Key Properties**:
- `search_api`: API to use for search
- `number_of_queries`: Number of search queries to generate
- `max_search_depth`: Maximum depth of search results to analyze
- Additional configuration options for specialized research

### Integration with Task Management

The parallel research system integrates with the unified task management system to leverage its task execution, monitoring, and cancellation capabilities.

**Location**: `core/task_management/`

**Key Components**:
- `TaskManager`: Manages and executes tasks
- `Task`: Represents a task that can be executed
- `Executor`: Executes tasks using different strategies

## API Reference

### ParallelResearchManager

```python
class ParallelResearchManager:
    def __init__(self, max_concurrent_research: int = 3):
        """
        Initialize the parallel research manager.
        
        Args:
            max_concurrent_research: Maximum number of concurrent research tasks
        """
        
    async def create_research_task(
        self,
        topic: str,
        config: Optional[Configuration] = None,
        use_multi_agent: bool = False,
        priority: TaskPriority = TaskPriority.NORMAL,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new research task.
        
        Args:
            topic: Research topic
            config: Research configuration
            use_multi_agent: Whether to use the multi-agent approach
            priority: Priority of the task
            tags: List of tags for categorizing the task
            metadata: Additional metadata for the task
            
        Returns:
            Task ID
        """
        
    async def execute_research_task(
        self,
        task_id: str,
        wait: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a research task.
        
        Args:
            task_id: Task ID
            wait: Whether to wait for the task to complete
            
        Returns:
            Research result if wait is True, None otherwise
        """
        
    async def cancel_research(self, research_id: str) -> bool:
        """
        Cancel a research task.
        
        Args:
            research_id: Research ID
            
        Returns:
            True if the research was cancelled, False otherwise
        """
        
    def get_research_status(self, research_id: str) -> Dict[str, Any]:
        """
        Get the status of a research task.
        
        Args:
            research_id: Research ID
            
        Returns:
            Research status
        """
        
    def get_research_result(self, research_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the result of a research task.
        
        Args:
            research_id: Research ID
            
        Returns:
            Research result if available, None otherwise
        """
        
    def get_all_research(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all research tasks.
        
        Returns:
            Dictionary of research tasks
        """
        
    def get_active_research(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active research tasks.
        
        Returns:
            Dictionary of active research tasks
        """
        
    def get_completed_research(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all completed research tasks.
        
        Returns:
            Dictionary of completed research tasks
        """
        
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about the research tasks.
        
        Returns:
            Dictionary of metrics
        """
```

### Configuration

```python
class Configuration:
    def __init__(
        self,
        search_api: str = "exa",
        number_of_queries: int = 5,
        max_search_depth: int = 3,
        include_academic_papers: bool = False,
        academic_sources: Optional[List[str]] = None,
        time_range: str = "last_year",
        focus_entities: Optional[List[str]] = None,
        include_financial_data: bool = False,
        visualization: str = "knowledge_graph",
        **kwargs
    ):
        """
        Initialize the research configuration.
        
        Args:
            search_api: API to use for search
            number_of_queries: Number of search queries to generate
            max_search_depth: Maximum depth of search results to analyze
            include_academic_papers: Whether to include academic papers
            academic_sources: Academic sources to search
            time_range: Time range for search results
            focus_entities: Entities to focus on
            include_financial_data: Whether to include financial data
            visualization: Visualization type
            **kwargs: Additional configuration options
        """
```

## Integration Examples

### Creating and Executing Research Tasks

```python
from core.plugins.connectors.research.parallel_manager import parallel_research_manager
from core.plugins.connectors.research.configuration import Configuration
from core.task_management import TaskPriority

async def run_research():
    # Create a research task
    task_id = await parallel_research_manager.create_research_task(
        topic="Artificial Intelligence Ethics",
        config=Configuration(
            search_api="exa",
            number_of_queries=5,
            max_search_depth=3,
            include_academic_papers=True,
            academic_sources=["arxiv", "ieee", "acm"],
            time_range="last_year"
        ),
        use_multi_agent=True,
        priority=TaskPriority.HIGH,
        tags=["ai", "ethics", "research"],
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
    
    return research_id
```

### Monitoring Research Progress

```python
async def monitor_research(research_id):
    import time
    
    # Check status periodically
    while True:
        status = parallel_research_manager.get_research_status(research_id)
        
        if status["status"] in ["completed", "failed", "cancelled"]:
            break
            
        print(f"Research progress: {status.get('progress', 0):.2f}")
        time.sleep(5)
    
    # Get result if completed
    if status["status"] == "completed":
        result = parallel_research_manager.get_research_result(research_id)
        return result
    
    return None
```

### Cancelling Research

```python
async def cancel_research(research_id):
    # Cancel research
    success = await parallel_research_manager.cancel_research(research_id)
    return success
```

## Extending the System

### Creating a Custom Research Workflow

To create a custom research workflow, you need to:

1. Create a new module in `core/plugins/connectors/research/`
2. Implement the research workflow as a function or class
3. Register the workflow with the parallel research manager

Example:

```python
# core/plugins/connectors/research/custom_workflow.py
from typing import Dict, Any, Optional
from core.plugins.connectors.research.configuration import Configuration

async def custom_research_workflow(
    topic: str,
    config: Optional[Configuration] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Custom research workflow.
    
    Args:
        topic: Research topic
        config: Research configuration
        **kwargs: Additional arguments
        
    Returns:
        Research result
    """
    # Implement custom research workflow
    # ...
    
    return {
        "topic": topic,
        "sections": [...],
        "entities": [...],
        "summary": "...",
        "metadata": {...}
    }

# Register the workflow
from core.plugins.connectors.research.parallel_manager import ParallelResearchManager

# Get the parallel research manager instance
manager = ParallelResearchManager()

# Register the custom workflow
manager.register_workflow("custom", custom_research_workflow)
```

### Adding a New Visualization Type

To add a new visualization type:

1. Create a new module in `dashboard/visualization/`
2. Implement the visualization logic
3. Register the visualization type with the dashboard

Example:

```python
# dashboard/visualization/timeline.py
from typing import Dict, Any, List
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime

def create_timeline_visualization(
    sections: List[Dict[str, Any]],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a timeline visualization.
    
    Args:
        sections: Research sections
        config: Visualization configuration
        
    Returns:
        Visualization data
    """
    # Extract events and dates from sections
    events = []
    for section in sections:
        for entity in section.get("entities", []):
            if "date" in entity:
                events.append({
                    "name": entity["name"],
                    "date": datetime.fromisoformat(entity["date"]),
                    "description": entity.get("description", "")
                })
    
    # Sort events by date
    events.sort(key=lambda x: x["date"])
    
    # Create timeline visualization
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Plot events
    for i, event in enumerate(events):
        ax.scatter(event["date"], i, s=100, color="blue")
        ax.text(event["date"], i + 0.1, event["name"], ha="center")
    
    # Set labels and title
    ax.set_yticks([])
    ax.set_xlabel("Date")
    ax.set_title("Timeline Visualization")
    
    # Save figure to file
    filename = f"timeline_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    filepath = f"dashboard/static/visualizations/{filename}"
    plt.savefig(filepath)
    
    return {
        "type": "timeline",
        "image_url": f"/static/visualizations/{filename}",
        "events": events
    }

# Register the visualization type
from dashboard.visualization import register_visualization

register_visualization("timeline", create_timeline_visualization)
```

## Event System Integration

The parallel research system integrates with the event system to publish events when research tasks are created, started, completed, failed, or cancelled.

```python
from core.event_system import EventType, subscribe

# Define event handler
def research_event_handler(event):
    print(f"Research event: {event.type}")
    print(f"Research ID: {event.data.get('research_id')}")
    print(f"Task ID: {event.data.get('task_id')}")
    print(f"Status: {event.data.get('status')}")
    print(f"Timestamp: {event.timestamp}")

# Subscribe to research events
subscribe(EventType.RESEARCH_CREATED, research_event_handler)
subscribe(EventType.RESEARCH_STARTED, research_event_handler)
subscribe(EventType.RESEARCH_COMPLETED, research_event_handler)
subscribe(EventType.RESEARCH_FAILED, research_event_handler)
subscribe(EventType.RESEARCH_CANCELLED, research_event_handler)
```

## Performance Considerations

### Concurrency Control

The parallel research manager limits the number of concurrent research tasks to prevent overloading the system. This limit can be configured when creating the manager:

```python
from core.plugins.connectors.research.parallel_manager import ParallelResearchManager

# Create a parallel research manager with a specific concurrency limit
parallel_research_manager = ParallelResearchManager(max_concurrent_research=5)
```

### Resource Usage

Research tasks can be resource-intensive, especially when using the multi-agent approach. Consider the following when designing systems that use parallel research:

- **Memory Usage**: Each research task requires memory for storing intermediate results and the final report
- **CPU Usage**: Research tasks involve text processing and analysis, which can be CPU-intensive
- **API Rate Limits**: Research tasks make API calls to search engines and other services, which may have rate limits
- **Network Bandwidth**: Research tasks download content from the web, which requires network bandwidth

### Scaling Strategies

To scale the parallel research system:

1. **Vertical Scaling**: Increase the resources (CPU, memory) of the machine running WiseFlow
2. **Horizontal Scaling**: Distribute research tasks across multiple machines
3. **Task Prioritization**: Use the priority system to ensure important tasks are executed first
4. **Caching**: Cache search results and research outputs to avoid redundant work
5. **Asynchronous Processing**: Use asynchronous processing to improve throughput

## Testing

### Unit Testing

Unit tests for the parallel research system are located in `tests/unit/plugins/connectors/research/`.

To run the tests:

```bash
pytest tests/unit/plugins/connectors/research/
```

### Integration Testing

Integration tests that verify the interaction between the parallel research system and other components are located in `tests/integration/`.

To run the integration tests:

```bash
pytest tests/integration/test_parallel_research.py
```

### Load Testing

Load tests that verify the system's performance under load are located in `tests/load/`.

To run the load tests:

```bash
pytest tests/load/test_parallel_research_load.py
```

## Debugging

### Logging

The parallel research system uses Python's logging module to log information about its operation. To enable detailed logging:

```python
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("core.plugins.connectors.research")
logger.setLevel(logging.DEBUG)
```

### Common Issues

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Task stuck in "pending" state | Maximum concurrent research limit reached | Increase `max_concurrent_research` or wait for other tasks to complete |
| Task fails with "API rate limit exceeded" | Too many requests to search API | Reduce number of concurrent tasks or use a different search API |
| Memory usage grows over time | Research results not being cleaned up | Implement periodic cleanup of completed research |
| System becomes unresponsive | Too many concurrent tasks | Reduce `max_concurrent_research` or increase system resources |

## Best Practices

- **Use Asynchronous Execution**: Always use asynchronous execution (`wait=False`) when starting research tasks from user-facing code
- **Implement Timeouts**: Set appropriate timeouts for research tasks to prevent them from running indefinitely
- **Monitor Resource Usage**: Implement resource monitoring to detect and address performance issues
- **Clean Up Completed Research**: Periodically clean up completed research to free up memory
- **Use Task Priorities**: Assign appropriate priorities to research tasks based on their importance
- **Implement Rate Limiting**: Implement rate limiting for API calls to prevent exceeding rate limits
- **Cache Results**: Cache search results and research outputs to avoid redundant work
- **Use Event System**: Subscribe to research events to monitor and respond to research task lifecycle events

