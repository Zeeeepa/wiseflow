"""
Tests for the Code Search Connector.
"""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from core.connectors.code_search import CodeSearchConnector, CodeSearchError, CodeSearchRateLimitError
from core.connectors import DataItem
from core.crawl4ai.cache_context import CacheMode, CacheContext


@pytest.fixture
def code_search_connector():
    """Create a code search connector for testing."""
    config = {
        "github_token": "test_github_token",
        "gitlab_token": "test_gitlab_token",
        "bitbucket_token": "test_bitbucket_token",
        "sourcegraph_token": "test_sourcegraph_token",
        "concurrency": 2,
        "timeout": 5,
        "cache_enabled": True,
        "cache_ttl": 60,  # 1 minute for testing
        "cache_dir": "/tmp/wiseflow_test_cache"
    }
    
    connector = CodeSearchConnector(config)
    connector.initialize()
    
    # Create a test session
    loop = asyncio.get_event_loop()
    loop.run_until_complete(connector._create_session())
    
    yield connector
    
    # Clean up
    loop.run_until_complete(connector._close_session())


@pytest.mark.asyncio
async def test_initialize(code_search_connector):
    """Test connector initialization."""
    assert code_search_connector.initialized is True
    assert code_search_connector.github_token == "test_github_token"
    assert code_search_connector.gitlab_token == "test_gitlab_token"
    assert code_search_connector.bitbucket_token == "test_bitbucket_token"
    assert code_search_connector.sourcegraph_token == "test_sourcegraph_token"
    assert code_search_connector.concurrency == 2
    assert code_search_connector.timeout == 5
    assert code_search_connector.cache_enabled is True
    assert code_search_connector.cache_ttl == 60


@pytest.mark.asyncio
async def test_cache_operations(code_search_connector):
    """Test cache operations."""
    # Test data
    service = "github"
    query = "test_query"
    params = {"language": "python"}
    
    # Create test items
    items = [
        DataItem(
            source_id="test1",
            content="test content 1",
            metadata={"repo": "test/repo1", "path": "file1.py"},
            url="https://github.com/test/repo1/blob/main/file1.py",
            content_type="text/x-python"
        ),
        DataItem(
            source_id="test2",
            content="test content 2",
            metadata={"repo": "test/repo2", "path": "file2.py"},
            url="https://github.com/test/repo2/blob/main/file2.py",
            content_type="text/x-python"
        )
    ]
    
    # Save to cache
    await code_search_connector._save_to_cache(service, query, params, items)
    
    # Get from cache
    cached_items = await code_search_connector._get_from_cache(service, query, params)
    
    # Verify cache hit
    assert cached_items is not None
    assert len(cached_items) == 2
    assert cached_items[0].source_id == "test1"
    assert cached_items[0].content == "test content 1"
    assert cached_items[1].source_id == "test2"
    assert cached_items[1].content == "test content 2"
    
    # Test cache with different params
    different_params = {"language": "javascript"}
    different_cached_items = await code_search_connector._get_from_cache(service, query, different_params)
    
    # Verify cache miss
    assert different_cached_items is None


@pytest.mark.asyncio
async def test_rate_limit_handling():
    """Test rate limit handling."""
    config = {
        "github_token": "test_github_token",
        "concurrency": 1,
        "timeout": 5,
        "cache_enabled": False
    }
    
    connector = CodeSearchConnector(config)
    connector.initialize()
    
    # Create a test session
    await connector._create_session()
    
    # Mock response with rate limit headers
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.headers = {
        "X-RateLimit-Remaining": "5",
        "X-RateLimit-Reset": str(int((datetime.now() + timedelta(minutes=1)).timestamp()))
    }
    
    # Update rate limit state
    await connector._update_rate_limit_state("github", mock_response)
    
    # Check rate limit state
    can_proceed, retry_after = await connector._check_rate_limit("github")
    assert can_proceed is True
    assert retry_after is None
    
    # Mock rate limit exceeded
    mock_response.headers = {
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": str(int((datetime.now() + timedelta(minutes=1)).timestamp()))
    }
    
    # Update rate limit state
    await connector._update_rate_limit_state("github", mock_response)
    
    # Check rate limit state
    can_proceed, retry_after = await connector._check_rate_limit("github")
    assert can_proceed is False
    assert retry_after is not None
    assert retry_after > 0
    
    # Clean up
    await connector._close_session()


@pytest.mark.asyncio
async def test_github_search(code_search_connector):
    """Test GitHub code search."""
    # Mock the _make_request method
    with patch.object(code_search_connector, '_make_request', new_callable=AsyncMock) as mock_make_request:
        # Mock response data
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {
            "X-RateLimit-Remaining": "100",
            "X-RateLimit-Reset": str(int((datetime.now() + timedelta(minutes=1)).timestamp()))
        }
        
        # Mock search results
        mock_search_data = {
            "total_count": 2,
            "incomplete_results": False,
            "items": [
                {
                    "name": "test_file1.py",
                    "path": "src/test_file1.py",
                    "repository": {
                        "full_name": "test/repo1"
                    },
                    "html_url": "https://github.com/test/repo1/blob/main/src/test_file1.py"
                },
                {
                    "name": "test_file2.py",
                    "path": "src/test_file2.py",
                    "repository": {
                        "full_name": "test/repo2"
                    },
                    "html_url": "https://github.com/test/repo2/blob/main/src/test_file2.py"
                }
            ]
        }
        
        # Mock file content
        mock_file_content = {
            "content": "ZGVmIHRlc3RfZnVuY3Rpb24oKToKICAgIHBhc3M=",  # base64 encoded "def test_function():\n    pass"
            "encoding": "base64"
        }
        
        # Set up mock return values
        mock_make_request.side_effect = [
            (mock_search_data, mock_response),  # First call for search
            (mock_file_content, mock_response),  # Second call for first file content
            (mock_file_content, mock_response)   # Third call for second file content
        ]
        
        # Disable caching for this test
        code_search_connector.cache_enabled = False
        
        # Call the search method
        results = await code_search_connector._search_github({
            "query": "test_function",
            "language": "python",
            "max_results": 10
        })
        
        # Verify results
        assert len(results) == 2
        assert results[0].metadata["name"] == "test_file1.py"
        assert results[0].metadata["repo"] == "test/repo1"
        assert results[0].content == "def test_function():\n    pass"
        assert results[1].metadata["name"] == "test_file2.py"
        assert results[1].metadata["repo"] == "test/repo2"
        assert results[1].content == "def test_function():\n    pass"
        
        # Verify API calls
        assert mock_make_request.call_count == 3
        
        # First call should be to search API
        args, kwargs = mock_make_request.call_args_list[0]
        assert args[0] == "github"
        assert "search/code" in args[1]
        assert "test_function" in kwargs["params"]["q"]
        assert "language:python" in kwargs["params"]["q"]


@pytest.mark.asyncio
async def test_error_handling(code_search_connector):
    """Test error handling."""
    # Mock the _make_request method to raise an exception
    with patch.object(code_search_connector, '_make_request', new_callable=AsyncMock) as mock_make_request:
        # Mock a rate limit error
        mock_make_request.side_effect = CodeSearchRateLimitError(
            "GitHub rate limit exceeded",
            service="github",
            retry_after=60
        )
        
        # Disable caching for this test
        code_search_connector.cache_enabled = False
        
        # Call the search method and expect an exception
        with pytest.raises(CodeSearchError) as excinfo:
            await code_search_connector._search_github({
                "query": "test_function",
                "language": "python",
                "max_results": 10
            })
        
        # Verify the exception
        assert "GitHub search error" in str(excinfo.value)
        assert "rate limit exceeded" in str(excinfo.value.__cause__)


@pytest.mark.asyncio
async def test_content_type_detection(code_search_connector):
    """Test content type detection."""
    # Test various file extensions
    assert code_search_connector._get_content_type("test.py") == "text/x-python"
    assert code_search_connector._get_content_type("test.js") == "text/javascript"
    assert code_search_connector._get_content_type("test.jsx") == "text/javascript"
    assert code_search_connector._get_content_type("test.ts") == "text/typescript"
    assert code_search_connector._get_content_type("test.tsx") == "text/typescript"
    assert code_search_connector._get_content_type("test.html") == "text/html"
    assert code_search_connector._get_content_type("test.css") == "text/css"
    assert code_search_connector._get_content_type("test.json") == "application/json"
    assert code_search_connector._get_content_type("test.md") == "text/markdown"
    assert code_search_connector._get_content_type("test.java") == "text/x-java"
    assert code_search_connector._get_content_type("test.c") == "text/x-c"
    assert code_search_connector._get_content_type("test.cpp") == "text/x-c++"
    assert code_search_connector._get_content_type("test.go") == "text/x-go"
    assert code_search_connector._get_content_type("test.rb") == "text/x-ruby"
    assert code_search_connector._get_content_type("test.unknown") == "text/plain"


@pytest.mark.asyncio
async def test_search_all_sources(code_search_connector):
    """Test searching across all sources."""
    # Mock the individual search methods
    with patch.object(code_search_connector, '_search_github', new_callable=AsyncMock) as mock_github_search, \
         patch.object(code_search_connector, '_search_gitlab', new_callable=AsyncMock) as mock_gitlab_search, \
         patch.object(code_search_connector, '_search_sourcegraph', new_callable=AsyncMock) as mock_sourcegraph_search:
        
        # Set up mock return values
        mock_github_search.return_value = [
            DataItem(
                source_id="github1",
                content="github content 1",
                metadata={"repo": "github/repo1", "path": "file1.py", "source": "github"},
                url="https://github.com/github/repo1/blob/main/file1.py"
            )
        ]
        
        mock_gitlab_search.return_value = [
            DataItem(
                source_id="gitlab1",
                content="gitlab content 1",
                metadata={"project_id": "123", "path": "file1.py", "source": "gitlab"},
                url="https://gitlab.com/gitlab/repo1/blob/main/file1.py"
            )
        ]
        
        mock_sourcegraph_search.return_value = [
            DataItem(
                source_id="sourcegraph1",
                content="sourcegraph content 1",
                metadata={"repo": "sourcegraph/repo1", "path": "file1.py", "source": "sourcegraph"},
                url="https://sourcegraph.com/github.com/sourcegraph/repo1/-/blob/file1.py"
            )
        ]
        
        # Disable caching for this test
        code_search_connector.cache_enabled = False
        
        # Call the search_all_sources method
        results = await code_search_connector._search_all_sources({
            "query": "test_function",
            "sources": ["github", "gitlab", "sourcegraph"],
            "max_results": 10
        })
        
        # Verify results
        assert len(results) == 3
        
        # Verify source distribution
        sources = [item.metadata["source"] for item in results]
        assert "github" in sources
        assert "gitlab" in sources
        assert "sourcegraph" in sources
        
        # Verify that each search method was called
        mock_github_search.assert_called_once()
        mock_gitlab_search.assert_called_once()
        mock_sourcegraph_search.assert_called_once()


@pytest.mark.asyncio
async def test_get_file_content(code_search_connector):
    """Test getting file content from URLs."""
    # Mock the session get method
    with patch.object(code_search_connector.session, 'get', new_callable=AsyncMock) as mock_get:
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="def test_function():\n    pass")
        
        # Set up mock return value
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Call the get_file_content method
        content = await code_search_connector.get_file_content("https://example.com/test.py")
        
        # Verify result
        assert content == "def test_function():\n    pass"
        
        # Verify API call
        mock_get.assert_called_once_with("https://example.com/test.py", headers={})


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])

