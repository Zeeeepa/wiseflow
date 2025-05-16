"""
GitHub connector plugin for fetching data from GitHub repositories.
"""

import os
import time
import json
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import requests
import logging
from urllib.parse import urlparse, parse_qs

from core.plugins.base import ConnectorPlugin

logger = logging.getLogger(__name__)


class GitHubRateLimitExceeded(Exception):
    """Exception raised when GitHub API rate limit is exceeded."""
    
    def __init__(self, reset_time: Optional[datetime] = None, message: str = "GitHub API rate limit exceeded"):
        self.reset_time = reset_time
        self.message = message
        super().__init__(self.message)


class GitHubAPIError(Exception):
    """Exception raised for GitHub API errors."""
    
    def __init__(self, status_code: int, message: str, errors: Optional[List[Dict[str, Any]]] = None):
        self.status_code = status_code
        self.message = message
        self.errors = errors or []
        super().__init__(f"GitHub API error: {status_code} - {message}")


class GitHubConnector(ConnectorPlugin):
    """Connector for fetching data from GitHub repositories."""
    
    name = "github_connector"
    description = "Fetches data from GitHub repositories"
    version = "1.1.0"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the GitHub connector.
        
        Args:
            config: Configuration dictionary with the following keys:
                - api_token: GitHub API token (optional)
                - rate_limit_pause: Seconds to pause when rate limited (default: 60)
                - max_retries: Maximum number of retries for API calls (default: 3)
                - cache_enabled: Whether to enable caching (default: True)
                - cache_ttl: Time-to-live for cached items in seconds (default: 300)
                - cache_dir: Directory to store cache files (default: '.github_cache')
                - user_agent: User agent string to use for requests (default: 'Wiseflow-GitHub-Connector')
        """
        super().__init__(config)
        self.api_token = self.config.get('api_token', os.environ.get('GITHUB_API_TOKEN'))
        self.rate_limit_pause = self.config.get('rate_limit_pause', 60)
        self.max_retries = self.config.get('max_retries', 3)
        self.base_url = "https://api.github.com"
        self.session = None
        
        # Rate limiting state
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
        self.rate_limit_limit = None
        
        # Caching configuration
        self.cache_enabled = self.config.get('cache_enabled', True)
        self.cache_ttl = self.config.get('cache_ttl', 300)  # 5 minutes default
        self.cache_dir = self.config.get('cache_dir', '.github_cache')
        self.etags = {}  # Store ETags for conditional requests
        
        # User agent
        self.user_agent = self.config.get('user_agent', 'Wiseflow-GitHub-Connector')
        
        # Create cache directory if it doesn't exist
        if self.cache_enabled and not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir)
                logger.info(f"Created GitHub cache directory: {self.cache_dir}")
            except Exception as e:
                logger.warning(f"Failed to create GitHub cache directory: {e}")
                self.cache_enabled = False
        
    def initialize(self) -> bool:
        """Initialize the GitHub connector.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        if not self.validate_config():
            logger.error("Invalid GitHub connector configuration")
            return False
        
        self.session = requests.Session()
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": self.user_agent
        }
        
        if self.api_token:
            # Check if token is a JWT (GitHub App)
            if self._is_jwt_token(self.api_token):
                headers["Authorization"] = f"Bearer {self.api_token}"
            else:
                headers["Authorization"] = f"token {self.api_token}"
        else:
            logger.warning("No GitHub API token provided. Rate limits will be stricter.")
        
        self.session.headers.update(headers)
        
        # Load ETags from cache if available
        self._load_etags()
        
        self.initialized = True
        return True
    
    def _is_jwt_token(self, token: str) -> bool:
        """Check if a token is a JWT token.
        
        Args:
            token: Token to check
            
        Returns:
            bool: True if token is a JWT token, False otherwise
        """
        # Simple check: JWT tokens typically have 3 parts separated by dots
        return token.count('.') == 2 and all(self._is_base64(part) for part in token.split('.'))
    
    def _is_base64(self, s: str) -> bool:
        """Check if a string is base64 encoded.
        
        Args:
            s: String to check
            
        Returns:
            bool: True if string is base64 encoded, False otherwise
        """
        import base64
        try:
            # Add padding if necessary
            padding = 4 - (len(s) % 4) if len(s) % 4 else 0
            s = s + "=" * padding
            base64.b64decode(s)
            return True
        except Exception:
            return False
        
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
        """
        if not self.initialized:
            return self.initialize()
        return True
        
    def disconnect(self) -> bool:
        """Disconnect from GitHub API.
        
        Returns:
            bool: True if disconnection was successful, False otherwise
        """
        if self.session:
            self.session.close()
            self.session = None
        
        # Save ETags to cache
        self._save_etags()
        
        self.initialized = False
        return True
    
    def _update_rate_limit_info(self, response: requests.Response) -> None:
        """Update rate limit information from response headers.
        
        Args:
            response: Response object from GitHub API
        """
        # Extract rate limit information from headers
        if 'X-RateLimit-Remaining' in response.headers:
            self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
        
        if 'X-RateLimit-Reset' in response.headers:
            reset_timestamp = int(response.headers['X-RateLimit-Reset'])
            self.rate_limit_reset = datetime.fromtimestamp(reset_timestamp)
        
        if 'X-RateLimit-Limit' in response.headers:
            self.rate_limit_limit = int(response.headers['X-RateLimit-Limit'])
        
        # Log rate limit information
        if all(x is not None for x in [self.rate_limit_remaining, self.rate_limit_reset, self.rate_limit_limit]):
            reset_in = (self.rate_limit_reset - datetime.now()).total_seconds()
            logger.debug(f"GitHub API rate limit: {self.rate_limit_remaining}/{self.rate_limit_limit}, resets in {reset_in:.0f} seconds")
    
    def _should_wait_for_rate_limit(self) -> Tuple[bool, float]:
        """Check if we should wait for rate limit to reset.
        
        Returns:
            Tuple[bool, float]: (should_wait, wait_time_seconds)
        """
        if self.rate_limit_remaining is not None and self.rate_limit_remaining < 5:
            if self.rate_limit_reset is not None:
                now = datetime.now()
                if now < self.rate_limit_reset:
                    wait_time = (self.rate_limit_reset - now).total_seconds() + 5  # Add 5 seconds buffer
                    return True, wait_time
        
        return False, 0
    
    def _get_cache_key(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate a cache key for the request.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            str: Cache key
        """
        import hashlib
        
        # Normalize endpoint
        endpoint = endpoint.lstrip('/')
        
        # Create a string representation of the request
        request_str = endpoint
        if params:
            # Sort params to ensure consistent cache keys
            sorted_params = sorted(params.items())
            param_str = '&'.join(f"{k}={v}" for k, v in sorted_params)
            request_str += '?' + param_str
        
        # Hash the request string
        return hashlib.md5(request_str.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> str:
        """Get the file path for a cache item.
        
        Args:
            cache_key: Cache key
            
        Returns:
            str: Cache file path
        """
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Optional[Dict[str, Any]]: Cached data or None if not found or expired
        """
        if not self.cache_enabled:
            return None
        
        cache_path = self._get_cache_path(cache_key)
        
        try:
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as f:
                    cache_data = json.load(f)
                
                # Check if cache is expired
                cache_time = datetime.fromisoformat(cache_data.get('_cache_time', '2000-01-01T00:00:00'))
                if datetime.now() - cache_time < timedelta(seconds=self.cache_ttl):
                    logger.debug(f"Cache hit for {cache_key}")
                    return cache_data.get('data')
                else:
                    logger.debug(f"Cache expired for {cache_key}")
        except Exception as e:
            logger.warning(f"Error reading from cache: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, data: Dict[str, Any], etag: Optional[str] = None) -> None:
        """Save data to cache.
        
        Args:
            cache_key: Cache key
            data: Data to cache
            etag: ETag for the response
        """
        if not self.cache_enabled:
            return
        
        cache_path = self._get_cache_path(cache_key)
        
        try:
            cache_data = {
                '_cache_time': datetime.now().isoformat(),
                'data': data
            }
            
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)
            
            # Store ETag for conditional requests
            if etag:
                self.etags[cache_key] = etag
            
            logger.debug(f"Saved to cache: {cache_key}")
        except Exception as e:
            logger.warning(f"Error saving to cache: {e}")
    
    def _load_etags(self) -> None:
        """Load ETags from cache."""
        if not self.cache_enabled:
            return
        
        etags_path = os.path.join(self.cache_dir, 'etags.json')
        
        try:
            if os.path.exists(etags_path):
                with open(etags_path, 'r') as f:
                    self.etags = json.load(f)
                logger.debug(f"Loaded {len(self.etags)} ETags from cache")
        except Exception as e:
            logger.warning(f"Error loading ETags: {e}")
            self.etags = {}
    
    def _save_etags(self) -> None:
        """Save ETags to cache."""
        if not self.cache_enabled or not self.etags:
            return
        
        etags_path = os.path.join(self.cache_dir, 'etags.json')
        
        try:
            with open(etags_path, 'w') as f:
                json.dump(self.etags, f)
            logger.debug(f"Saved {len(self.etags)} ETags to cache")
        except Exception as e:
            logger.warning(f"Error saving ETags: {e}")
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, method: str = 'GET') -> Dict[str, Any]:
        """Make a request to the GitHub API with retry logic and caching.
        
        Args:
            endpoint: API endpoint to call
            params: Query parameters for the request
            method: HTTP method (GET, POST, etc.)
            
        Returns:
            Dict[str, Any]: Response data
            
        Raises:
            GitHubRateLimitExceeded: If rate limit is exceeded
            GitHubAPIError: If the API returns an error
            Exception: For other errors
        """
        if not self.session:
            self.connect()
            
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        retries = 0
        cache_key = None
        
        # Check if we should wait for rate limit to reset
        should_wait, wait_time = self._should_wait_for_rate_limit()
        if should_wait:
            logger.warning(f"Approaching rate limit, waiting for {wait_time:.0f} seconds before making request")
            time.sleep(wait_time)
        
        # For GET requests, try to use cache
        if method.upper() == 'GET' and self.cache_enabled:
            cache_key = self._get_cache_key(endpoint, params)
            cached_data = self._get_from_cache(cache_key)
            
            if cached_data:
                return cached_data
        
        # Prepare headers for conditional request
        headers = {}
        if method.upper() == 'GET' and cache_key and cache_key in self.etags:
            headers['If-None-Match'] = self.etags[cache_key]
        
        while retries < self.max_retries:
            try:
                if method.upper() == 'GET':
                    response = self.session.get(url, params=params, headers=headers)
                elif method.upper() == 'POST':
                    response = self.session.post(url, json=params, headers=headers)
                elif method.upper() == 'PUT':
                    response = self.session.put(url, json=params, headers=headers)
                elif method.upper() == 'DELETE':
                    response = self.session.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Update rate limit information
                self._update_rate_limit_info(response)
                
                # Handle 304 Not Modified (cached response is still valid)
                if response.status_code == 304 and cache_key:
                    cached_data = self._get_from_cache(cache_key)
                    if cached_data:
                        logger.debug(f"Using cached data for {endpoint} (304 Not Modified)")
                        return cached_data
                
                # Handle successful response
                if response.status_code == 200:
                    data = response.json()
                    
                    # Cache the response for GET requests
                    if method.upper() == 'GET' and self.cache_enabled and cache_key:
                        etag = response.headers.get('ETag')
                        self._save_to_cache(cache_key, data, etag)
                    
                    return data
                
                # Handle rate limiting
                elif response.status_code == 403 and 'rate limit exceeded' in response.text.lower():
                    reset_time = None
                    if 'X-RateLimit-Reset' in response.headers:
                        reset_timestamp = int(response.headers['X-RateLimit-Reset'])
                        reset_time = datetime.fromtimestamp(reset_timestamp)
                    
                    wait_time = self.rate_limit_pause
                    if reset_time:
                        wait_time = max(1, (reset_time - datetime.now()).total_seconds() + 5)  # Add 5 seconds buffer
                    
                    logger.warning(f"Rate limit exceeded. Waiting for {wait_time:.0f} seconds.")
                    time.sleep(wait_time)
                    retries += 1
                
                # Handle other errors
                else:
                    error_message = f"GitHub API error: {response.status_code}"
                    errors = []
                    
                    try:
                        error_data = response.json()
                        if 'message' in error_data:
                            error_message = f"GitHub API error: {response.status_code} - {error_data['message']}"
                        if 'errors' in error_data:
                            errors = error_data['errors']
                    except Exception:
                        error_message = f"GitHub API error: {response.status_code} - {response.text}"
                    
                    # Determine if we should retry based on status code
                    if response.status_code in [500, 502, 503, 504]:
                        # Server errors - retry with exponential backoff
                        retry_after = int(response.headers.get('Retry-After', 2 ** retries))
                        logger.warning(f"{error_message}. Retrying in {retry_after} seconds.")
                        time.sleep(retry_after)
                        retries += 1
                    else:
                        # Client errors - don't retry
                        raise GitHubAPIError(response.status_code, error_message, errors)
                    
            except GitHubAPIError:
                # Re-raise GitHubAPIError exceptions
                raise
            except GitHubRateLimitExceeded:
                # Re-raise GitHubRateLimitExceeded exceptions
                raise
            except Exception as e:
                logger.error(f"Error making GitHub API request: {str(e)}")
                retries += 1
                if retries >= self.max_retries:
                    raise
                time.sleep(2 ** retries)  # Exponential backoff
                
        raise Exception(f"Failed to make GitHub API request after {self.max_retries} retries")
    
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get current rate limit information.
        
        Returns:
            Dict[str, Any]: Rate limit information
        """
        try:
            data = self._make_request('rate_limit')
            return data.get('resources', {})
        except Exception as e:
            logger.error(f"Error getting rate limit info: {e}")
            return {}
    
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
        """
        if not self.initialized:
            if not self.initialize():
                return {'error': 'Failed to initialize GitHub connector'}
            
        query_type = kwargs.get('query_type', 'repo')
        
        try:
            if query_type == 'repo':
                # Format: owner/repo or full repo URL
                repo_path = query.split('github.com/')[-1].rstrip('/')
                if not '/' in repo_path:
                    raise ValueError("Invalid repository path. Format should be 'owner/repo'")
                    
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
                raise ValueError(f"Unsupported query type: {query_type}")
        except GitHubRateLimitExceeded as e:
            logger.error(f"Rate limit exceeded: {e}")
            return {'error': 'Rate limit exceeded', 'reset_time': e.reset_time.isoformat() if e.reset_time else None}
        except GitHubAPIError as e:
            logger.error(f"GitHub API error: {e}")
            return {'error': str(e), 'status_code': e.status_code, 'errors': e.errors}
        except Exception as e:
            logger.error(f"Error fetching data from GitHub: {e}")
            return {'error': str(e)}
            
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
        """
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
            raise ValueError(f"Unsupported data type: {data_type}")
