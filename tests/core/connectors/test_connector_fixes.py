#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for the connector fixes.
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime
import time
import requests
import json

from core.connectors import ConnectorBase, DataItem
from core.plugins.connectors.github_connector import GitHubConnector
from core.event_system import EventType


class TestConnectorBaseFixes(unittest.TestCase):
    """Test cases for the ConnectorBase fixes."""

    class MockConnector(ConnectorBase):
        """Mock connector for testing."""
        
        name = "mock_connector"
        description = "Mock connector for testing"
        source_type = "mock"
        
        def __init__(self, config=None, should_fail=False):
            super().__init__(config)
            self.should_fail = should_fail
            self.collect_called = False
            self.session = MagicMock()
            
        def collect(self, params=None):
            """Mock collect method."""
            self.collect_called = True
            if self.should_fail:
                raise Exception("Mock collection failure")
            return [
                DataItem(
                    source_id="mock-1",
                    content="Mock content 1",
                    url="https://example.com/1",
                    metadata={"key": "value"}
                ),
                DataItem(
                    source_id="mock-2",
                    content="Mock content 2",
                    url="https://example.com/2",
                    metadata={"key": "value2"}
                )
            ]

    def test_initialization(self):
        """Test connector initialization."""
        connector = self.MockConnector({
            "rate_limit": 100, 
            "max_connections": 5,
            "retry_count": 3,
            "retry_delay": 1
        })
        self.assertEqual(connector.rate_limit, 100)
        self.assertEqual(connector.max_connections, 5)
        self.assertEqual(connector.retry_count, 3)
        self.assertEqual(connector.retry_delay, 1)
        self.assertEqual(connector.error_count, 0)
        self.assertIsNone(connector.last_run_time)

    def test_shutdown(self):
        """Test connector shutdown."""
        connector = self.MockConnector()
        connector.session = MagicMock()
        
        # Test shutdown
        result = connector.shutdown()
        self.assertTrue(result)
        connector.session.close.assert_called_once()
        self.assertIsNone(connector.session)
        self.assertFalse(connector._initialized)

    def test_update_last_run(self):
        """Test update_last_run method."""
        connector = self.MockConnector()
        self.assertIsNone(connector.last_run_time)
        
        connector.update_last_run()
        self.assertIsNotNone(connector.last_run_time)
        self.assertIsInstance(connector.last_run_time, datetime)

    def test_get_status(self):
        """Test get_status method."""
        connector = self.MockConnector({
            "api_key": "secret_key",
            "rate_limit": 100
        })
        connector.error_count = 5
        connector.update_last_run()
        
        status = connector.get_status()
        self.assertEqual(status["name"], "mock_connector")
        self.assertEqual(status["description"], "Mock connector for testing")
        self.assertEqual(status["source_type"], "mock")
        self.assertEqual(status["error_count"], 5)
        self.assertIsNotNone(status["last_run"])
        
        # Check that sensitive info is not included
        self.assertNotIn("api_key", status["config"])
        self.assertIn("rate_limit", status["config"])

    @patch('core.connectors.publish_sync')
    def test_collect_with_retry_success(self, mock_publish):
        """Test collect_with_retry with successful collection."""
        connector = self.MockConnector()
        
        # Run the async method in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            items = loop.run_until_complete(connector.collect_with_retry())
            self.assertEqual(len(items), 2)
            self.assertEqual(items[0].source_id, "mock-1")
            self.assertTrue(connector.collect_called)
            # Check that success event was published
            self.assertEqual(mock_publish.call_count, 1)
            # Check that last_run_time was updated
            self.assertIsNotNone(connector.last_run_time)
        finally:
            loop.close()

    @patch('core.connectors.publish_sync')
    @patch('core.connectors.logger')
    def test_collect_with_retry_failure(self, mock_logger, mock_publish):
        """Test collect_with_retry with failed collection."""
        connector = self.MockConnector(should_fail=True)
        connector.retry_count = 2
        connector.retry_delay = 0.1  # Short delay for testing
        
        # Run the async method in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with self.assertRaises(ConnectionError):
                loop.run_until_complete(connector.collect_with_retry())
            
            self.assertTrue(connector.collect_called)
            # Check that error events were published (2 attempts + final error)
            self.assertEqual(mock_publish.call_count, 2)
            # Check that warning and error were logged
            mock_logger.warning.assert_called()
            mock_logger.error.assert_called()
            # Check that error_count was incremented
            self.assertEqual(connector.error_count, 2)
        finally:
            loop.close()


class TestGitHubConnectorFixes(unittest.TestCase):
    """Test cases for the GitHubConnector fixes."""

    @patch('requests.Session')
    def test_initialization(self, mock_session):
        """Test GitHub connector initialization."""
        # Mock the session and response
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session_instance.get.return_value = mock_response
        
        # Create connector with API token
        connector = GitHubConnector({
            "api_token": "test_token",
            "rate_limit_pause": 30,
            "max_retries": 5
        })
        
        # Test initialization
        result = connector.initialize()
        self.assertTrue(result)
        self.assertTrue(connector._initialized)
        
        # Check that session was created with correct headers
        mock_session_instance.headers.update.assert_called_with({
            "Authorization": "token test_token",
            "Accept": "application/vnd.github.v3+json"
        })
        
        # Check that a test request was made
        mock_session_instance.get.assert_called_with("https://api.github.com/rate_limit")

    @patch('requests.Session')
    def test_initialization_failure(self, mock_session):
        """Test GitHub connector initialization failure."""
        # Mock the session and response
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_session_instance.get.return_value = mock_response
        
        # Create connector with invalid API token
        connector = GitHubConnector({
            "api_token": "invalid_token"
        })
        
        # Test initialization
        result = connector.initialize()
        self.assertFalse(result)
        self.assertFalse(connector._initialized)

    @patch('requests.Session')
    def test_shutdown(self, mock_session):
        """Test GitHub connector shutdown."""
        # Mock the session
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session_instance.get.return_value = mock_response
        
        # Create and initialize connector
        connector = GitHubConnector({"api_token": "test_token"})
        connector.initialize()
        
        # Test shutdown
        result = connector.shutdown()
        self.assertTrue(result)
        mock_session_instance.close.assert_called_once()
        self.assertIsNone(connector.session)
        self.assertFalse(connector._initialized)

    @patch('requests.Session')
    def test_make_request_success(self, mock_session):
        """Test _make_request with successful request."""
        # Mock the session and response
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}
        mock_session_instance.get.return_value = mock_response
        
        # Create and initialize connector
        connector = GitHubConnector({"api_token": "test_token"})
        connector.initialize()
        
        # Test _make_request
        result = connector._make_request("users/octocat")
        self.assertEqual(result, {"key": "value"})
        mock_session_instance.get.assert_called_with(
            "https://api.github.com/users/octocat",
            params=None,
            timeout=30
        )

    @patch('requests.Session')
    def test_make_request_rate_limit(self, mock_session):
        """Test _make_request with rate limit error."""
        # Mock the session and responses
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        
        # First response is rate limited, second is successful
        mock_rate_limit_response = MagicMock()
        mock_rate_limit_response.status_code = 403
        mock_rate_limit_response.text = "API rate limit exceeded"
        
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {"key": "value"}
        
        mock_session_instance.get.side_effect = [
            mock_rate_limit_response,
            mock_success_response
        ]
        
        # Create and initialize connector with short rate limit pause
        connector = GitHubConnector({
            "api_token": "test_token",
            "rate_limit_pause": 0.1
        })
        connector.initialize()
        
        # Test _make_request
        result = connector._make_request("users/octocat")
        self.assertEqual(result, {"key": "value"})
        self.assertEqual(mock_session_instance.get.call_count, 2)

    @patch('requests.Session')
    def test_make_request_timeout(self, mock_session):
        """Test _make_request with timeout error."""
        # Mock the session and response
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.get.side_effect = requests.exceptions.Timeout("Request timed out")
        
        # Create and initialize connector with short retry delay
        connector = GitHubConnector({
            "api_token": "test_token",
            "max_retries": 2,
            "retry_delay": 0.1
        })
        connector.initialize()
        
        # Test _make_request
        with self.assertRaises(TimeoutError):
            connector._make_request("users/octocat")
        
        # Should have tried max_retries times
        self.assertEqual(mock_session_instance.get.call_count, 2)

    @patch('requests.Session')
    def test_collect_repo_data(self, mock_session):
        """Test _collect_repo_data method."""
        # Mock the session and response
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        
        # Mock response for repo info
        mock_repo_response = MagicMock()
        mock_repo_response.status_code = 200
        mock_repo_response.json.return_value = {
            "id": 123,
            "name": "test-repo",
            "full_name": "octocat/test-repo",
            "description": "Test repository",
            "owner": {"login": "octocat"},
            "stargazers_count": 100,
            "forks_count": 50,
            "open_issues_count": 10,
            "default_branch": "main",
            "created_at": "2020-01-01T00:00:00Z",
            "updated_at": "2020-01-02T00:00:00Z",
            "language": "Python",
            "topics": ["test", "example"],
            "html_url": "https://github.com/octocat/test-repo"
        }
        
        # Mock response for rate limit check
        mock_rate_limit_response = MagicMock()
        mock_rate_limit_response.status_code = 200
        
        mock_session_instance.get.side_effect = [
            mock_rate_limit_response,  # For initialization
            mock_repo_response  # For repo info
        ]
        
        # Create and initialize connector
        connector = GitHubConnector({"api_token": "test_token"})
        connector.initialize()
        
        # Test _collect_repo_data
        results = connector._collect_repo_data("octocat/test-repo", {"data_type": "info"})
        
        # Check results
        self.assertEqual(len(results), 1)
        data_item = results[0]
        self.assertEqual(data_item.source_id, "github_repo_123")
        self.assertIn("# test-repo", data_item.content)
        self.assertEqual(data_item.metadata["repo_name"], "test-repo")
        self.assertEqual(data_item.metadata["owner"], "octocat")
        self.assertEqual(data_item.url, "https://github.com/octocat/test-repo")


if __name__ == '__main__':
    unittest.main()

