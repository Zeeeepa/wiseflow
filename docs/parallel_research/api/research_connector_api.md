# Research Connector API

The Research Connector API provides access to WiseFlow's parallel research capabilities. It allows you to initiate, monitor, and retrieve results from research tasks using different research modes and configurations.

## Class: ResearchConnector

The `ResearchConnector` class is the main entry point for the research API. It provides methods for performing research on topics and continuing research based on previous results.

### Initialization

```python
from core.plugins.connectors.research_connector import ResearchConnector
from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI

# Create configuration
config = Configuration(
    research_mode=ResearchMode.MULTI_AGENT,
    search_api=SearchAPI.TAVILY,
    number_of_queries=3,
    max_search_depth=2
)

# Initialize the research connector
connector = ResearchConnector(config)
```

### Methods

#### research(topic, **kwargs)

Performs research on a specified topic.

**Parameters:**
- `topic` (str): The topic to research
- `**kwargs`: Additional arguments to override configuration

**Returns:**
- `Dict[str, Any]`: The research results including report sections and metadata

**Example:**
```python
results = connector.research("Artificial Intelligence in Healthcare")

print(f"Research topic: {results['topic']}")
print(f"Number of sections: {len(results['sections'])}")
print(f"Research mode: {results['metadata']['research_mode']}")
```

#### continuous_research(previous_results, new_topic, **kwargs)

Continues research based on previous results.

**Parameters:**
- `previous_results` (Dict[str, Any]): Results from a previous research call
- `new_topic` (str): The new topic or follow-up question
- `**kwargs`: Additional arguments to override configuration

**Returns:**
- `Dict[str, Any]`: The research results including report sections and metadata

**Example:**
```python
# Perform initial research
initial_results = connector.research("Artificial Intelligence in Healthcare")

# Continue with a follow-up topic
follow_up_topic = "Recent advancements in AI diagnostic tools"
follow_up_results = connector.continuous_research(initial_results, follow_up_topic)

print(f"Follow-up topic: {follow_up_results['topic']}")
print(f"Previous topic: {follow_up_results['previous_topic']}")
print(f"Number of sections: {len(follow_up_results['sections'])}")
```

#### set_config(**kwargs)

Updates the configuration of the research connector.

**Parameters:**
- `**kwargs`: Configuration parameters to update

**Example:**
```python
connector.set_config(
    research_mode=ResearchMode.GRAPH,
    max_search_depth=3,
    number_of_queries=4
)
```

## Configuration

The `Configuration` class provides options for configuring the research process.

### Common Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `report_structure` | str | DEFAULT_REPORT_STRUCTURE | Template for the report structure |
| `search_api` | SearchAPI | SearchAPI.TAVILY | The search API to use |
| `search_api_config` | Dict[str, Any] | None | Additional configuration for the search API |
| `research_mode` | ResearchMode | ResearchMode.LINEAR | The research mode to use |
| `number_of_queries` | int | 2 | Number of search queries to generate per iteration |
| `max_search_depth` | int | 2 | Maximum number of reflection + search iterations |

### Research Modes

The `ResearchMode` enum defines the available research modes:

```python
class ResearchMode(Enum):
    LINEAR = "linear"
    GRAPH = "graph"
    MULTI_AGENT = "multi_agent"
```

#### LINEAR Mode

The simplest research approach, following a sequential process:
1. Generate a report plan
2. Write sections based on search results

Best for: Quick research on straightforward topics

#### GRAPH Mode

An iterative research approach with reflection and refinement:
1. Initialize research with a plan
2. Generate search queries
3. Execute searches
4. Synthesize knowledge
5. Update the report
6. Reflect on research and identify gaps
7. Continue with new queries or finalize

Best for: In-depth research requiring multiple iterations and refinement

#### MULTI_AGENT Mode

A collaborative research approach using specialized agents:
1. Supervisor agent plans the research and assigns subtopics
2. Researcher agents investigate each subtopic in parallel
3. Integration agent combines findings into a cohesive report

Best for: Complex topics with distinct subtopics that can be researched in parallel

### Search APIs

The `SearchAPI` enum defines the available search APIs:

```python
class SearchAPI(Enum):
    PERPLEXITY = "perplexity"
    TAVILY = "tavily"
    EXA = "exa"
    ARXIV = "arxiv"
    PUBMED = "pubmed"
    LINKUP = "linkup"
    DUCKDUCKGO = "duckduckgo"
    GOOGLESEARCH = "googlesearch"
```

## Response Format

The research results are returned as a dictionary with the following structure:

```python
{
    "topic": "The research topic",
    "sections": [
        {
            "title": "Section Title",
            "content": "Section content...",
            "subsections": [
                {
                    "title": "Subsection Title",
                    "content": "Subsection content..."
                }
            ]
        }
    ],
    "raw_sections": Sections(...),  # Internal representation
    "metadata": {
        "search_api": "tavily",
        "research_mode": "multi_agent",
        "search_depth": 2,
        "queries_per_iteration": 3
    }
}
```

For continuous research, the response includes an additional field:

```python
{
    "topic": "The new research topic",
    "previous_topic": "The previous research topic",
    "sections": [...],
    "raw_sections": Sections(...),
    "metadata": {
        "search_api": "tavily",
        "research_mode": "multi_agent",
        "search_depth": 2,
        "queries_per_iteration": 3,
        "continuous": True
    }
}
```

## Error Handling

The Research Connector API uses exceptions to indicate errors:

- `ValueError`: Raised for invalid configuration values
- `TypeError`: Raised for invalid parameter types
- `RuntimeError`: Raised for execution errors during research

Example error handling:

```python
try:
    results = connector.research("Artificial Intelligence in Healthcare")
except ValueError as e:
    print(f"Configuration error: {e}")
except RuntimeError as e:
    print(f"Research execution error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Thread Safety

The `ResearchConnector` class is thread-safe and can be used concurrently from multiple threads. Each research call creates a new state object and does not modify shared state.

## Performance Considerations

- Research tasks can be resource-intensive, especially in MULTI_AGENT mode
- Consider limiting the number of concurrent research tasks
- The `max_search_depth` and `number_of_queries` parameters significantly impact performance
- For large-scale research, consider using the Task Management API to schedule and monitor tasks

## See Also

- [Thread Pool Management API](./thread_pool_api.md)
- [Task Management API](./task_management_api.md)
- [Search API Integration](./search_api_integration.md)

