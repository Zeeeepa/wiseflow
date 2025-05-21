"""
GitHub connector plugin for fetching data from GitHub repositories.
Provides robust error handling, rate limiting, caching, and pagination support.
"""

import os
import time
import json
import logging
import functools
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable, Iterator, TypeVar, Generic
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import backoff

from core.plugins.base import ConnectorPlugin

logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar('T')

# Constants
DEFAULT_CACHE_TTL = 300  # 5 minutes
DEFAULT_RATE_LIMIT_PAUSE = 60  # 1 minute
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_MAX_TIME = 300  # 5 minutes
DEFAULT_BACKOFF_MAX_TRIES = 5
DEFAULT_TIMEOUT = 30  # 30 seconds
DEFAULT_POOL_CONNECTIONS = 10
DEFAULT_POOL_MAXSIZE = 10
DEFAULT_PAGE_SIZE = 30
MAX_PAGE_SIZE = 100

class GitHubApiError(Exception):
    """Base exception for GitHub API errors."""
    pass

class GitHubRateLimitError(GitHubApiError):
    """Exception raised when GitHub API rate limit is exceeded."""
    def __init__(self, reset_time: Optional[int] = None, message: str = "GitHub API rate limit exceeded"):
        self.reset_time = reset_time
        super().__init__(message)

class GitHubAuthenticationError(GitHubApiError):
    """Exception raised when GitHub API authentication fails."""
    pass

class GitHubNotFoundError(GitHubApiError):
    """Exception raised when a GitHub resource is not found."""
    pass

class GitHubServerError(GitHubApiError):
    """Exception raised when GitHub API returns a server error."""
    pass

class GitHubValidationError(GitHubApiError):
    """Exception raised when GitHub API request validation fails."""
    pass

class Cache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, ttl: int = DEFAULT_CACHE_TTL):
        """Initialize the cache.
        
        Args:
            ttl: Time-to-live in seconds for cache entries
        """
        self.cache = {}
        self.ttl = ttl
        self.expiry = {}
        self.hits = 0
        self.misses = 0
        
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if key in self.cache:
            if self.expiry[key] > datetime.now():
                self.hits += 1
                return self.cache[key]
            else:
                # Remove expired entry
                del self.cache[key]
                del self.expiry[key]
        
        self.misses += 1
        return None
        
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional custom TTL in seconds
        """
        self.cache[key] = value
        self.expiry[key] = datetime.now() + timedelta(seconds=ttl or self.ttl)
        
    def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()
        self.expiry.clear()
        
    def remove(self, key: str) -> None:
        """Remove a specific key from the cache.
        
        Args:
            key: Cache key to remove
        """
        if key in self.cache:
            del self.cache[key]
            del self.expiry[key]
            
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics.
        
        Returns:
            Dict with cache statistics
        """
        return {
            'size': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_ratio': self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        }

class RateLimiter:
    """Rate limiter for GitHub API with quota tracking."""
    
    def __init__(self, pause_time: int = DEFAULT_RATE_LIMIT_PAUSE):
        """Initialize the rate limiter.
        
        Args:
            pause_time: Default time to pause when rate limited
        """
        self.pause_time = pause_time
        self.reset_time = 0
        self.remaining = 0
        self.limit = 0
        self.last_updated = 0
        
    def update_from_headers(self, headers: Dict[str, str]) -> None:
        """Update rate limit information from response headers.
        
        Args:
            headers: Response headers from GitHub API
        """
        if 'X-RateLimit-Remaining' in headers:
            self.remaining = int(headers['X-RateLimit-Remaining'])
            
        if 'X-RateLimit-Reset' in headers:
            self.reset_time = int(headers['X-RateLimit-Reset'])
            
        if 'X-RateLimit-Limit' in headers:
            self.limit = int(headers['X-RateLimit-Limit'])
            
        self.last_updated = int(time.time())
        
        logger.debug(f"Rate limit updated: {self.remaining}/{self.limit}, reset at {self.reset_time}")
        
    def wait_if_needed(self) -> None:
        """Wait if rate limit is close to being exceeded."""
        # If we have no data yet, don't wait
        if self.last_updated == 0:
            return
            
        # If we have plenty of quota left, don't wait
        if self.remaining > 10:
            return
            
        current_time = int(time.time())
        
        # If reset time is in the past, don't wait
        if self.reset_time <= current_time:
            return
            
        # Calculate wait time with a small buffer
        wait_time = self.reset_time - current_time + 2
        
        logger.warning(f"Rate limit almost exceeded. Waiting {wait_time} seconds until reset.")
        time.sleep(wait_time)
        
    def is_rate_limited(self) -> bool:
        """Check if we're currently rate limited.
        
        Returns:
            bool: True if rate limited, False otherwise
        """
        if self.remaining == 0 and self.reset_time > int(time.time()):
            return True
        return False
        
    def get_wait_time(self) -> int:
        """Get the time to wait if rate limited.
        
        Returns:
            int: Time to wait in seconds
        """
        current_time = int(time.time())
        if self.reset_time > current_time:
            return self.reset_time - current_time + 2
        return self.pause_time

class PaginatedResults(Generic[T]):
    """Iterator for paginated GitHub API results."""
    
    def __init__(
        self, 
        fetch_func: Callable[[int], List[T]], 
        page_size: int = DEFAULT_PAGE_SIZE,
        max_items: Optional[int] = None
    ):
        """Initialize the paginated results.
        
        Args:
            fetch_func: Function to fetch a page of results
            page_size: Number of items per page
            max_items: Maximum number of items to fetch
        """
        self.fetch_func = fetch_func
        self.page_size = page_size
        self.max_items = max_items
        self.current_page = 1
        self.current_items = []
        self.item_index = 0
        self.total_items_fetched = 0
        self.exhausted = False
        
    def __iter__(self) -> 'PaginatedResults[T]':
        return self
        
    def __next__(self) -> T:
        # Check if we've reached the maximum number of items
        if self.max_items and self.total_items_fetched >= self.max_items:
            raise StopIteration
            
        # If we've exhausted the current page, fetch the next one
        if self.item_index >= len(self.current_items):
            if self.exhausted:
                raise StopIteration
                
            self.current_items = self.fetch_func(self.current_page)
            
            # If we got an empty page, we're done
            if not self.current_items:
                self.exhausted = True
                raise StopIteration
                
            self.current_page += 1
            self.item_index = 0
            
        # Get the next item
        item = self.current_items[self.item_index]
        self.item_index += 1
        self.total_items_fetched += 1
        
        return item
        
    def to_list(self) -> List[T]:
        """Convert the iterator to a list.
        
        Returns:
            List of all items
        """
        return list(self)

def handle_github_errors(func):
    """Decorator to handle GitHub API errors."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as e:
            response = e.response
            status_code = response.status_code
            
            # Try to get error details from response
            error_message = f"GitHub API error: {status_code}"
            try:
                error_data = response.json()
                if 'message' in error_data:
                    error_message = f"GitHub API error: {status_code} - {error_data['message']}"
            except:
                error_message = f"GitHub API error: {status_code} - {response.text}"
                
            # Map HTTP errors to specific exceptions
            if status_code == 401:
                raise GitHubAuthenticationError(error_message)
            elif status_code == 403:
                if 'rate limit exceeded' in response.text.lower():
                    reset_time = None
                    if 'X-RateLimit-Reset' in response.headers:
                        reset_time = int(response.headers['X-RateLimit-Reset'])
                    raise GitHubRateLimitError(reset_time, error_message)
                else:
                    raise GitHubAuthenticationError(error_message)
            elif status_code == 404:
                raise GitHubNotFoundError(error_message)
            elif status_code == 422:
                raise GitHubValidationError(error_message)
            elif status_code >= 500:
                raise GitHubServerError(error_message)
            else:
                raise GitHubApiError(error_message)
        except requests.exceptions.ConnectionError as e:
            raise GitHubApiError(f"Connection error: {str(e)}")
        except requests.exceptions.Timeout as e:
            raise GitHubApiError(f"Request timed out: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise GitHubApiError(f"Request error: {str(e)}")
    return wrapper

def backoff_handler(details):
    """Handler for backoff events."""
    logger.warning(
        f"Backing off {details['wait']:0.1f} seconds after {details['tries']} tries "
        f"calling function {details['target'].__name__} with args {details['args']} and kwargs "
        f"{details['kwargs']}"
    )

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
                - cache_ttl: Time-to-live in seconds for cache entries (default: 300)
                - timeout: Timeout in seconds for API requests (default: 30)
                - pool_connections: Number of connection pool connections (default: 10)
                - pool_maxsize: Maximum size of the connection pool (default: 10)
                - page_size: Default page size for paginated results (default: 30)
        """
        super().__init__(config)
        
        # Load configuration with defaults
        self.api_token = self.config.get('api_token', os.environ.get('GITHUB_API_TOKEN'))
        self.rate_limit_pause = int(self.config.get('rate_limit_pause', os.environ.get('GITHUB_RATE_LIMIT_PAUSE', DEFAULT_RATE_LIMIT_PAUSE)))
        self.max_retries = int(self.config.get('max_retries', os.environ.get('GITHUB_MAX_RETRIES', DEFAULT_MAX_RETRIES)))
        self.cache_ttl = int(self.config.get('cache_ttl', os.environ.get('GITHUB_CACHE_TTL', DEFAULT_CACHE_TTL)))
        self.timeout = int(self.config.get('timeout', os.environ.get('GITHUB_TIMEOUT', DEFAULT_TIMEOUT)))
        self.pool_connections = int(self.config.get('pool_connections', os.environ.get('GITHUB_POOL_CONNECTIONS', DEFAULT_POOL_CONNECTIONS)))
        self.pool_maxsize = int(self.config.get('pool_maxsize', os.environ.get('GITHUB_POOL_MAXSIZE', DEFAULT_POOL_MAXSIZE)))
        self.page_size = int(self.config.get('page_size', os.environ.get('GITHUB_PAGE_SIZE', DEFAULT_PAGE_SIZE)))
        
        # Initialize components
        self.base_url = "https://api.github.com"
        self.session = None
        self.cache = Cache(ttl=self.cache_ttl)
        self.rate_limiter = RateLimiter(pause_time=self.rate_limit_pause)
        
    def initialize(self) -> bool:
        """Initialize the GitHub connector.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        if not self.validate_config():
            logger.error("Invalid GitHub connector configuration")
            return False
        
        # Create session with retry configuration
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD", "OPTIONS"]
        )
        
        # Configure connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self.pool_connections,
            pool_maxsize=self.pool_maxsize
        )
        
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        # Set default timeout
        self.session.timeout = self.timeout
        
        # Set headers
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
        
        self.initialized = True
        return True
        
    def validate_config(self) -> bool:
        """Validate the connector configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        # API token is optional but recommended
        if not self.api_token:
            logger.warning("No GitHub API token provided. Rate limits will be stricter.")
        
        # Validate numeric parameters
        if self.rate_limit_pause <= 0:
            logger.error("Rate limit pause must be positive")
            return False
            
        if self.max_retries < 0:
            logger.error("Max retries must be non-negative")
            return False
            
        if self.cache_ttl <= 0:
            logger.error("Cache TTL must be positive")
            return False
            
        if self.timeout <= 0:
            logger.error("Timeout must be positive")
            return False
            
        if self.pool_connections <= 0:
            logger.error("Pool connections must be positive")
            return False
            
        if self.pool_maxsize <= 0:
            logger.error("Pool maxsize must be positive")
            return False
            
        if self.page_size <= 0 or self.page_size > MAX_PAGE_SIZE:
            logger.error(f"Page size must be between 1 and {MAX_PAGE_SIZE}")
            return False
        
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
        
        self.initialized = False
        return True
        
    def clear_cache(self) -> None:
        """Clear the cache."""
        self.cache.clear()
        
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics.
        
        Returns:
            Dict with cache statistics
        """
        return self.cache.get_stats()
        
    @backoff.on_exception(
        backoff.expo,
        (GitHubRateLimitError, GitHubServerError, requests.exceptions.ConnectionError),
        max_tries=DEFAULT_BACKOFF_MAX_TRIES,
        max_time=DEFAULT_BACKOFF_MAX_TIME,
        on_backoff=backoff_handler
    )
    @handle_github_errors
    def _make_request(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """Make a request to the GitHub API with retry logic and caching.
        
        Args:
            endpoint: API endpoint to call
            params: Query parameters for the request
            use_cache: Whether to use cache for this request
            cache_ttl: Custom cache TTL for this request
            
        Returns:
            Dict[str, Any]: Response data
            
        Raises:
            GitHubApiError: If the request fails
        """
        if not self.session:
            self.connect()
            
        # Check if we're rate limited
        self.rate_limiter.wait_if_needed()
            
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Generate cache key if using cache
        cache_key = None
        if use_cache:
            # Create a cache key from the URL and params
            cache_key = f"{url}:{json.dumps(params or {}, sort_keys=True)}"
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for {url}")
                return cached_result
        
        logger.debug(f"Making request to {url} with params {params}")
        
        try:
            response = self.session.get(url, params=params)
            
            # Update rate limit info from headers
            self.rate_limiter.update_from_headers(response.headers)
            
            # Raise exception for error status codes
            response.raise_for_status()
            
            result = response.json()
            
            # Cache the result if using cache
            if use_cache and cache_key:
                self.cache.set(cache_key, result, ttl=cache_ttl)
                
            return result
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making GitHub API request: {str(e)}")
            raise
        
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
                - use_cache: Whether to use cache (default: True)
                - cache_ttl: Custom cache TTL in seconds
                
        Returns:
            Dict[str, Any]: Dictionary containing the fetched data
        """
        if not self.initialized:
            if not self.initialize():
                return {'error': 'Failed to initialize GitHub connector'}
            
        query_type = kwargs.get('query_type', 'repo')
        use_cache = kwargs.get('use_cache', True)
        cache_ttl = kwargs.get('cache_ttl')
        
        try:
            if query_type == 'repo':
                # Format: owner/repo or full repo URL
                repo_path = query.split('github.com/')[-1].rstrip('/')
                if not '/' in repo_path:
                    raise ValueError("Invalid repository path. Format should be 'owner/repo'")
                    
                return self._fetch_repo_data(repo_path, use_cache=use_cache, cache_ttl=cache_ttl, **kwargs)
                
            elif query_type == 'code':
                # Search code in repositories
                search_params = {
                    'q': query,
                    'sort': kwargs.get('sort', 'best-match'),
                    'order': kwargs.get('order', 'desc'),
                    'per_page': min(kwargs.get('per_page', self.page_size), MAX_PAGE_SIZE),
                    'page': kwargs.get('page', 1)
                }
                
                return self._make_request('search/code', search_params, use_cache=use_cache, cache_ttl=cache_ttl)
                
            elif query_type == 'issues':
                # Search issues and pull requests
                search_params = {
                    'q': query,
                    'sort': kwargs.get('sort', 'created'),
                    'order': kwargs.get('order', 'desc'),
                    'per_page': min(kwargs.get('per_page', self.page_size), MAX_PAGE_SIZE),
                    'page': kwargs.get('page', 1)
                }
                
                return self._make_request('search/issues', search_params, use_cache=use_cache, cache_ttl=cache_ttl)
                
            elif query_type == 'user':
                # Get user information
                return self._make_request(f'users/{query}', use_cache=use_cache, cache_ttl=cache_ttl)
                
            else:
                raise ValueError(f"Unsupported query type: {query_type}")
        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}")
            return {'error': str(e)}
            
    def fetch_paginated_data(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        max_items: Optional[int] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None
    ) -> PaginatedResults[Dict[str, Any]]:
        """Fetch paginated data from GitHub API.
        
        Args:
            endpoint: API endpoint to call
            params: Query parameters for the request
            max_items: Maximum number of items to fetch
            use_cache: Whether to use cache for this request
            cache_ttl: Custom cache TTL for this request
            
        Returns:
            PaginatedResults: Iterator for paginated results
        """
        if not params:
            params = {}
            
        # Ensure per_page is set
        if 'per_page' not in params:
            params['per_page'] = self.page_size
            
        # Create a function to fetch a specific page
        def fetch_page(page: int) -> List[Dict[str, Any]]:
            page_params = params.copy()
            page_params['page'] = page
            
            result = self._make_request(endpoint, page_params, use_cache=use_cache, cache_ttl=cache_ttl)
            
            # Handle different response formats
            if isinstance(result, dict) and 'items' in result:
                return result['items']
            elif isinstance(result, list):
                return result
            else:
                return []
                
        return PaginatedResults(fetch_page, params.get('per_page', self.page_size), max_items)
            
    def _fetch_repo_data(
        self, 
        repo_path: str, 
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Fetch repository data.
        
        Args:
            repo_path: Repository path in format 'owner/repo'
            use_cache: Whether to use cache for this request
            cache_ttl: Custom cache TTL for this request
            **kwargs: Additional parameters:
                - data_type: Type of data to fetch ('info', 'contents', 'commits', 'issues', 'pulls')
                - path: Path within repository (for contents)
                - ref: Git reference (branch, tag, commit)
                - max_items: Maximum number of items to fetch for paginated results
                
        Returns:
            Dict[str, Any]: Repository data
        """
        data_type = kwargs.get('data_type', 'info')
        max_items = kwargs.get('max_items')
        
        try:
            if data_type == 'info':
                # Get repository information
                return self._make_request(f'repos/{repo_path}', use_cache=use_cache, cache_ttl=cache_ttl)
                
            elif data_type == 'contents':
                # Get repository contents
                path = kwargs.get('path', '')
                ref = kwargs.get('ref')
                
                params = {}
                if ref:
                    params['ref'] = ref
                    
                return self._make_request(f'repos/{repo_path}/contents/{path}', params, use_cache=use_cache, cache_ttl=cache_ttl)
                
            elif data_type == 'commits':
                # Get repository commits
                params = {
                    'per_page': min(kwargs.get('per_page', self.page_size), MAX_PAGE_SIZE)
                }
                
                if kwargs.get('path'):
                    params['path'] = kwargs.get('path')
                    
                if kwargs.get('since'):
                    params['since'] = kwargs.get('since')
                    
                if kwargs.get('until'):
                    params['until'] = kwargs.get('until')
                
                # Use paginated results
                paginated = self.fetch_paginated_data(
                    f'repos/{repo_path}/commits', 
                    params, 
                    max_items=max_items,
                    use_cache=use_cache,
                    cache_ttl=cache_ttl
                )
                
                # If a specific page was requested, return just that page
                if 'page' in kwargs:
                    params['page'] = kwargs.get('page')
                    return self._make_request(f'repos/{repo_path}/commits', params, use_cache=use_cache, cache_ttl=cache_ttl)
                
                # Otherwise, return all items as a list
                return {'items': paginated.to_list()}
                
            elif data_type == 'issues':
                # Get repository issues
                params = {
                    'state': kwargs.get('state', 'open'),
                    'per_page': min(kwargs.get('per_page', self.page_size), MAX_PAGE_SIZE)
                }
                
                if kwargs.get('labels'):
                    params['labels'] = kwargs.get('labels')
                
                # Use paginated results
                paginated = self.fetch_paginated_data(
                    f'repos/{repo_path}/issues', 
                    params, 
                    max_items=max_items,
                    use_cache=use_cache,
                    cache_ttl=cache_ttl
                )
                
                # If a specific page was requested, return just that page
                if 'page' in kwargs:
                    params['page'] = kwargs.get('page')
                    return self._make_request(f'repos/{repo_path}/issues', params, use_cache=use_cache, cache_ttl=cache_ttl)
                
                # Otherwise, return all items as a list
                return {'items': paginated.to_list()}
                
            elif data_type == 'pulls':
                # Get repository pull requests
                params = {
                    'state': kwargs.get('state', 'open'),
                    'per_page': min(kwargs.get('per_page', self.page_size), MAX_PAGE_SIZE)
                }
                
                # Use paginated results
                paginated = self.fetch_paginated_data(
                    f'repos/{repo_path}/pulls', 
                    params, 
                    max_items=max_items,
                    use_cache=use_cache,
                    cache_ttl=cache_ttl
                )
                
                # If a specific page was requested, return just that page
                if 'page' in kwargs:
                    params['page'] = kwargs.get('page')
                    return self._make_request(f'repos/{repo_path}/pulls', params, use_cache=use_cache, cache_ttl=cache_ttl)
                
                # Otherwise, return all items as a list
                return {'items': paginated.to_list()}
                
            else:
                raise ValueError(f"Unsupported data type: {data_type}")
        except Exception as e:
            logger.error(f"Error fetching repository data: {str(e)}")
            return {'error': str(e)}
