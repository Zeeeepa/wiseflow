"""
AsyncWebCrawler module for Wiseflow.

This module provides an asynchronous web crawler for fetching web content.
"""

import os
import time
import psutil
from colorama import Fore
from typing import Optional, Dict, List, Any, Tuple
import asyncio
import gc
import logging
import traceback

# from contextlib import nullcontext, asynccontextmanager
from contextlib import asynccontextmanager

from .async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from .async_crawler_strategy import CrawlerStrategy
from .async_database import AsyncDatabaseManager
from .async_logger import AsyncLogger
from .cache_context import CacheContext
from .models import CrawlResult
from .ssl_certificate import get_ssl_certificate
from .utils import (
    sanitize_input_encode,
    create_box_message,
    get_domain_from_url,
    get_base_url,
    get_url_path,
)


class AsyncWebCrawler:
    """
    Asynchronous web crawler for fetching web content.
    
    This class provides an asynchronous web crawler that can fetch web content
    with caching, error handling, and resource management.
    """

    _domain_last_hit = {}
    # Track memory usage over time for better decision making
    _memory_history: List[float] = []
    # Maximum number of memory history points to keep
    _max_memory_history_size = 10
    # Domain-specific cooldown tracking
    _domain_cooldowns: Dict[str, float] = {}

    def __init__(
        self,
        config: Optional[BrowserConfig] = None,
        base_directory: str = os.getenv("PROJECT_DIR", ''),
        thread_safe: bool = False,
        memory_threshold_percent: float = 85.0,
        memory_warning_percent: float = 75.0,
        memory_check_interval: float = 10.0,
        cooldown_period: int = 300,  # 5 minutes in seconds
        max_retries: int = 3,
        retry_delay: int = 5,
        **kwargs,
    ):
        """
        Initialize the AsyncWebCrawler.
        
        Args:
            config: Browser configuration
            base_directory: Base directory for storing cache
            thread_safe: Whether to use thread-safe operations
            memory_threshold_percent: Percentage of memory usage that triggers cooldown
            memory_warning_percent: Percentage of memory usage that triggers a warning
            memory_check_interval: How often to check memory usage (in seconds)
            cooldown_period: How long to wait during cooldown (in seconds)
            max_retries: Maximum number of retries for failed requests
            retry_delay: Delay between retries (in seconds)
            **kwargs: Additional arguments for backwards compatibility
        """

        self.memory_threshold_percent = memory_threshold_percent
        self.memory_warning_percent = memory_warning_percent
        self.memory_check_interval = memory_check_interval
        self.cooldown_period = cooldown_period
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.browser_config = config or BrowserConfig()
        
        # Initialize logger first since other components may need it
        self.logger = AsyncLogger(
            log_file=os.path.join(base_directory, ".crawl4ai", "crawler.log"),
            console=True,
        )

        # Initialize database manager
        self.async_db_manager = AsyncDatabaseManager(
            base_directory=base_directory,
            logger=self.logger,
        )

        # Initialize crawler strategy
        self.crawler_strategy = CrawlerStrategy(
            browser_config=self.browser_config,
            logger=self.logger,
            **kwargs,  # Pass remaining kwargs for backwards compatibility
        )

        # If crawler strategy doesn't have logger, use crawler logger
        if not self.crawler_strategy.logger:
            self.crawler_strategy.logger = self.logger

        # Thread safety setup
        self._lock = asyncio.Lock() if thread_safe else None
        self._memory_monitor_task = None

        # Initialize directories
        self.crawl4ai_folder = os.path.join(base_directory, ".craw4ai-de")
        os.makedirs(self.crawl4ai_folder, exist_ok=True)

        # Initialize robots.txt parser
        from .utils import RobotsParser
        self.robots_parser = RobotsParser()

        self.ready = False
        
        # Initialize memory history
        self._memory_history = []
        
        # Track active crawl tasks
        self._active_tasks = set()
        self._task_lock = asyncio.Lock()

    async def _monitor_memory_usage(self):
        """
        Continuously monitor memory usage and take action if it exceeds thresholds.
        """
        try:
            while True:
                await asyncio.sleep(self.memory_check_interval)
                
                # Get current memory usage
                memory_percent = psutil.virtual_memory().percent
                
                # Update memory history
                self._memory_history.append(memory_percent)
                if len(self._memory_history) > self._max_memory_history_size:
                    self._memory_history.pop(0)
                
                # Calculate average memory usage
                avg_memory = sum(self._memory_history) / len(self._memory_history)
                
                # Log memory usage at warning level
                if memory_percent >= self.memory_warning_percent:
                    self.logger.warning(
                        f"Memory usage at {memory_percent:.1f}% (avg: {avg_memory:.1f}%), "
                        f"threshold: {self.memory_threshold_percent}%"
                    )
                else:
                    self.logger.info(
                        f"Memory usage at {memory_percent:.1f}% (avg: {avg_memory:.1f}%)"
                    )
                
                # If memory usage is consistently high, trigger garbage collection
                if avg_memory > self.memory_warning_percent:
                    self.logger.warning("Triggering garbage collection due to high memory usage")
                    gc.collect()
        except asyncio.CancelledError:
            self.logger.info("Memory monitor task cancelled")
        except Exception as e:
            self.logger.error(f"Error in memory monitor: {e}")
            traceback.print_exc()

    async def start(self):
        """
        Start the crawler.
        
        This method initializes the crawler and prepares it for use.
        
        Returns:
            self: The crawler instance
        """
        await self.crawler_strategy.__aenter__()
        await self.awarmup()
        
        # Start memory monitoring
        if self._memory_monitor_task is None or self._memory_monitor_task.done():
            self._memory_monitor_task = asyncio.create_task(self._monitor_memory_usage())
            
        return self

    async def close(self):
        """
        Close the crawler.
        
        This method cleans up resources used by the crawler.
        
        Steps:
        1. Clean up browser resources
        2. Close any open pages and contexts
        """
        # Cancel memory monitor task
        if self._memory_monitor_task and not self._memory_monitor_task.done():
            self._memory_monitor_task.cancel()
            try:
                await self._memory_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Cancel any active tasks
        async with self._task_lock:
            for task in self._active_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for all tasks to complete or be cancelled
            if self._active_tasks:
                await asyncio.gather(*self._active_tasks, return_exceptions=True)
            self._active_tasks.clear()
        
        # Close crawler strategy
        await self.crawler_strategy.__aexit__(None, None, None)
        
        # Force garbage collection
        gc.collect()

    async def __aenter__(self):
        return await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def awarmup(self):
        """
        Warm up the crawler.
        
        This method prepares the crawler for use by initializing the database
        and other components.
        """
        await self.async_db_manager.ainit()
        self.ready = True
        return self

    async def nullcontext(self):
        """Async null context manager."""
        yield

    async def _check_and_handle_memory(self, url: str) -> bool:
        """
        Check memory usage and handle high memory situations.
        
        Returns:
            bool: True if processing should continue, False if it should be aborted
        """
        # Get current memory usage
        memory_percent = psutil.virtual_memory().percent
        
        # Extract domain from URL for domain-specific cooldown
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
        except:
            domain = "unknown"
            
        # Check if domain is in cooldown
        current_time = time.time()
        if domain in self._domain_cooldowns:
            cooldown_until = self._domain_cooldowns[domain]
            if current_time < cooldown_until:
                remaining = int(cooldown_until - current_time)
                self.logger.warning(
                    f"Domain {domain} is in cooldown for {remaining} more seconds"
                )
                return False
            else:
                # Cooldown period is over
                del self._domain_cooldowns[domain]
        
        # Handle high memory usage
        if memory_percent >= self.memory_threshold_percent:
            self.logger.warning(
                f"Memory usage exceeds {self.memory_threshold_percent}%, "
                f"initiating cooldown for {self.cooldown_period} seconds"
            )
            
            # Put domain in cooldown
            self._domain_cooldowns[domain] = current_time + self.cooldown_period
            
            # Try to free memory
            gc.collect()
            
            # Restart crawler if memory is still high
            if psutil.virtual_memory().percent >= self.memory_threshold_percent:
                self.logger.warning("Memory still high after garbage collection, restarting crawler")
                await self.close()
                await asyncio.sleep(5)  # Short delay before restart
                await self.start()
                
            return False
            
        return True

    async def arun(
        self,
        url: str,
        config: CrawlerRunConfig = None,
        **kwargs,
    ) -> CrawlResult:
        """
        Run the crawler for a single URL with improved error handling and memory management.
        
        Args:
            url: The URL to crawl
            config: Configuration for this crawl operation
            **kwargs: Additional parameters
            
        Returns:
            CrawlResult: The result of the crawl operation
        """
        crawler_config = config or CrawlerRunConfig()
        
        if not isinstance(url, str) or not url:
            error_msg = "Invalid URL, make sure the URL is a non-empty string"
            self.logger.error(error_msg)
            return CrawlResult(
                url=url, 
                html="", 
                success=False, 
                error_message=error_msg
            )

        # Use lock if thread safety is enabled
        async with self._lock or self.nullcontext():
            # Check memory usage and handle high memory situations
            if not await self._check_and_handle_memory(url):
                return CrawlResult(
                    url=url,
                    html="",
                    success=False,
                    error_message="Crawler is in cooldown due to high memory usage"
                )

            # Track this task
            task = asyncio.current_task()
            if task:
                async with self._task_lock:
                    self._active_tasks.add(task)

            try:
                # Create cache context
                cache_context = CacheContext(
                    url=url,
                    cache_mode=crawler_config.cache_mode,
                    db_manager=self.async_db_manager,
                    logger=self.logger,
                )

                # Start timing
                start_time = time.perf_counter()

                # Try to get from cache
                html = ""
                cached_result = None

                # Check if we should use cache
                if cache_context.should_read():
                    # Try to get from cache
                    cached_result = await cache_context.get_from_cache()
                    html = cached_result.html if cached_result else ""
                    screenshot_data = cached_result.screenshot
                    pdf_data = cached_result.pdf
                    # if config.screenshot and not screenshot or config.pdf and not pdf:
                    if crawler_config.screenshot and not screenshot_data:
                        cached_result = None
                
                # Fetch fresh content if needed
                if not cached_result or not html:
                    t1 = time.perf_counter()
                    
                    # Check robots.txt if enabled
                    if crawler_config and crawler_config.check_robots_txt:
                        if not await self.robots_parser.can_fetch(url, self.browser_config.user_agent):
                            self.logger.warning(f"Robots.txt disallows crawling {url}")
                            return CrawlResult(
                                url=url,
                                html="",
                                success=False,
                                error_message="Robots.txt disallows crawling this URL",
                            )

                    # Update domain last hit time
                    domain = get_domain_from_url(url)
                    self._domain_last_hit[domain] = time.time()

                    ##############################
                    # Call CrawlerStrategy.crawl #
                    ##############################
                    # Implement retry logic for network errors
                    retry_count = 0
                    last_error = None
                    
                    while retry_count <= self.max_retries:
                        try:
                            async_response = await self.crawler_strategy.crawl(
                                url,
                                config=crawler_config,  # Pass the entire config object
                            )
                            # If successful, break out of retry loop
                            break
                        except Exception as e:
                            last_error = e
                            retry_count += 1
                            
                            # Log the error
                            self.logger.warning(
                                f"Error crawling {url} (attempt {retry_count}/{self.max_retries}): {str(e)}"
                            )
                            
                            # If we've reached max retries, re-raise the exception
                            if retry_count > self.max_retries:
                                raise
                            
                            # Exponential backoff for retries
                            backoff_time = self.retry_delay * (2 ** (retry_count - 1))
                            self.logger.info(f"Retrying in {backoff_time} seconds...")
                            await asyncio.sleep(backoff_time)
                    
                    # If we got here without a response, it means all retries failed
                    if not async_response:
                        error_msg = f"Failed to crawl {url} after {self.max_retries} retries"
                        self.logger.error(error_msg)
                        return CrawlResult(
                            url=url,
                            html="",
                            success=False,
                            error_message=error_msg,
                            last_error=str(last_error) if last_error else "Unknown error"
                        )

                    html = sanitize_input_encode(async_response.html)
                    screenshot_data = async_response.screenshot
                    pdf_data = async_response.pdf
                    redirected_url = async_response.redirected_url or url

                    # Create the crawl result
                    crawl_result = CrawlResult(
                        url=url,
                        html=html,
                        redirected_url=redirected_url,
                        screenshot=screenshot_data,
                        pdf=pdf_data,
                        metadata=async_response.metadata,
                        media=async_response.media,
                        markdown=async_response.markdown,
                        ssl_certificate=get_ssl_certificate(redirected_url),
                    )  # Add SSL certificate

                    crawl_result.success = bool(html)
                    crawl_result.session_id = getattr(crawler_config, "session_id", None)

                    self.logger.success(
                        message="{url:.50}... | Status: {status} | Total: {timing}",
                        url=url,
                        status="Success" if crawl_result.success else "Failed",
                        timing=f"{time.perf_counter() - start_time:.2f}s",
                        tag="CRAWL",
                    )

                    # Cache the result if needed
                    if cache_context.should_write() and not bool(cached_result):
                        await async_db_manager.acache_url(crawl_result)

                    # Remove this task from active tasks
                    task = asyncio.current_task()
                    if task:
                        async with self._task_lock:
                            self._active_tasks.discard(task)
                            
                    return crawl_result

                else:
                    # Use cached result
                    self.logger.success(
                        message="{url:.50}... | Status: {status} | Total: {timing}",
                        url=url,
                        status="Cached",
                        timing=f"{time.perf_counter() - start_time:.2f}s",
                        tag="CACHE",
                    )

                    cached_result.success = bool(html)
                    cached_result.session_id = getattr(crawler_config, "session_id", None)
                    cached_result.redirected_url = cached_result.redirected_url or url
                    
                    # Remove this task from active tasks
                    task = asyncio.current_task()
                    if task:
                        async with self._task_lock:
                            self._active_tasks.discard(task)
                            
                    return cached_result

            except Exception as e:
                # Handle any exceptions
                error_message = f"Error crawling {url}: {str(e)}"
                self.logger.error(
                    message="{url:.50}... | {error}",
                    url=url,
                    error=create_box_message(error_message, type="error"),
                    tag="ERROR",
                )
                
                # Remove this task from active tasks
                task = asyncio.current_task()
                if task:
                    async with self._task_lock:
                        self._active_tasks.discard(task)

                return CrawlResult(
                    url=url, html="", success=False, error_message=error_message
                )

