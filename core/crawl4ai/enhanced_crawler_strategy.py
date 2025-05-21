"""
Enhanced crawler strategy for web crawling.

This module provides an improved implementation of the crawler strategy with better
error handling, resource management, and performance optimizations.
"""

import asyncio
import base64
import time
import traceback
from typing import Dict, Any, List, Optional, Union, Tuple
import os
import sys
import logging
from urllib.parse import urlparse
from playwright.async_api import Page, Error, BrowserContext, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import Response as PlaywrightResponse

from .async_crawler_strategy import AsyncCrawlerStrategy
from .models import AsyncCrawlResponse
from .async_configs import BrowserConfig, CrawlerRunConfig
from .enhanced_content_scraping import EnhancedWebScrapingStrategy

# Common HTTP error status codes and their descriptions
HTTP_ERROR_CODES = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    408: "Request Timeout",
    429: "Too Many Requests",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout"
}

# Common content types
CONTENT_TYPES = {
    "text/html": "HTML",
    "application/json": "JSON",
    "text/plain": "Text",
    "application/xml": "XML",
    "text/xml": "XML",
    "application/pdf": "PDF",
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/gif": "GIF",
    "image/webp": "WebP",
    "application/javascript": "JavaScript",
    "text/css": "CSS",
}

class EnhancedCrawlerStrategy(AsyncCrawlerStrategy):
    """
    Enhanced crawler strategy with improved error handling and performance.
    
    Features:
    - Better error handling and recovery
    - Improved resource management
    - Enhanced content extraction
    - Performance optimizations
    - Detailed response analysis
    """
    
    def __init__(self, browser_config=None, logger=None, **kwargs):
        """
        Initialize the enhanced crawler strategy.
        
        Args:
            browser_config: Browser configuration
            logger: Logger instance
            **kwargs: Additional arguments
        """
        super().__init__(browser_config, logger, **kwargs)
        
        # Use enhanced content scraping strategy
        self.content_scraping_strategy = EnhancedWebScrapingStrategy(logger=logger)
        
        # Track performance metrics
        self.performance_metrics = {
            "page_load_times": [],
            "content_extraction_times": [],
            "total_processing_times": [],
            "status_codes": {},
            "content_types": {},
            "errors": {},
        }
        
        # Maximum number of metrics to keep
        self.max_metrics_history = 100
        
        # Track browser context usage
        self.context_usage = {}
        
    async def crawl(self, url: str, config: CrawlerRunConfig = None, **kwargs) -> AsyncCrawlResponse:
        """
        Crawl a URL with enhanced error handling and performance tracking.
        
        Args:
            url: URL to crawl
            config: Crawler configuration
            **kwargs: Additional arguments
            
        Returns:
            AsyncCrawlResponse: Crawl response
        """
        start_time = time.time()
        config = config or CrawlerRunConfig()
        
        # Validate URL
        try:
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid URL format: {url}")
        except Exception as e:
            self.logger.error(f"URL validation error: {e}")
            return AsyncCrawlResponse(
                success=False,
                error_message=f"Invalid URL: {str(e)}",
                status_code=400
            )
        
        try:
            # Get or create browser context
            context = await self._get_browser_context(config)
            
            # Create a new page
            page = await context.new_page()
            
            try:
                # Set up page event handlers
                response_info = {"status": None, "content_type": None}
                
                async def handle_response(response):
                    if response.url == url or response.url.rstrip('/') == url.rstrip('/'):
                        response_info["status"] = response.status
                        response_info["content_type"] = response.headers.get("content-type", "")
                
                # Listen for responses
                page.on("response", handle_response)
                
                # Configure page
                await self._configure_page(page, config)
                
                # Navigate to the URL with timeout
                navigation_start = time.time()
                response = await page.goto(
                    url=url,
                    wait_until=config.wait_until,
                    timeout=config.timeout * 1000,  # Convert to milliseconds
                )
                navigation_time = time.time() - navigation_start
                
                # Update performance metrics
                self.performance_metrics["page_load_times"].append(navigation_time)
                if len(self.performance_metrics["page_load_times"]) > self.max_metrics_history:
                    self.performance_metrics["page_load_times"].pop(0)
                
                # Get status code and content type
                status_code = response.status if response else response_info["status"]
                content_type = response.headers.get("content-type", "") if response else response_info["content_type"]
                
                # Update status code metrics
                self.performance_metrics["status_codes"][status_code] = self.performance_metrics["status_codes"].get(status_code, 0) + 1
                
                # Update content type metrics
                content_type_key = next((k for k in CONTENT_TYPES if k in content_type.lower()), "other")
                self.performance_metrics["content_types"][content_type_key] = self.performance_metrics["content_types"].get(content_type_key, 0) + 1
                
                # Check for HTTP errors
                if status_code >= 400:
                    error_message = f"HTTP Error {status_code}: {HTTP_ERROR_CODES.get(status_code, 'Unknown Error')}"
                    self.logger.warning(f"Error crawling {url}: {error_message}")
                    
                    # Update error metrics
                    error_key = f"HTTP_{status_code}"
                    self.performance_metrics["errors"][error_key] = self.performance_metrics["errors"].get(error_key, 0) + 1
                    
                    # For some errors, we can still try to extract content
                    if status_code not in [404, 410]:  # Not Found, Gone
                        try:
                            html = await page.content()
                            if html:
                                return await self._process_page_content(page, url, html, config, status_code)
                        except Exception as e:
                            self.logger.error(f"Error extracting content from error page: {e}")
                    
                    return AsyncCrawlResponse(
                        success=False,
                        error_message=error_message,
                        status_code=status_code,
                        redirected_url=response.url if response else None
                    )
                
                # Wait for network to be idle
                try:
                    await page.wait_for_load_state("networkidle", timeout=config.wait_time * 1000)
                except PlaywrightTimeoutError:
                    self.logger.warning(f"Network idle timeout for {url}")
                
                # Wait for specific selector if configured
                if config.wait_for_selector:
                    try:
                        await page.wait_for_selector(config.wait_for_selector, timeout=10000)
                    except PlaywrightTimeoutError:
                        self.logger.warning(f"Selector '{config.wait_for_selector}' not found for {url}")
                
                # Get the final HTML content
                html = await page.content()
                
                # Process the page content
                result = await self._process_page_content(page, url, html, config, status_code)
                
                # Update total processing time metrics
                total_time = time.time() - start_time
                self.performance_metrics["total_processing_times"].append(total_time)
                if len(self.performance_metrics["total_processing_times"]) > self.max_metrics_history:
                    self.performance_metrics["total_processing_times"].pop(0)
                
                return result
                
            finally:
                # Close the page
                await page.close()
                
                # Update context usage
                context_key = self._get_context_key(config)
                if context_key in self.context_usage:
                    self.context_usage[context_key]["pages_processed"] += 1
                    self.context_usage[context_key]["last_used"] = time.time()
                
        except PlaywrightTimeoutError as e:
            error_message = f"Timeout error crawling {url}: {str(e)}"
            self.logger.error(error_message)
            
            # Update error metrics
            self.performance_metrics["errors"]["timeout"] = self.performance_metrics["errors"].get("timeout", 0) + 1
            
            return AsyncCrawlResponse(
                success=False,
                error_message=error_message,
                status_code=408  # Request Timeout
            )
            
        except Exception as e:
            error_message = f"Error crawling {url}: {str(e)}"
            self.logger.error(error_message)
            self.logger.error(traceback.format_exc())
            
            # Update error metrics
            error_type = type(e).__name__
            self.performance_metrics["errors"][error_type] = self.performance_metrics["errors"].get(error_type, 0) + 1
            
            return AsyncCrawlResponse(
                success=False,
                error_message=error_message,
                status_code=500  # Internal Server Error
            )
    
    async def _process_page_content(self, page: Page, url: str, html: str, config: CrawlerRunConfig, status_code: int) -> AsyncCrawlResponse:
        """
        Process the content of a page.
        
        Args:
            page: Playwright page
            url: URL of the page
            html: HTML content
            config: Crawler configuration
            status_code: HTTP status code
            
        Returns:
            AsyncCrawlResponse: Processed response
        """
        extraction_start = time.time()
        
        # Get the final URL after any redirects
        redirected_url = page.url
        
        # Take screenshot if requested
        screenshot_data = None
        if config.screenshot:
            try:
                screenshot_data = await self._take_screenshot(page, config)
            except Exception as e:
                self.logger.warning(f"Error taking screenshot: {e}")
        
        # Generate PDF if requested
        pdf_data = None
        if config.pdf:
            try:
                pdf_data = await self._generate_pdf(page, config)
            except Exception as e:
                self.logger.warning(f"Error generating PDF: {e}")
        
        # Extract content using the enhanced scraping strategy
        try:
            scraping_result = await self.content_scraping_strategy.ascrap(url=url, html=html)
            
            # Update content extraction time metrics
            extraction_time = time.time() - extraction_start
            self.performance_metrics["content_extraction_times"].append(extraction_time)
            if len(self.performance_metrics["content_extraction_times"]) > self.max_metrics_history:
                self.performance_metrics["content_extraction_times"].pop(0)
            
            return AsyncCrawlResponse(
                success=True,
                html=html,
                markdown=scraping_result.markdown if hasattr(scraping_result, "markdown") else None,
                screenshot=screenshot_data,
                pdf=pdf_data,
                media=scraping_result.media,
                metadata=scraping_result.metadata,
                redirected_url=redirected_url,
                status_code=status_code
            )
        except Exception as e:
            self.logger.error(f"Error extracting content: {e}")
            self.logger.error(traceback.format_exc())
            
            # Update error metrics
            error_type = type(e).__name__
            self.performance_metrics["errors"][error_type] = self.performance_metrics["errors"].get(error_type, 0) + 1
            
            # Return partial response with raw HTML
            return AsyncCrawlResponse(
                success=True,  # Still consider it a success if we have HTML
                html=html,
                markdown=None,
                screenshot=screenshot_data,
                pdf=pdf_data,
                media=None,
                metadata={},
                redirected_url=redirected_url,
                status_code=status_code
            )
    
    async def _configure_page(self, page: Page, config: CrawlerRunConfig):
        """
        Configure a page with the specified settings.
        
        Args:
            page: Playwright page
            config: Crawler configuration
        """
        # Set viewport size
        await page.set_viewport_size({
            "width": config.viewport_width,
            "height": config.viewport_height
        })
        
        # Set extra HTTP headers
        if config.headers:
            await page.set_extra_http_headers(config.headers)
        
        # Set JavaScript enabled/disabled
        context = page.context
        if hasattr(context, "set_javascript_enabled"):
            await context.set_javascript_enabled(config.javascript_enabled)
        
        # Set user agent if not already set in headers
        if not config.headers or "user-agent" not in {k.lower(): v for k, v in config.headers.items()}:
            await page.set_user_agent(config.user_agent)
        
        # Configure request interception if needed
        if config.block_resources:
            await page.route("**/*", self._handle_route)
    
    async def _handle_route(self, route, request):
        """
        Handle route interception for resource blocking.
        
        Args:
            route: Playwright route
            request: Playwright request
        """
        resource_type = request.resource_type
        if resource_type in ["image", "stylesheet", "font", "media"]:
            await route.abort()
        else:
            await route.continue_()
    
    async def _take_screenshot(self, page: Page, config: CrawlerRunConfig) -> bytes:
        """
        Take a screenshot of the page.
        
        Args:
            page: Playwright page
            config: Crawler configuration
            
        Returns:
            bytes: Screenshot data
        """
        # Get page dimensions
        dimensions = await page.evaluate("""() => {
            return {
                width: document.documentElement.scrollWidth,
                height: document.documentElement.scrollHeight,
                deviceScaleFactor: window.devicePixelRatio
            }
        }""")
        
        # Limit height to avoid memory issues
        height = min(dimensions["height"], config.max_screenshot_height)
        
        # Take screenshot
        screenshot = await page.screenshot(
            full_page=True,
            type="jpeg",
            quality=config.screenshot_quality,
            clip={
                "x": 0,
                "y": 0,
                "width": dimensions["width"],
                "height": height
            }
        )
        
        return screenshot
    
    async def _generate_pdf(self, page: Page, config: CrawlerRunConfig) -> bytes:
        """
        Generate a PDF of the page.
        
        Args:
            page: Playwright page
            config: Crawler configuration
            
        Returns:
            bytes: PDF data
        """
        pdf = await page.pdf(
            format="A4",
            printBackground=True,
            margin={
                "top": "1cm",
                "right": "1cm",
                "bottom": "1cm",
                "left": "1cm"
            }
        )
        
        return pdf
    
    def _get_context_key(self, config: CrawlerRunConfig) -> str:
        """
        Generate a unique key for a browser context based on configuration.
        
        Args:
            config: Crawler configuration
            
        Returns:
            str: Context key
        """
        # Create a string representation of the key configuration parameters
        key_parts = [
            f"js:{config.javascript_enabled}",
            f"proxy:{config.proxy or 'none'}",
            f"mobile:{config.mobile}",
            f"locale:{config.locale or 'default'}"
        ]
        
        return ":".join(key_parts)
    
    async def _get_browser_context(self, config: CrawlerRunConfig) -> BrowserContext:
        """
        Get or create a browser context based on configuration.
        
        Args:
            config: Crawler configuration
            
        Returns:
            BrowserContext: Browser context
        """
        context_key = self._get_context_key(config)
        
        # Check if we need to create a new context
        async with self._contexts_lock:
            # Get existing context or create a new one
            if context_key in self.contexts_by_config:
                context = self.contexts_by_config[context_key]
                
                # Track usage
                if context_key not in self.context_usage:
                    self.context_usage[context_key] = {
                        "created": time.time(),
                        "pages_processed": 0,
                        "last_used": time.time()
                    }
                
                return context
            
            # Create a new context
            context = await self._create_browser_context(config)
            self.contexts_by_config[context_key] = context
            
            # Initialize usage tracking
            self.context_usage[context_key] = {
                "created": time.time(),
                "pages_processed": 0,
                "last_used": time.time()
            }
            
            return context
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the crawler.
        
        Returns:
            Dict[str, Any]: Performance metrics
        """
        metrics = self.performance_metrics.copy()
        
        # Calculate averages
        if metrics["page_load_times"]:
            metrics["avg_page_load_time"] = sum(metrics["page_load_times"]) / len(metrics["page_load_times"])
        else:
            metrics["avg_page_load_time"] = 0
            
        if metrics["content_extraction_times"]:
            metrics["avg_content_extraction_time"] = sum(metrics["content_extraction_times"]) / len(metrics["content_extraction_times"])
        else:
            metrics["avg_content_extraction_time"] = 0
            
        if metrics["total_processing_times"]:
            metrics["avg_total_processing_time"] = sum(metrics["total_processing_times"]) / len(metrics["total_processing_times"])
        else:
            metrics["avg_total_processing_time"] = 0
        
        # Add context usage information
        metrics["contexts"] = {
            "active": len(self.contexts_by_config),
            "usage": self.context_usage
        }
        
        return metrics
    
    async def cleanup_old_contexts(self, max_age_seconds: int = 300, max_pages_processed: int = 50):
        """
        Clean up old browser contexts to free resources.
        
        Args:
            max_age_seconds: Maximum age of a context in seconds
            max_pages_processed: Maximum number of pages a context can process
        """
        current_time = time.time()
        contexts_to_remove = []
        
        async with self._contexts_lock:
            for context_key, usage in self.context_usage.items():
                age = current_time - usage["created"]
                pages_processed = usage["pages_processed"]
                time_since_last_use = current_time - usage["last_used"]
                
                # Check if context should be removed
                if (age > max_age_seconds or pages_processed > max_pages_processed or time_since_last_use > 120):
                    if context_key in self.contexts_by_config:
                        contexts_to_remove.append(context_key)
            
            # Remove old contexts
            for context_key in contexts_to_remove:
                try:
                    context = self.contexts_by_config[context_key]
                    await context.close()
                    del self.contexts_by_config[context_key]
                    del self.context_usage[context_key]
                    self.logger.info(f"Closed old browser context: {context_key}")
                except Exception as e:
                    self.logger.error(f"Error closing browser context: {e}")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Clean up resources when exiting the context.
        """
        # Clean up all browser contexts
        async with self._contexts_lock:
            for context_key, context in list(self.contexts_by_config.items()):
                try:
                    await context.close()
                except Exception as e:
                    self.logger.error(f"Error closing browser context: {e}")
            
            self.contexts_by_config.clear()
            self.context_usage.clear()
        
        # Call parent implementation
        await super().__aexit__(exc_type, exc_val, exc_tb)

