import os
import time
import psutil
from colorama import Fore
from typing import Optional, Dict, List, Any, Tuple
import asyncio
import gc
import logging
import traceback
import weakref

# from contextlib import nullcontext, asynccontextmanager
from contextlib import asynccontextmanager

from .async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from .async_crawler_strategy import AsyncCrawlerStrategy
from .async_database import AsyncDatabaseManager
from .async_logger import AsyncLogger
from .cache_context import CacheContext
from .models import CrawlResult
from .utils import (
    create_box_message,
    sanitize_input_encode,
    get_domain_from_url,
    get_ssl_certificate,
    RobotsParser,
)

# Initialize memory monitoring and management
class AsyncWebCrawler:
    """
    Asynchronous web crawler for fetching web content.
    
    This class provides a high-level interface for crawling web pages asynchronously,
    with support for caching, browser configuration, and error handling.
    """

    _domain_last_hit = {}
    # Track memory usage over time for better decision making
    _memory_history: List[float] = []
    # Maximum number of memory history points to keep
    _max_memory_history_size = 10
    # Domain-specific cooldown tracking
    _domain_cooldowns: Dict[str, float] = {}
    # Domain-specific rate limiting
    _domain_request_counts: Dict[str, int] = {}
    _domain_rate_limits: Dict[str, Tuple[int, int]] = {}  # (requests, seconds)

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
        default_rate_limit: Tuple[int, int] = (10, 60),  # 10 requests per 60 seconds
        **kwargs,
    ):
        """
        Initialize the web crawler.
        
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
            default_rate_limit: Default rate limit as (requests, seconds)
            **kwargs: Additional arguments for backwards compatibility
        """

        self.memory_threshold_percent = memory_threshold_percent
        self.memory_warning_percent = memory_warning_percent
        self.memory_check_interval = memory_check_interval
        self.cooldown_period = cooldown_period
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.default_rate_limit = default_rate_limit
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
        params = {k: v for k, v in kwargs.items() if k != "always_by_pass_cache"}
        self.crawler_strategy = AsyncCrawlerStrategy(
            browser_config=self.browser_config,
            logger=self.logger,
            **params,  # Pass remaining kwargs for backwards compatibility
        )

        # If crawler strategy doesn't have logger, use crawler logger
        if not self.crawler_strategy.logger:
            self.crawler_strategy.logger = self.logger

        # Thread safety setup
        self._lock = asyncio.Lock() if thread_safe else None
        self._memory_monitor_task = None
        self._rate_limit_locks = {}

        # Initialize directories
        self.crawl4ai_folder = os.path.join(base_directory, ".craw4ai-de")
        os.makedirs(self.crawl4ai_folder, exist_ok=True)

        # Initialize robots.txt parser
        self.robots_parser = RobotsParser()

        self.ready = False
        
        # Initialize memory history
        self._memory_history = []
        
        # Track active crawl tasks
        self._active_tasks = weakref.WeakSet()
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
                    
                    # If memory is still high after GC, consider more aggressive cleanup
                    if psutil.virtual_memory().percent > self.memory_threshold_percent:
                        self.logger.warning("Memory still high after garbage collection, performing additional cleanup")
                        # Clear caches and release resources
                        self._domain_last_hit.clear()
                        self._domain_cooldowns.clear()
                        self._domain_request_counts.clear()
                        await self._clear_browser_cache()
        except asyncio.CancelledError:
            self.logger.info("Memory monitor task cancelled")
        except Exception as e:
            self.logger.error(f"Error in memory monitor: {e}")
            traceback.print_exc()

    async def _clear_browser_cache(self):
        """Clear browser cache to free up memory"""
        try:
            await self.crawler_strategy.clear_cache()
            self.logger.info("Browser cache cleared")
        except Exception as e:
            self.logger.error(f"Error clearing browser cache: {e}")

    async def start(self):
        """
        Start the web crawler.
        
        This method initializes the crawler strategy and warms up the browser.
        
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
        Close the web crawler.
        
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
            for task in list(self._active_tasks):
                if not task.done():
                    task.cancel()
            
            # Wait for all tasks to complete or be cancelled
            if self._active_tasks:
                pending = [task for task in self._active_tasks if not task.done()]
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)
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
        """Warm up the browser."""
        self.ready = True
        return self

    async def nullcontext(self):
        """异步空上下文管理器"""
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
            
            # If memory is still high, try more aggressive cleanup
            if psutil.virtual_memory().percent >= self.memory_threshold_percent:
                self.logger.warning("Memory still high after garbage collection, restarting crawler")
                await self.close()
                await asyncio.sleep(5)  # Short delay before restart
                await self.start()
                
            return False
            
        return True

    async def _check_rate_limit(self, domain: str) -> bool:
        """
        Check if a domain has exceeded its rate limit.
        
        Args:
            domain: The domain to check
            
        Returns:
            bool: True if request can proceed, False if rate limited
        """
        # Get rate limit for this domain (or use default)
        rate_limit = self._domain_rate_limits.get(domain, self.default_rate_limit)
        max_requests, period = rate_limit
        
        # Get or create lock for this domain
        if domain not in self._rate_limit_locks:
            self._rate_limit_locks[domain] = asyncio.Lock()
            
        # Acquire lock to update request count
        async with self._rate_limit_locks[domain]:
            current_time = time.time()
            
            # Initialize or clean up old request counts
            if domain not in self._domain_request_counts:
                self._domain_request_counts[domain] = 1
                self._domain_last_hit[domain] = current_time
                return True
                
            # Check if we've exceeded the rate limit
            if self._domain_request_counts[domain] >= max_requests:
                # Calculate time to wait
                time_since_first = current_time - self._domain_last_hit[domain]
                if time_since_first < period:
                    wait_time = period - time_since_first
                    self.logger.warning(
                        f"Rate limit exceeded for {domain}: {max_requests} requests per {period}s. "
                        f"Waiting {wait_time:.1f}s"
                    )
                    return False
                else:
                    # Reset counter if period has passed
                    self._domain_request_counts[domain] = 1
                    self._domain_last_hit[domain] = current_time
                    return True
            else:
                # Increment counter
                self._domain_request_counts[domain] += 1
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
                
            # Extract domain for rate limiting
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
            except:
                domain = "unknown"
                
            # Check rate limit
            if not await self._check_rate_limit(domain):
                return CrawlResult(
                    url=url,
                    html="",
                    success=False,
                    error_message=f"Rate limit exceeded for domain: {domain}"
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
                    logger=self.logger,
                )

                # Get the database manager
                async_db_manager = self.async_db_manager

                # Start timing
                start_time = time.perf_counter()

                # Check cache first if enabled
                html = ""
                screenshot_data = None
                pdf_data = None
                cached_result = None

                if cache_context.should_read():
                    cached_result = await async_db_manager.aget_url_cache(url)
                    if cached_result:
                        html = cached_result.html
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
                            self.logger.warning(
                                f"URL {url} is disallowed by robots.txt"
                            )
                            return CrawlResult(
                                url=url,
                                html="",
                                success=False,
                                error_message="URL is disallowed by robots.txt",
                            )

                    # Update domain last hit time
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

                    # Create a CrawlResult
                    crawl_result = CrawlResult(
                        url=url,
                        html=html,
                        markdown=async_response.markdown,
                        screenshot=screenshot_data,
                        pdf=pdf_data,
                        media=async_response.media,
                        metadata=async_response.metadata,
                        redirected_url=async_response.redirected_url or url,
                        timing=time.perf_counter() - t1,
                    )

                    # Add SSL certificate
                    crawl_result.ssl_certificate = await get_ssl_certificate(
                        url=url, logger=self.logger
                    )  # Add SSL certificate

                    crawl_result.success = bool(html)
                    crawl_result.session_id = getattr(crawler_config, "session_id", None)

                    self.logger.success(
                        message="{url:.50}... | Status: {status} | Total: {timing}",
                        url=url,
                        status=crawl_result.success,
                        timing=time.perf_counter() - start_time,
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
                        status=bool(html),
                        timing=time.perf_counter() - start_time,
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
                error_message = f"Error crawling {url}: {str(e)}"
                self.logger.error(
                    message="{url:.50}... | Error: {error}",
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
