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
from core.connectors.code_search import CodeSearchConnector as AsyncCodeSearchConnector
from core.connectors.code_search.errors import (
    CodeSearchError, ServiceError, AuthenticationError, RateLimitError,
    ResourceNotFoundError, InvalidRequestError, NetworkError, TimeoutError,
    ServerError, handle_service_errors, retry_on_error
)

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
        """
        super().__init__(config or {})
        
        # Create async connector instance
        self.async_connector = AsyncCodeSearchConnector(config)
        
        # Extract configuration for backward compatibility
        self.api_keys = self.config.get('api_keys', {})
        self.rate_limit_pause = self.config.get('rate_limit_pause', 60)
        self.max_retries = self.config.get('max_retries', 3)
        self.default_service = self.config.get('default_service', 'github')
        
        # Service-specific base URLs
        self.base_urls = {
            'github': 'https://api.github.com',
            'gitlab': 'https://gitlab.com/api/v4',
            'searchcode': 'https://searchcode.com/api'
        }
        
        self.session = None
        
    def initialize(self) -> bool:
        """Initialize the code search connector.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        if not self.validate_config():
            logger.error("Invalid code search connector configuration")
            return False
        
        self.session = requests.Session()
        self.initialized = True
        
        # Initialize async connector
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._initialize_async_connector())
        
        return True
    
    async def _initialize_async_connector(self) -> None:
        """Initialize the async connector."""
        self.async_connector.initialize()
    
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
        if self.session:
            self.session.close()
            self.session = None
        
        self.initialized = False
        return True
    
    @handle_service_errors
    @retry_on_error()
    def _make_request(self, service: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the code search service API with retry logic.
        
        Args:
            service: Service name ('github', 'gitlab', 'searchcode')
            endpoint: API endpoint to call
            params: Query parameters for the request
            
        Returns:
            Dict[str, Any]: Response data
            
        Raises:
            Exception: If the request fails after max retries
        """
        if not self.session:
            self.connect()
            
        if service not in self.base_urls:
            raise InvalidRequestError(service, f"Unsupported service: {service}")
            
        url = f"{self.base_urls[service]}/{endpoint.lstrip('/')}"
        headers = {}
        
        # Add authentication headers if API key is available
        if service in self.api_keys and self.api_keys[service]:
            if service == 'github':
                headers['Authorization'] = f"token {self.api_keys[service]}"
                headers['Accept'] = 'application/vnd.github.v3+json'
            elif service == 'gitlab':
                headers['PRIVATE-TOKEN'] = self.api_keys[service]
        
        try:
            response = self.session.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403 and 'rate limit exceeded' in response.text.lower():
                logger.warning(f"Rate limit exceeded for {service}. Pausing for {self.rate_limit_pause} seconds.")
                raise RateLimitError(service, f"Rate limit exceeded for {service}", self.rate_limit_pause)
            else:
                logger.error(f"{service} API error: {response.status_code} - {response.text}")
                raise ServiceError(service, f"{service} API error: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error making {service} API request: {str(e)}")
            raise NetworkError(f"Network error making {service} API request: {str(e)}")
    
    def fetch_data(self, query: str, **kwargs) -> Dict[str, Any]:
        """Fetch code data based on query.
        
        Args:
            query: Query string for code search
            **kwargs: Additional parameters:
                - service: Service to use ('github', 'gitlab', 'searchcode')
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
        
        # Use the async connector via a synchronous wrapper
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Prepare parameters for async connector
            params = {
                "source": service,
                "query": query
            }
            
            # Add additional parameters
            for key, value in kwargs.items():
                if key != 'service':  # 'service' is already handled
                    params[key] = value
            
            # Run async collection
            results = loop.run_until_complete(self.async_connector.collect(params))
            
            # Convert to dictionary format expected by the old API
            return self._convert_results_to_dict(service, results)
        finally:
            loop.close()
    
    def _convert_results_to_dict(self, service: str, results: List[Any]) -> Dict[str, Any]:
        """Convert async connector results to the format expected by the old API.
        
        Args:
            service: Service name
            results: List of DataItem objects
            
        Returns:
            Dict[str, Any]: Dictionary in the format expected by the old API
        """
        if service == 'github':
            items = []
            for item in results:
                items.append(item.raw_data)
            
            return {
                "total_count": len(items),
                "incomplete_results": False,
                "items": items
            }
        elif service == 'gitlab':
            return [item.raw_data for item in results]
        elif service == 'searchcode':
            return {
                "count": len(results),
                "page": 0,
                "total": len(results),
                "results": [item.raw_data for item in results]
            }
        else:
            # Generic format
            return {
                "count": len(results),
                "results": [item.raw_data for item in results]
            }
    
    def _github_code_search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search code on GitHub.
        
        Args:
            query: Query string for code search
            **kwargs: Additional parameters:
                - language: Programming language filter
                - sort: Sort field ('indexed', 'best-match')
                - order: Sort order ('asc' or 'desc')
                - per_page: Results per page (max 100)
                - page: Page number
                
        Returns:
            Dict[str, Any]: Search results
        """
        # This is now a wrapper around the async implementation
        return self.fetch_data(query, service='github', **kwargs)
    
    def _gitlab_code_search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search code on GitLab.
        
        Args:
            query: Query string for code search
            **kwargs: Additional parameters:
                - scope: Search scope ('blobs', 'projects', 'issues', 'merge_requests')
                - per_page: Results per page (max 100)
                - page: Page number
                
        Returns:
            Dict[str, Any]: Search results
        """
        # This is now a wrapper around the async implementation
        return self.fetch_data(query, service='gitlab', **kwargs)
    
    def _searchcode_search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search code on searchcode.com.
        
        Args:
            query: Query string for code search
            **kwargs: Additional parameters:
                - lan: Programming language filter
                - src: Source filter
                - per_page: Results per page (max 100)
                - page: Page number
                
        Returns:
            Dict[str, Any]: Search results
        """
        # This is now a wrapper around the async implementation
        return self.fetch_data(query, service='searchcode', **kwargs)
    
    def get_file_content(self, service: str, file_url: str) -> str:
        """Get the content of a file from a code search result.
        
        Args:
            service: Service name ('github', 'gitlab', 'searchcode')
            file_url: URL or path to the file
            
        Returns:
            str: File content
            
        Raises:
            ValueError: If the service is not supported
            Exception: If the file content cannot be retrieved
        """
        # Use the async connector via a synchronous wrapper
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Get the appropriate service adapter
            service_adapter = loop.run_until_complete(self.async_connector._get_service(service))
            
            # Get file content
            content = loop.run_until_complete(service_adapter.get_file_content(file_url))
            return content
        except Exception as e:
            logger.error(f"Error getting file content from {service}: {e}")
            raise
        finally:
            loop.close()
"""

