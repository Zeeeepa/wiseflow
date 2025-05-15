# Parallel Research API Documentation

This section provides comprehensive documentation for the API endpoints and interfaces related to parallel research capabilities in WiseFlow.

## Table of Contents

1. [Research Connector API](./research_connector_api.md)
2. [Thread Pool Management API](./thread_pool_api.md)
3. [Task Management API](./task_management_api.md)
4. [Search API Integration](./search_api_integration.md)
5. [OpenAPI Specification](./openapi_spec.md)

## Overview

The WiseFlow Parallel Research API provides programmatic access to the research capabilities of the system. It allows developers to:

- Initiate research tasks with different modes and configurations
- Monitor and manage parallel research tasks
- Retrieve and process research results
- Configure parallel processing parameters
- Extend the research capabilities with custom plugins

## Authentication

All API requests require authentication. WiseFlow supports the following authentication methods:

- API Key Authentication
- OAuth 2.0
- JWT Token Authentication

For more information, see the [Authentication Guide](../developer_guide/authentication.md).

## Rate Limiting

To ensure system stability and fair usage, API requests are subject to rate limiting. The current limits are:

- 100 requests per minute per API key
- 10 concurrent research tasks per user

## Error Handling

The API uses standard HTTP status codes to indicate the success or failure of requests. In addition, error responses include a JSON body with detailed error information:

```json
{
  "error": {
    "code": "research_task_failed",
    "message": "Research task failed due to invalid configuration",
    "details": {
      "task_id": "12345",
      "reason": "Invalid search API configuration"
    }
  }
}
```

## Versioning

The API is versioned to ensure backward compatibility. The current version is `v1`. The version can be specified in the URL path:

```
https://api.wiseflow.example/v1/research
```

## Examples

### Initiating a Research Task

```python
import requests

api_key = "your_api_key"
base_url = "https://api.wiseflow.example/v1"

# Research configuration
config = {
    "topic": "Artificial Intelligence in Healthcare",
    "research_mode": "multi_agent",
    "search_api": "tavily",
    "max_search_depth": 3,
    "number_of_queries": 5,
    "parallel_workers": 4
}

# Send request
response = requests.post(
    f"{base_url}/research",
    json=config,
    headers={"Authorization": f"Bearer {api_key}"}
)

# Get task ID
task_id = response.json()["task_id"]
print(f"Research task initiated with ID: {task_id}")
```

### Checking Research Task Status

```python
import requests
import time

api_key = "your_api_key"
base_url = "https://api.wiseflow.example/v1"
task_id = "12345"

# Poll for task completion
while True:
    response = requests.get(
        f"{base_url}/research/{task_id}/status",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    
    status = response.json()["status"]
    print(f"Task status: {status}")
    
    if status in ["completed", "failed", "cancelled"]:
        break
        
    time.sleep(5)  # Poll every 5 seconds
```

### Retrieving Research Results

```python
import requests

api_key = "your_api_key"
base_url = "https://api.wiseflow.example/v1"
task_id = "12345"

# Get research results
response = requests.get(
    f"{base_url}/research/{task_id}/results",
    headers={"Authorization": f"Bearer {api_key}"}
)

results = response.json()
print(f"Research topic: {results['topic']}")
print(f"Number of sections: {len(results['sections'])}")

# Print section titles
for section in results["sections"]:
    print(f"- {section['title']}")
```

## API Reference

For detailed information about each API endpoint, see the [OpenAPI Specification](./openapi_spec.md).

