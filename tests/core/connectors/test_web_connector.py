#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for the WebConnector class.
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import os
import tempfile
from datetime import datetime

from core.connectors.web import WebConnector, DomainRateLimiter
from core.crawl4ai import AsyncWebCrawler, CacheMode
from core.crawl4ai.models import CrawlResult


class TestDomainRateLimiter(unittest.TestCase):
    """Test cases for the DomainRateLimiter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rate_limiter = DomainRateLimiter(default_rate_limit=10, default_cooldown=1.0)
    
    def test_initialization(self):
        """Test rate limiter initialization."""
        self.assertEqual(self.rate_limiter.default_rate_limit, 10)
        self.assertEqual(self.rate_limiter.default_cooldown, 1.0)
        self.assertEqual(self.rate_limiter.domain_limits, {})
        self.assertEqual(len(self.rate_limiter.domain_timestamps), 0)
    
    def test_set_domain_limit(self):
        """Test setting domain-specific rate limits."""
        self.rate_limiter.set_domain_limit("example.com", 5, 2.0)
        self.assertEqual(self.rate_limiter.domain_limits["example.com"], 5)
        self.assertEqual(self.rate_limiter.domain_cooldowns["example.com"], 2.0)
        
        # Test setting only rate limit
        self.rate_limiter.set_domain_limit("test.com", 15)
        self.assertEqual(self.rate_limiter.domain_limits["test.com"], 15)
        self.assertNotIn("test.com", self.rate_limiter.domain_cooldowns)
    
    def test_get_domain_limit(self):
        """Test getting domain-specific rate limits."""
        self.rate_limiter.set_domain_limit("example.com", 5)
        self.assertEqual(self.rate_limiter.get_domain_limit("example.com"), 5)
        self.assertEqual(self.rate_limiter.get_domain_limit("unknown.com"), 10)  # Default
    
    def test_get_domain_cooldown(self):
        """Test getting domain-specific cooldown periods."""
        self.rate_limiter.set_domain_limit("example.com", 5, 2.0)
        self.assertEqual(self.rate_limiter.get_domain_cooldown("example.com"), 2.0)
        self.assertEqual(self.rate_limiter.get_domain_cooldown("unknown.com"), 1.0)  # Default
    
    async def async_test_register_request(self):
        """Test registering requests to domains."""
        await self.rate_limiter.register_request("example.com")
        self.assertEqual(len(self.rate_limiter.domain_timestamps["example.com"]), 1)
        
        # Register multiple requests
        for _ in range(3):
            await self.rate_limiter.register_request("example.com")
        self.assertEqual(len(self.rate_limiter.domain_timestamps["example.com"]), 4)
    
    async def async_test_should_throttle(self):
        """Test throttling logic."""
        # Set up a domain with low rate limit
        self.rate_limiter.set_domain_limit("example.com", 3, 1.0)
        
        # Register requests up to the limit
        for _ in range(3):
            await self.rate_limiter.register_request("example.com")
        
        # Should throttle after limit is reached
        should_throttle, wait_time = await self.rate_limiter.should_throttle("example.com")
        self.assertTrue(should_throttle)
        self.assertGreater(wait_time, 0)
        
        # Should not throttle for a different domain
        should_throttle, wait_time = await self.rate_limiter.should_throttle("other.com")
        self.assertFalse(should_throttle)
        self.assertEqual(wait_time, 0)
    
    async def async_test_adapt_rate_limit(self):
        """Test adaptive rate limiting."""
        # Initial rate limit
        self.rate_limiter.set_domain_limit("example.com", 20, 1.0)
        
        # Adapt based on slow response
        await self.rate_limiter.adapt_rate_limit("example.com", 3.0, 200)
        self.assertEqual(self.rate_limiter.get_domain_limit("example.com"), 10)  # Reduced
        self.assertEqual(self.rate_limiter.get_domain_cooldown("example.com"), 1.5)  # Increased
        
        # Adapt based on 429 status code
        await self.rate_limiter.adapt_rate_limit("example.com", 1.0, 429)
        self.assertEqual(self.rate_limiter.get_domain_limit("example.com"), 3)  # Significantly reduced
        self.assertEqual(self.rate_limiter.get_domain_cooldown("example.com"), 4.5)  # Significantly increased
    
    def test_async_methods(self):
        """Run async tests."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.async_test_register_request())
            loop.run_until_complete(self.async_test_should_throttle())
            loop.run_until_complete(self.async_test_adapt_rate_limit())
        finally:
            loop.close()


class TestWebConnector(unittest.TestCase):
    """Test cases for the WebConnector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "concurrency": 3,
            "default_rate_limit": 20,
            "default_cooldown": 1.0,
            "domain_rate_limits": {
                "example.com": {"rate_limit": 5, "cooldown": 2.0},
                "test.com": 10
            },
            "max_depth": 2,
            "max_pages": 10,
            "timeout": 30,
            "user_agent": "Test User Agent",
            "javascript_enabled": True
        }
        self.connector = WebConnector(self.config)
    
    def test_initialization(self):
        """Test connector initialization."""
        self.assertEqual(self.connector.name, "web_connector")
        self.assertEqual(self.connector.source_type, "web")
        self.assertIsNone(self.connector.crawler)
        self.assertEqual(self.connector.semaphore._value, 3)
        
        # Check rate limiter configuration
        self.assertEqual(self.connector.rate_limiter.default_rate_limit, 20)
        self.assertEqual(self.connector.rate_limiter.default_cooldown, 1.0)
        self.assertEqual(self.connector.rate_limiter.domain_limits["example.com"], 5)
        self.assertEqual(self.connector.rate_limiter.domain_cooldowns["example.com"], 2.0)
        self.assertEqual(self.connector.rate_limiter.domain_limits["test.com"], 10)
    
    @patch('core.crawl4ai.AsyncWebCrawler')
    def test_initialize(self, mock_crawler):
        """Test connector initialization."""
        # Set up mock
        mock_crawler.return_value = MagicMock()
        
        # Call initialize
        result = self.connector.initialize()
        
        # Check result
        self.assertTrue(result)
        self.assertIsNotNone(self.connector.crawler)
        
        # Verify crawler was created with correct config
        mock_crawler.assert_called_once()
        args, kwargs = mock_crawler.call_args
        config = kwargs.get('config')
        self.assertEqual(config.max_depth, 2)
        self.assertEqual(config.max_pages, 10)
        self.assertEqual(config.timeout, 30)
        self.assertEqual(config.user_agent, "Test User Agent")
        self.assertEqual(config.javascript_enabled, True)
    
    @patch('core.crawl4ai.AsyncWebCrawler')
    def test_initialize_failure(self, mock_crawler):
        """Test connector initialization failure."""
        # Set up mock to raise exception
        mock_crawler.side_effect = Exception("Test error")
        
        # Call initialize
        result = self.connector.initialize()
        
        # Check result
        self.assertFalse(result)
        self.assertIsNone(self.connector.crawler)
    
    @patch('core.connectors.web.WebConnector.initialize')
    @patch('core.connectors.web.WebConnector._process_url')
    async def async_test_collect(self, mock_process_url, mock_initialize):
        """Test collect method."""
        # Set up mocks
        mock_initialize.return_value = True
        mock_process_url.return_value = [MagicMock()]
        self.connector.crawler = AsyncMock()
        
        # Call collect
        params = {"urls": ["https://example.com", "https://test.com"]}
        result = await self.connector.collect(params)
        
        # Check result
        self.assertEqual(len(result), 2)  # Two URLs processed
        self.assertEqual(mock_process_url.call_count, 2)
        self.connector.crawler.start.assert_called_once()
        self.connector.crawler.close.assert_called_once()
    
    @patch('core.connectors.web.WebConnector.initialize')
    async def async_test_collect_no_urls(self, mock_initialize):
        """Test collect method with no URLs."""
        # Set up mock
        mock_initialize.return_value = True
        
        # Call collect with empty params
        result = await self.connector.collect({})
        
        # Check result
        self.assertEqual(result, [])
        
        # Call collect with URLs in config
        self.connector.config["urls"] = ["https://example.com"]
        self.connector.crawler = AsyncMock()
        self.connector._process_url = AsyncMock(return_value=[MagicMock()])
        
        result = await self.connector.collect({})
        
        # Check result
        self.assertEqual(len(result), 1)
        self.connector._process_url.assert_called_once_with("https://example.com", {})
    
    @patch('core.connectors.web.isURL')
    async def async_test_process_url(self, mock_is_url):
        """Test _process_url method."""
        # Set up mocks
        mock_is_url.return_value = True
        self.connector.crawler = AsyncMock()
        
        # Create a mock crawl result
        mock_result = CrawlResult(
            url="https://example.com",
            html="<html><body>Test</body></html>",
            markdown="Test",
            success=True,
            metadata={"title": "Test Page", "author": "Test Author", "publish_date": "2023-01-01"},
            redirected_url="https://example.com"
        )
        self.connector.crawler.arun.return_value = mock_result
        
        # Call _process_url
        result = await self.connector._process_url("https://example.com", {})
        
        # Check result
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].url, "https://example.com")
        self.assertEqual(result[0].content, "Test")
        self.assertEqual(result[0].metadata["title"], "Test Page")
        self.assertEqual(result[0].content_type, "text/markdown")
    
    @patch('core.connectors.web.isURL')
    async def async_test_process_url_failure(self, mock_is_url):
        """Test _process_url method with failure."""
        # Set up mocks
        mock_is_url.return_value = True
        self.connector.crawler = AsyncMock()
        
        # Create a failed crawl result
        mock_result = CrawlResult(
            url="https://example.com",
            html="",
            success=False,
            error_message="Test error"
        )
        self.connector.crawler.arun.return_value = mock_result
        
        # Call _process_url
        result = await self.connector._process_url("https://example.com", {})
        
        # Check result
        self.assertEqual(result, [])
        self.assertEqual(self.connector.stats["failed_requests"], 1)
        self.assertIn("https://example.com", self.connector.failed_urls)
    
    @patch('core.connectors.web.isURL')
    async def async_test_process_url_exception(self, mock_is_url):
        """Test _process_url method with exception."""
        # Set up mocks
        mock_is_url.return_value = True
        self.connector.crawler = AsyncMock()
        self.connector.crawler.arun.side_effect = Exception("Test error")
        
        # Call _process_url
        result = await self.connector._process_url("https://example.com", {})
        
        # Check result
        self.assertEqual(result, [])
        self.assertEqual(self.connector.stats["failed_requests"], 1)
        self.assertIn("https://example.com", self.connector.failed_urls)
    
    async def async_test_get_stats(self):
        """Test get_stats method."""
        # Set up some stats
        self.connector.stats["total_requests"] = 10
        self.connector.stats["successful_requests"] = 8
        self.connector.stats["failed_requests"] = 2
        self.connector.stats["total_processing_time"] = 5.0
        self.connector.stats["domains_accessed"] = {"example.com", "test.com"}
        
        # Call get_stats
        stats = await self.connector.get_stats()
        
        # Check result
        self.assertEqual(stats["total_requests"], 10)
        self.assertEqual(stats["successful_requests"], 8)
        self.assertEqual(stats["failed_requests"], 2)
        self.assertEqual(stats["avg_processing_time"], 0.625)  # 5.0 / 8
        self.assertEqual(stats["success_rate"], 80.0)  # 8 / 10 * 100
        self.assertIn("example.com", stats["domains_accessed"])
        self.assertIn("test.com", stats["domains_accessed"])
    
    async def async_test_retry_failed_urls(self):
        """Test retry_failed_urls method."""
        # Set up failed URLs
        self.connector.failed_urls = {
            "https://example.com": {
                "error": "Test error",
                "timestamp": datetime.now().isoformat(),
                "attempts": 1
            },
            "https://old.com": {
                "error": "Test error",
                "timestamp": "2020-01-01T00:00:00",  # Old timestamp
                "attempts": 1
            },
            "https://max-attempts.com": {
                "error": "Test error",
                "timestamp": datetime.now().isoformat(),
                "attempts": 3  # Max attempts reached
            }
        }
        
        # Mock collect method
        self.connector.collect = AsyncMock(return_value=[MagicMock()])
        
        # Call retry_failed_urls
        result = await self.connector.retry_failed_urls()
        
        # Check result
        self.assertEqual(len(result), 1)  # Only one URL should be retried
        self.connector.collect.assert_called_once()
        call_args = self.connector.collect.call_args[0][0]
        self.assertEqual(len(call_args["urls"]), 1)
        self.assertEqual(call_args["urls"][0], "https://example.com")
        self.assertTrue(call_args["force_refresh"])
    
    async def async_test_shutdown(self):
        """Test shutdown method."""
        # Set up mock
        self.connector.crawler = AsyncMock()
        
        # Call shutdown
        result = await self.connector.shutdown()
        
        # Check result
        self.assertTrue(result)
        self.connector.crawler.close.assert_called_once()
        
        # Test shutdown with exception
        self.connector.crawler.close.side_effect = Exception("Test error")
        result = await self.connector.shutdown()
        self.assertFalse(result)
    
    def test_async_methods(self):
        """Run async tests."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.async_test_collect())
            loop.run_until_complete(self.async_test_collect_no_urls())
            loop.run_until_complete(self.async_test_process_url())
            loop.run_until_complete(self.async_test_process_url_failure())
            loop.run_until_complete(self.async_test_process_url_exception())
            loop.run_until_complete(self.async_test_get_stats())
            loop.run_until_complete(self.async_test_retry_failed_urls())
            loop.run_until_complete(self.async_test_shutdown())
        finally:
            loop.close()


if __name__ == '__main__':
    unittest.main()

