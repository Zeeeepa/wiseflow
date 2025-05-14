# WiseFlow Research Module

This module provides deep research capabilities for WiseFlow, allowing users to perform comprehensive research on various topics using different search APIs and research modes.

## Components

### ResearchConnector

The main entry point for research functionality. It provides methods for:
- Performing synchronous research on a topic
- Continuing research based on previous results
- Starting and managing parallel research flows

### ParallelResearchManager

A robust manager for handling multiple concurrent research flows, with resource management, status tracking, and error handling capabilities.

## Usage Examples

### Basic Research

```python
from core.plugins.connectors.research_connector import ResearchConnector
from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI

# Create a research connector with default configuration
connector = ResearchConnector()

# Perform research on a topic
results = connector.research("Artificial Intelligence in Healthcare")

# Print the research sections
for section in results["sections"]:
    print(f"## {section['title']}")
    print(section["content"])
    print()
```

### Customized Research

```python
from core.plugins.connectors.research_connector import ResearchConnector
from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI

# Create a custom configuration
config = Configuration(
    search_api=SearchAPI.EXA,
    research_mode=ResearchMode.GRAPH,
    max_search_depth=3,
    number_of_queries=3
)

# Create a research connector with custom configuration
connector = ResearchConnector(config)

# Perform research on a topic
results = connector.research("Quantum Computing Advancements")
```

### Continuous Research

```python
from core.plugins.connectors.research_connector import ResearchConnector

# Create a research connector
connector = ResearchConnector()

# Perform initial research
initial_results = connector.research("Renewable Energy Sources")

# Continue research with a follow-up question
follow_up_results = connector.continuous_research(
    initial_results, 
    "What are the latest advancements in solar panel efficiency?"
)
```

### Parallel Research

```python
import asyncio
from core.plugins.connectors.research_connector import ResearchConnector
from core.plugins.connectors.research.configuration import Configuration, ResearchMode

async def run_parallel_research():
    # Create a research connector
    connector = ResearchConnector()
    
    # Start multiple parallel research flows
    flow_id1 = await connector.start_parallel_research("Artificial Intelligence")
    flow_id2 = await connector.start_parallel_research(
        "Blockchain Technology",
        research_mode=ResearchMode.MULTI_AGENT
    )
    
    # Check status of flows
    while True:
        status1 = await connector.get_parallel_research_status(flow_id1)
        status2 = await connector.get_parallel_research_status(flow_id2)
        
        print(f"Flow 1: {status1['status']} - Progress: {status1['progress']:.0%}")
        print(f"Flow 2: {status2['status']} - Progress: {status2['progress']:.0%}")
        
        if status1['status'] == 'completed' and status2['status'] == 'completed':
            break
            
        await asyncio.sleep(1)
    
    # Get results
    results1 = await connector.get_parallel_research_results(flow_id1)
    results2 = await connector.get_parallel_research_results(flow_id2)
    
    return results1, results2

# Run the async function
results1, results2 = asyncio.run(run_parallel_research())
```

### Managing Parallel Research Flows

```python
import asyncio
from core.plugins.connectors.research_connector import ResearchConnector

async def manage_research_flows():
    connector = ResearchConnector()
    
    # Start a research flow
    flow_id = await connector.start_parallel_research("Climate Change Solutions")
    
    # Get all active flows
    all_flows = await connector.get_all_parallel_research_flows()
    print(f"Active flows: {len(all_flows)}")
    
    # Cancel a flow
    cancelled = await connector.cancel_parallel_research(flow_id)
    print(f"Flow cancelled: {cancelled}")
    
    # Start a new flow and then continue research
    flow_id = await connector.start_parallel_research("Space Exploration")
    
    # Wait for completion
    while True:
        status = await connector.get_parallel_research_status(flow_id)
        if status['status'] == 'completed':
            break
        await asyncio.sleep(1)
    
    # Continue research with a follow-up
    new_flow_id = await connector.start_continuous_parallel_research(
        flow_id, 
        "What are the challenges of Mars colonization?"
    )

# Run the async function
asyncio.run(manage_research_flows())
```

## Configuration Options

The research module can be configured with various options:

### Search APIs

- `PERPLEXITY`: Perplexity AI search API
- `TAVILY`: Tavily search API
- `EXA`: Exa search API
- `ARXIV`: arXiv research papers
- `PUBMED`: PubMed medical research
- `LINKUP`: LinkUp job search
- `DUCKDUCKGO`: DuckDuckGo search
- `GOOGLESEARCH`: Google search

### Research Modes

- `LINEAR`: Simple linear research flow
- `GRAPH`: Graph-based research with reflection and iteration
- `MULTI_AGENT`: Multi-agent research with specialized agents

### Other Configuration Options

- `max_search_depth`: Maximum number of search iterations
- `number_of_queries`: Number of search queries per iteration
- `planner_model`: Model for planning research
- `writer_model`: Model for writing research content

## ParallelResearchManager Features

The `ParallelResearchManager` provides several features for managing parallel research flows:

- **Concurrency Control**: Limits the number of concurrent research flows to prevent resource exhaustion
- **API Rate Limiting**: Prevents rate limit errors from external APIs
- **Status Tracking**: Monitors the progress and status of all research flows
- **Error Handling**: Provides robust error handling and recovery mechanisms
- **Resource Management**: Efficiently manages memory and computational resources
- **Flow Cancellation**: Allows cancellation of running research flows
- **Continuous Research**: Supports building on previous research results
- **Metadata Management**: Stores and retrieves metadata for research flows
- **Cleanup**: Automatically cleans up completed or failed flows after a specified time

## Error Handling

The parallel research manager includes comprehensive error handling:

- **Flow Failures**: Failed flows are marked with an error message and can be retried
- **API Errors**: Errors from external APIs are caught and handled gracefully
- **Cancellation**: Research flows can be cancelled at any time
- **Resource Exhaustion**: Prevents system overload by limiting concurrent flows
- **Recovery**: Provides mechanisms for retrying failed flows

