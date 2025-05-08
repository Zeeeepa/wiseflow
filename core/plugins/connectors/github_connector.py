"""
GitHub connector plugin for fetching data from GitHub repositories.
"""

import os
import time
from typing import Any, Dict, List, Optional, Union
import requests
import logging

from core.plugins.base import ConnectorPlugin
from core.plugins.exceptions import PluginError, PluginResourceError
from core.plugins.utils import get_resource_monitor

logger = logging.getLogger(__name__)


class GitHubConnector(ConnectorPlugin):
    """Connector for fetching data from GitHub repositories."""
    
    name = "github_connector"
    description = "Fetches data from GitHub repositories"
    version = "1.0.0"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the GitHub connector.
        
        Args:
            config: Configuration dictionary with the following keys:
                - api_token: GitHub API token (optional)
                - rate_limit_pause: Seconds to pause when rate limited (default: 60)
                - max_retries: Maximum number of retries for API calls (default: 3)
        """
        super().__init__(config)
        self.api_token = self.config.get('api_token', os.environ.get('GITHUB_API_TOKEN'))
        self.rate_limit_pause = self.config.get('rate_limit_pause', 60)
        self.max_retries = self.config.get('max_retries', 3)
        self.base_url = "https://api.github.com"
        self.session = None
        self.resource_monitor = get_resource_monitor()
        
    def initialize(self) -> bool:
        """Initialize the GitHub connector.
        
        Returns:
            bool: True if initialization was successful, False otherwise
            
        Raises:
            PluginError: If initialization fails
        """
        try:
            if not self.validate_config():
                logger.error("Invalid GitHub connector configuration")
                return False
            
            self.session = requests.Session()
            if self.api_token:
                self.session.headers.update({
                    "Authorization": f"token {self.api_token}",
                    "Accept": "application/vnd.github.v3+json"
                })
            else:
                self.session.headers.update({
                    "Accept": "application/vnd.github.v3+json"
                })
                logger.warning("No GitHub API token provided. Rate limits will be stricter.")
            
            # Register the session as a resource
            self._register_resource("session", self.session)
            
            # Register with resource monitor
            self.resource_monitor.register_resource(
                self.name, "session", self.session
            )
            
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"Error initializing GitHub connector: {e}")
            raise PluginError(f"Failed to initialize GitHub connector: {e}")
        
    def validate_config(self) -> bool:
        """Validate the connector configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        # API token is optional but recommended
        if not self.api_token:
            logger.warning("No GitHub API token provided. Rate limits will be stricter.")
        
        return True
        
    def connect(self) -> bool:
        """Connect to GitHub API.
        
        Returns:
            bool: True if connection was successful, False otherwise
            
        Raises:
            PluginError: If connection fails
        """
        try:
            if not self.initialized:
                return self.initialize()
            return True
        except Exception as e:
            logger.error(f"Error connecting to GitHub API: {e}")
            raise PluginError(f"Failed to connect to GitHub API: {e}")
        
    def disconnect(self) -> bool:
        """Disconnect from GitHub API.
        
        Returns:
            bool: True if disconnection was successful, False otherwise
            
        Raises:
            PluginError: If disconnection fails
        """
        try:
            if self.session:
                # Release the session resource
                self._release_resource("session")
                self.session = None
            
            self.initialized = False
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from GitHub API: {e}")
            raise PluginError(f"Failed to disconnect from GitHub API: {e}")
        
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the GitHub API with retry logic.
        
        Args:
            endpoint: API endpoint to call
            params: Query parameters for the request
            
        Returns:
            Dict[str, Any]: Response data
            
        Raises:
            PluginError: If the request fails after max retries
        """
        if not self.session:
            self.connect()
            
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        retries = 0
        
        while retries < self.max_retries:
            try:
                response = self.session.get(url, params=params)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 403 and 'rate limit exceeded' in response.text.lower():
                    logger.warning(f"Rate limit exceeded. Pausing for {self.rate_limit_pause} seconds.")
                    time.sleep(self.rate_limit_pause)
                    retries += 1
                else:
                    error_msg = f"GitHub API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise PluginError(error_msg)
                    
            except PluginError:
                # Re-raise plugin errors
                raise
            except Exception as e:
                logger.error(f"Error making GitHub API request: {str(e)}")
                retries += 1
                if retries >= self.max_retries:
                    raise PluginError(f"Failed to make GitHub API request after {self.max_retries} retries: {str(e)}")
                time.sleep(2 ** retries)  # Exponential backoff
                
        raise PluginError(f"Failed to make GitHub API request after {self.max_retries} retries")
        
    def fetch_data(self, query: str, **kwargs) -> Dict[str, Any]:
        """Fetch data from GitHub based on query.
        
        Args:
            query: Query string or repository path
            **kwargs: Additional parameters:
                - query_type: Type of query ('repo', 'code', 'issues', 'user')
                - sort: Sort field
                - order: Sort order ('asc' or 'desc')
                - per_page: Results per page (max 100)
                - page: Page number
                
        Returns:
            Dict[str, Any]: Dictionary containing the fetched data
            
        Raises:
            PluginError: If data fetching fails
        """
        try:
            if not self.initialized:
                if not self.initialize():
                    return {'error': 'Failed to initialize GitHub connector'}
                
            query_type = kwargs.get('query_type', 'repo')
            
            if query_type == 'repo':
                # Format: owner/repo or full repo URL
                repo_path = query.split('github.com/')[-1].rstrip('/')
                if not '/' in repo_path:
                    raise PluginError("Invalid repository path. Format should be 'owner/repo'")
                    
                return self._fetch_repo_data(repo_path, **kwargs)
                
            elif query_type == 'code':
                # Search code in repositories
                search_params = {
                    'q': query,
                    'sort': kwargs.get('sort', 'best-match'),
                    'order': kwargs.get('order', 'desc'),
                    'per_page': min(kwargs.get('per_page', 30), 100),
                    'page': kwargs.get('page', 1)
                }
                
                return self._make_request('search/code', search_params)
                
            elif query_type == 'issues':
                # Search issues and pull requests
                search_params = {
                    'q': query,
                    'sort': kwargs.get('sort', 'created'),
                    'order': kwargs.get('order', 'desc'),
                    'per_page': min(kwargs.get('per_page', 30), 100),
                    'page': kwargs.get('page', 1)
                }
                
                return self._make_request('search/issues', search_params)
                
            elif query_type == 'user':
                # Get user information
                return self._make_request(f'users/{query}')
                
            else:
                raise PluginError(f"Unsupported query type: {query_type}")
        except PluginError:
            # Re-raise plugin errors
            raise
        except Exception as e:
            logger.error(f"Error fetching data from GitHub: {str(e)}")
            raise PluginError(f"Failed to fetch data from GitHub: {str(e)}")
            
    def _fetch_repo_data(self, repo_path: str, **kwargs) -> Dict[str, Any]:
        """Fetch repository data.
        
        Args:
            repo_path: Repository path in format 'owner/repo'
            **kwargs: Additional parameters:
                - data_type: Type of data to fetch ('info', 'contents', 'commits', 'issues', 'pulls')
                - path: Path within repository (for contents)
                - ref: Git reference (branch, tag, commit)
                
        Returns:
            Dict[str, Any]: Repository data
            
        Raises:
            PluginError: If data fetching fails
        """
        try:
            data_type = kwargs.get('data_type', 'info')
            
            if data_type == 'info':
                # Get repository information
                return self._make_request(f'repos/{repo_path}')
                
            elif data_type == 'contents':
                # Get repository contents
                path = kwargs.get('path', '')
                ref = kwargs.get('ref')
                
                params = {}
                if ref:
                    params['ref'] = ref
                    
                return self._make_request(f'repos/{repo_path}/contents/{path}', params)
                
            elif data_type == 'commits':
                # Get repository commits
                params = {
                    'per_page': min(kwargs.get('per_page', 30), 100),
                    'page': kwargs.get('page', 1)
                }
                
                if kwargs.get('path'):
                    params['path'] = kwargs.get('path')
                    
                if kwargs.get('since'):
                    params['since'] = kwargs.get('since')
                    
                if kwargs.get('until'):
                    params['until'] = kwargs.get('until')
                    
                return self._make_request(f'repos/{repo_path}/commits', params)
                
            elif data_type == 'issues':
                # Get repository issues
                params = {
                    'state': kwargs.get('state', 'open'),
                    'per_page': min(kwargs.get('per_page', 30), 100),
                    'page': kwargs.get('page', 1)
                }
                
                if kwargs.get('labels'):
                    params['labels'] = kwargs.get('labels')
                    
                return self._make_request(f'repos/{repo_path}/issues', params)
                
            elif data_type == 'pulls':
                # Get repository pull requests
                params = {
                    'state': kwargs.get('state', 'open'),
                    'per_page': min(kwargs.get('per_page', 30), 100),
                    'page': kwargs.get('page', 1)
                }
                
                return self._make_request(f'repos/{repo_path}/pulls', params)
                
            else:
                raise PluginError(f"Unsupported data type: {data_type}")
        except PluginError:
            # Re-raise plugin errors
            raise
        except Exception as e:
            logger.error(f"Error fetching repository data: {str(e)}")
            raise PluginError(f"Failed to fetch repository data: {str(e)}")
            
    def shutdown(self) -> bool:
        """Shutdown the plugin and release resources.
        
        Returns:
            bool: True if shutdown was successful, False otherwise
        """
        try:
            # Disconnect from GitHub API
            self.disconnect()
            
            # Call parent shutdown method
            return super().shutdown()
        except Exception as e:
            logger.error(f"Error shutting down GitHub connector: {e}")
            return False
