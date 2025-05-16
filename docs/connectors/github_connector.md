# GitHub Connector

The GitHub Connector provides integration with GitHub repositories, allowing Wiseflow to fetch data from GitHub including repositories, issues, pull requests, code, and users.

## Features

- **Rate Limiting**: Intelligent handling of GitHub API rate limits with adaptive backoff
- **Caching**: Efficient caching with ETag support to reduce API calls
- **Error Handling**: Comprehensive error handling with specific exception types
- **Authentication**: Support for multiple authentication methods (personal access tokens, JWT tokens)
- **Asynchronous Support**: Both synchronous and asynchronous implementations available

## Configuration

The GitHub Connector accepts the following configuration options:

| Option | Description | Default |
|--------|-------------|---------|
| `api_token` | GitHub API token (personal access token or JWT) | Environment variable `GITHUB_API_TOKEN` or `GITHUB_TOKEN` |
| `rate_limit_pause` | Seconds to pause when rate limited | 60 |
| `max_retries` | Maximum number of retries for API calls | 3 |
| `cache_enabled` | Whether to enable caching | True |
| `cache_ttl` | Time-to-live for cached items in seconds | 300 (5 minutes) |
| `cache_dir` | Directory to store cache files | '.github_cache' |
| `user_agent` | User agent string to use for requests | 'Wiseflow-GitHub-Connector' |
| `concurrency` | Maximum number of concurrent requests (async only) | 5 |

## Usage

### Synchronous Connector

```python
from core.plugins.connectors.github_connector import GitHubConnector

# Initialize the connector
config = {
    'api_token': 'your_github_token',
    'cache_enabled': True
}
connector = GitHubConnector(config)
connector.initialize()

# Fetch repository information
repo_data = connector.fetch_data('owner/repo', query_type='repo')

# Search for code
code_results = connector.fetch_data('language:python web scraping', query_type='code')

# Get repository issues
issues = connector.fetch_data('owner/repo', query_type='repo', data_type='issues')

# Clean up
connector.disconnect()
```

### Asynchronous Connector

```python
import asyncio
from core.connectors.github import GitHubConnector

async def fetch_github_data():
    # Initialize the connector
    config = {
        'api_token': 'your_github_token',
        'cache_enabled': True,
        'concurrency': 3
    }
    connector = GitHubConnector(config)
    connector.initialize()
    
    # Collect repository information
    repo_items = await connector.collect({'repo': 'owner/repo'})
    
    # Search for repositories
    search_items = await connector.collect({
        'search': 'topic:machine-learning language:python',
        'search_type': 'repositories'
    })
    
    # Get user information
    user_items = await connector.collect({'user': 'username'})
    
    return repo_items, search_items, user_items

# Run the async function
repo_items, search_items, user_items = asyncio.run(fetch_github_data())
```

## Rate Limiting

The GitHub Connector implements intelligent rate limit handling:

1. Parses GitHub's rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`)
2. Implements adaptive backoff when approaching rate limits
3. Waits for the appropriate time when rate limits are exceeded
4. Provides rate limit information through the `get_rate_limit_info()` method

## Caching

The connector implements an efficient caching strategy:

1. Uses ETags for conditional requests to reduce API usage
2. Caches responses based on configurable TTL
3. Automatically invalidates cache when needed
4. Supports file-based caching for persistence

## Error Handling

The connector provides comprehensive error handling:

1. Specific exception types for different error scenarios:
   - `GitHubRateLimitExceeded`: Raised when rate limits are exceeded
   - `GitHubAPIError`: Raised for GitHub API errors with status code and message
2. Automatic retries for transient errors
3. Exponential backoff for retries
4. Detailed error logging

## Authentication

The connector supports multiple authentication methods:

1. Personal access tokens (default)
2. JWT tokens (for GitHub Apps)
3. Unauthenticated access (with stricter rate limits)

## Best Practices

1. Always provide an API token to avoid stricter rate limits
2. Enable caching to reduce API usage
3. Handle rate limit exceptions in your code
4. Use the asynchronous connector for better performance with multiple requests
5. Set appropriate concurrency limits to avoid overwhelming the GitHub API

