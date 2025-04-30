"""
Code search connector plugin for mining code repositories from various sources.
"""

import os
import time
import json
from typing import Any, Dict, List, Optional, Union
import requests
import logging
import re

from core.plugins.base import ConnectorPlugin

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
        super().__init__(config)
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
        if self.session:
            self.session.close()
            self.session = None
        
        self.initialized = False
        return True
        
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
            raise ValueError(f"Unsupported service: {service}")
            
        url = f"{self.base_urls[service]}/{endpoint.lstrip('/')}"
        headers = {}
        
        # Add authentication headers if API key is available
        if service in self.api_keys and self.api_keys[service]:
            if service == 'github':
                headers['Authorization'] = f"token {self.api_keys[service]}"
                headers['Accept'] = 'application/vnd.github.v3+json'
            elif service == 'gitlab':
                headers['PRIVATE-TOKEN'] = self.api_keys[service]
        
        retries = 0
        
        while retries < self.max_retries:
            try:
                response = self.session.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 403 and 'rate limit exceeded' in response.text.lower():
                    logger.warning(f"Rate limit exceeded for {service}. Pausing for {self.rate_limit_pause} seconds.")
                    time.sleep(self.rate_limit_pause)
                    retries += 1
                else:
                    logger.error(f"{service} API error: {response.status_code} - {response.text}")
                    raise Exception(f"{service} API error: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"Error making {service} API request: {str(e)}")
                retries += 1
                if retries >= self.max_retries:
                    raise
                time.sleep(2 ** retries)  # Exponential backoff
                
        raise Exception(f"Failed to make {service} API request after {self.max_retries} retries")
        
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
        
        if service == 'github':
            return self._github_code_search(query, **kwargs)
        elif service == 'gitlab':
            return self._gitlab_code_search(query, **kwargs)
        elif service == 'searchcode':
            return self._searchcode_search(query, **kwargs)
        else:
            raise ValueError(f"Unsupported service: {service}")
            
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
        # Build the search query
        search_query = query
        
        if kwargs.get('language'):
            search_query += f" language:{kwargs['language']}"
            
        if kwargs.get('repo'):
            search_query += f" repo:{kwargs['repo']}"
            
        if kwargs.get('path'):
            search_query += f" path:{kwargs['path']}"
            
        if kwargs.get('extension'):
            search_query += f" extension:{kwargs['extension']}"
            
        # Build the search parameters
        search_params = {
            'q': search_query,
            'sort': kwargs.get('sort', 'best-match'),
            'order': kwargs.get('order', 'desc'),
            'per_page': min(kwargs.get('per_page', 30), 100),
            'page': kwargs.get('page', 1)
        }
        
        return self._make_request('github', 'search/code', search_params)
        
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
        search_params = {
            'search': query,
            'scope': kwargs.get('scope', 'blobs'),
            'per_page': min(kwargs.get('per_page', 20), 100),
            'page': kwargs.get('page', 1)
        }
        
        if kwargs.get('project_id'):
            return self._make_request('gitlab', f"projects/{kwargs['project_id']}/search", search_params)
        else:
            return self._make_request('gitlab', 'search', search_params)
            
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
        search_params = {
            'q': query,
            'per_page': min(kwargs.get('per_page', 20), 100),
            'p': kwargs.get('page', 0)  # searchcode uses 0-based indexing
        }
        
        if kwargs.get('lan'):
            search_params['lan'] = kwargs['lan']
            
        if kwargs.get('src'):
            search_params['src'] = kwargs['src']
            
        return self._make_request('searchcode', 'codesearch/json', search_params)
        
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
        if service == 'github':
            # Extract owner, repo, and path from GitHub URL
            match = re.search(r'github\.com/([^/]+)/([^/]+)/blob/[^/]+/(.+)', file_url)
            if not match:
                raise ValueError(f"Invalid GitHub file URL: {file_url}")
                
            owner, repo, path = match.groups()
            endpoint = f"repos/{owner}/{repo}/contents/{path}"
            
            response = self._make_request('github', endpoint)
            if 'content' in response:
                import base64
                return base64.b64decode(response['content']).decode('utf-8')
            else:
                raise Exception(f"Could not retrieve file content from GitHub: {file_url}")
                
        elif service == 'gitlab':
            # Extract project ID and path from GitLab URL
            match = re.search(r'gitlab\.com/([^/]+/[^/]+)/-/blob/[^/]+/(.+)', file_url)
            if not match:
                raise ValueError(f"Invalid GitLab file URL: {file_url}")
                
            project_path, file_path = match.groups()
            
            # URL encode the project path
            project_path_encoded = requests.utils.quote(project_path, safe='')
            
            endpoint = f"projects/{project_path_encoded}/repository/files/{requests.utils.quote(file_path, safe='')}/raw"
            
            # Make a direct request to get the raw file content
            url = f"{self.base_urls['gitlab']}/{endpoint}"
            headers = {}
            
            if 'gitlab' in self.api_keys and self.api_keys['gitlab']:
                headers['PRIVATE-TOKEN'] = self.api_keys['gitlab']
                
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.text
            else:
                raise Exception(f"Could not retrieve file content from GitLab: {file_url}")
                
        elif service == 'searchcode':
            # searchcode doesn't provide direct file content access through API
            # We need to make a request to the raw URL
            response = self.session.get(file_url)
            
            if response.status_code == 200:
                return response.text
            else:
                raise Exception(f"Could not retrieve file content from searchcode: {file_url}")
                
        else:
            raise ValueError(f"Unsupported service: {service}")

