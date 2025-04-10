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
from core.utils.general_utils import extract_and_convert_dates, isURL

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
        self.semaphore = asyncio.Semaphore(self.config.get("concurrency", 5))
        
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
            logger.info(f"Initialized web connector with config: {configs}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize web connector: {e}")
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
            url_results = await asyncio.gather(*tasks)
            for items in url_results:
                results.extend(items)
        
        # Close the crawler
        await self.crawler.close()
        
        logger.info(f"Collected {len(results)} items from web sources")
        return results
    
    async def _process_url(self, url: str, params: Dict[str, Any]) -> List[DataItem]:
        """Process a single URL."""
        async with self.semaphore:
            try:
                logger.info(f"Crawling URL: {url}")
                
                # Check if URL is a common file type to skip
                common_file_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar', '.tar', '.gz', '.mp3', '.mp4', '.avi', '.mov', '.jpg', '.jpeg', '.png', '.gif', '.svg']
                has_common_ext = any(url.lower().endswith(ext) for ext in common_file_exts)
                if has_common_ext:
                    logger.debug(f'{url} is a common file, skip')
                    return []
                
                # Configure crawler
                crawler_config = AsyncConfigs()
                crawler_config.cache_mode = CacheMode.WRITE_ONLY if params.get("force_refresh", False) else CacheMode.ENABLED
                
                # Crawl the URL
                try:
                    result = await self.crawler.arun(url=url, config=crawler_config)
                except Exception as e:
                    logger.error(f"Error crawling URL {url}: {e}")
                    return []
                
                if not result.success:
                    logger.warning(f'{url} failed to crawl')
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
                        "crawl_time": datetime.now().isoformat()
                    },
                    url=url,
                    content_type="text/markdown",
                    language=metadata_dict.get("language")
                )
                
                return [item]
            except Exception as e:
                logger.error(f"Error processing URL {url}: {e}")
                return []
