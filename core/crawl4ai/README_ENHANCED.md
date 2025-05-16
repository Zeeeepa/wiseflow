# Enhanced Web Connector

This document describes the enhanced web connector implementation for the Wiseflow codebase, which addresses performance, error handling, and integration issues.

## Overview

The enhanced web connector provides the following improvements:

1. **Performance Optimization**
   - Domain-specific rate limiting
   - Adaptive rate limiting based on server responses
   - Browser context reuse and management
   - Memory usage monitoring and optimization
   - Content caching for repeated requests

2. **Error Handling Enhancement**
   - Comprehensive exception handling
   - Detailed error classification and reporting
   - Automatic retry with exponential backoff
   - Recovery mechanisms for various failure scenarios
   - Graceful degradation for non-critical failures

3. **Content Extraction Improvement**
   - Main content detection for better accuracy
   - Enhanced image processing and relevance scoring
   - Improved metadata extraction
   - Better text cleaning and normalization
   - Support for different content types

4. **Resource Management Optimization**
   - Efficient browser context management
   - Automatic resource cleanup
   - Memory usage tracking and throttling
   - Connection pooling for HTTP requests
   - Proper cleanup in error scenarios

5. **Integration Enhancement**
   - Clear interfaces between components
   - Consistent data formats
   - Validation for data passed between components
   - Detailed performance metrics
   - Health monitoring capabilities

## Components

The enhanced implementation consists of the following components:

1. **WebConnector** (`core/connectors/web/__init__.py`)
   - Main entry point for web crawling
   - Handles URL processing and rate limiting
   - Manages statistics and failed URLs
   - Provides retry capabilities

2. **DomainRateLimiter** (`core/connectors/web/__init__.py`)
   - Implements domain-specific rate limiting
   - Provides adaptive rate limiting based on server responses
   - Manages cooldown periods for domains

3. **AsyncWebCrawler** (`core/crawl4ai/async_webcrawler.py`)
   - Manages browser resources and memory
   - Implements caching and retry logic
   - Monitors system resources
   - Handles browser restarts

4. **EnhancedCrawlerStrategy** (`core/crawl4ai/enhanced_crawler_strategy.py`)
   - Implements improved browser automation
   - Provides detailed response analysis
   - Manages browser contexts efficiently
   - Tracks performance metrics

5. **EnhancedWebScrapingStrategy** (`core/crawl4ai/enhanced_content_scraping.py`)
   - Implements improved content extraction
   - Detects main content areas
   - Processes images with relevance scoring
   - Cleans and normalizes text content

6. **Integration Factory** (`core/crawl4ai/enhanced_web_connector.py`)
   - Provides a factory function to create an enhanced web connector
   - Integrates all enhanced components
   - Configures components with appropriate settings

## Usage

To use the enhanced web connector:

```python
from core.crawl4ai.enhanced_web_connector import create_enhanced_web_connector

# Create an enhanced web connector
config = {
    "concurrency": 5,
    "default_rate_limit": 60,
    "domain_rate_limits": {
        "example.com": {"rate_limit": 10, "cooldown": 2.0}
    },
    "max_depth": 2,
    "timeout": 30,
    "javascript_enabled": True
}

connector = create_enhanced_web_connector(config)

# Use the connector
results = await connector.collect({"urls": ["https://example.com"]})
```

## Performance Metrics

The enhanced web connector provides detailed performance metrics:

```python
# Get connector statistics
stats = await connector.get_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Success rate: {stats['success_rate']}%")
print(f"Average processing time: {stats['avg_processing_time']:.2f}s")

# Get crawler performance metrics
crawler_metrics = await connector.crawler.get_resource_stats()
print(f"Peak memory usage: {crawler_metrics['peak_memory_percent']}%")
print(f"Browser restarts: {crawler_metrics['browser_restarts']}")

# Get crawler strategy performance metrics
strategy_metrics = await connector.crawler.crawler_strategy.get_performance_metrics()
print(f"Average page load time: {strategy_metrics['avg_page_load_time']:.2f}s")
print(f"Status codes: {strategy_metrics['status_codes']}")
```

## Testing

Unit tests for the enhanced web connector are provided in `tests/core/connectors/test_web_connector.py`. These tests cover:

- Domain rate limiter functionality
- Web connector initialization and configuration
- URL processing and error handling
- Statistics and metrics collection
- Retry mechanisms

To run the tests:

```bash
python -m unittest tests/core/connectors/test_web_connector.py
```

## Future Improvements

Potential future improvements include:

1. **Distributed Crawling**
   - Implement a distributed crawling architecture
   - Add support for multiple worker nodes
   - Implement a job queue for crawling tasks

2. **Advanced Content Analysis**
   - Add support for semantic content analysis
   - Implement content classification
   - Add support for entity extraction

3. **Improved Browser Management**
   - Add support for browser profiles
   - Implement browser fingerprint randomization
   - Add support for proxy rotation

4. **Enhanced Monitoring**
   - Add support for real-time monitoring
   - Implement alerting for critical issues
   - Add support for performance dashboards

