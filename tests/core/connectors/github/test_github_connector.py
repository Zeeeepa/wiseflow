"""
Tests for the asynchronous GitHub connector.
"""

import os
import json
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from core.connectors.github import GitHubConnector, GitHubRateLimitExceeded, GitHubAPIError


@pytest.fixture
def github_connector():
    """Create a GitHub connector instance for testing."""
    config = {
        'api_token': 'test_token',
        'rate_limit_pause': 1,  # Short pause for testing
        'max_retries': 2,
        'cache_enabled': False,  # Disable caching for tests
        'concurrency': 3
    }
    connector = GitHubConnector(config)
    connector.initialize()
    return connector


@pytest.fixture
def mock_response():
    """Create a mock response object."""
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={'key': 'value'})
    response.text = AsyncMock(return_value='{"key": "value"}')
    response.headers = {
        'X-RateLimit-Remaining': '50',
        'X-RateLimit-Reset': str(int((datetime.now() + timedelta(hours=1)).timestamp())),
        'X-RateLimit-Limit': '60',
        'ETag': 'W/"random-etag"'
    }
    return response


@pytest.mark.asyncio
async def test_initialization(github_connector):
    """Test connector initialization."""
    assert github_connector.api_token == 'test_token'
    assert github_connector.semaphore._value == 3
    
    # Test session creation
    session = await github_connector._create_session()
    assert session is not None
    assert 'Authorization' in session.headers
    assert 'Accept' in session.headers
    
    # Clean up
    await github_connector._close_session()


@pytest.mark.asyncio
async def test_make_request_success(github_connector, mock_response):
    """Test successful API request."""
    # Mock the session get method
    github_connector.session = AsyncMock()
    github_connector.session.get = AsyncMock()
    github_connector.session.get.return_value.__aenter__.return_value = mock_response
    
    result = await github_connector._make_request('repos/test/repo')
    
    assert result == {'key': 'value'}
    github_connector.session.get.assert_called_once()
    assert github_connector.rate_limit_remaining == 50
    assert github_connector.rate_limit_limit == 60
    
    # Clean up
    await github_connector._close_session()


@pytest.mark.asyncio
async def test_make_request_rate_limit(github_connector):
    """Test rate limit handling."""
    # Create a response that indicates rate limiting
    rate_limit_response = AsyncMock()
    rate_limit_response.status = 403
    rate_limit_response.text = AsyncMock(return_value='API rate limit exceeded')
    rate_limit_response.headers = {
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Reset': str(int((datetime.now() + timedelta(seconds=5)).timestamp())),
        'X-RateLimit-Limit': '60'
    }
    
    # Create a success response for the retry
    success_response = AsyncMock()
    success_response.status = 200
    success_response.json = AsyncMock(return_value={'key': 'value'})
    success_response.text = AsyncMock(return_value='{"key": "value"}')
    success_response.headers = {
        'X-RateLimit-Remaining': '59',
        'X-RateLimit-Reset': str(int((datetime.now() + timedelta(hours=1)).timestamp())),
        'X-RateLimit-Limit': '60'
    }
    
    # Mock the session get method
    github_connector.session = AsyncMock()
    github_connector.session.get = AsyncMock()
    github_connector.session.get.return_value.__aenter__.side_effect = [
        rate_limit_response,
        success_response
    ]
    
    result = await github_connector._make_request('repos/test/repo')
    
    assert result == {'key': 'value'}
    assert github_connector.session.get.call_count == 2
    assert github_connector.rate_limit_remaining == 59
    
    # Clean up
    await github_connector._close_session()


@pytest.mark.asyncio
async def test_make_request_error(github_connector):
    """Test error handling."""
    # Create an error response
    error_response = AsyncMock()
    error_response.status = 404
    error_response.text = AsyncMock(return_value='Not found')
    error_response.json = AsyncMock(return_value={'message': 'Not found'})
    error_response.headers = {}
    
    # Mock the session get method
    github_connector.session = AsyncMock()
    github_connector.session.get = AsyncMock()
    github_connector.session.get.return_value.__aenter__.return_value = error_response
    
    with pytest.raises(GitHubAPIError) as excinfo:
        await github_connector._make_request('repos/test/repo')
    
    assert excinfo.value.status_code == 404
    assert 'Not found' in str(excinfo.value)
    
    # Clean up
    await github_connector._close_session()


@pytest.mark.asyncio
async def test_make_request_retry_server_error(github_connector):
    """Test retry on server error."""
    # Create a server error response
    server_error = AsyncMock()
    server_error.status = 500
    server_error.text = AsyncMock(return_value='Internal server error')
    server_error.json = AsyncMock(side_effect=ValueError("Invalid JSON"))
    server_error.headers = {}
    
    # Create a success response for the retry
    success_response = AsyncMock()
    success_response.status = 200
    success_response.json = AsyncMock(return_value={'key': 'value'})
    success_response.text = AsyncMock(return_value='{"key": "value"}')
    success_response.headers = {}
    
    # Mock the session get method
    github_connector.session = AsyncMock()
    github_connector.session.get = AsyncMock()
    github_connector.session.get.return_value.__aenter__.side_effect = [
        server_error,
        success_response
    ]
    
    result = await github_connector._make_request('repos/test/repo')
    
    assert result == {'key': 'value'}
    assert github_connector.session.get.call_count == 2
    
    # Clean up
    await github_connector._close_session()


@pytest.mark.asyncio
async def test_collect_repo_info(github_connector, mock_response):
    """Test collecting repository information."""
    # Mock the _make_request method
    github_connector._make_request = AsyncMock(return_value={
        'name': 'test-repo',
        'full_name': 'test/test-repo',
        'description': 'Test repository',
        'owner': {'login': 'test'},
        'html_url': 'https://github.com/test/test-repo',
        'updated_at': '2023-01-01T00:00:00Z'
    })
    
    # Mock the _get_repo_readme method
    github_connector._get_repo_readme = AsyncMock(return_value='# Test Repository\n\nThis is a test repository.')
    
    result = await github_connector._collect_repo_info('test/test-repo')
    
    assert len(result) == 1
    assert result[0].source_id == 'github_repo_test_test-repo'
    assert result[0].content == '# Test Repository\n\nThis is a test repository.'
    assert result[0].metadata['name'] == 'test-repo'
    assert result[0].content_type == 'text/markdown'
    
    # Clean up
    await github_connector._close_session()


@pytest.mark.asyncio
async def test_get_repo_readme(github_connector):
    """Test getting repository README."""
    # Mock the _make_request method
    github_connector._make_request = AsyncMock(return_value={
        'content': base64.b64encode('# Test Repository\n\nThis is a test repository.'.encode()).decode()
    })
    
    result = await github_connector._get_repo_readme('test/test-repo')
    
    assert result == '# Test Repository\n\nThis is a test repository.'
    github_connector._make_request.assert_called_once_with('repos/test/test-repo/readme')
    
    # Test handling of 404 (no README)
    github_connector._make_request = AsyncMock(side_effect=GitHubAPIError(404, 'Not found'))
    
    result = await github_connector._get_repo_readme('test/test-repo')
    
    assert result is None
    
    # Clean up
    await github_connector._close_session()


@pytest.mark.asyncio
async def test_collect_with_rate_limit_error(github_connector):
    """Test collect method with rate limit error."""
    # Mock the _make_request method to raise a rate limit error
    reset_time = datetime.now() + timedelta(minutes=10)
    github_connector._make_request = AsyncMock(side_effect=GitHubRateLimitExceeded(reset_time))
    
    result = await github_connector.collect({'repo': 'test/test-repo'})
    
    assert len(result) == 1
    assert 'rate_limit_exceeded' in result[0].metadata['error']
    assert reset_time.isoformat() in result[0].metadata['reset_time']
    
    # Clean up
    await github_connector._close_session()


@pytest.mark.asyncio
async def test_collect_with_api_error(github_connector):
    """Test collect method with API error."""
    # Mock the _make_request method to raise an API error
    github_connector._make_request = AsyncMock(side_effect=GitHubAPIError(404, 'Not found'))
    
    result = await github_connector.collect({'repo': 'test/test-repo'})
    
    assert len(result) == 1
    assert 'api_error' in result[0].metadata['error']
    assert result[0].metadata['status_code'] == 404
    
    # Clean up
    await github_connector._close_session()


@pytest.mark.asyncio
async def test_collect_with_general_error(github_connector):
    """Test collect method with general error."""
    # Mock the _make_request method to raise a general error
    github_connector._make_request = AsyncMock(side_effect=Exception('Test error'))
    
    result = await github_connector.collect({'repo': 'test/test-repo'})
    
    assert len(result) == 1
    assert 'general_error' in result[0].metadata['error']
    assert 'Test error' in result[0].metadata['message']
    
    # Clean up
    await github_connector._close_session()


@pytest.mark.asyncio
async def test_search_github(github_connector, mock_response):
    """Test searching GitHub."""
    # Mock the _make_request method
    github_connector._make_request = AsyncMock(return_value={
        'items': [
            {
                'name': 'test-repo',
                'full_name': 'test/test-repo',
                'description': 'Test repository',
                'owner': {'login': 'test'},
                'html_url': 'https://github.com/test/test-repo',
                'updated_at': '2023-01-01T00:00:00Z',
                'stargazers_count': 10,
                'forks_count': 5,
                'language': 'Python',
                'topics': ['test', 'example'],
                'score': 0.9
            }
        ]
    })
    
    result = await github_connector._search_github('repositories', 'test', {'per_page': 10})
    
    assert len(result) == 1
    assert result[0].source_id == 'github_repo_test_test-repo'
    assert result[0].metadata['name'] == 'test-repo'
    assert result[0].metadata['search_score'] == 0.9
    
    # Clean up
    await github_connector._close_session()


@pytest.mark.asyncio
async def test_get_rate_limit_info(github_connector):
    """Test getting rate limit information."""
    # Mock the _make_request method
    github_connector._make_request = AsyncMock(return_value={
        'resources': {
            'core': {
                'limit': 60,
                'remaining': 50,
                'reset': int((datetime.now() + timedelta(hours=1)).timestamp())
            },
            'search': {
                'limit': 10,
                'remaining': 8,
                'reset': int((datetime.now() + timedelta(hours=1)).timestamp())
            }
        }
    })
    
    result = await github_connector.get_rate_limit_info()
    
    assert 'core' in result
    assert 'search' in result
    github_connector._make_request.assert_called_once_with('rate_limit')
    
    # Clean up
    await github_connector._close_session()

