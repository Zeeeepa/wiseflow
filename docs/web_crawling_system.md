# WiseFlow Web Crawling and Data Collection System

This document provides an overview of the web crawling and data collection system in WiseFlow.

## Architecture

The web crawling system consists of several components:

1. **AsyncWebCrawler**: The main entry point for crawling web pages. It manages the crawling process, handles memory usage, and provides retry logic for failed requests.

2. **Content Scraping Strategies**: Responsible for extracting content from web pages. Different strategies can be used for different types of content.

3. **Database Management**: Handles caching of crawled content to avoid redundant requests.

4. **HTML to Text Conversion**: Converts HTML content to Markdown for easier processing.

5. **PDF Processing**: Extracts text and images from PDF files.

6. **Specialized Scrapers**: Custom scrapers for specific content types (e.g., WeChat MP articles).

## Key Components

### AsyncWebCrawler

The `AsyncWebCrawler` class in `core/crawl4ai/async_webcrawler.py` is the main entry point for crawling web pages. It provides:

- Memory management to prevent excessive memory usage
- Retry logic for failed requests with exponential backoff
- Resource cleanup to prevent memory leaks
- Domain-specific cooldown periods to prevent overloading websites

Usage:

```python
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def crawl_example():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com", CrawlerRunConfig())
        print(result.html)
```

### Content Scraping Strategies

The `ContentScrapingStrategy` class in `core/crawl4ai/content_scraping_strategy.py` defines the interface for content extraction. The `WebScrapingStrategy` class provides a default implementation.

### Database Management

The `AsyncDatabaseManager` class in `core/crawl4ai/async_database.py` handles caching of crawled content. It uses SQLite with WAL mode for better performance and provides retry logic for database operations.

### PDF Processing

The `NaivePDFProcessorStrategy` class in `core/crawl4ai/processors/pdf/processor.py` handles extraction of text and images from PDF files. It uses PyPDF2 for PDF processing.

## Error Handling

The system includes robust error handling:

1. **Retry Logic**: Failed requests are retried with exponential backoff.
2. **Memory Management**: High memory usage triggers cooldown periods and garbage collection.
3. **Resource Cleanup**: Resources are properly released to prevent memory leaks.
4. **Database Connection Management**: Database connections are properly managed to prevent connection leaks.

## Rate Limiting

The system includes several mechanisms to prevent overloading websites:

1. **Domain-Specific Cooldown**: Each domain has a cooldown period to prevent too many requests in a short time.
2. **Robots.txt Compliance**: The system respects robots.txt directives.
3. **Memory-Based Rate Limiting**: High memory usage triggers cooldown periods.

## Best Practices

1. **Use Caching**: Enable caching to avoid redundant requests.
2. **Set Appropriate Timeouts**: Set appropriate timeouts for requests to prevent hanging.
3. **Handle Errors**: Always handle errors and provide fallback mechanisms.
4. **Clean Up Resources**: Always clean up resources to prevent memory leaks.
5. **Respect Website Policies**: Always respect robots.txt directives and rate limits.

## Example Usage

```python
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

async def main():
    # Create a crawler with default settings
    async with AsyncWebCrawler() as crawler:
        # Create a configuration with caching enabled
        config = CrawlerRunConfig(cache_mode=CacheMode.READ_WRITE)
        
        # Crawl a URL
        result = await crawler.arun("https://example.com", config)
        
        # Print the result
        print(f"Title: {result.metadata.get('title', 'No title')}")
        print(f"Content length: {len(result.html)}")
        
        # Extract images
        images = result.media.get('images', [])
        print(f"Found {len(images)} images")

if __name__ == "__main__":
    asyncio.run(main())
```

## Troubleshooting

### Common Issues

1. **Memory Leaks**: If you experience memory leaks, make sure you're properly closing the crawler using the `async with` statement or calling `await crawler.close()`.

2. **Database Errors**: If you experience database errors, try clearing the cache by deleting the `.crawl4ai` directory.

3. **Rate Limiting**: If you're being rate limited, try increasing the cooldown period or using a proxy.

4. **PDF Processing Errors**: If you experience PDF processing errors, make sure you have PyPDF2 installed (`pip install crawl4ai[pdf]`).

### Logging

The system uses a custom logger that writes to both the console and a log file. You can enable verbose logging by setting the `verbose` parameter to `True` when creating the crawler:

```python
crawler = AsyncWebCrawler(verbose=True)
```

Log files are stored in the `.crawl4ai` directory.

