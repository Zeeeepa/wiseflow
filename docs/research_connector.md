# Research Connector

The Research Connector is a plugin for Wiseflow that enables deep, continuous research on topics using the open_deep_research library. It provides a flexible way to perform comprehensive research with different modes and search APIs.

## Features

- **Multiple Research Modes**: Choose between linear, graph-based, or multi-agent research approaches
- **Configurable Search APIs**: Use different search providers like Tavily, Perplexity, Exa, and more
- **Continuous Research**: Build on previous research topics for deeper exploration
- **Customizable Parameters**: Configure search depth, number of queries, and more
- **Structured Output**: Get well-organized research results with sections and sources

## Configuration

The Research Connector accepts the following configuration parameters:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `research_mode` | Research mode (linear, graph, multi_agent) | linear |
| `search_api` | Search API to use (tavily, perplexity, exa, etc.) | tavily |
| `api_keys` | Dict of API keys for search services | {} |
| `max_search_depth` | Maximum search depth for graph-based research | 2 |
| `number_of_queries` | Number of search queries to generate per iteration | 2 |
| `planner_model` | Model to use for planning | claude-3-7-sonnet-latest |
| `writer_model` | Model to use for writing | claude-3-5-sonnet-latest |
| `continuous_topic` | Whether to maintain a continuous research topic | False |

## Usage

### Basic Usage

```python
from core.plugins.connectors.research_connector import ResearchConnector

# Create research connector with configuration
config = {
    "research_mode": "linear",
    "search_api": "tavily",
    "api_keys": {
        "tavily": "your-tavily-api-key"
    }
}

connector = ResearchConnector(config)
connector.initialize()

# Perform research on a topic
result = connector.fetch_data("The impact of artificial intelligence on healthcare")

# Process the results
print(f"Research topic: {result['topic']}")
print(f"Full report: {result['report']}")

# Access individual sections
for section in result['sections']:
    print(f"Section: {section['title']}")
    print(f"Content: {section['content']}")
    print(f"Sources: {section['sources']}")
```

### Advanced Usage

```python
# Configure for graph-based research with more depth
connector = ResearchConnector({
    "research_mode": "graph",
    "search_api": "perplexity",
    "api_keys": {
        "perplexity": "your-perplexity-api-key"
    },
    "max_search_depth": 3,
    "number_of_queries": 4,
    "continuous_topic": True
})

# Initial research
result1 = connector.fetch_data("Quantum computing fundamentals")

# Continue research on the same topic with more specific focus
result2 = connector.fetch_data(
    "Quantum error correction techniques",
    continuous=True  # Build on previous research
)
```

## Research Modes

### Linear Mode

The linear mode performs straightforward research by generating a plan, searching for information, and compiling a report. This is the simplest and fastest mode.

### Graph Mode

The graph mode uses a more sophisticated approach with multiple iterations of reflection and search. It creates a graph of research topics and explores them in depth, resulting in more comprehensive research.

### Multi-Agent Mode

The multi-agent mode employs multiple specialized agents working together to perform research. It includes a supervisor agent that coordinates research agents, resulting in the most thorough but also the most resource-intensive research.

## Requirements

- The open_deep_research package must be installed: `pip install open-deep-research`
- API keys for the search services you want to use (Tavily, Perplexity, Exa, etc.)

## Example

See the `examples/research_connector_example.py` file for a complete example of how to use the Research Connector.

