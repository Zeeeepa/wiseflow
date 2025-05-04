from .__version__ import __version__ as crawl4ai_version
import os
import sys
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
from .models import CrawlResult, MarkdownGenerationResult
from .async_database import async_db_manager

from .async_crawler_strategy import (
    AsyncCrawlerStrategy,
    AsyncPlaywrightCrawlerStrategy,
    AsyncCrawlResponse,
)
from .cache_context import CacheContext
from .markdown_generation_strategy import (
    DefaultMarkdownGenerator,
    MarkdownGenerationStrategy,
)
from .async_logger import AsyncLogger
from .async_configs import BrowserConfig, CrawlerRunConfig
from .utils import (
    sanitize_input_encode,
    InvalidCSSSelectorError,
    fast_format_html,
    create_box_message,
    get_error_context,
    RobotsParser,
)


# todo 4.x 也许可以推动开源版本和服务器版本的爬虫归一为一��版本
# 缓存全部使用本地方案，直接缓存 prepross 之后的 data
# 增加totally_forbidden_domains 配置，默认一些设计平台（这些需要专门的爬虫），另外用户可以添加，最后就是自动对爬取失败的直接添加。爬取时遇到这些直接返回空的结果

class AsyncWebCrawler:
    """
    Asynchronous web crawler for fetching web pages.
    
    This class provides an asynchronous interface for crawling web pages,
    with support for caching, robots.txt, and various browser configurations.
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
            always_bypass_cache: Whether to always bypass the cache
            always_by_pass_cache: Deprecated, use always_bypass_cache instead
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
            log_level=logging.INFO,
        )

        # Initialize crawler strategy
        params = {k: v for k, v in kwargs.items() if k in ["browser_config", "logger"]}
        self.crawler_strategy = AsyncPlaywrightCrawlerStrategy(
            browser_config=self.browser_config,
            logger=self.logger,
            **params,  # Pass remaining kwargs for backwards compatibility
        )

        # If craweler strategy doesnt have logger, use crawler logger
        if not self.crawler_strategy.logger:
            self.crawler_strategy.logger = self.logger

        # Thread safety setup
        self._lock = asyncio.Lock() if thread_safe else None
        self._memory_monitor_task = None

        # Initialize directories
        self.crawl4ai_folder = os.path.join(base_directory, ".craw4ai-de")
        os.makedirs(self.crawl4ai_folder, exist_ok=True)
        os.makedirs(f"{self.crawl4ai_folder}/cache", exist_ok=True)

        # Initialize robots parser
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
        It should be called before any crawling operations.
        
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
        It should be called when the crawler is no longer needed.
        
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
        Initialize the crawler with warm-up sequence.

        This method:
        1. Logs initialization info
        2. Sets up browser configuration
        3. Marks the crawler as ready
        """
        self.logger.info(f"Crawl4AI {crawl4ai_version}", tag="INIT")
        self.ready = True

    @asynccontextmanager
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
                    cache_ttl=crawler_config.cache_ttl,
                    cache_key=crawler_config.cache_key,
                )

                # Initialize processing variables
                async_response: AsyncCrawlResponse = None
                cached_result: CrawlResult = None
                screenshot_data = None
                pdf_data = None
                extracted_content = None
                start_time = time.perf_counter()

                # Try to get cached result if appropriate
                if cache_context.should_read():
                    cached_result = await async_db_manager.aget_cached_url(url)

                if cached_result:
                    html = sanitize_input_encode(cached_result.html)
                    extracted_content = sanitize_input_encode(
                        cached_result.extracted_content or ""
                    )
                    extracted_content = (
                        None
                        if not extracted_content or extracted_content == "[]"
                        else extracted_content
                    )
                    # If screenshot is requested but its not in cache, then set cache_result to None
                    screenshot_data = cached_result.screenshot
                    pdf_data = cached_result.pdf
                    # if config.screenshot and not screenshot or config.pdf and not pdf:
                    if config.screenshot and not screenshot_data:
                        cached_result = None

                    if config.pdf and not pdf_data:
                        cached_result = None

                    self.logger.url_status(
                        url=cache_context.display_url,
                        success=bool(html),
                        timing=time.perf_counter() - start_time,
                        tag="CACHING",
                    )

                # Fetch fresh content if needed
                if not cached_result or not html:
                    t1 = time.perf_counter()
                    
                    # Check robots.txt if enabled
                    if crawler_config and crawler_config.check_robots_txt:
                        if not await self.robots_parser.can_fetch(url, self.browser_config.user_agent):
                            self.logger.warning(
                                f"Robots.txt disallows crawling {url}"
                            )
                            return CrawlResult(
                                url=url,
                                html="",
                                success=False,
                                error_message="Robots.txt disallows crawling this URL",
                            )

                    ##############################
                    # Call CrawlerStrategy.crawl #
                    ##############################
                    async_response = await self.crawler_strategy.crawl(
                        url,
                        config=crawler_config,  # Pass the entire config object
                    )

                    html = sanitize_input_encode(async_response.html)
                    screenshot_data = async_response.screenshot
                    pdf_data = async_response.pdf_data
                    js_execution_result = async_response.js_execution_result

                    t2 = time.perf_counter()
                    self.logger.url_status(
                        url=cache_context.display_url,
                        success=bool(html),
                        timing=t2 - t1,
                        tag="FETCH",
                    )

                    ###############################################################
                    # Process the HTML content, Call CrawlerStrategy.process_html #
                    ###############################################################
                    crawl_result : CrawlResult = await self.aprocess_html(
                        url=url,
                        html=html,
                        extracted_content=extracted_content,
                        config=crawler_config,  # Pass the config object instead of individual parameters
                        screenshot=screenshot_data,
                        pdf_data=pdf_data,
                        verbose=crawler_config.verbose,
                        is_raw_html=True if url.startswith("raw:") else False,
                        **kwargs,
                    )

                    crawl_result.status_code = async_response.status_code
                    crawl_result.redirected_url = async_response.redirected_url or url
                    crawl_result.response_headers = async_response.response_headers
                    crawl_result.downloaded_files = async_response.downloaded_files
                    crawl_result.js_execution_result = js_execution_result
                    crawl_result.ssl_certificate = (
                        async_response.ssl_certificate
                    )  # Add SSL certificate

                    crawl_result.success = bool(html)
                    crawl_result.session_id = getattr(config, "session_id", None)

                    self.logger.success(
                        message="{url:.50}... | Status: {status} | Total: {timing}",
                        tag="COMPLETE",
                        params={
                            "url": cache_context.display_url,
                            "status": crawl_result.success,
                            "timing": f"{time.perf_counter() - start_time:.2f}s",
                        },
                        colors={
                            "status": Fore.GREEN if crawl_result.success else Fore.RED,
                            "timing": Fore.YELLOW,
                        },
                    )

                    # Update cache if appropriate
                    if cache_context.should_write() and not bool(cached_result):
                        await async_db_manager.acache_url(crawl_result)

                    return crawl_result

                else:
                    self.logger.success(
                        message="{url:.50}... | Status: {status} | Total: {timing}",
                        tag="COMPLETE",
                        params={
                            "url": cache_context.display_url,
                            "status": True,
                            "timing": f"{time.perf_counter() - start_time:.2f}s",
                        },
                        colors={"status": Fore.GREEN, "timing": Fore.YELLOW},
                    )

                    cached_result.success = bool(html)
                    cached_result.session_id = getattr(config, "session_id", None)
                    cached_result.redirected_url = cached_result.redirected_url or url
                    return cached_result

            except Exception as e:
                error_context = get_error_context(sys.exc_info())

                error_message = (
                    f"Unexpected error in _crawl_web at line {error_context['line_no']} "
                    f"in {error_context['function']} ({error_context['filename']}):\n"
                    f"Error: {str(e)}\n\n"
                    f"Code context:\n{error_context['code_context']}"
                )

                self.logger.error_status(
                    url=url,
                    error=create_box_message(error_message, type="error"),
                    tag="ERROR",
                )

                return CrawlResult(
                    url=url, html="", success=False, error_message=error_message
                )

    async def aprocess_html(
        self,
        url: str,
        html: str,
        extracted_content: str,
        config: CrawlerRunConfig,
        screenshot: str,
        pdf_data: str,
        **kwargs,
    ) -> CrawlResult:
        """
        Process HTML content using the provided configuration.

        Args:
            url: The URL being processed
            html: Raw HTML content
            extracted_content: Previously extracted content (if any)
            config: Configuration object controlling processing behavior
            screenshot: Screenshot data (if any)
            pdf_data: PDF data (if any)
            verbose: Whether to enable verbose logging
            **kwargs: Additional parameters for backwards compatibility

        Returns:
            CrawlResult: Processed result containing extracted and formatted content
        """
        cleaned_html = ""
        try:
            _url = url if not kwargs.get("is_raw_html", False) else "Raw HTML"
            t1 = time.perf_counter()

            # Get scraping strategy and ensure it has a logger
            scraping_strategy = config.scraping_strategy
            if not scraping_strategy.logger:
                scraping_strategy.logger = self.logger

            # Process HTML content
            params = {k: v for k, v in config.to_dict().items() if k not in ["url"]}
            # add keys from kwargs to params that doesn't exist in params
            params.update({k: v for k, v in kwargs.items() if k not in params.keys()})

            ################################
            # Scraping Strategy Execution  #
            ################################
            result = scraping_strategy.scrap(url, html, **params)

            if result is None:
                raise ValueError(
                    f"Process HTML, Failed to extract content from the website: {url}"
                )

        except InvalidCSSSelectorError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise ValueError(
                f"Process HTML, Failed to extract content from the website: {url}, error: {str(e)}"
            )

        # Extract results - handle both dict and ScrapingResult
        if isinstance(result, dict):
            cleaned_html = sanitize_input_encode(result.get("cleaned_html", ""))
            media = result.get("media", {})
            links = {}
            metadata = result.get("metadata", {})
        else:
            cleaned_html = sanitize_input_encode(result.cleaned_html)
            media = result.media.model_dump()
            links = {}
            metadata = result.metadata

        ################################
        # Generate Markdown            #
        ################################
        markdown_generator: Optional[MarkdownGenerationStrategy] = (
            config.markdown_generator or DefaultMarkdownGenerator()
        )

        # Uncomment if by default we want to use PruningContentFilter
        # if not config.content_filter and not markdown_generator.content_filter:
        #     markdown_generator.content_filter = PruningContentFilter()

        markdown_result: MarkdownGenerationResult = (
            markdown_generator.generate_markdown(
                cleaned_html=cleaned_html,
                base_url=url,
                citations=False
            )
        )

        # Log processing completion
        self.logger.info(
            message="Processed {url:.50}... | Time: {timing}ms",
            tag="SCRAPE",
            params={"url": _url, "timing": int((time.perf_counter() - t1) * 1000)},
        )

        # Handle screenshot and PDF data
        screenshot_data = None if not screenshot else screenshot
        pdf_data = None if not pdf_data else pdf_data

        # Apply HTML formatting if requested
        if config.prettiify:
            cleaned_html = fast_format_html(cleaned_html)

        # Return complete crawl result
        return CrawlResult(
            url=url,
            html=html,
            cleaned_html=cleaned_html,
            markdown=markdown_result.raw_markdown,
            media=media,
            links={},
            metadata=metadata,
            screenshot=screenshot_data,
            pdf=pdf_data,
            extracted_content=extracted_content,
            success=True,
            error_message="",
        )
