# Research Connector

The Research Connector is a powerful tool for conducting deep, comprehensive research on any topic. It leverages various search APIs and research methodologies to gather, analyze, and synthesize information into well-structured reports.

## Features

- **Multiple Research Modes**:
  - **Linear**: Simple sequential research process
  - **Graph-based**: Iterative research with reflection and refinement
  - **Multi-agent**: Collaborative research using specialized agents

- **Configurable Search APIs**:
  - Tavily
  - Perplexity
  - Exa
  - arXiv
  - PubMed
  - LinkUp
  - DuckDuckGo
  - Google Search

- **Continuous Research**: Build on previous research results for follow-up questions

- **Customizable Parameters**:
  - Search depth
  - Number of queries per iteration
  - Report structure
  - LLM models for planning and writing

## Installation

The Research Connector is built into wiseflow and doesn't require additional installation. However, to use specific search APIs, you may need to set up API keys:

```python
import os

# Set up API keys
os.environ["TAVILY_API_KEY"] = "your-tavily-api-key"
os.environ["PERPLEXITY_API_KEY"] = "your-perplexity-api-key"
os.environ["EXA_API_KEY"] = "your-exa-api-key"
```

## Basic Usage

```python
from core.plugins.connectors.research_connector import ResearchConnector
from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI

# Create a configuration
config = Configuration(
    search_api=SearchAPI.TAVILY,
    research_mode=ResearchMode.LINEAR,
    max_search_depth=2,
    number_of_queries=2
)

# Initialize the research connector
connector = ResearchConnector(config)

# Perform research on a topic
topic = "The impact of artificial intelligence on healthcare"
results = connector.research(topic)

# Access the research results
print(f"Research Results for: {results['topic']}")
for section in results["sections"]:
    print(f"\n## {section['title']}")
    print(section["content"])
```

## Continuous Research

You can continue research based on previous results:

```python
# Perform initial research
initial_results = connector.research("The impact of artificial intelligence on healthcare")

# Continue with a follow-up question
follow_up_topic = "Ethical considerations in AI healthcare applications"
follow_up_results = connector.continuous_research(initial_results, follow_up_topic)
```

## Advanced Configuration

The Research Connector offers extensive configuration options:

```python
config = Configuration(
    # Research mode
    research_mode=ResearchMode.GRAPH,
    
    # Search configuration
    search_api=SearchAPI.EXA,
    search_api_config={"max_results": 15},
    
    # Graph-specific configuration
    number_of_queries=3,
    max_search_depth=3,
    
    # Model configuration
    planner_provider="anthropic",
    planner_model="claude-3-7-sonnet-latest",
    writer_provider="anthropic",
    writer_model="claude-3-5-sonnet-latest",
    
    # Multi-agent configuration
    supervisor_model="openai:gpt-4.1",
    researcher_model="openai:gpt-4.1",
    
    # Report structure
    report_structure="""
    1. Introduction
    2. Background
    3. Key Findings
    4. Analysis
    5. Conclusion
    """
)
```

## Research Modes

### Linear Mode

The simplest research approach, following a sequential process:
1. Generate a report plan with sections
2. Perform searches for each section
3. Write content for each section

Best for: Quick research on straightforward topics

### Graph-based Mode

An iterative research approach with reflection and refinement:
1. Initialize research with a plan
2. Generate search queries
3. Execute searches
4. Synthesize knowledge
5. Update the report
6. Reflect on research and identify gaps
7. Continue with more targeted queries or finalize

Best for: Complex topics requiring depth and breadth

### Multi-agent Mode

A collaborative research approach using specialized agents:
1. Supervisor agent breaks down the topic into subtopics
2. Researcher agents investigate each subtopic
3. Integration agent combines findings into a cohesive report

Best for: Multifaceted topics requiring different perspectives

## Output Format

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
        "research_mode": "linear",
        "search_depth": 2,
        "queries_per_iteration": 2
    }
}
```

## Example

See `examples/research_connector_example.py` for a complete example of using the Research Connector.

