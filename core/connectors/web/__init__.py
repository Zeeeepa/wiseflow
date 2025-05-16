"""
Web connector for Wiseflow.

This module provides a connector for web sources using crawl4ai.
"""

from typing import Dict, List, Any, Optional, Union, Tuple
import logging
import uuid
import asyncio
from datetime import datetime
import os
import re
import time
from urllib.parse import urlparse
from collections import defaultdict

from core.plugins import PluginBase
from core.connectors import ConnectorBase, DataItem
from core.crawl4ai import AsyncWebCrawler, CacheMode
from core.crawl4ai.async_configs import AsyncConfigs
from core.utils.general_utils import extract_and_convert_dates, isURL

logger = logging.getLogger(__name__)

class DomainRateLimiter:
    """Rate limiter for domain-specific request throttling."""
    
    def __init__(self, default_rate_limit: int = 60, default_cooldown: float = 1.0):
        """
        Initialize the domain rate limiter.
        
        Args:
            default_rate_limit: Default requests per minute for domains
            default_cooldown: Default cooldown period in seconds between requests
        """
        self.default_rate_limit = default_rate_limit
        self.default_cooldown = default_cooldown
        self.domain_limits = {}  # Domain-specific rate limits
        self.domain_timestamps = defaultdict(list)  # Timestamps of requests per domain
        self.domain_cooldowns = {}  # Domain-specific cooldown periods
        self.lock = asyncio.Lock()
    
    def set_domain_limit(self, domain: str, rate_limit: int, cooldown: float = None):
        """Set domain-specific rate limit."""
        self.domain_limits[domain] = rate_limit
        if cooldown is not None:
            self.domain_cooldowns[domain] = cooldown
    
    def get_domain_limit(self, domain: str) -> int:
        """Get rate limit for a specific domain."""
        return self.domain_limits.get(domain, self.default_rate_limit)
    
    def get_domain_cooldown(self, domain: str) -> float:
        """Get cooldown period for a specific domain."""
        return self.domain_cooldowns.get(domain, self.default_cooldown)
    
    async def register_request(self, domain: str):
        """Register a request to a domain."""
        async with self.lock:
            now = time.time()
            self.domain_timestamps[domain].append(now)
            # Clean up old timestamps
            self.domain_timestamps[domain] = [
                ts for ts in self.domain_timestamps[domain] 
                if now - ts < 60  # Keep only timestamps from the last minute
            ]
    
    async def should_throttle(self, domain: str) -> Tuple[bool, float]:
        """
        Check if requests to a domain should be throttled.
        
        Returns:
            Tuple of (should_throttle, wait_time)
        """
        async with self.lock:
            now = time.time()
            rate_limit = self.get_domain_limit(domain)
            cooldown = self.get_domain_cooldown(domain)
            
            # Clean up old timestamps
            self.domain_timestamps[domain] = [
                ts for ts in self.domain_timestamps[domain] 
                if now - ts < 60  # Keep only timestamps from the last minute
            ]
            
            # Check if we've exceeded the rate limit
            if len(self.domain_timestamps[domain]) >= rate_limit:
                # Calculate time until oldest timestamp expires
                oldest = min(self.domain_timestamps[domain]) if self.domain_timestamps[domain] else now
                wait_time = max(60 - (now - oldest), cooldown)
                return True, wait_time
            
            # Check if we need to apply cooldown
            if self.domain_timestamps[domain]:
                last_request = max(self.domain_timestamps[domain])
                time_since_last = now - last_request
                if time_since_last < cooldown:
                    return True, cooldown - time_since_last
            
            return False, 0
    
    async def adapt_rate_limit(self, domain: str, response_time: float, status_code: int):
        """
        Adapt rate limit based on server response.
        
        Args:
            domain: Domain that was accessed
            response_time: Time taken for the response in seconds
            status_code: HTTP status code
        """
        async with self.lock:
            current_limit = self.get_domain_limit(domain)
            current_cooldown = self.get_domain_cooldown(domain)
            
            # Adjust based on response time
            if response_time > 2.0:  # Slow response
                new_limit = max(5, current_limit // 2)
                new_cooldown = min(5.0, current_cooldown * 1.5)
            elif response_time < 0.5:  # Fast response
                new_limit = min(120, current_limit + 5)
                new_cooldown = max(0.5, current_cooldown * 0.9)
            else:
                return  # No change needed
            
            # Adjust based on status code
            if status_code == 429:  # Too Many Requests
                new_limit = max(3, current_limit // 3)
                new_cooldown = min(10.0, current_cooldown * 3)
            elif status_code >= 500:  # Server errors
                new_limit = max(10, current_limit // 2)
                new_cooldown = min(5.0, current_cooldown * 2)
            
            # Apply new limits
            self.domain_limits[domain] = new_limit
            self.domain_cooldowns[domain] = new_cooldown
            logger.info(f"Adapted rate limit for {domain}: {new_limit} req/min, {new_cooldown:.2f}s cooldown")

class WebConnector(ConnectorBase):
    """Connector for web sources."""
    
    name: str = "web_connector"
    description: str = "Connector for web sources using crawl4ai"
    source_type: str = "web"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the web connector."""
        super().__init__(config or {})
        self.crawler: Optional[AsyncWebCrawler] = None
        self.semaphore = asyncio.Semaphore(self.config.get("concurrency", 5))
        self.rate_limiter = DomainRateLimiter(
            default_rate_limit=self.config.get("default_rate_limit", 60),
            default_cooldown=self.config.get("default_cooldown", 1.0)
        )
        
        # Configure domain-specific rate limits if provided
        domain_limits = self.config.get("domain_rate_limits", {})
        for domain, limit_info in domain_limits.items():
            if isinstance(limit_info, dict):
                rate_limit = limit_info.get("rate_limit")
                cooldown = limit_info.get("cooldown")
                if rate_limit:
                    self.rate_limiter.set_domain_limit(domain, rate_limit, cooldown)
            elif isinstance(limit_info, int):
                self.rate_limiter.set_domain_limit(domain, limit_info)
        
        # Track failed URLs for potential retry
        self.failed_urls = {}
        
        # Statistics for monitoring
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cached_requests": 0,
            "total_processing_time": 0,
            "domains_accessed": set()
        }
    
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
            if self.config.get("proxy"):
                configs.proxy = self.config["proxy"]
            if self.config.get("headers"):
                configs.headers = self.config["headers"]
            
            # Create the crawler
            self.crawler = AsyncWebCrawler(
                config=configs,
                memory_threshold_percent=self.config.get("memory_threshold_percent", 85.0),
                memory_warning_percent=self.config.get("memory_warning_percent", 75.0),
                cooldown_period=self.config.get("cooldown_period", 300),
                max_retries=self.config.get("max_retries", 3),
                retry_delay=self.config.get("retry_delay", 5)
            )
            logger.info(f"Initialized web connector with config: {configs}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize web connector: {e}", exc_info=True)
            return False
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from web sources."""
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
                tasks.append(self._process_url(url, params))
        
        results = []
        if tasks:
            # Gather all results
            url_results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in url_results:
                if isinstance(result, Exception):
                    logger.error(f"Error processing URL batch: {result}", exc_info=True)
                    self.stats["failed_requests"] += 1
                else:
                    results.extend(result)
        
        # Close the crawler
        await self.crawler.close()
        
        logger.info(f"Collected {len(results)} items from web sources")
        return results
    
    async def _process_url(self, url: str, params: Dict[str, Any]) -> List[DataItem]:
        """Process a single URL."""
        async with self.semaphore:
            try:
                # Extract domain for rate limiting
                parsed_url = urlparse(url)
                domain = parsed_url.netloc
                
                # Check if we should throttle requests to this domain
                should_throttle, wait_time = await self.rate_limiter.should_throttle(domain)
                if should_throttle:
                    logger.info(f"Rate limiting applied for {domain}, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                
                # Register this request
                await self.rate_limiter.register_request(domain)
                
                logger.info(f"Crawling URL: {url}")
                self.stats["total_requests"] += 1
                self.stats["domains_accessed"].add(domain)
                
                start_time = time.time()
                
                # Check if URL is a common file type to skip
                common_file_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar', '.tar', '.gz', '.mp3', '.mp4', '.avi', '.mov', '.jpg', '.jpeg', '.png', '.gif', '.svg']
                has_common_ext = any(url.lower().endswith(ext) for ext in common_file_exts)
                if has_common_ext:
                    logger.debug(f'{url} is a common file, skip')
                    return []
                
                # Configure crawler
                crawler_config = AsyncConfigs()
                crawler_config.cache_mode = CacheMode.WRITE_ONLY if params.get("force_refresh", False) else CacheMode.ENABLED
                
                # Add custom headers if provided
                if params.get("headers"):
                    crawler_config.headers = params["headers"]
                
                # Add custom timeout if provided
                if params.get("timeout"):
                    crawler_config.timeout = params["timeout"]
                
                # Crawl the URL
                try:
                    result = await self.crawler.arun(url=url, config=crawler_config)
                    
                    # Update rate limiter based on response
                    response_time = time.time() - start_time
                    status_code = getattr(result, "status_code", 200)  # Default to 200 if not available
                    await self.rate_limiter.adapt_rate_limit(domain, response_time, status_code)
                    
                except Exception as e:
                    logger.error(f"Error crawling URL {url}: {e}", exc_info=True)
                    self.stats["failed_requests"] += 1
                    self.failed_urls[url] = {
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                        "attempts": self.failed_urls.get(url, {}).get("attempts", 0) + 1
                    }
                    return []
                
                if not result.success:
                    logger.warning(f'{url} failed to crawl')
                    self.stats["failed_requests"] += 1
                    self.failed_urls[url] = {
                        "error": result.error_message or "Unknown error",
                        "timestamp": datetime.now().isoformat(),
                        "attempts": self.failed_urls.get(url, {}).get("attempts", 0) + 1
                    }
                    return []
                
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
                if not base_url:
                    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                if not author:
                    author = parsed_url.netloc
                
                # Convert publish date to standard format
                publish_date = extract_and_convert_dates(publish_date)
                
                # Update statistics
                self.stats["successful_requests"] += 1
                self.stats["total_processing_time"] += (time.time() - start_time)
                
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
                        "processing_time": time.time() - start_time,
                        "word_count": len(raw_markdown.split()) if raw_markdown else 0,
                        "domain": domain,
                        "status_code": getattr(result, "status_code", None),
                        "content_type": metadata_dict.get("content_type"),
                        "language": metadata_dict.get("language")
                    },
                    url=url,
                    content_type="text/markdown",
                    language=metadata_dict.get("language")
                )
                
                return [item]
            except Exception as e:
                logger.error(f"Error processing URL {url}: {e}", exc_info=True)
                self.stats["failed_requests"] += 1
                return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get connector statistics."""
        stats = self.stats.copy()
        stats["domains_accessed"] = list(stats["domains_accessed"])
        stats["avg_processing_time"] = (
            stats["total_processing_time"] / stats["successful_requests"] 
            if stats["successful_requests"] > 0 else 0
        )
        stats["success_rate"] = (
            stats["successful_requests"] / stats["total_requests"] * 100
            if stats["total_requests"] > 0 else 0
        )
        return stats
    
    async def retry_failed_urls(self, max_age_minutes: int = 60) -> List[DataItem]:
        """
        Retry URLs that previously failed.
        
        Args:
            max_age_minutes: Only retry URLs that failed within this many minutes
        
        Returns:
            List of DataItems from successful retries
        """
        now = datetime.now()
        urls_to_retry = []
        
        for url, info in self.failed_urls.items():
            # Skip URLs that have been attempted too many times
            if info.get("attempts", 0) >= self.retry_count:
                continue
                
            # Skip URLs that are too old
            try:
                timestamp = datetime.fromisoformat(info["timestamp"])
                age_minutes = (now - timestamp).total_seconds() / 60
                if age_minutes > max_age_minutes:
                    continue
            except (ValueError, KeyError):
                continue
                
            urls_to_retry.append(url)
        
        if not urls_to_retry:
            return []
            
        logger.info(f"Retrying {len(urls_to_retry)} previously failed URLs")
        return await self.collect({"urls": urls_to_retry, "force_refresh": True})
    
    async def shutdown(self) -> bool:
        """Shutdown the connector and release resources."""
        if self.crawler:
            try:
                await self.crawler.close()
                return True
            except Exception as e:
                logger.error(f"Error shutting down web connector: {e}", exc_info=True)
                return False
        return True
