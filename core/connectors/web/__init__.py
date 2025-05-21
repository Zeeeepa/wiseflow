"""
Web connector for Wiseflow.

This module provides a connector for web sources using crawl4ai.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import uuid
import asyncio
from datetime import datetime
import os
import re
from urllib.parse import urlparse

from core.plugins import PluginBase
from core.connectors import ConnectorBase, DataItem
from core.crawl4ai import AsyncWebCrawler, CacheMode
from core.crawl4ai.async_configs import AsyncConfigs
from core.crawl4ai.config_manager import ConfigManager
from core.crawl4ai.url_utils import is_valid_url, normalize_url, is_file_url, filter_urls
from core.crawl4ai.errors import Crawl4AIError, NetworkError, ValidationError
from core.utils.general_utils import extract_and_convert_dates

logger = logging.getLogger(__name__)

class WebConnector(ConnectorBase):
    """Connector for web sources."""
    
    name: str = "web_connector"
    description: str = "Connector for web sources using crawl4ai"
    source_type: str = "web"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the web connector."""
        super().__init__(config)
        self.crawler: Optional[AsyncWebCrawler] = None
        self.config_manager = None
        
        # Initialize semaphore for concurrency control
        concurrency = self.config.get("concurrency", 5)
        self.semaphore = asyncio.Semaphore(concurrency)
        
        # Track active tasks for proper cleanup
        self._active_tasks = set()
        self._task_lock = asyncio.Lock()
        
    def initialize(self) -> bool:
        """Initialize the connector."""
        try:
            # Create config manager
            base_directory = self.config.get("base_directory", os.getenv("PROJECT_DIR", ""))
            config_path = self.config.get("config_path")
            self.config_manager = ConfigManager(config_path, base_directory)
            
            # Apply custom configurations from connector config
            crawler_config = self.config_manager.get_crawler_config()
            
            # Override with connector config if provided
            if self.config.get("max_depth") is not None:
                crawler_config["max_depth"] = self.config["max_depth"]
            if self.config.get("max_pages") is not None:
                crawler_config["max_pages"] = self.config["max_pages"]
            if self.config.get("timeout") is not None:
                crawler_config["timeout"] = self.config["timeout"]
            if self.config.get("concurrency") is not None:
                crawler_config["concurrency"] = self.config["concurrency"]
                # Update semaphore if concurrency changed
                self.semaphore = asyncio.Semaphore(crawler_config["concurrency"])
            
            # Apply browser config
            browser_config = self.config_manager.get_browser_config()
            if self.config.get("user_agent") is not None:
                browser_config["user_agent"] = self.config["user_agent"]
            if self.config.get("javascript_enabled") is not None:
                browser_config["javascript_enabled"] = self.config["javascript_enabled"]
            if self.config.get("wait_for_selector") is not None:
                browser_config["wait_for_selector"] = self.config["wait_for_selector"]
            if self.config.get("wait_time") is not None:
                browser_config["wait_time"] = self.config["wait_time"]
            
            # Create AsyncConfigs from config manager
            configs = AsyncConfigs()
            configs.max_depth = crawler_config.get("max_depth", 1)
            configs.max_pages = crawler_config.get("max_pages", 10)
            configs.timeout = crawler_config.get("timeout", 60000)
            configs.user_agent = browser_config.get("user_agent", configs.user_agent)
            configs.javascript_enabled = browser_config.get("javascript_enabled", True)
            configs.wait_for_selector = browser_config.get("wait_for_selector", "")
            configs.wait_time = browser_config.get("wait_time", 0)
            
            # Create the crawler with enhanced configuration
            self.crawler = AsyncWebCrawler(
                config=configs,
                base_directory=base_directory,
                thread_safe=True,
                memory_threshold_percent=crawler_config.get("memory_threshold_percent", 85.0),
                memory_warning_percent=crawler_config.get("memory_warning_percent", 75.0),
                memory_check_interval=crawler_config.get("memory_check_interval", 10.0),
                cooldown_period=crawler_config.get("cooldown_period", 300),
                max_retries=crawler_config.get("retry_attempts", 3),
                retry_delay=crawler_config.get("retry_delay", 5),
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
        
        # Get URLs from config if not provided in params
        if not urls:
            if self.config.get("urls"):
                urls = self.config["urls"]
            else:
                logger.error("No URLs provided for web connector")
                return []
        
        # Initialize crawler if not already initialized
        if not self.crawler:
            if not self.initialize():
                logger.error("Failed to initialize crawler")
                return []
        
        # Start the crawler
        try:
            await self.crawler.start()
            
            # Filter and validate URLs
            exclude_file_urls = params.get("exclude_file_urls", True)
            exclude_social_media = params.get("exclude_social_media", False)
            exclude_domains = set(params.get("exclude_domains", []))
            
            filtered_urls = filter_urls(
                urls,
                exclude_social_media=exclude_social_media,
                exclude_file_urls=exclude_file_urls,
                exclude_domains=exclude_domains
            )
            
            if not filtered_urls:
                logger.warning("No valid URLs to process after filtering")
                return []
            
            logger.info(f"Processing {len(filtered_urls)} URLs after filtering")
            
            # Process URLs concurrently with semaphore to control concurrency
            tasks = []
            for url in filtered_urls:
                task = asyncio.create_task(self._process_url(url, params))
                tasks.append(task)
                
                # Track active tasks for proper cleanup
                async with self._task_lock:
                    self._active_tasks.add(task)
                    task.add_done_callback(lambda t: self._remove_task(t))
            
            # Gather all results
            results = []
            if tasks:
                url_results = await asyncio.gather(*tasks, return_exceptions=True)
                for items in url_results:
                    # Skip exceptions
                    if isinstance(items, Exception):
                        logger.error(f"Error processing URL: {items}")
                        continue
                    
                    # Add valid results
                    if isinstance(items, list):
                        results.extend(items)
            
            logger.info(f"Collected {len(results)} items from web sources")
            return results
        except Exception as e:
            logger.error(f"Error collecting data from web sources: {e}", exc_info=True)
            return []
        finally:
            # Ensure crawler is closed properly
            try:
                await self.crawler.close()
            except Exception as e:
                logger.error(f"Error closing crawler: {e}", exc_info=True)
    
    def _remove_task(self, task):
        """Remove a task from the active tasks set."""
        asyncio.create_task(self._remove_task_async(task))
    
    async def _remove_task_async(self, task):
        """Asynchronously remove a task from the active tasks set."""
        async with self._task_lock:
            self._active_tasks.discard(task)
    
    async def _process_url(self, url: str, params: Dict[str, Any]) -> List[DataItem]:
        """Process a single URL."""
        async with self.semaphore:
            try:
                logger.info(f"Crawling URL: {url}")
                
                # Normalize URL
                try:
                    normalized_url = normalize_url(url)
                except ValidationError as e:
                    logger.warning(f"Invalid URL {url}: {e}")
                    return []
                
                # Check if URL is a common file type to skip
                if is_file_url(normalized_url):
                    logger.debug(f'{url} is a file URL, skipping')
                    return []
                
                # Configure crawler
                crawler_config = AsyncConfigs()
                
                # Set cache mode based on params
                force_refresh = params.get("force_refresh", False)
                crawler_config.cache_mode = CacheMode.WRITE_ONLY if force_refresh else CacheMode.ENABLED
                
                # Set timeout from params or config
                timeout = params.get("timeout", self.config.get("timeout"))
                if timeout:
                    crawler_config.page_timeout = timeout
                
                # Set other crawler options from params
                for key in ["wait_until", "wait_for", "javascript_enabled", "user_agent"]:
                    if params.get(key) is not None:
                        setattr(crawler_config, key, params[key])
                
                # Crawl the URL with proper error handling
                try:
                    result = await self.crawler.arun(url=normalized_url, config=crawler_config)
                except Crawl4AIError as e:
                    logger.error(f"Crawl4AI error for URL {url}: {e}")
                    return []
                except asyncio.TimeoutError:
                    logger.error(f"Timeout crawling URL {url}")
                    return []
                except Exception as e:
                    logger.error(f"Unexpected error crawling URL {url}: {e}", exc_info=True)
                    return []
                
                if not result.success:
                    logger.warning(f'{url} failed to crawl: {result.error_message}')
                    return []
                
                # Process the result
                metadata_dict = result.metadata if result.metadata else {}
                raw_markdown = result.markdown
                media_dict = result.media if result.media else {}
                used_img = [d['src'] for d in media_dict.get('images', [])] if isinstance(media_dict.get('images', []), list) else []
                
                # Extract metadata with better error handling
                title = metadata_dict.get('title', '')
                base_url = metadata_dict.get('base', '')
                author = metadata_dict.get('author', '')
                publish_date = metadata_dict.get('publish_date', '')
                
                # Parse URL for fallback metadata
                try:
                    parsed_url = urlparse(url)
                    if not base_url:
                        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                    if not author:
                        author = parsed_url.netloc
                except Exception as e:
                    logger.warning(f"Error parsing URL {url}: {e}")
                    if not base_url:
                        base_url = url
                    if not author:
                        author = "unknown"
                
                # Convert publish date to standard format with error handling
                try:
                    publish_date = extract_and_convert_dates(publish_date)
                except Exception as e:
                    logger.warning(f"Error converting publish date for {url}: {e}")
                    publish_date = ""
                
                # Create a data item with comprehensive metadata
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
                        "url": url,
                        "normalized_url": normalized_url,
                        "redirected_url": result.redirected_url if result.redirected_url else url,
                        "content_length": len(raw_markdown) if raw_markdown else 0,
                        "html_length": len(result.html) if result.html else 0,
                        "ssl_certificate": result.ssl_certificate if hasattr(result, 'ssl_certificate') else None,
                    },
                    url=url,
                    content_type="text/markdown",
                    language=metadata_dict.get("language")
                )
                
                return [item]
            except Exception as e:
                logger.error(f"Error processing URL {url}: {e}", exc_info=True)
                return []
