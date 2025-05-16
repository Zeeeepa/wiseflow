"""
Tests for the Code Search Connector Plugin.
"""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from core.plugins.connectors.code_search_connector import CodeSearchConnector
from core.connectors.code_search import CodeSearchConnector as BaseCodeSearchConnector


@pytest.fixture
def code_search_connector():
    """Create a code search connector plugin for testing."""
    config = {
        'api_keys': {
            'github': 'test_github_token',
            'gitlab': 'test_gitlab_token',
            'bitbucket': 'test_bitbucket_token',
            'sourcegraph': 'test_sourcegraph_token'
        },
        'rate_limit_pause': 30,
        'max_retries': 3,
        'default_service': 'github',
        'cache_enabled': True,
        'cache_ttl': 60,  # 1 minute for testing
        'concurrency': 2
    }
    
    connector = CodeSearchConnector(config)
    connector.initialize()
    
    yield connector
    
    # Clean up
    connector.disconnect()


def test_initialize(code_search_connector):
    """Test connector initialization."""
    assert code_search_connector.initialized is True
    assert code_search_connector.api_keys['github'] == 'test_github_token'
    assert code_search_connector.api_keys['gitlab'] == 'test_gitlab_token'
    assert code_search_connector.default_service == 'github'
    assert hasattr(code_search_connector, 'base_connector')
    assert isinstance(code_search_connector.base_connector, BaseCodeSearchConnector)


def test_validate_config(code_search_connector):
    """Test configuration validation."""
    # Valid configuration
    assert code_search_connector.validate_config() is True
    
    # Invalid service
    code_search_connector.default_service = 'invalid_service'
    assert code_search_connector.validate_config() is False
    
    # Reset to valid service
    code_search_connector.default_service = 'github'
    assert code_search_connector.validate_config() is True


def test_connect_disconnect(code_search_connector):
    """Test connect and disconnect methods."""
    # Test connect
    assert code_search_connector.connect() is True
    
    # Test disconnect
    assert code_search_connector.disconnect() is True
    assert code_search_connector.initialized is False
    
    # Test reconnect
    assert code_search_connector.connect() is True
    assert code_search_connector.initialized is True


def test_fetch_data(code_search_connector):
    """Test fetch_data method."""
    # Mock the base connector's collect method
    with patch.object(code_search_connector.base_connector, 'collect', new_callable=AsyncMock) as mock_collect, \
         patch.object(code_search_connector, '_convert_results_to_dict') as mock_convert:
        
        # Set up mock return values
        mock_collect.return_value = ['result1', 'result2']
        mock_convert.return_value = {'items': ['result1', 'result2']}
        
        # Call fetch_data
        result = code_search_connector.fetch_data('test_query', language='python')
        
        # Verify result
        assert result == {'items': ['result1', 'result2']}
        
        # Verify that collect was called with the right parameters
        mock_collect.assert_called_once()
        args, kwargs = mock_collect.call_args
        assert kwargs['query'] == 'test_query'
        assert kwargs['source'] == 'github'  # default service
        assert kwargs['language'] == 'python'
        
        # Verify that convert was called
        mock_convert.assert_called_once_with(['result1', 'result2'], 'github')


def test_get_file_content(code_search_connector):
    """Test get_file_content method."""
    # Mock the base connector's get_file_content method
    with patch.object(code_search_connector.base_connector, 'get_file_content', new_callable=AsyncMock) as mock_get_content:
        
        # Set up mock return value
        mock_get_content.return_value = 'file content'
        
        # Call get_file_content
        content = code_search_connector.get_file_content('github', 'https://github.com/test/repo/blob/main/file.py')
        
        # Verify result
        assert content == 'file content'
        
        # Verify that get_file_content was called with the right parameters
        mock_get_content.assert_called_once_with('https://github.com/test/repo/blob/main/file.py')
        
        # Test with None return value
        mock_get_content.return_value = None
        
        # Call get_file_content and expect an exception
        with pytest.raises(Exception) as excinfo:
            code_search_connector.get_file_content('github', 'https://github.com/test/repo/blob/main/file.py')
        
        # Verify the exception
        assert 'Could not retrieve file content' in str(excinfo.value)


def test_convert_results_to_dict(code_search_connector):
    """Test _convert_results_to_dict method."""
    from core.connectors import DataItem
    
    # Create test items
    items = [
        DataItem(
            source_id='test1',
            content='test content 1',
            metadata={'repo': 'test/repo1', 'path': 'file1.py', 'name': 'file1.py'},
            url='https://github.com/test/repo1/blob/main/file1.py',
            content_type='text/x-python'
        ),
        DataItem(
            source_id='test2',
            content='test content 2',
            metadata={'repo': 'test/repo2', 'path': 'file2.py', 'name': 'file2.py'},
            url='https://github.com/test/repo2/blob/main/file2.py',
            content_type='text/x-python'
        )
    ]
    
    # Test GitHub format
    github_result = code_search_connector._convert_results_to_dict(items, 'github')
    assert 'total_count' in github_result
    assert 'items' in github_result
    assert len(github_result['items']) == 2
    assert github_result['items'][0]['name'] == 'file1.py'
    assert github_result['items'][0]['repository']['full_name'] == 'test/repo1'
    assert github_result['items'][0]['content'] == 'test content 1'
    
    # Test GitLab format
    items[0].metadata['project_id'] = '123'
    items[0].metadata['ref'] = 'main'
    items[1].metadata['project_id'] = '456'
    items[1].metadata['ref'] = 'main'
    
    gitlab_result = code_search_connector._convert_results_to_dict(items, 'gitlab')
    assert len(gitlab_result) == 2
    assert gitlab_result[0]['path'] == 'file1.py'
    assert gitlab_result[0]['project_id'] == '123'
    assert gitlab_result[0]['ref'] == 'main'
    assert gitlab_result[0]['content'] == 'test content 1'
    
    # Test Sourcegraph format
    sourcegraph_result = code_search_connector._convert_results_to_dict(items, 'sourcegraph')
    assert 'data' in sourcegraph_result
    assert 'search' in sourcegraph_result['data']
    assert 'results' in sourcegraph_result['data']['search']
    assert 'results' in sourcegraph_result['data']['search']['results']
    assert len(sourcegraph_result['data']['search']['results']['results']) == 2
    assert sourcegraph_result['data']['search']['results']['results'][0]['repository']['name'] == 'test/repo1'
    assert sourcegraph_result['data']['search']['results']['results'][0]['file']['path'] == 'file1.py'
    assert sourcegraph_result['data']['search']['results']['results'][0]['file']['content'] == 'test content 1'
    
    # Test generic format
    generic_result = code_search_connector._convert_results_to_dict(items, 'unknown')
    assert 'items' in generic_result
    assert len(generic_result['items']) == 2
    assert 'source_id' in generic_result['items'][0]
    assert 'content' in generic_result['items'][0]
    assert 'metadata' in generic_result['items'][0]


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])

