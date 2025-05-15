# Parallel Research User Guide

## Introduction

WiseFlow's parallel research capabilities allow you to run multiple research tasks simultaneously, significantly improving throughput and efficiency. This guide will help you understand how to use these capabilities effectively.

## Getting Started

### Prerequisites

Before using the parallel research capabilities, ensure you have:

- WiseFlow installed and configured
- API access (if using the API)
- Proper authentication credentials

### Basic Concepts

- **Research Task**: A single research operation focused on a specific topic
- **Parallel Research**: Multiple research tasks running concurrently
- **Research Configuration**: Settings that control how research is conducted
- **Multi-Agent Approach**: An advanced research method using multiple specialized agents

## Using Parallel Research

### Through the Dashboard

1. **Navigate to the Research Page**:
   - Open your browser and go to `http://your-wiseflow-server:8000/dashboard`
   - Click on the "Research" tab in the navigation menu

2. **Create a New Research Task**:
   - Click the "New Research" button
   - Enter your research topic
   - Configure research settings (optional)
   - Toggle "Use Multi-Agent Approach" if desired
   - Set priority level
   - Add tags for organization (optional)
   - Click "Start Research"

3. **Monitor Research Progress**:
   - View all active research tasks in the "Active Research" section
   - Track progress indicators for each task
   - View estimated completion times

4. **View Research Results**:
   - Click on a completed research task to view results
   - Navigate through different sections of the research report
   - Use the visualization tools to explore relationships and trends

### Through the API

```python
import requests
import json

# API endpoint
url = "http://your-wiseflow-server:8000/api/v1/research"

# API key authentication
headers = {
    "Content-Type": "application/json",
    "X-API-Key": "your-api-key"
}

# Research request
data = {
    "topic": "Artificial Intelligence Ethics",
    "use_multi_agent": True,
    "priority": "HIGH",
    "tags": ["ai", "ethics", "research"],
    "config": {
        "search_api": "exa",
        "number_of_queries": 5,
        "max_search_depth": 3,
        "include_academic_papers": True
    }
}

# Send request
response = requests.post(url, headers=headers, data=json.dumps(data))
result = response.json()

# Get research ID
research_id = result["research_id"]

# Check research status
status_url = f"{url}/{research_id}"
status_response = requests.get(status_url, headers=headers)
status = status_response.json()

# Get research result when completed
if status["status"] == "completed":
    result_url = f"{url}/{research_id}/result"
    result_response = requests.get(result_url, headers=headers)
    research_result = result_response.json()
```

## Common Use Cases

### Competitive Analysis

```python
# Example: Competitive analysis of electric vehicle manufacturers
data = {
    "topic": "Electric vehicle market competitive analysis",
    "use_multi_agent": True,
    "config": {
        "search_api": "exa",
        "number_of_queries": 10,
        "max_search_depth": 4,
        "focus_entities": ["Tesla", "Rivian", "Lucid Motors", "BYD", "NIO"],
        "time_range": "last_year"
    }
}
```

### Academic Research

```python
# Example: Research on recent advances in quantum computing
data = {
    "topic": "Recent advances in quantum computing",
    "use_multi_agent": True,
    "config": {
        "search_api": "exa",
        "number_of_queries": 8,
        "max_search_depth": 5,
        "include_academic_papers": True,
        "academic_sources": ["arxiv", "ieee", "acm"],
        "time_range": "last_two_years"
    }
}
```

### Market Trend Analysis

```python
# Example: Analysis of AI startup funding trends
data = {
    "topic": "AI startup funding trends",
    "use_multi_agent": True,
    "config": {
        "search_api": "exa",
        "number_of_queries": 7,
        "max_search_depth": 4,
        "include_financial_data": True,
        "time_range": "last_three_years",
        "visualization": "trend_graph"
    }
}
```

## Research Configuration Options

| Option | Description | Default | Example Values |
|--------|-------------|---------|---------------|
| `search_api` | API to use for search | `"exa"` | `"exa"`, `"google"`, `"bing"` |
| `number_of_queries` | Number of search queries to generate | `5` | `1`-`20` |
| `max_search_depth` | Maximum depth of search results to analyze | `3` | `1`-`10` |
| `include_academic_papers` | Whether to include academic papers | `false` | `true`, `false` |
| `academic_sources` | Academic sources to search | `["arxiv"]` | `["arxiv", "ieee", "acm"]` |
| `time_range` | Time range for search results | `"last_year"` | `"last_month"`, `"last_year"`, `"last_five_years"` |
| `focus_entities` | Entities to focus on | `[]` | `["Tesla", "SpaceX"]` |
| `include_financial_data` | Whether to include financial data | `false` | `true`, `false` |
| `visualization` | Visualization type | `"knowledge_graph"` | `"knowledge_graph"`, `"trend_graph"` |

## Multi-Agent Approach

The multi-agent approach uses multiple specialized agents to conduct research, each focusing on different aspects:

- **Query Generator Agent**: Generates effective search queries
- **Information Retrieval Agent**: Retrieves relevant information
- **Analysis Agent**: Analyzes retrieved information
- **Synthesis Agent**: Synthesizes findings into a coherent report
- **Critique Agent**: Reviews and improves the report

This approach often produces more comprehensive and insightful research results, especially for complex topics.

## Visualizing Research Results

WiseFlow provides several visualization options for research results:

### Knowledge Graph

The knowledge graph visualization shows entities and their relationships discovered during research. To create a knowledge graph:

1. View a completed research result
2. Click the "Visualize" button
3. Select "Knowledge Graph" as the visualization type
4. Configure visualization settings (optional)
5. Click "Generate Visualization"

### Trend Visualization

The trend visualization shows how topics, sentiments, or metrics change over time:

1. View a completed research result
2. Click the "Visualize" button
3. Select "Trend" as the visualization type
4. Choose the trend metric (e.g., mention frequency, sentiment)
5. Configure time range and granularity
6. Click "Generate Visualization"

## Troubleshooting

### Common Issues

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Research task stuck at "pending" | Maximum concurrent research limit reached | Wait for other tasks to complete or increase `max_concurrent_research` in configuration |
| "API rate limit exceeded" error | Too many requests to search API | Reduce number of concurrent tasks or use a different search API |
| Empty research results | Topic too narrow or specific | Broaden the research topic or increase search depth |
| Research task fails with timeout | Research task too complex | Break down into multiple smaller research tasks |
| Visualization fails to generate | Result data too large | Filter the data or use a different visualization type |

### Getting Help

If you encounter issues not covered in this guide:

- Check the system logs for error messages
- Consult the [Troubleshooting Guide](../troubleshooting.md)
- Contact support with details about your issue

## Best Practices

- **Start Small**: Begin with a few concurrent research tasks to understand system performance
- **Use Specific Topics**: More specific research topics often yield better results
- **Leverage Tags**: Use tags to organize and categorize research tasks
- **Monitor Resource Usage**: Keep an eye on system resources when running many parallel tasks
- **Use Multi-Agent for Complex Topics**: The multi-agent approach works best for complex, nuanced topics
- **Combine Results**: For comprehensive research, combine results from multiple related research tasks

