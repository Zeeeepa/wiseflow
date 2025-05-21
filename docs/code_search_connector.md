# Code Search Connector

The Code Search Connector provides functionality for searching and retrieving code from various sources like GitHub, GitLab, Bitbucket, and Sourcegraph.

## Overview

The connector has been refactored to improve performance, error handling, and integration with other components. Key improvements include:

1. **Asynchronous Operations**: All operations are now asynchronous for better performance.
2. **Robust Caching**: Implemented a file-based caching system with TTL support.
3. **Improved Rate Limiting**: Added adaptive rate limiting based on API responses.
4. **Enhanced Error Handling**: Comprehensive error handling with specific error types.
5. **Better Integration**: Standardized interfaces for all supported services.
6. **Performance Optimization**: Concurrent requests, request deduplication, and efficient data processing.

## Usage

### Basic Usage

```python
from core.connectors.code_search import CodeSearchConnector

# Create a connector instance
config = {
    "github_token": "your_github_token",
    "gitlab_token": "your_gitlab_token",
    "bitbucket_token": "your_bitbucket_token",
    "sourcegraph_token": "your_sourcegraph_token",
    "cache_enabled": True,
    "cache_ttl": 3600,  # 1 hour
    "concurrency": 5
}

connector = CodeSearchConnector(config)
connector.initialize()

# Search for code
import asyncio

async def search_code():
    results = await connector.search("function calculateTotal", 
                                    sources=["github", "gitlab"],
                                    language="javascript",
                                    max_results=20)
    
    for item in results:
        print(f"Found in {item.metadata['source']}: {item.metadata['path']}")
        print(f"URL: {item.url}")
        print(f"Content: {item.content[:100]}...")
        print("---")

# Run the search
asyncio.run(search_code())
```

### Plugin-Based Usage

The plugin-based connector (`core.plugins.connectors.code_search_connector.CodeSearchConnector`) now uses the new connector-based implementation internally, providing backward compatibility with improved functionality.

```python
from core.plugins.connectors.code_search_connector import CodeSearchConnector

# Create a connector instance
config = {
    'api_keys': {
        'github': 'your_github_token',
        'gitlab': 'your_gitlab_token',
        'bitbucket': 'your_bitbucket_token',
        'sourcegraph': 'your_sourcegraph_token'
    },
    'default_service': 'github',
    'cache_enabled': True,
    'cache_ttl': 3600,  # 1 hour
    'concurrency': 5
}

connector = CodeSearchConnector(config)
connector.initialize()

# Search for code
results = connector.fetch_data("function calculateTotal", 
                              service="github",
                              language="javascript",
                              per_page=20)

for item in results['items']:
    print(f"Found in {item['repository']['full_name']}: {item['path']}")
    print(f"URL: {item['html_url']}")
    print("---")
```

## Configuration Options

### Common Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `github_token` | GitHub API token | Environment variable `GITHUB_TOKEN` |
| `gitlab_token` | GitLab API token | Environment variable `GITLAB_TOKEN` |
| `bitbucket_token` | Bitbucket API token | Environment variable `BITBUCKET_TOKEN` |
| `sourcegraph_token` | Sourcegraph API token | Environment variable `SOURCEGRAPH_TOKEN` |
| `sourcegraph_url` | Sourcegraph instance URL | `https://sourcegraph.com` |
| `concurrency` | Maximum number of concurrent requests | 5 |
| `timeout` | Request timeout in seconds | 30 |
| `cache_enabled` | Whether to enable caching | `True` |
| `cache_ttl` | Cache time-to-live in seconds | 3600 (1 hour) |
| `cache_size` | Maximum number of items in the LRU cache | 1024 |
| `cache_dir` | Directory for cache files | System temp directory |

### Rate Limiting Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `github_rate_limit` | GitHub API rate limit (requests per minute) | 30 |
| `gitlab_rate_limit` | GitLab API rate limit (requests per minute) | 30 |
| `bitbucket_rate_limit` | Bitbucket API rate limit (requests per minute) | 30 |
| `sourcegraph_rate_limit` | Sourcegraph API rate limit (requests per minute) | 30 |

## Search Parameters

### Common Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `query` | Search query string | Required |
| `sources` | List of sources to search | `["github", "sourcegraph"]` |
| `max_results` | Maximum number of results to return per source | 10 |
| `language` | Programming language filter | None |
| `cache_mode` | Caching mode (`ENABLED`, `DISABLED`, `READ_ONLY`, `WRITE_ONLY`) | `ENABLED` |

### GitHub-Specific Parameters

| Parameter | Description |
|-----------|-------------|
| `repo` | Repository filter (e.g., `"owner/repo"`) |
| `path` | Path filter |
| `extension` | File extension filter |
| `sort` | Sort field (`"indexed"`, `"best-match"`) |
| `order` | Sort order (`"asc"`, `"desc"`) |

### GitLab-Specific Parameters

| Parameter | Description |
|-----------|-------------|
| `project_id` | Project ID filter |
| `scope` | Search scope (`"blobs"`, `"projects"`, `"issues"`, `"merge_requests"`) |

### Bitbucket-Specific Parameters

| Parameter | Description |
|-----------|-------------|
| `workspace` | Workspace name (required for Bitbucket Cloud) |
| `server_url` | Bitbucket Server URL (for Bitbucket Server) |
| `project` | Project filter (for Bitbucket Server) |
| `repository` | Repository filter (for Bitbucket Server) |

## Error Handling

The connector provides specific error types for better error handling:

- `CodeSearchError`: Base error for all code search operations
- `CodeSearchRateLimitError`: Error when rate limits are exceeded

Example error handling:

```python
from core.connectors.code_search import CodeSearchConnector, CodeSearchError, CodeSearchRateLimitError

async def search_with_error_handling():
    try:
        results = await connector.search("function calculateTotal")
        # Process results
    except CodeSearchRateLimitError as e:
        print(f"Rate limit exceeded for {e.details['service']}. Retry after {e.details['retry_after']} seconds.")
        # Implement retry logic
    except CodeSearchError as e:
        print(f"Search error: {e.message}")
        # Handle general search errors
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        # Handle other errors
```

## Caching

The connector implements a file-based caching system with TTL support. You can control caching behavior using the `cache_mode` parameter:

```python
from core.crawl4ai.cache_context import CacheMode

# Disable caching for this search
results = await connector.search("function calculateTotal", cache_mode=CacheMode.DISABLED)

# Read from cache but don't update it
results = await connector.search("function calculateTotal", cache_mode=CacheMode.READ_ONLY)

# Update cache but don't read from it
results = await connector.search("function calculateTotal", cache_mode=CacheMode.WRITE_ONLY)
```

## Performance Considerations

1. **Concurrency**: Adjust the `concurrency` parameter based on your system's capabilities and the rate limits of the services you're using.
2. **Caching**: Enable caching to improve performance for repeated queries.
3. **Query Specificity**: More specific queries will yield faster and more relevant results.
4. **Service Selection**: Different services have different performance characteristics. GitHub and Sourcegraph typically provide the best search capabilities.

## Integration with Other Components

The Code Search Connector integrates with other components through the `DataItem` interface, which provides a standardized way to represent content from different sources.

Example integration:

```python
from core.processors.code_analyzer import CodeAnalyzer

# Search for code
results = await connector.search("function calculateTotal")

# Pass results to a code analyzer
analyzer = CodeAnalyzer()
for item in results:
    analysis = analyzer.analyze(item.content, item.metadata.get("path"))
    print(f"Analysis of {item.metadata.get('path')}: {analysis}")
```

