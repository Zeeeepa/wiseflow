"""
Tests for the GitHub connector plugin.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from core.plugins.connectors.github_connector import GitHubConnector, GitHubRateLimitExceeded, GitHubAPIError


@pytest.fixture
def github_connector():
    """Create a GitHub connector instance for testing."""
    config = {
        'api_token': 'test_token',
        'rate_limit_pause': 1,  # Short pause for testing
        'max_retries': 2,
        'cache_enabled': False,  # Disable caching for tests
    }
    connector = GitHubConnector(config)
    connector.initialize()
    return connector


@pytest.fixture
def mock_response():
    """Create a mock response object."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {'key': 'value'}
    response.headers = {
        'X-RateLimit-Remaining': '50',
        'X-RateLimit-Reset': str(int((datetime.now() + timedelta(hours=1)).timestamp())),
        'X-RateLimit-Limit': '60',
        'ETag': 'W/"random-etag"'
    }
    return response


def test_initialization(github_connector):
    """Test connector initialization."""
    assert github_connector.initialized
    assert github_connector.api_token == 'test_token'
    assert github_connector.rate_limit_pause == 1
    assert github_connector.max_retries == 2
    assert github_connector.session is not None


def test_validate_config(github_connector):
    """Test configuration validation."""
    assert github_connector.validate_config()
    
    # Test with no API token
    github_connector.api_token = None
    assert github_connector.validate_config()  # Should still be valid, just with a warning


def test_connect_disconnect(github_connector):
    """Test connect and disconnect methods."""
    # Already initialized in fixture
    assert github_connector.connect()
    
    # Test disconnect
    assert github_connector.disconnect()
    assert github_connector.session is None
    assert not github_connector.initialized


@patch('requests.Session.get')
def test_make_request_success(mock_get, github_connector, mock_response):
    """Test successful API request."""
    mock_get.return_value = mock_response
    
    result = github_connector._make_request('repos/test/repo')
    
    assert result == {'key': 'value'}
    mock_get.assert_called_once()
    assert github_connector.rate_limit_remaining == 50
    assert github_connector.rate_limit_limit == 60


@patch('requests.Session.get')
def test_make_request_rate_limit(mock_get, github_connector):
    """Test rate limit handling."""
    # Create a response that indicates rate limiting
    rate_limit_response = MagicMock()
    rate_limit_response.status_code = 403
    rate_limit_response.text = 'API rate limit exceeded'
    rate_limit_response.headers = {
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Reset': str(int((datetime.now() + timedelta(seconds=5)).timestamp())),
        'X-RateLimit-Limit': '60'
    }
    
    # Create a success response for the retry
    success_response = MagicMock()
    success_response.status_code = 200
    success_response.json.return_value = {'key': 'value'}
    success_response.headers = {
        'X-RateLimit-Remaining': '59',
        'X-RateLimit-Reset': str(int((datetime.now() + timedelta(hours=1)).timestamp())),
        'X-RateLimit-Limit': '60'
    }
    
    # First call returns rate limit, second call succeeds
    mock_get.side_effect = [rate_limit_response, success_response]
    
    result = github_connector._make_request('repos/test/repo')
    
    assert result == {'key': 'value'}
    assert mock_get.call_count == 2
    assert github_connector.rate_limit_remaining == 59


@patch('requests.Session.get')
def test_make_request_error(mock_get, github_connector):
    """Test error handling."""
    # Create an error response
    error_response = MagicMock()
    error_response.status_code = 404
    error_response.text = 'Not found'
    error_response.json.return_value = {'message': 'Not found'}
    error_response.headers = {}
    
    mock_get.return_value = error_response
    
    with pytest.raises(GitHubAPIError) as excinfo:
        github_connector._make_request('repos/test/repo')
    
    assert excinfo.value.status_code == 404
    assert 'Not found' in str(excinfo.value)


@patch('requests.Session.get')
def test_make_request_retry_server_error(mock_get, github_connector):
    """Test retry on server error."""
    # Create a server error response
    server_error = MagicMock()
    server_error.status_code = 500
    server_error.text = 'Internal server error'
    server_error.json.side_effect = ValueError("Invalid JSON")
    server_error.headers = {}
    
    # Create a success response for the retry
    success_response = MagicMock()
    success_response.status_code = 200
    success_response.json.return_value = {'key': 'value'}
    success_response.headers = {}
    
    # First call returns server error, second call succeeds
    mock_get.side_effect = [server_error, success_response]
    
    result = github_connector._make_request('repos/test/repo')
    
    assert result == {'key': 'value'}
    assert mock_get.call_count == 2


@patch('requests.Session.get')
def test_fetch_data_repo(mock_get, github_connector, mock_response):
    """Test fetching repository data."""
    mock_get.return_value = mock_response
    
    result = github_connector.fetch_data('test/repo', query_type='repo')
    
    assert result == {'key': 'value'}
    mock_get.assert_called_once()


@patch('requests.Session.get')
def test_fetch_data_code_search(mock_get, github_connector, mock_response):
    """Test code search."""
    mock_get.return_value = mock_response
    
    result = github_connector.fetch_data('test query', query_type='code')
    
    assert result == {'key': 'value'}
    mock_get.assert_called_once()
    # Verify the URL contains search/code
    args, kwargs = mock_get.call_args
    assert 'search/code' in args[0]


@patch('requests.Session.get')
def test_fetch_data_issues_search(mock_get, github_connector, mock_response):
    """Test issues search."""
    mock_get.return_value = mock_response
    
    result = github_connector.fetch_data('test query', query_type='issues')
    
    assert result == {'key': 'value'}
    mock_get.assert_called_once()
    # Verify the URL contains search/issues
    args, kwargs = mock_get.call_args
    assert 'search/issues' in args[0]


@patch('requests.Session.get')
def test_fetch_data_user(mock_get, github_connector, mock_response):
    """Test fetching user data."""
    mock_get.return_value = mock_response
    
    result = github_connector.fetch_data('testuser', query_type='user')
    
    assert result == {'key': 'value'}
    mock_get.assert_called_once()
    # Verify the URL contains users/testuser
    args, kwargs = mock_get.call_args
    assert 'users/testuser' in args[0]


@patch('requests.Session.get')
def test_fetch_data_error_handling(mock_get, github_connector):
    """Test error handling in fetch_data."""
    # Create an error response
    error_response = MagicMock()
    error_response.status_code = 404
    error_response.text = 'Not found'
    error_response.json.return_value = {'message': 'Not found'}
    error_response.headers = {}
    
    mock_get.return_value = error_response
    
    result = github_connector.fetch_data('test/repo', query_type='repo')
    
    assert 'error' in result
    assert result['status_code'] == 404


@patch('requests.Session.get')
def test_fetch_repo_data_info(mock_get, github_connector, mock_response):
    """Test fetching repository info."""
    mock_get.return_value = mock_response
    
    result = github_connector._fetch_repo_data('test/repo', data_type='info')
    
    assert result == {'key': 'value'}
    mock_get.assert_called_once()
    # Verify the URL contains repos/test/repo
    args, kwargs = mock_get.call_args
    assert 'repos/test/repo' in args[0]


@patch('requests.Session.get')
def test_fetch_repo_data_contents(mock_get, github_connector, mock_response):
    """Test fetching repository contents."""
    mock_get.return_value = mock_response
    
    result = github_connector._fetch_repo_data('test/repo', data_type='contents', path='src')
    
    assert result == {'key': 'value'}
    mock_get.assert_called_once()
    # Verify the URL contains repos/test/repo/contents/src
    args, kwargs = mock_get.call_args
    assert 'repos/test/repo/contents/src' in args[0]


@patch('requests.Session.get')
def test_fetch_repo_data_commits(mock_get, github_connector, mock_response):
    """Test fetching repository commits."""
    mock_get.return_value = mock_response
    
    result = github_connector._fetch_repo_data('test/repo', data_type='commits')
    
    assert result == {'key': 'value'}
    mock_get.assert_called_once()
    # Verify the URL contains repos/test/repo/commits
    args, kwargs = mock_get.call_args
    assert 'repos/test/repo/commits' in args[0]


@patch('requests.Session.get')
def test_fetch_repo_data_issues(mock_get, github_connector, mock_response):
    """Test fetching repository issues."""
    mock_get.return_value = mock_response
    
    result = github_connector._fetch_repo_data('test/repo', data_type='issues')
    
    assert result == {'key': 'value'}
    mock_get.assert_called_once()
    # Verify the URL contains repos/test/repo/issues
    args, kwargs = mock_get.call_args
    assert 'repos/test/repo/issues' in args[0]


@patch('requests.Session.get')
def test_fetch_repo_data_pulls(mock_get, github_connector, mock_response):
    """Test fetching repository pull requests."""
    mock_get.return_value = mock_response
    
    result = github_connector._fetch_repo_data('test/repo', data_type='pulls')
    
    assert result == {'key': 'value'}
    mock_get.assert_called_once()
    # Verify the URL contains repos/test/repo/pulls
    args, kwargs = mock_get.call_args
    assert 'repos/test/repo/pulls' in args[0]


def test_fetch_repo_data_invalid_type(github_connector):
    """Test fetching repository data with invalid type."""
    with pytest.raises(ValueError) as excinfo:
        github_connector._fetch_repo_data('test/repo', data_type='invalid')
    
    assert 'Unsupported data type' in str(excinfo.value)


@patch('requests.Session.get')
def test_get_rate_limit_info(mock_get, github_connector):
    """Test getting rate limit information."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
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
    }
    response.headers = {}
    
    mock_get.return_value = response
    
    result = github_connector.get_rate_limit_info()
    
    assert 'core' in result
    assert 'search' in result
    mock_get.assert_called_once()
    # Verify the URL contains rate_limit
    args, kwargs = mock_get.call_args
    assert 'rate_limit' in args[0]

