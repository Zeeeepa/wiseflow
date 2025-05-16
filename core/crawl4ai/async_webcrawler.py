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
from contextlib import asynccontextmanager

from .async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from .async_crawler_strategy import AsyncCrawlerStrategy
from .async_database import AsyncDatabaseManager
from .async_logger import AsyncLogger
from .cache_context import CacheContext
from .enhanced_cache import EnhancedCache
from .models import CrawlResult
from .errors import Crawl4AIError, NetworkError, TimeoutError, ResourceError
from .url_utils import normalize_url, get_domain_from_url
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
    # Global instance registry for cleanup
    _instances: Set['AsyncWebCrawler'] = set()

    def __init__(
        self,
        config: Optional[BrowserConfig] = None,
        base_directory: str = os.getenv("PROJECT_DIR", ''),
        thread_safe: bool = False,
        memory_threshold_percent: float = 85.0,
        memory_warning_percent: float = 75.0,
        memory_check_interval: float = 10.0,  # 10 seconds
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
        self.base_directory = base_directory
        
        # Create crawl4ai directory if it doesn't exist
        self.crawl4ai_folder = os.path.join(base_directory, ".crawl4ai")
        os.makedirs(self.crawl4ai_folder, exist_ok=True)
        
        # Initialize logger first since other components may need it
        self.logger = AsyncLogger(
            log_file=os.path.join(self.crawl4ai_folder, "crawler.log"),
            console=True,
        )

        # Initialize database manager
        self.async_db_manager = AsyncDatabaseManager(
            base_directory=base_directory,
            logger=self.logger,
        )

        # Initialize enhanced cache
        self.enhanced_cache = EnhancedCache(
            cache_dir=os.path.join(self.crawl4ai_folder, "cache"),
            ttl=kwargs.get("cache_ttl", 86400),  # 24 hours in seconds
            max_size=kwargs.get("cache_max_size", 1000),
            cleanup_interval=kwargs.get("cache_cleanup_interval", 3600),  # 1 hour in seconds
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

        # Initialize robots.txt parser
        self.robots_parser = RobotsParser()

        self.ready = False
        
        # Initialize memory history
        self._memory_history = []
        
        # Track active crawl tasks
        self._active_tasks = set()
        self._task_lock = asyncio.Lock()
        
        # Register instance for global cleanup
        AsyncWebCrawler._instances.add(weakref.ref(self))
        
        # Register signal handlers for graceful shutdown
        self._register_signal_handlers()
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        # Only register if not already registered
        if not hasattr(AsyncWebCrawler, "_signals_registered"):
            try:
                for sig in (signal.SIGINT, signal.SIGTERM):
                    signal.signal(sig, AsyncWebCrawler._signal_handler)
                AsyncWebCrawler._signals_registered = True
            except (ValueError, AttributeError):
                # Signal handling might not be available in all environments
                pass
    
    @staticmethod
    def _signal_handler(signum, frame):
        """Handle signals for graceful shutdown."""
        logging.info(f"Received signal {signum}, shutting down all crawlers...")
        
        # Create a new event loop for cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Close all active crawlers
        for ref in list(AsyncWebCrawler._instances):
            instance = ref()
            if instance is not None:
                loop.run_until_complete(instance.close())
        
        # Exit with appropriate status
        os._exit(0)

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
                
                # Log memory usage at appropriate level
                if memory_percent >= self.memory_threshold_percent:
                    self.logger.error(
                        f"Memory usage critical at {memory_percent:.1f}% (avg: {avg_memory:.1f}%), "
                        f"threshold: {self.memory_threshold_percent}%"
                    )
                elif memory_percent >= self.memory_warning_percent:
                    self.logger.warning(
                        f"Memory usage high at {memory_percent:.1f}% (avg: {avg_memory:.1f}%), "
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
                    
                    # If memory is still critical after GC, take more drastic measures
                    if psutil.virtual_memory().percent >= self.memory_threshold_percent:
                        self.logger.error("Memory still critical after garbage collection, pausing operations")
                        # Put all domains in cooldown
                        current_time = time.time()
                        for domain in self._domain_last_hit.keys():
                            self._domain_cooldowns[domain] = current_time + self.cooldown_period
        except asyncio.CancelledError:
            self.logger.info("Memory monitor task cancelled")
        except Exception as e:
            self.logger.error(f"Error in memory monitor: {e}")
            traceback.print_exc()

    async def start(self):
        """
        Start the web crawler.
        
        This method initializes the crawler strategy and warms up the browser.
        
        Returns:
            self: The crawler instance
        """
        try:
            await self.crawler_strategy.__aenter__()
            await self.awarmup()
            
            # Start memory monitoring
            if self._memory_monitor_task is None or self._memory_monitor_task.done():
                self._memory_monitor_task = asyncio.create_task(self._monitor_memory_usage())
                
            return self
        except Exception as e:
            self.logger.error(f"Error starting crawler: {e}")
            # Clean up resources if startup fails
            try:
                await self.close()
            except Exception as cleanup_error:
                self.logger.error(f"Error during cleanup after failed start: {cleanup_error}")
            raise ResourceError("Failed to start crawler", original_error=e)

    async def close(self):
        """
        Close the web crawler.
        
        This method cleans up resources used by the crawler.
        
        Steps:
        1. Cancel memory monitor task
        2. Cancel any active tasks
        3. Close crawler strategy
        4. Force garbage collection
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
        try:
            await self.crawler_strategy.__aexit__(None, None, None)
        except Exception as e:
            self.logger.error(f"Error closing crawler strategy: {e}")
        
        # Force garbage collection
        gc.collect()
        
        # Remove from instance registry
        for ref in list(AsyncWebCrawler._instances):
            if ref() is self:
                AsyncWebCrawler._instances.remove(ref)
                break

    async def __aenter__(self):
        return await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def awarmup(self):
        """Warm up the browser."""
        self.ready = True
        return self

    @asynccontextmanager
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
            domain = get_domain_from_url(url)
        except Exception:
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
            
            # Check if memory is still high after garbage collection
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
            
        Raises:
            ValidationError: If the URL is invalid
            NetworkError: If there are network-related errors
            TimeoutError: If the crawl operation times out
            ResourceError: If there are resource management issues
            Crawl4AIError: For other crawl-related errors
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
                # Normalize URL for consistency
                try:
                    normalized_url = normalize_url(url)
                except Exception as e:
                    self.logger.error(f"Failed to normalize URL {url}: {e}")
                    normalized_url = url

                # Create cache context
                cache_context = CacheContext(
                    url=normalized_url,
                    cache_mode=crawler_config.cache_mode,
                    logger=self.logger,
                )

                # Start timing
                start_time = time.perf_counter()

                # Check cache first if enabled
                html = ""
                screenshot_data = None
                pdf_data = None
                cached_result = None

                if cache_context.should_read():
                    # Try enhanced cache first
                    cached_result = await self.enhanced_cache.get(normalized_url)
                    
                    # Fall back to legacy cache if not found
                    if not cached_result:
                        cached_result = await self.async_db_manager.aget_url_cache(normalized_url)
                    
                    if cached_result:
                        html = cached_result.html
                        screenshot_data = cached_result.screenshot
                        pdf_data = cached_result.pdf
                        
                        # Check if we need to refetch for missing assets
                        if crawler_config.screenshot and not screenshot_data:
                            cached_result = None
                
                # Fetch fresh content if needed
                if not cached_result or not html:
                    t1 = time.perf_counter()
                    
                    # Check robots.txt if enabled
                    if crawler_config and crawler_config.check_robots_txt:
                        if not await self.robots_parser.can_fetch(normalized_url, self.browser_config.user_agent):
                            self.logger.warning(
                                f"URL {normalized_url} is disallowed by robots.txt"
                            )
                            return CrawlResult(
                                url=normalized_url,
                                html="",
                                success=False,
                                error_message="URL is disallowed by robots.txt",
                            )

                    # Update domain last hit time
                    domain = get_domain_from_url(normalized_url)
                    self._domain_last_hit[domain] = time.time()

                    # Implement retry logic for network errors
                    retry_count = 0
                    last_error = None
                    
                    while retry_count <= self.max_retries:
                        try:
                            async_response = await self.crawler_strategy.crawl(
                                normalized_url,
                                config=crawler_config,  # Pass the entire config object
                            )
                            # If successful, break out of retry loop
                            break
                        except Exception as e:
                            last_error = e
                            retry_count += 1
                            
                            # Log the error
                            self.logger.warning(
                                f"Error crawling {normalized_url} (attempt {retry_count}/{self.max_retries}): {str(e)}"
                            )
                            
                            # If we've reached max retries, re-raise the exception
                            if retry_count > self.max_retries:
                                if isinstance(e, (asyncio.TimeoutError, TimeoutError)):
                                    raise TimeoutError(
                                        f"Timeout crawling {normalized_url} after {self.max_retries} retries",
                                        url=normalized_url,
                                        original_error=e
                                    )
                                else:
                                    raise NetworkError(
                                        f"Failed to crawl {normalized_url} after {self.max_retries} retries",
                                        url=normalized_url,
                                        original_error=e
                                    )
                            
                            # Exponential backoff for retries
                            backoff_time = self.retry_delay * (2 ** (retry_count - 1))
                            self.logger.info(f"Retrying in {backoff_time} seconds...")
                            await asyncio.sleep(backoff_time)
                    
                    # If we got here without a response, it means all retries failed
                    if not async_response:
                        error_msg = f"Failed to crawl {normalized_url} after {self.max_retries} retries"
                        self.logger.error(error_msg)
                        return CrawlResult(
                            url=normalized_url,
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
                        url=normalized_url,
                        html=html,
                        markdown=async_response.markdown,
                        screenshot=screenshot_data,
                        pdf=pdf_data,
                        media=async_response.media,
                        metadata=async_response.metadata,
                        redirected_url=async_response.redirected_url or normalized_url,
                        timing=time.perf_counter() - t1,
                    )

                    # Add SSL certificate
                    try:
                        crawl_result.ssl_certificate = await get_ssl_certificate(
                            url=normalized_url, logger=self.logger
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to get SSL certificate for {normalized_url}: {e}")
                        crawl_result.ssl_certificate = None

                    crawl_result.success = bool(html)
                    crawl_result.session_id = getattr(crawler_config, "session_id", None)

                    self.logger.success(
                        message="{url:.50}... | Status: {status} | Total: {timing}",
                        url=normalized_url,
                        status=crawl_result.success,
                        timing=time.perf_counter() - start_time,
                        tag="CRAWL",
                    )

                    # Cache the result if needed
                    if cache_context.should_write() and not bool(cached_result):
                        # Use enhanced cache
                        await self.enhanced_cache.set(crawl_result)
                        # Also update legacy cache for backward compatibility
                        await self.async_db_manager.acache_url(crawl_result)

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
                        url=normalized_url,
                        status=bool(html),
                        timing=time.perf_counter() - start_time,
                        tag="CACHE",
                    )

                    cached_result.success = bool(html)
                    cached_result.session_id = getattr(crawler_config, "session_id", None)
                    cached_result.redirected_url = cached_result.redirected_url or normalized_url
                    
                    # Remove this task from active tasks
                    task = asyncio.current_task()
                    if task:
                        async with self._task_lock:
                            self._active_tasks.discard(task)
                            
                    return cached_result

            except Crawl4AIError as e:
                # Re-raise custom exceptions
                raise e
            except asyncio.TimeoutError as e:
                error_message = f"Timeout crawling {url}"
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
                
                raise TimeoutError(error_message, url=url, original_error=e)
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

                # Return error result
                return CrawlResult(
                    url=url, html="", success=False, error_message=error_message
                )
