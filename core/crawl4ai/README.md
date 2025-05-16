# Crawl4AI - Web Crawling and Content Extraction

Crawl4AI is a powerful web crawling and content extraction library designed for AI applications. It provides a high-level interface for crawling web pages asynchronously, with support for caching, browser configuration, and error handling.

## Key Features

- **Asynchronous Web Crawling**: Efficiently crawl multiple web pages concurrently
- **Content Extraction**: Extract clean, structured content from web pages
- **Markdown Generation**: Convert HTML content to markdown for AI processing
- **Caching**: Intelligent caching with TTL and size limits
- **Error Handling**: Comprehensive error handling and retry mechanisms
- **Resource Management**: Proper cleanup of resources to prevent memory leaks
- **Concurrency Control**: Prevent race conditions and manage concurrent operations
- **Configuration Management**: Centralized configuration with environment variable support

## Components

### AsyncWebCrawler

The main entry point for web crawling operations. It provides methods for crawling web pages asynchronously, with support for caching, browser configuration, and error handling.

```python
from core.crawl4ai import AsyncWebCrawler, AsyncConfigs, CacheMode

# Create crawler
crawler = AsyncWebCrawler()

# Start crawler
await crawler.start()

# Configure crawler
config = AsyncConfigs()
config.cache_mode = CacheMode.ENABLED
config.timeout = 60000  # 60 seconds

# Crawl a URL
result = await crawler.arun(url="https://example.com", config=config)

# Access result
html = result.html
markdown = result.markdown
metadata = result.metadata

# Close crawler
await crawler.close()
```

### EnhancedCache

A sophisticated caching mechanism with TTL support, configurable size limits, and cache invalidation strategies.

```python
from core.crawl4ai import EnhancedCache

# Create cache
cache = EnhancedCache(
    cache_dir="/path/to/cache",
    ttl=86400,  # 24 hours in seconds
    max_size=1000,  # Maximum number of items in cache
    cleanup_interval=3600,  # 1 hour in seconds
)

# Get cached result
result = await cache.get(url)

# Cache result
await cache.set(result)

# Invalidate cache
await cache.invalidate(url)

# Clear cache
await cache.clear()

# Get cache statistics
stats = await cache.get_stats()
```

### ConfigManager

A centralized configuration system for the crawl4ai package, with support for environment variables, configuration files, and sensible defaults.

```python
from core.crawl4ai import ConfigManager

# Create config manager
config_manager = ConfigManager(
    config_path="/path/to/config.json",
    base_directory="/path/to/base/dir",
)

# Get configuration values
browser_config = config_manager.get_browser_config()
crawler_config = config_manager.get_crawler_config()
cache_config = config_manager.get_cache_config()

# Set configuration values
config_manager.set(60000, "crawler", "timeout")
```

### EnhancedWebScrapingStrategy

An improved implementation of web content scraping with better error handling, performance optimizations, and resource management.

```python
from core.crawl4ai import EnhancedWebScrapingStrategy

# Create scraping strategy
scraping_strategy = EnhancedWebScrapingStrategy()

# Scrape content
result = scraping_strategy.scrap(url="https://example.com", html="<html>...</html>")

# Access result
cleaned_html = result.cleaned_html
media = result.media
links = result.links
metadata = result.metadata
```

## Error Handling

Crawl4AI provides a comprehensive error handling system with custom exceptions for different types of errors:

- `Crawl4AIError`: Base exception class for all crawl4ai errors
- `NetworkError`: Exception raised for network-related errors during crawling
- `ParsingError`: Exception raised for errors during HTML parsing
- `TimeoutError`: Exception raised when a crawling operation times out
- `RobotsError`: Exception raised when crawling is disallowed by robots.txt
- `ResourceError`: Exception raised when there are issues with resource management
- `ConfigurationError`: Exception raised for configuration-related errors
- `CacheError`: Exception raised for cache-related errors
- `ValidationError`: Exception raised for validation errors

## Configuration

Crawl4AI can be configured using environment variables, configuration files, or programmatically:

### Environment Variables

```
# Browser configuration
CRAWL4AI_BROWSER_TYPE=chromium
CRAWL4AI_HEADLESS=true
CRAWL4AI_USER_AGENT=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/116.0.0.0 Safari/537.36

# Crawler configuration
CRAWL4AI_MAX_DEPTH=1
CRAWL4AI_MAX_PAGES=10
CRAWL4AI_TIMEOUT=60000
CRAWL4AI_CONCURRENCY=5

# Cache configuration
CRAWL4AI_CACHE_ENABLED=true
CRAWL4AI_CACHE_TTL=86400
CRAWL4AI_CACHE_MAX_SIZE=1000
```

### Configuration File

```json
{
  "browser": {
    "type": "chromium",
    "headless": true,
    "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/116.0.0.0 Safari/537.36"
  },
  "crawler": {
    "max_depth": 1,
    "max_pages": 10,
    "timeout": 60000,
    "concurrency": 5
  },
  "cache": {
    "enabled": true,
    "ttl": 86400,
    "max_size": 1000
  }
}
```

### Programmatic Configuration

```python
from core.crawl4ai import AsyncWebCrawler, AsyncConfigs, BrowserConfig

# Create browser config
browser_config = BrowserConfig(
    browser_type="chromium",
    headless=True,
    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/116.0.0.0 Safari/537.36",
)

# Create crawler
crawler = AsyncWebCrawler(
    config=browser_config,
    memory_threshold_percent=85.0,
    memory_warning_percent=75.0,
    memory_check_interval=10.0,
    cooldown_period=300,
    max_retries=3,
    retry_delay=5,
)

# Create crawler config
crawler_config = AsyncConfigs(
    max_depth=1,
    max_pages=10,
    timeout=60000,
    cache_mode=CacheMode.ENABLED,
)
```

## Best Practices

- **Resource Management**: Always use `async with` or `await crawler.close()` to properly clean up resources
- **Error Handling**: Use try-except blocks to handle errors and implement retry mechanisms
- **Concurrency Control**: Use semaphores to control concurrency and prevent overloading servers
- **Caching**: Use caching to improve performance and reduce load on servers
- **Configuration**: Use environment variables or configuration files for deployment-specific settings

