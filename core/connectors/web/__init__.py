"""
Web connector for Wiseflow.

This module provides a connector for web sources using crawl4ai with enhanced concurrency and error handling.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import uuid
import asyncio
from datetime import datetime
import os
import re
import time
from urllib.parse import urlparse
import traceback

from core.plugins import PluginBase
from core.connectors import ConnectorBase, DataItem
from core.crawl4ai import AsyncWebCrawler, CacheMode
from core.crawl4ai.async_configs import AsyncConfigs
from core.utils.general_utils import extract_and_convert_dates, isURL

logger = logging.getLogger(__name__)

class WebConnector(ConnectorBase):
    """Connector for web sources with enhanced concurrency and error handling."""
    
    name: str = "web_connector"
    description: str = "Enhanced connector for web sources using crawl4ai"
    source_type: str = "web"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the web connector."""
        super().__init__(config)
        self.crawler: Optional[AsyncWebCrawler] = None
        
        # Enhanced concurrency settings
        self.concurrency = self.config.get("concurrency", 5)
        self.semaphore = asyncio.Semaphore(self.concurrency)
        self.retry_count = self.config.get("retry_count", 3)
        self.retry_delay = self.config.get("retry_delay", 5)
        self.timeout = self.config.get("timeout", 60)
        
        # Rate limiting
        self.rate_limit = self.config.get("rate_limit", 10)  # requests per minute
        self.rate_limit_semaphore = asyncio.Semaphore(self.rate_limit)
        self.rate_limit_reset_task = None
        
        # Error tracking
        self.error_counts: Dict[str, int] = {}
        self.error_domains: Dict[str, datetime] = {}
        self.max_domain_errors = self.config.get("max_domain_errors", 5)
        self.domain_error_timeout = self.config.get("domain_error_timeout", 3600)  # 1 hour
        
    def initialize(self) -> bool:
        """Initialize the connector."""
        try:
            # Create the crawler
            configs = AsyncConfigs()
            
            # Apply custom configurations if provided
            if self.config.get("max_depth"):
                configs.max_depth = self.config["max_depth"]
            if self.config.get("max_pages"):
                configs.max_pages = self.config["max_pages"]
            if self.config.get("timeout"):
                configs.timeout = self.config["timeout"]
            if self.config.get("user_agent"):
                configs.user_agent = self.config["user_agent"]
            if self.config.get("javascript_enabled") is not None:
                configs.javascript_enabled = self.config["javascript_enabled"]
            if self.config.get("wait_for_selector"):
                configs.wait_for_selector = self.config["wait_for_selector"]
            if self.config.get("wait_time"):
                configs.wait_time = self.config["wait_time"]
            
            # Create the crawler
            self.crawler = AsyncWebCrawler(config=configs)
            
            # Start rate limit reset task
            if self.rate_limit_reset_task is None:
                self.rate_limit_reset_task = asyncio.create_task(self._reset_rate_limit())
            
            logger.info(f"Initialized enhanced web connector with concurrency: {self.concurrency}, retry_count: {self.retry_count}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize web connector: {e}")
            return False
    
    async def _reset_rate_limit(self):
        """Reset rate limit semaphore periodically."""
        while True:
            await asyncio.sleep(60)  # Reset every minute
            
            # Reset the semaphore
            current_value = self.rate_limit_semaphore._value
            for _ in range(self.rate_limit - current_value):
                self.rate_limit_semaphore.release()
            
            # Reset any domain error timeouts that have expired
            current_time = datetime.now()
            expired_domains = [domain for domain, timeout in self.error_domains.items() 
                              if (current_time - timeout).total_seconds() > self.domain_error_timeout]
            
            for domain in expired_domains:
                if domain in self.error_domains:
                    del self.error_domains[domain]
                if domain in self.error_counts:
                    del self.error_counts[domain]
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from web sources with enhanced concurrency and error handling."""
        params = params or {}
        urls = params.get("urls", [])
        if not urls:
            if self.config.get("urls"):
                urls = self.config["urls"]
            else:
                logger.error("No URLs provided for web connector")
                return []
        
        if not self.crawler:
            if not self.initialize():
                return []
        
        # Start the crawler
        await self.crawler.start()
        
        # Process URLs concurrently with semaphore to control concurrency
        tasks = []
        for url in urls:
            if isURL(url):
                # Check if domain is in error timeout
                domain = urlparse(url).netloc
                if domain in self.error_domains:
                    logger.warning(f"Domain {domain} is in error timeout, skipping URL: {url}")
                    continue
                
                tasks.append(self._process_url(url, params))
        
        results = []
        if tasks:
            # Gather all results
            url_results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in url_results:
                if isinstance(result, Exception):
                    logger.error(f"Error processing URL: {result}")
                elif isinstance(result, list):
                    results.extend(result)
        
        # Close the crawler
        await self.crawler.close()
        
        logger.info(f"Collected {len(results)} items from web sources")
        return results
    
    async def _process_url(self, url: str, params: Dict[str, Any]) -> List[DataItem]:
        """Process a single URL with retries and error handling."""
        async with self.semaphore:
            # Apply rate limiting
            async with self.rate_limit_semaphore:
                domain = urlparse(url).netloc
                
                # Check common file types to skip
                common_file_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar', '.tar', '.gz', '.mp3', '.mp4', '.avi', '.mov', '.jpg', '.jpeg', '.png', '.gif', '.svg']
                has_common_ext = any(url.lower().endswith(ext) for ext in common_file_exts)
                if has_common_ext:
                    logger.debug(f'{url} is a common file, skip')
                    return []
                
                # Implement retry logic
                for attempt in range(self.retry_count):
                    try:
                        logger.info(f"Crawling URL: {url} (attempt {attempt + 1}/{self.retry_count})")
                        
                        # Configure crawler
                        crawler_config = AsyncConfigs()
                        crawler_config.cache_mode = CacheMode.WRITE_ONLY if params.get("force_refresh", False) else CacheMode.ENABLED
                        crawler_config.timeout = self.timeout
                        
                        # Crawl the URL
                        result = await self.crawler.arun(url=url, config=crawler_config)
                        
                        if not result.success:
                            logger.warning(f'{url} failed to crawl on attempt {attempt + 1}')
                            
                            # Track domain errors
                            if domain not in self.error_counts:
                                self.error_counts[domain] = 0
                            self.error_counts[domain] += 1
                            
                            # Check if domain has too many errors
                            if self.error_counts[domain] >= self.max_domain_errors:
                                logger.warning(f"Domain {domain} has reached error threshold, adding to timeout")
                                self.error_domains[domain] = datetime.now()
                            
                            # Wait before retry
                            if attempt < self.retry_count - 1:
                                await asyncio.sleep(self.retry_delay * (attempt + 1))
                            continue
                        
                        # Process the result
                        metadata_dict = result.metadata if result.metadata else {}
                        raw_markdown = result.markdown
                        media_dict = result.media if result.media else {}
                        used_img = [d['src'] for d in media_dict.get('images', [])]
                        
                        # Extract metadata
                        title = metadata_dict.get('title', '')
                        base_url = metadata_dict.get('base', '')
                        author = metadata_dict.get('author', '')
                        publish_date = metadata_dict.get('publish_date', '')
                        
                        # Parse URL for fallback metadata
                        parsed_url = urlparse(url)
                        if not base_url:
                            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                        if not author:
                            author = parsed_url.netloc
                        
                        # Convert publish date to standard format
                        publish_date = extract_and_convert_dates(publish_date)
                        
                        # Create a data item
                        item = DataItem(
                            source_id=f"web_{uuid.uuid4().hex[:8]}",
                            content=raw_markdown,
                            metadata={
                                "title": title,
                                "author": author,
                                "publish_date": publish_date,
                                "base_url": base_url,
                                "images": used_img,
                                "crawl_time": datetime.now().isoformat(),
                                "attempt": attempt + 1,
                                "domain": domain
                            },
                            url=url,
                            content_type="text/markdown",
                            language=metadata_dict.get("language")
                        )
                        
                        # Reset error count for successful domain
                        if domain in self.error_counts:
                            self.error_counts[domain] = 0
                        
                        return [item]
                    
                    except asyncio.CancelledError:
                        logger.warning(f"Task for URL {url} was cancelled")
                        raise
                    except Exception as e:
                        logger.error(f"Error processing URL {url} on attempt {attempt + 1}: {e}")
                        logger.debug(traceback.format_exc())
                        
                        # Track domain errors
                        if domain not in self.error_counts:
                            self.error_counts[domain] = 0
                        self.error_counts[domain] += 1
                        
                        # Check if domain has too many errors
                        if self.error_counts[domain] >= self.max_domain_errors:
                            logger.warning(f"Domain {domain} has reached error threshold, adding to timeout")
                            self.error_domains[domain] = datetime.now()
                        
                        # Wait before retry
                        if attempt < self.retry_count - 1:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                
                logger.error(f"Failed to process URL {url} after {self.retry_count} attempts")
                return []
    
    async def close(self):
        """Close the connector and release resources."""
        if self.rate_limit_reset_task:
            self.rate_limit_reset_task.cancel()
            try:
                await self.rate_limit_reset_task
            except asyncio.CancelledError:
                pass
            self.rate_limit_reset_task = None
        
        if self.crawler:
            await self.crawler.close()
