import os
import time
import psutil
from colorama import Fore
from typing import Optional, Dict, List, Any, Tuple, Set
import asyncio
import gc
import logging
import traceback
import weakref
import signal

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
    # Track active crawlers for global resource management
    _active_crawlers: Set["AsyncWebCrawler"] = set()
    # Class-level lock for managing shared resources
    _class_lock = asyncio.Lock()

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
        self._resource_monitor_task = None

        # Initialize directories
        self.crawl4ai_folder = os.path.join(base_directory, ".craw4ai-de")
        os.makedirs(self.crawl4ai_folder, exist_ok=True)

        # Initialize robots.txt parser
        self.robots_parser = RobotsParser()

        self.ready = False
        
        # Initialize memory history
        self._memory_history = []
        
        # Track active crawl tasks
        self._active_tasks = set()
        self._task_lock = asyncio.Lock()
        
        # Track resource usage
        self.resource_stats = {
            "peak_memory_percent": 0.0,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cached_requests": 0,
            "total_processing_time": 0.0,
            "browser_restarts": 0,
            "last_gc_time": time.time(),
        }
        
        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        # Register this crawler instance
        asyncio.create_task(self._register_crawler())
    
    async def _register_crawler(self):
        """Register this crawler instance in the class-level set."""
        async with self._class_lock:
            self._active_crawlers.add(self)
    
    async def _unregister_crawler(self):
        """Unregister this crawler instance from the class-level set."""
        async with self._class_lock:
            if self in self._active_crawlers:
                self._active_crawlers.remove(self)
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        # Use a weak reference to avoid reference cycles
        weak_self = weakref.ref(self)
        
        def handle_signal(signum, frame):
            # Get the actual instance from the weak reference
            instance = weak_self()
            if instance:
                # Create a task to close the crawler
                loop = asyncio.get_event_loop()
                loop.create_task(instance.close())
        
        # Register signal handlers
        try:
            signal.signal(signal.SIGINT, handle_signal)
            signal.signal(signal.SIGTERM, handle_signal)
        except (ValueError, AttributeError):
            # Signal handling might not be available in all environments
            pass

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
                
                # Update peak memory usage
                self.resource_stats["peak_memory_percent"] = max(
                    self.resource_stats["peak_memory_percent"], memory_percent
                )
                
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
                    self.resource_stats["last_gc_time"] = time.time()
                
                # If memory usage is extremely high, take more aggressive action
                if memory_percent > self.memory_threshold_percent:
                    self.logger.error(f"Memory usage critical at {memory_percent:.1f}%, restarting browser")
                    await self._restart_browser()
                    self.resource_stats["browser_restarts"] += 1
        except asyncio.CancelledError:
            self.logger.info("Memory monitor task cancelled")
        except Exception as e:
            self.logger.error(f"Error in memory monitor: {e}")
            traceback.print_exc()
    
    async def _monitor_resources(self):
        """Monitor and manage system resources."""
        try:
            while True:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Check if we need to perform garbage collection
                time_since_last_gc = time.time() - self.resource_stats["last_gc_time"]
                if time_since_last_gc > 300:  # 5 minutes
                    self.logger.info("Performing routine garbage collection")
                    gc.collect()
                    self.resource_stats["last_gc_time"] = time.time()
                
                # Log resource statistics
                self.logger.info(
                    f"Resource stats: "
                    f"Requests: {self.resource_stats['total_requests']}, "
                    f"Success: {self.resource_stats['successful_requests']}, "
                    f"Failed: {self.resource_stats['failed_requests']}, "
                    f"Cached: {self.resource_stats['cached_requests']}, "
                    f"Browser restarts: {self.resource_stats['browser_restarts']}"
                )
        except asyncio.CancelledError:
            self.logger.info("Resource monitor task cancelled")
        except Exception as e:
            self.logger.error(f"Error in resource monitor: {e}")
            traceback.print_exc()
    
    async def _restart_browser(self):
        """Restart the browser to free up resources."""
        try:
            self.logger.warning("Restarting browser to free up resources")
            
            # Close the current browser
            await self.crawler_strategy.__aexit__(None, None, None)
            
            # Force garbage collection
            gc.collect()
            
            # Wait a moment for resources to be released
            await asyncio.sleep(2)
            
            # Start a new browser
            await self.crawler_strategy.__aenter__()
            
            self.logger.info("Browser successfully restarted")
        except Exception as e:
            self.logger.error(f"Error restarting browser: {e}")
            traceback.print_exc()

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
        
        # Start resource monitoring
        if self._resource_monitor_task is None or self._resource_monitor_task.done():
            self._resource_monitor_task = asyncio.create_task(self._monitor_resources())
            
        return self

    async def close(self):
        """
        Close the web crawler.
        
        This method cleans up resources used by the crawler.
        
        Steps:
        1. Clean up browser resources
        2. Close any open pages and contexts
        """
        # Cancel monitoring tasks
        for task_name in ["_memory_monitor_task", "_resource_monitor_task"]:
            task = getattr(self, task_name, None)
            if task and not task.done():
                task.cancel()
                try:
                    await task
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
        
        # Unregister this crawler
        await self._unregister_crawler()
        
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
            self.resource_stats["last_gc_time"] = time.time()
            
            # Restart crawler if memory is still high
            if psutil.virtual_memory().percent >= self.memory_threshold_percent:
                self.logger.warning("Memory still high after garbage collection, restarting crawler")
                await self._restart_browser()
                self.resource_stats["browser_restarts"] += 1
                
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
            self.resource_stats["failed_requests"] += 1
            return CrawlResult(
                url=url, 
                html="", 
                success=False, 
                error_message=error_msg
            )

        # Use lock if thread safety is enabled
        async with self._lock or self.nullcontext():
            # Update request statistics
            self.resource_stats["total_requests"] += 1
            
            # Check memory usage and handle high memory situations
            if not await self._check_and_handle_memory(url):
                self.resource_stats["failed_requests"] += 1
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
                        else:
                            # Update cache statistics
                            self.resource_stats["cached_requests"] += 1
                
                # Fetch fresh content if needed
                if not cached_result or not html:
                    t1 = time.perf_counter()
                    
                    # Check robots.txt if enabled
                    if crawler_config and crawler_config.check_robots_txt:
                        if not await self.robots_parser.can_fetch(url, self.browser_config.user_agent):
                            self.logger.warning(
                                f"URL {url} is disallowed by robots.txt"
                            )
                            self.resource_stats["failed_requests"] += 1
                            return CrawlResult(
                                url=url,
                                html="",
                                success=False,
                                error_message="URL is disallowed by robots.txt",
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
                        self.resource_stats["failed_requests"] += 1
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
                        status_code=async_response.status_code,
                    )

                    # Add SSL certificate
                    crawl_result.ssl_certificate = await get_ssl_certificate(
                        url=url, logger=self.logger
                    )  # Add SSL certificate

                    crawl_result.success = bool(html)
                    crawl_result.session_id = getattr(crawler_config, "session_id", None)

                    # Update resource statistics
                    processing_time = time.perf_counter() - start_time
                    self.resource_stats["total_processing_time"] += processing_time
                    if crawl_result.success:
                        self.resource_stats["successful_requests"] += 1
                    else:
                        self.resource_stats["failed_requests"] += 1

                    self.logger.success(
                        message="{url:.50}... | Status: {status} | Total: {timing}",
                        url=url,
                        status=crawl_result.success,
                        timing=processing_time,
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
                    processing_time = time.perf_counter() - start_time
                    self.logger.success(
                        message="{url:.50}... | Status: {status} | Total: {timing}",
                        url=url,
                        status=bool(html),
                        timing=processing_time,
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
                
                # Update statistics
                self.resource_stats["failed_requests"] += 1
                
                # Remove this task from active tasks
                task = asyncio.current_task()
                if task:
                    async with self._task_lock:
                        self._active_tasks.discard(task)

                return CrawlResult(
                    url=url, html="", success=False, error_message=error_message
                )
    
    async def get_resource_stats(self) -> Dict[str, Any]:
        """Get resource statistics."""
        stats = self.resource_stats.copy()
        
        # Calculate derived statistics
        if stats["total_requests"] > 0:
            stats["success_rate"] = (stats["successful_requests"] / stats["total_requests"]) * 100
            stats["cache_hit_rate"] = (stats["cached_requests"] / stats["total_requests"]) * 100
        else:
            stats["success_rate"] = 0
            stats["cache_hit_rate"] = 0
            
        if stats["successful_requests"] > 0:
            stats["avg_processing_time"] = stats["total_processing_time"] / stats["successful_requests"]
        else:
            stats["avg_processing_time"] = 0
            
        # Add current memory usage
        stats["current_memory_percent"] = psutil.virtual_memory().percent
        
        # Add active tasks count
        stats["active_tasks"] = len(self._active_tasks)
        
        return stats
    
    @classmethod
    async def get_global_stats(cls) -> Dict[str, Any]:
        """Get global statistics for all active crawlers."""
        async with cls._class_lock:
            active_count = len(cls._active_crawlers)
            
            # Aggregate statistics from all active crawlers
            total_requests = 0
            successful_requests = 0
            failed_requests = 0
            cached_requests = 0
            browser_restarts = 0
            
            for crawler in cls._active_crawlers:
                stats = crawler.resource_stats
                total_requests += stats["total_requests"]
                successful_requests += stats["successful_requests"]
                failed_requests += stats["failed_requests"]
                cached_requests += stats["cached_requests"]
                browser_restarts += stats["browser_restarts"]
            
            return {
                "active_crawlers": active_count,
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "cached_requests": cached_requests,
                "browser_restarts": browser_restarts,
                "current_memory_percent": psutil.virtual_memory().percent,
            }
    
    @classmethod
    async def shutdown_all(cls):
        """Shutdown all active crawlers."""
        async with cls._class_lock:
            shutdown_tasks = []
            for crawler in list(cls._active_crawlers):
                shutdown_tasks.append(crawler.close())
            
            if shutdown_tasks:
                await asyncio.gather(*shutdown_tasks, return_exceptions=True)
