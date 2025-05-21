import asyncio
import os
from core.crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from core.crawl4ai.crawlers.google_search import GoogleSearchCrawler

async def test_web_crawler():
    """Test the AsyncWebCrawler functionality."""
    print("Testing AsyncWebCrawler...")
    
    browser_config = BrowserConfig(headless=True)
    async with AsyncWebCrawler(config=browser_config) as crawler:
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            delay_before_return_html=2
        )
        
        result = await crawler.arun(url="https://example.com", config=config)
        
        if result.success:
            print("✅ AsyncWebCrawler test passed!")
            print(f"Title: {result.metadata.get('title', 'No title')}")
            print(f"Content length: {len(result.html)} characters")
        else:
            print("❌ AsyncWebCrawler test failed!")
            print(f"Error: {result.error_message}")

async def test_google_search_crawler():
    """Test the GoogleSearchCrawler functionality."""
    print("\nTesting GoogleSearchCrawler...")
    
    try:
        crawler = GoogleSearchCrawler()
        result = await crawler.run(query="python programming")
        
        if result:
            print("✅ GoogleSearchCrawler test passed!")
            print(f"Result length: {len(result)} characters")
        else:
            print("❌ GoogleSearchCrawler test failed!")
            print("No result returned")
    except Exception as e:
        print(f"❌ GoogleSearchCrawler test failed with error: {str(e)}")

async def main():
    """Run all tests."""
    print("=== Crawl4AI Module Tests ===")
    
    await test_web_crawler()
    await test_google_search_crawler()
    
    print("\n=== Tests completed ===")

if __name__ == "__main__":
    asyncio.run(main())

