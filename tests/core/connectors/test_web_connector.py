#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the web connector module.

This module contains tests for the web connector to ensure it works correctly.
"""

import os
import json
import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, List, Any, Optional

import pytest
import aiohttp

from core.connectors.web import WebConnector, WebDataItem
from core.validation import ValidationResult


class TestWebConnector(unittest.TestCase):
    """Test cases for the WebConnector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "rate_limit": 10,
            "max_connections": 5,
            "retry_count": 3,
            "retry_delay": 0.1,  # Short delay for testing
            "user_agent": "Wiseflow Test Agent/1.0",
            "timeout": 10
        }
        self.connector = WebConnector(self.config)
    
    @patch('core.connectors.web.aiohttp.ClientSession')
    def test_initialization(self, mock_session):
        """Test connector initialization."""
        self.assertEqual(self.connector.rate_limit, 10)
        self.assertEqual(self.connector.max_connections, 5)
        self.assertEqual(self.connector.retry_count, 3)
        self.assertEqual(self.connector.retry_delay, 0.1)
        self.assertEqual(self.connector.user_agent, "Wiseflow Test Agent/1.0")
        self.assertEqual(self.connector.timeout, 10)
    
    @patch('core.connectors.web.aiohttp.ClientSession')
    def test_validate_config(self, mock_session):
        """Test config validation."""
        # Valid config
        result = self.connector.validate_config()
        self.assertTrue(result)
        
        # Invalid config (negative rate limit)
        invalid_connector = WebConnector({"rate_limit": -1})
        result = invalid_connector.validate_config()
        self.assertFalse(result)
    
    @patch('core.connectors.web.aiohttp.ClientSession')
    async def test_fetch_url_success(self, mock_session):
        """Test successful URL fetching."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="<html><body>Test content</body></html>")
        mock_response.headers = {"Content-Type": "text/html"}
        
        # Mock session
        mock_session_instance = MagicMock()
        mock_session_instance.get = AsyncMock(return_value=mock_response)
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Call fetch_url
        url = "https://example.com"
        result = await self.connector.fetch_url(url)
        
        # Check result
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value.url, url)
        self.assertEqual(result.value.content, "<html><body>Test content</body></html>")
        self.assertEqual(result.value.metadata["status_code"], 200)
        self.assertEqual(result.value.metadata["content_type"], "text/html")
        
        # Check session was called correctly
        mock_session_instance.get.assert_called_once()
        call_args = mock_session_instance.get.call_args[0]
        call_kwargs = mock_session_instance.get.call_args[1]
        self.assertEqual(call_args[0], url)
        self.assertEqual(call_kwargs["headers"]["User-Agent"], "Wiseflow Test Agent/1.0")
        self.assertEqual(call_kwargs["timeout"], 10)
    
    @patch('core.connectors.web.aiohttp.ClientSession')
    async def test_fetch_url_failure(self, mock_session):
        """Test failed URL fetching."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Not Found")
        mock_response.headers = {"Content-Type": "text/plain"}
        
        # Mock session
        mock_session_instance = MagicMock()
        mock_session_instance.get = AsyncMock(return_value=mock_response)
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Call fetch_url
        url = "https://example.com/not-found"
        result = await self.connector.fetch_url(url)
        
        # Check result
        self.assertFalse(result.is_valid)
        self.assertIn("HTTP error 404", result.errors[0])
    
    @patch('core.connectors.web.aiohttp.ClientSession')
    async def test_fetch_url_exception(self, mock_session):
        """Test URL fetching with exception."""
        # Mock session to raise exception
        mock_session_instance = MagicMock()
        mock_session_instance.get = AsyncMock(side_effect=aiohttp.ClientError("Connection error"))
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Call fetch_url
        url = "https://example.com"
        result = await self.connector.fetch_url(url)
        
        # Check result
        self.assertFalse(result.is_valid)
        self.assertIn("Connection error", result.errors[0])
    
    @patch('core.connectors.web.WebConnector.fetch_url')
    def test_collect(self, mock_fetch_url):
        """Test the collect method."""
        # Mock fetch_url to return success
        mock_fetch_url.return_value = asyncio.Future()
        mock_fetch_url.return_value.set_result(ValidationResult(
            True,
            WebDataItem(
                source_id="web-1",
                content="<html><body>Test content</body></html>",
                url="https://example.com",
                metadata={
                    "status_code": 200,
                    "content_type": "text/html",
                    "headers": {"Content-Type": "text/html"}
                }
            )
        ))
        
        # Call collect
        params = {"urls": ["https://example.com"]}
        items = self.connector.collect(params)
        
        # Check result
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source_id, "web-1")
        self.assertEqual(items[0].url, "https://example.com")
        self.assertEqual(items[0].content, "<html><body>Test content</body></html>")
    
    @patch('core.connectors.web.WebConnector.fetch_url')
    def test_collect_multiple_urls(self, mock_fetch_url):
        """Test collecting from multiple URLs."""
        # Mock fetch_url to return success for multiple URLs
        def mock_fetch_url_side_effect(url):
            future = asyncio.Future()
            future.set_result(ValidationResult(
                True,
                WebDataItem(
                    source_id=f"web-{url.split('.')[-1]}",
                    content=f"<html><body>Content from {url}</body></html>",
                    url=url,
                    metadata={
                        "status_code": 200,
                        "content_type": "text/html",
                        "headers": {"Content-Type": "text/html"}
                    }
                )
            ))
            return future
        
        mock_fetch_url.side_effect = mock_fetch_url_side_effect
        
        # Call collect
        params = {"urls": ["https://example.com", "https://example.org"]}
        items = self.connector.collect(params)
        
        # Check result
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].url, "https://example.com")
        self.assertEqual(items[1].url, "https://example.org")
    
    @patch('core.connectors.web.WebConnector.fetch_url')
    def test_collect_with_failures(self, mock_fetch_url):
        """Test collecting with some failures."""
        # Mock fetch_url to return success for one URL and failure for another
        def mock_fetch_url_side_effect(url):
            future = asyncio.Future()
            if "success" in url:
                future.set_result(ValidationResult(
                    True,
                    WebDataItem(
                        source_id="web-success",
                        content="<html><body>Success content</body></html>",
                        url=url,
                        metadata={
                            "status_code": 200,
                            "content_type": "text/html",
                            "headers": {"Content-Type": "text/html"}
                        }
                    )
                ))
            else:
                future.set_result(ValidationResult(
                    False,
                    None,
                    ["HTTP error 404"]
                ))
            return future
        
        mock_fetch_url.side_effect = mock_fetch_url_side_effect
        
        # Call collect
        params = {"urls": ["https://success.com", "https://failure.com"]}
        items = self.connector.collect(params)
        
        # Check result
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].url, "https://success.com")
    
    @patch('core.connectors.web.WebConnector.fetch_url')
    def test_collect_with_no_urls(self, mock_fetch_url):
        """Test collecting with no URLs."""
        # Call collect with no URLs
        params = {"urls": []}
        items = self.connector.collect(params)
        
        # Check result
        self.assertEqual(len(items), 0)
        mock_fetch_url.assert_not_called()
    
    @patch('core.connectors.web.WebConnector.fetch_url')
    def test_collect_with_invalid_params(self, mock_fetch_url):
        """Test collecting with invalid parameters."""
        # Call collect with invalid params
        with self.assertRaises(ValueError):
            self.connector.collect({"invalid": "params"})
        
        # Call collect with None params
        with self.assertRaises(ValueError):
            self.connector.collect(None)
        
        mock_fetch_url.assert_not_called()


# Run the async tests
def test_fetch_url_success():
    """Run the async test for successful URL fetching."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(TestWebConnector().test_fetch_url_success())
    finally:
        loop.close()

def test_fetch_url_failure():
    """Run the async test for failed URL fetching."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(TestWebConnector().test_fetch_url_failure())
    finally:
        loop.close()

def test_fetch_url_exception():
    """Run the async test for URL fetching with exception."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(TestWebConnector().test_fetch_url_exception())
    finally:
        loop.close()


if __name__ == "__main__":
    unittest.main()

