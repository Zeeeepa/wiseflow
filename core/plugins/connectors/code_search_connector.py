"""
Code search connector plugin for mining code repositories from various sources.
"""

import os
import time
import json
import asyncio
from typing import Any, Dict, List, Optional, Union
import requests
import logging
import re

from core.plugins.base import ConnectorPlugin
from core.connectors.code_search import CodeSearchConnector as BaseCodeSearchConnector
from core.utils.error_handling import handle_exceptions, ConnectionError, CodeSearchError

logger = logging.getLogger(__name__)


class CodeSearchConnector(ConnectorPlugin):
    """Connector for searching and mining code from various sources."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the code search connector.
        
        Args:
            config: Configuration dictionary with the following keys:
                - api_keys: Dictionary of API keys for different services
                - rate_limit_pause: Seconds to pause when rate limited (default: 60)
                - max_retries: Maximum number of retries for API calls (default: 3)
                - default_service: Default service to use ('github', 'gitlab', 'searchcode')
                - cache_enabled: Whether to enable caching (default: True)
                - cache_ttl: Cache time-to-live in seconds (default: 3600)
                - concurrency: Maximum number of concurrent requests (default: 5)
        """
        super().__init__(config)
        
        # Extract API keys from config
        self.api_keys = self.config.get('api_keys', {})
        
        # Configure the base connector
        base_config = {
            "github_token": self.api_keys.get('github', ''),
            "gitlab_token": self.api_keys.get('gitlab', ''),
            "bitbucket_token": self.api_keys.get('bitbucket', ''),
            "sourcegraph_token": self.api_keys.get('sourcegraph', ''),
            "concurrency": self.config.get('concurrency', 5),
            "timeout": self.config.get('timeout', 30),
            "cache_enabled": self.config.get('cache_enabled', True),
            "cache_ttl": self.config.get('cache_ttl', 3600),
            "github_rate_limit": self.config.get('github_rate_limit', 30),
            "gitlab_rate_limit": self.config.get('gitlab_rate_limit', 30),
            "bitbucket_rate_limit": self.config.get('bitbucket_rate_limit', 30),
            "sourcegraph_rate_limit": self.config.get('sourcegraph_rate_limit', 30),
        }
        
        # Create the base connector instance
        self.base_connector = BaseCodeSearchConnector(base_config)
        
        # Service-specific base URLs
        self.base_urls = {
            'github': 'https://api.github.com',
            'gitlab': 'https://gitlab.com/api/v4',
            'searchcode': 'https://searchcode.com/api',
            'sourcegraph': self.config.get('sourcegraph_url', 'https://sourcegraph.com')
        }
        
        self.default_service = self.config.get('default_service', 'github')
        self.initialized = False
        
    def initialize(self) -> bool:
        """Initialize the code search connector.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        if not self.validate_config():
            logger.error("Invalid code search connector configuration")
            return False
        
        # Initialize the base connector
        self.base_connector.initialize()
        
        self.initialized = True
        return True
        
    def validate_config(self) -> bool:
        """Validate the connector configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        # Check if the default service is supported
        if self.default_service not in self.base_urls:
            logger.error(f"Unsupported default service: {self.default_service}")
            return False
        
        # API keys are optional for some services
        if self.default_service in ['github', 'gitlab'] and self.default_service not in self.api_keys:
            logger.warning(f"No API key provided for {self.default_service}. Rate limits will be stricter.")
        
        return True
        
    def connect(self) -> bool:
        """Connect to the code search service.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        if not self.initialized:
            return self.initialize()
        return True
        
    def disconnect(self) -> bool:
        """Disconnect from the code search service.
        
        Returns:
            bool: True if disconnection was successful, False otherwise
        """
        # Close the base connector's session
        if hasattr(self, 'base_connector') and self.base_connector:
            asyncio.run(self.base_connector._close_session())
        
        self.initialized = False
        return True
    
    @handle_exceptions(error_types=[Exception], default_message="Failed to fetch data from code search service", log_error=True)
    def fetch_data(self, query: str, **kwargs) -> Dict[str, Any]:
        """Fetch code data based on query.
        
        Args:
            query: Query string for code search
            **kwargs: Additional parameters:
                - service: Service to use ('github', 'gitlab', 'searchcode', 'sourcegraph')
                - language: Programming language filter
                - sort: Sort field
                - order: Sort order ('asc' or 'desc')
                - per_page: Results per page
                - page: Page number
                
        Returns:
            Dict[str, Any]: Dictionary containing the fetched data
        """
        if not self.initialized:
            self.initialize()
            
        service = kwargs.get('service', self.default_service)
        
        # Map the parameters to the base connector format
        base_params = {
            "query": query,
            "source": service,
            "max_results": kwargs.get('per_page', 30),
        }
        
        # Add language filter if provided
        if 'language' in kwargs:
            base_params['language'] = kwargs['language']
        
        # Add repository filter if provided
        if 'repo' in kwargs:
            base_params['repo'] = kwargs['repo']
        
        # Add path filter if provided
        if 'path' in kwargs:
            base_params['path'] = kwargs['path']
        
        # Add extension filter if provided
        if 'extension' in kwargs:
            base_params['extension'] = kwargs['extension']
        
        # Add sorting if provided
        if 'sort' in kwargs:
            base_params['sort'] = kwargs['sort']
        
        # Add order if provided
        if 'order' in kwargs:
            base_params['order'] = kwargs['order']
        
        # Use the base connector to fetch data
        results = asyncio.run(self.base_connector.collect(base_params))
        
        # Convert the results to the expected format
        return self._convert_results_to_dict(results, service)
    
    def _convert_results_to_dict(self, results: List[Any], service: str) -> Dict[str, Any]:
        """Convert the base connector results to the expected dictionary format."""
        if service == 'github':
            items = []
            for item in results:
                items.append({
                    "name": item.metadata.get("name", ""),
                    "path": item.metadata.get("path", ""),
                    "repository": {
                        "full_name": item.metadata.get("repo", "")
                    },
                    "html_url": item.url,
                    "content": item.content
                })
            
            return {
                "total_count": len(items),
                "incomplete_results": False,
                "items": items
            }
        
        elif service == 'gitlab':
            items = []
            for item in results:
                items.append({
                    "path": item.metadata.get("path", ""),
                    "project_id": item.metadata.get("project_id", ""),
                    "ref": item.metadata.get("ref", ""),
                    "content": item.content
                })
            
            return items
        
        elif service == 'searchcode':
            items = []
            for item in results:
                items.append({
                    "name": item.metadata.get("name", ""),
                    "path": item.metadata.get("path", ""),
                    "repo": item.metadata.get("repo", ""),
                    "url": item.url,
                    "content": item.content
                })
            
            return {
                "total": len(items),
                "results": items
            }
        
        elif service == 'sourcegraph':
            items = []
            for item in results:
                items.append({
                    "repository": {
                        "name": item.metadata.get("repo", "")
                    },
                    "file": {
                        "path": item.metadata.get("path", ""),
                        "url": item.url,
                        "content": item.content
                    },
                    "lineMatches": item.metadata.get("line_matches", [])
                })
            
            return {
                "data": {
                    "search": {
                        "results": {
                            "results": items
                        }
                    }
                }
            }
        
        else:
            # Generic format
            return {
                "items": [item.to_dict() for item in results]
            }
    
    def get_file_content(self, service: str, file_url: str) -> str:
        """Get the content of a file from a code search result.
        
        Args:
            service: Service name ('github', 'gitlab', 'searchcode', 'sourcegraph')
            file_url: URL or path to the file
            
        Returns:
            str: File content
            
        Raises:
            ValueError: If the service is not supported
            Exception: If the file content cannot be retrieved
        """
        # Use the base connector to get file content
        content = asyncio.run(self.base_connector.get_file_content(file_url))
        
        if content is None:
            raise Exception(f"Could not retrieve file content from {service}: {file_url}")
        
        return content
