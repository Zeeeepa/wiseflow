"""
GitHub connector for Wiseflow.

This module provides a connector for GitHub repositories.
"""

from typing import Dict, List, Any, Optional, Union, Tuple
import logging
import uuid
import asyncio
from datetime import datetime, timedelta
import os
import re
import base64
import json
from urllib.parse import urlparse

import aiohttp

from core.plugins import PluginBase
from core.connectors import ConnectorBase, DataItem

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


class GitHubConnector(ConnectorBase):
    """Connector for GitHub repositories."""
    
    name: str = "github_connector"
    description: str = "Connector for GitHub repositories"
    source_type: str = "github"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the GitHub connector."""
        super().__init__(config)
        self.api_token = self.config.get("api_token", os.environ.get("GITHUB_TOKEN", ""))
        self.api_base_url = "https://api.github.com"
        self.semaphore = asyncio.Semaphore(self.config.get("concurrency", 5))
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
        """Initialize the connector."""
        try:
            if not self.api_token:
                logger.warning("No GitHub API token provided. Rate limits will be restricted.")
            
            # Load ETags from cache if available
            self._load_etags()
            
            logger.info("Initialized GitHub connector")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize GitHub connector: {e}")
            return False
    
    async def _create_session(self):
        """Create an aiohttp session if it doesn't exist."""
        if self.session is None or self.session.closed:
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
            
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
    
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
        try:
            # Add padding if necessary
            padding = 4 - (len(s) % 4) if len(s) % 4 else 0
            s = s + "=" * padding
            base64.b64decode(s)
            return True
        except Exception:
            return False
    
    async def _close_session(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            
            # Save ETags to cache
            self._save_etags()
    
    def _update_rate_limit_info(self, headers: Dict[str, str]) -> None:
        """Update rate limit information from response headers.
        
        Args:
            headers: Response headers from GitHub API
        """
        # Extract rate limit information from headers
        if 'X-RateLimit-Remaining' in headers:
            self.rate_limit_remaining = int(headers['X-RateLimit-Remaining'])
        
        if 'X-RateLimit-Reset' in headers:
            reset_timestamp = int(headers['X-RateLimit-Reset'])
            self.rate_limit_reset = datetime.fromtimestamp(reset_timestamp)
        
        if 'X-RateLimit-Limit' in headers:
            self.rate_limit_limit = int(headers['X-RateLimit-Limit'])
        
        # Log rate limit information
        if all(x is not None for x in [self.rate_limit_remaining, self.rate_limit_reset, self.rate_limit_limit]):
            reset_in = (self.rate_limit_reset - datetime.now()).total_seconds()
            logger.debug(f"GitHub API rate limit: {self.rate_limit_remaining}/{self.rate_limit_limit}, resets in {reset_in:.0f} seconds")
    
    async def _should_wait_for_rate_limit(self) -> Tuple[bool, float]:
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
    
    async def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
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
    
    async def _save_to_cache(self, cache_key: str, data: Dict[str, Any], etag: Optional[str] = None) -> None:
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
    
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, method: str = 'GET') -> Dict[str, Any]:
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
        # Create session if it doesn't exist
        await self._create_session()
            
        url = f"{self.api_base_url}/{endpoint.lstrip('/')}"
        retries = 0
        cache_key = None
        max_retries = self.config.get('max_retries', 3)
        
        # Check if we should wait for rate limit to reset
        should_wait, wait_time = await self._should_wait_for_rate_limit()
        if should_wait:
            logger.warning(f"Approaching rate limit, waiting for {wait_time:.0f} seconds before making request")
            await asyncio.sleep(wait_time)
        
        # For GET requests, try to use cache
        if method.upper() == 'GET' and self.cache_enabled:
            cache_key = self._get_cache_key(endpoint, params)
            cached_data = await self._get_from_cache(cache_key)
            
            if cached_data:
                return cached_data
        
        # Prepare headers for conditional request
        headers = {}
        if method.upper() == 'GET' and cache_key and cache_key in self.etags:
            headers['If-None-Match'] = self.etags[cache_key]
        
        while retries < max_retries:
            try:
                async with self.semaphore:
                    if method.upper() == 'GET':
                        async with self.session.get(url, params=params, headers=headers) as response:
                            # Update rate limit information
                            self._update_rate_limit_info(response.headers)
                            
                            # Handle 304 Not Modified (cached response is still valid)
                            if response.status == 304 and cache_key:
                                cached_data = await self._get_from_cache(cache_key)
                                if cached_data:
                                    logger.debug(f"Using cached data for {endpoint} (304 Not Modified)")
                                    return cached_data
                            
                            # Handle successful response
                            if response.status == 200:
                                data = await response.json()
                                
                                # Cache the response for GET requests
                                if self.cache_enabled and cache_key:
                                    etag = response.headers.get('ETag')
                                    await self._save_to_cache(cache_key, data, etag)
                                
                                return data
                            
                            # Handle rate limiting
                            elif response.status == 403 and 'rate limit exceeded' in (await response.text()).lower():
                                reset_time = None
                                if 'X-RateLimit-Reset' in response.headers:
                                    reset_timestamp = int(response.headers['X-RateLimit-Reset'])
                                    reset_time = datetime.fromtimestamp(reset_timestamp)
                                
                                wait_time = self.config.get('rate_limit_pause', 60)
                                if reset_time:
                                    wait_time = max(1, (reset_time - datetime.now()).total_seconds() + 5)  # Add 5 seconds buffer
                                
                                logger.warning(f"Rate limit exceeded. Waiting for {wait_time:.0f} seconds.")
                                await asyncio.sleep(wait_time)
                                retries += 1
                            
                            # Handle other errors
                            else:
                                error_message = f"GitHub API error: {response.status}"
                                errors = []
                                
                                try:
                                    error_data = await response.json()
                                    if 'message' in error_data:
                                        error_message = f"GitHub API error: {response.status} - {error_data['message']}"
                                    if 'errors' in error_data:
                                        errors = error_data['errors']
                                except Exception:
                                    error_message = f"GitHub API error: {response.status} - {await response.text()}"
                                
                                # Determine if we should retry based on status code
                                if response.status in [500, 502, 503, 504]:
                                    # Server errors - retry with exponential backoff
                                    retry_after = int(response.headers.get('Retry-After', 2 ** retries))
                                    logger.warning(f"{error_message}. Retrying in {retry_after} seconds.")
                                    await asyncio.sleep(retry_after)
                                    retries += 1
                                else:
                                    # Client errors - don't retry
                                    raise GitHubAPIError(response.status, error_message, errors)
                    
                    elif method.upper() == 'POST':
                        async with self.session.post(url, json=params, headers=headers) as response:
                            # Update rate limit information
                            self._update_rate_limit_info(response.headers)
                            
                            if response.status in [200, 201]:
                                return await response.json()
                            else:
                                # Handle errors
                                await self._handle_error_response(response, retries)
                                retries += 1
                    
                    elif method.upper() == 'PUT':
                        async with self.session.put(url, json=params, headers=headers) as response:
                            # Update rate limit information
                            self._update_rate_limit_info(response.headers)
                            
                            if response.status in [200, 201]:
                                return await response.json()
                            else:
                                # Handle errors
                                await self._handle_error_response(response, retries)
                                retries += 1
                    
                    elif method.upper() == 'DELETE':
                        async with self.session.delete(url, headers=headers) as response:
                            # Update rate limit information
                            self._update_rate_limit_info(response.headers)
                            
                            if response.status in [200, 204]:
                                return {}
                            else:
                                # Handle errors
                                await self._handle_error_response(response, retries)
                                retries += 1
                    
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
                
            except GitHubAPIError:
                # Re-raise GitHubAPIError exceptions
                raise
            except GitHubRateLimitExceeded:
                # Re-raise GitHubRateLimitExceeded exceptions
                raise
            except Exception as e:
                logger.error(f"Error making GitHub API request: {str(e)}")
                retries += 1
                if retries >= max_retries:
                    raise
                await asyncio.sleep(2 ** retries)  # Exponential backoff
                
        raise Exception(f"Failed to make GitHub API request after {max_retries} retries")
    
    async def _handle_error_response(self, response, retries):
        """Handle error responses from GitHub API.
        
        Args:
            response: Response object
            retries: Current retry count
            
        Raises:
            GitHubRateLimitExceeded: If rate limit is exceeded
            GitHubAPIError: If the API returns an error
        """
        error_message = f"GitHub API error: {response.status}"
        errors = []
        
        try:
            error_data = await response.json()
            if 'message' in error_data:
                error_message = f"GitHub API error: {response.status} - {error_data['message']}"
            if 'errors' in error_data:
                errors = error_data['errors']
        except Exception:
            error_message = f"GitHub API error: {response.status} - {await response.text()}"
        
        # Handle rate limiting
        if response.status == 403 and 'rate limit exceeded' in (await response.text()).lower():
            reset_time = None
            if 'X-RateLimit-Reset' in response.headers:
                reset_timestamp = int(response.headers['X-RateLimit-Reset'])
                reset_time = datetime.fromtimestamp(reset_timestamp)
            
            raise GitHubRateLimitExceeded(reset_time)
        
        # Determine if we should retry based on status code
        if response.status in [500, 502, 503, 504]:
            # Server errors - retry with exponential backoff
            retry_after = int(response.headers.get('Retry-After', 2 ** retries))
            logger.warning(f"{error_message}. Retrying in {retry_after} seconds.")
            await asyncio.sleep(retry_after)
        else:
            # Client errors - don't retry
            raise GitHubAPIError(response.status, error_message, errors)
    
    async def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get current rate limit information.
        
        Returns:
            Dict[str, Any]: Rate limit information
        """
        try:
            data = await self._make_request('rate_limit')
            return data.get('resources', {})
        except Exception as e:
            logger.error(f"Error getting rate limit info: {e}")
            return {}
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from GitHub repositories."""
        params = params or {}
        
        try:
            # Determine what to collect
            if "repo" in params:
                # Collect data from a specific repository
                repo = params["repo"]
                if "issue_number" in params:
                    # Collect a specific issue
                    issue_number = params["issue_number"]
                    return await self._collect_issue(repo, issue_number)
                elif "pr_number" in params:
                    # Collect a specific pull request
                    pr_number = params["pr_number"]
                    return await self._collect_pr(repo, pr_number)
                elif "path" in params:
                    # Collect a specific file or directory
                    path = params["path"]
                    return await self._collect_repo_content(repo, path)
                else:
                    # Collect repository information
                    return await self._collect_repo_info(repo)
            elif "search" in params:
                # Search for repositories, code, issues, or PRs
                search_type = params.get("search_type", "repositories")
                query = params["search"]
                return await self._search_github(search_type, query, params)
            elif "user" in params:
                # Collect data from a specific user
                user = params["user"]
                return await self._collect_user_info(user)
            else:
                logger.error("No repo, search, or user parameter provided for GitHub connector")
                return []
        except GitHubRateLimitExceeded as e:
            logger.error(f"Rate limit exceeded: {e}")
            # Create an error data item
            error_item = DataItem(
                source_id=f"github_error_{uuid.uuid4()}",
                content=f"GitHub API rate limit exceeded. Reset time: {e.reset_time.isoformat() if e.reset_time else 'unknown'}",
                metadata={"error": "rate_limit_exceeded", "reset_time": e.reset_time.isoformat() if e.reset_time else None},
                url="",
                content_type="text/plain",
                raw_data={"error": "rate_limit_exceeded", "reset_time": e.reset_time.isoformat() if e.reset_time else None}
            )
            return [error_item]
        except GitHubAPIError as e:
            logger.error(f"GitHub API error: {e}")
            # Create an error data item
            error_item = DataItem(
                source_id=f"github_error_{uuid.uuid4()}",
                content=f"GitHub API error: {e.status_code} - {e.message}",
                metadata={"error": "api_error", "status_code": e.status_code, "message": e.message, "errors": e.errors},
                url="",
                content_type="text/plain",
                raw_data={"error": "api_error", "status_code": e.status_code, "message": e.message, "errors": e.errors}
            )
            return [error_item]
        except Exception as e:
            logger.error(f"Error collecting data from GitHub: {e}")
            # Create an error data item
            error_item = DataItem(
                source_id=f"github_error_{uuid.uuid4()}",
                content=f"Error collecting data from GitHub: {str(e)}",
                metadata={"error": "general_error", "message": str(e)},
                url="",
                content_type="text/plain",
                raw_data={"error": "general_error", "message": str(e)}
            )
            return [error_item]
        finally:
            # Close session
            await self._close_session()
    
    async def _collect_repo_info(self, repo: str) -> List[DataItem]:
        """Collect information about a GitHub repository."""
        try:
            # Get repository information
            repo_data = await self._make_request(f'repos/{repo}')
            
            # Get repository README
            readme_content = await self._get_repo_readme(repo)
            
            # Create metadata
            metadata = {
                "name": repo_data.get("name", ""),
                "full_name": repo_data.get("full_name", ""),
                "description": repo_data.get("description", ""),
                "owner": repo_data.get("owner", {}).get("login", ""),
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "watchers": repo_data.get("watchers_count", 0),
                "open_issues": repo_data.get("open_issues_count", 0),
                "language": repo_data.get("language", ""),
                "created_at": repo_data.get("created_at", ""),
                "updated_at": repo_data.get("updated_at", ""),
                "pushed_at": repo_data.get("pushed_at", ""),
                "homepage": repo_data.get("homepage", ""),
                "license": repo_data.get("license", {}).get("name", ""),
                "topics": repo_data.get("topics", []),
                "has_wiki": repo_data.get("has_wiki", False),
                "has_pages": repo_data.get("has_pages", False),
                "has_projects": repo_data.get("has_projects", False),
                "has_downloads": repo_data.get("has_downloads", False),
                "archived": repo_data.get("archived", False),
                "disabled": repo_data.get("disabled", False),
                "visibility": repo_data.get("visibility", ""),
                "default_branch": repo_data.get("default_branch", "")
            }
            
            # Create data item
            item = DataItem(
                source_id=f"github_repo_{repo.replace('/', '_')}",
                content=readme_content or repo_data.get("description", ""),
                metadata=metadata,
                url=repo_data.get("html_url", f"https://github.com/{repo}"),
                timestamp=datetime.fromisoformat(repo_data.get("updated_at", "").replace("Z", "+00:00")) if repo_data.get("updated_at") else None,
                content_type="text/markdown" if readme_content else "text/plain",
                raw_data=repo_data
            )
            
            return [item]
        except Exception as e:
            logger.error(f"Error collecting repository info for {repo}: {e}")
            raise
    
    async def _get_repo_readme(self, repo: str) -> Optional[str]:
        """Get the README content of a repository."""
        try:
            try:
                readme_data = await self._make_request(f'repos/{repo}/readme')
                
                # Decode content
                if readme_data.get("content"):
                    content = base64.b64decode(readme_data["content"]).decode("utf-8")
                    return content
            except GitHubAPIError as e:
                if e.status_code == 404:
                    logger.warning(f"No README found for {repo}")
                else:
                    raise
                
            return None
        except Exception as e:
            logger.error(f"Error getting README for {repo}: {e}")
            return None
    
    async def _collect_repo_content(self, repo: str, path: str) -> List[DataItem]:
        """Collect content from a repository path."""
        try:
            # Get content information
            url = f"{self.api_base_url}/repos/{repo}/contents/{path}"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get content for {repo}/{path}: {response.status}")
                        return []
                    
                    content_data = await response.json()
            
            # Handle directory
            if isinstance(content_data, list):
                # This is a directory, collect all files
                results = []
                for item in content_data:
                    if item["type"] == "file":
                        # Get file content
                        file_content = await self._get_file_content(repo, item["path"])
                        
                        # Create data item
                        data_item = DataItem(
                            source_id=f"github_file_{repo.replace('/', '_')}_{item['path'].replace('/', '_')}",
                            content=file_content or "",
                            metadata={
                                "repo": repo,
                                "path": item["path"],
                                "name": item["name"],
                                "size": item["size"],
                                "type": item["type"],
                                "sha": item["sha"]
                            },
                            url=item["html_url"],
                            content_type=self._get_content_type(item["name"]),
                            raw_data=item
                        )
                        
                        results.append(data_item)
                
                return results
            else:
                # This is a file, get its content
                file_content = await self._get_file_content(repo, path)
                
                # Create data item
                data_item = DataItem(
                    source_id=f"github_file_{repo.replace('/', '_')}_{path.replace('/', '_')}",
                    content=file_content or "",
                    metadata={
                        "repo": repo,
                        "path": path,
                        "name": content_data["name"],
                        "size": content_data["size"],
                        "type": content_data["type"],
                        "sha": content_data["sha"]
                    },
                    url=content_data["html_url"],
                    content_type=self._get_content_type(path),
                    raw_data=content_data
                )
                
                return [data_item]
        except Exception as e:
            logger.error(f"Error collecting content for {repo}/{path}: {e}")
            return []
    
    async def _get_file_content(self, repo: str, path: str) -> Optional[str]:
        """Get the content of a file in a repository."""
        try:
            url = f"{self.api_base_url}/repos/{repo}/contents/{path}"
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to get file content for {repo}/{path}: {response.status}")
                    return None
                
                file_data = await response.json()
                
                # Decode content
                if file_data.get("content"):
                    content = base64.b64decode(file_data["content"]).decode("utf-8")
                    return content
                
                return None
        except Exception as e:
            logger.error(f"Error getting file content for {repo}/{path}: {e}")
            return None
    
    def _get_content_type(self, filename: str) -> str:
        """Determine the content type based on the file extension."""
        ext = os.path.splitext(filename)[1].lower()
        
        if ext in [".md", ".markdown"]:
            return "text/markdown"
        elif ext in [".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".cs", ".go", ".rb", ".php"]:
            return "text/plain"
        elif ext in [".json"]:
            return "application/json"
        elif ext in [".xml"]:
            return "application/xml"
        elif ext in [".html", ".htm"]:
            return "text/html"
        elif ext in [".css"]:
            return "text/css"
        elif ext in [".txt"]:
            return "text/plain"
        else:
            return "application/octet-stream"
    
    async def _collect_issue(self, repo: str, issue_number: int) -> List[DataItem]:
        """Collect information about a GitHub issue."""
        try:
            # Get issue information
            url = f"{self.api_base_url}/repos/{repo}/issues/{issue_number}"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get issue {issue_number} for {repo}: {response.status}")
                        return []
                    
                    issue_data = await response.json()
            
            # Get issue comments
            comments_url = f"{self.api_base_url}/repos/{repo}/issues/{issue_number}/comments"
            async with self.semaphore:
                async with self.session.get(comments_url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to get comments for issue {issue_number} in {repo}: {response.status}")
                        comments = []
                    else:
                        comments = await response.json()
            
            # Create content
            content = f"# {issue_data.get('title', '')}\n\n{issue_data.get('body', '')}"
            
            # Add comments to content
            if comments:
                content += "\n\n## Comments\n\n"
                for comment in comments:
                    content += f"### {comment.get('user', {}).get('login', '')} - {comment.get('created_at', '')}\n\n{comment.get('body', '')}\n\n"
            
            # Create metadata
            metadata = {
                "repo": repo,
                "issue_number": issue_number,
                "title": issue_data.get("title", ""),
                "state": issue_data.get("state", ""),
                "user": issue_data.get("user", {}).get("login", ""),
                "labels": [label.get("name", "") for label in issue_data.get("labels", [])],
                "assignees": [assignee.get("login", "") for assignee in issue_data.get("assignees", [])],
                "created_at": issue_data.get("created_at", ""),
                "updated_at": issue_data.get("updated_at", ""),
                "closed_at": issue_data.get("closed_at", ""),
                "comment_count": issue_data.get("comments", 0),
                "is_pull_request": "pull_request" in issue_data
            }
            
            # Create data item
            item = DataItem(
                source_id=f"github_issue_{repo.replace('/', '_')}_{issue_number}",
                content=content,
                metadata=metadata,
                url=issue_data.get("html_url", ""),
                timestamp=datetime.fromisoformat(issue_data.get("updated_at", "").replace("Z", "+00:00")) if issue_data.get("updated_at") else None,
                content_type="text/markdown",
                raw_data={"issue": issue_data, "comments": comments}
            )
            
            return [item]
        except Exception as e:
            logger.error(f"Error collecting issue {issue_number} for {repo}: {e}")
            return []
    
    async def _collect_pr(self, repo: str, pr_number: int) -> List[DataItem]:
        """Collect information about a GitHub pull request."""
        try:
            # Get PR information
            url = f"{self.api_base_url}/repos/{repo}/pulls/{pr_number}"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get PR {pr_number} for {repo}: {response.status}")
                        return []
                    
                    pr_data = await response.json()
            
            # Get PR comments
            comments_url = f"{self.api_base_url}/repos/{repo}/issues/{pr_number}/comments"
            async with self.semaphore:
                async with self.session.get(comments_url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to get comments for PR {pr_number} in {repo}: {response.status}")
                        comments = []
                    else:
                        comments = await response.json()
            
            # Get PR review comments
            review_comments_url = f"{self.api_base_url}/repos/{repo}/pulls/{pr_number}/comments"
            async with self.semaphore:
                async with self.session.get(review_comments_url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to get review comments for PR {pr_number} in {repo}: {response.status}")
                        review_comments = []
                    else:
                        review_comments = await response.json()
            
            # Create content
            content = f"# {pr_data.get('title', '')}\n\n{pr_data.get('body', '')}"
            
            # Add comments to content
            if comments:
                content += "\n\n## Comments\n\n"
                for comment in comments:
                    content += f"### {comment.get('user', {}).get('login', '')} - {comment.get('created_at', '')}\n\n{comment.get('body', '')}\n\n"
            
            # Add review comments to content
            if review_comments:
                content += "\n\n## Review Comments\n\n"
                for comment in review_comments:
                    content += f"### {comment.get('user', {}).get('login', '')} - {comment.get('created_at', '')}\n\n{comment.get('body', '')}\n\nOn file: {comment.get('path', '')}, line: {comment.get('line', '')}\n\n"
            
            # Create metadata
            metadata = {
                "repo": repo,
                "pr_number": pr_number,
                "title": pr_data.get("title", ""),
                "state": pr_data.get("state", ""),
                "user": pr_data.get("user", {}).get("login", ""),
                "labels": [label.get("name", "") for label in pr_data.get("labels", [])],
                "assignees": [assignee.get("login", "") for assignee in pr_data.get("assignees", [])],
                "created_at": pr_data.get("created_at", ""),
                "updated_at": pr_data.get("updated_at", ""),
                "closed_at": pr_data.get("closed_at", ""),
                "merged_at": pr_data.get("merged_at", ""),
                "comment_count": pr_data.get("comments", 0),
                "review_comment_count": pr_data.get("review_comments", 0),
                "commits": pr_data.get("commits", 0),
                "additions": pr_data.get("additions", 0),
                "deletions": pr_data.get("deletions", 0),
                "changed_files": pr_data.get("changed_files", 0),
                "base": pr_data.get("base", {}).get("ref", ""),
                "head": pr_data.get("head", {}).get("ref", ""),
                "is_merged": pr_data.get("merged", False),
                "mergeable": pr_data.get("mergeable", None),
                "mergeable_state": pr_data.get("mergeable_state", ""),
                "draft": pr_data.get("draft", False)
            }
            
            # Create data item
            item = DataItem(
                source_id=f"github_pr_{repo.replace('/', '_')}_{pr_number}",
                content=content,
                metadata=metadata,
                url=pr_data.get("html_url", ""),
                timestamp=datetime.fromisoformat(pr_data.get("updated_at", "").replace("Z", "+00:00")) if pr_data.get("updated_at") else None,
                content_type="text/markdown",
                raw_data={"pr": pr_data, "comments": comments, "review_comments": review_comments}
            )
            
            return [item]
        except Exception as e:
            logger.error(f"Error collecting PR {pr_number} for {repo}: {e}")
            return []
    
    async def _collect_user_info(self, username: str) -> List[DataItem]:
        """Collect information about a GitHub user."""
        try:
            # Get user information
            url = f"{self.api_base_url}/users/{username}"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get user info for {username}: {response.status}")
                        return []
                    
                    user_data = await response.json()
            
            # Get user repositories
            repos_url = f"{self.api_base_url}/users/{username}/repos"
            async with self.semaphore:
                async with self.session.get(repos_url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to get repositories for user {username}: {response.status}")
                        repos = []
                    else:
                        repos = await response.json()
            
            # Create content
            content = f"# {user_data.get('name', username)}\n\n{user_data.get('bio', '')}"
            
            if repos:
                content += "\n\n## Repositories\n\n"
                for repo in repos:
                    content += f"- [{repo.get('name', '')}]({repo.get('html_url', '')}) - {repo.get('description', '')}\n"
            
            # Create metadata
            metadata = {
                "username": username,
                "name": user_data.get("name", ""),
                "company": user_data.get("company", ""),
                "blog": user_data.get("blog", ""),
                "location": user_data.get("location", ""),
                "email": user_data.get("email", ""),
                "bio": user_data.get("bio", ""),
                "twitter_username": user_data.get("twitter_username", ""),
                "public_repos": user_data.get("public_repos", 0),
                "public_gists": user_data.get("public_gists", 0),
                "followers": user_data.get("followers", 0),
                "following": user_data.get("following", 0),
                "created_at": user_data.get("created_at", ""),
                "updated_at": user_data.get("updated_at", ""),
                "repositories": [repo.get("name", "") for repo in repos]
            }
            
            # Create data item
            item = DataItem(
                source_id=f"github_user_{username}",
                content=content,
                metadata=metadata,
                url=user_data.get("html_url", f"https://github.com/{username}"),
                timestamp=datetime.fromisoformat(user_data.get("updated_at", "").replace("Z", "+00:00")) if user_data.get("updated_at") else None,
                content_type="text/markdown",
                raw_data={"user": user_data, "repositories": repos}
            )
            
            return [item]
        except Exception as e:
            logger.error(f"Error collecting user info for {username}: {e}")
            return []
    
    async def _search_github(self, search_type: str, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """Search GitHub for repositories, code, issues, or PRs."""
        try:
            # Set up search parameters
            per_page = params.get("per_page", 10)
            page = params.get("page", 1)
            sort = params.get("sort", "")
            order = params.get("order", "desc")
            
            # Construct search URL
            url = f"{self.api_base_url}/search/{search_type}?q={query}&per_page={per_page}&page={page}"
            if sort:
                url += f"&sort={sort}"
            if order:
                url += f"&order={order}"
            
            # Execute search
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to search GitHub {search_type} with query {query}: {response.status}")
                        return []
                    
                    search_data = await response.json()
            
            # Process search results
            results = []
            for item in search_data.get("items", []):
                if search_type == "repositories":
                    # Create repository item
                    data_item = DataItem(
                        source_id=f"github_repo_{item.get('full_name', '').replace('/', '_')}",
                        content=item.get("description", ""),
                        metadata={
                            "name": item.get("name", ""),
                            "full_name": item.get("full_name", ""),
                            "owner": item.get("owner", {}).get("login", ""),
                            "description": item.get("description", ""),
                            "stars": item.get("stargazers_count", 0),
                            "forks": item.get("forks_count", 0),
                            "language": item.get("language", ""),
                            "topics": item.get("topics", []),
                            "created_at": item.get("created_at", ""),
                            "updated_at": item.get("updated_at", ""),
                            "search_score": item.get("score", 0)
                        },
                        url=item.get("html_url", ""),
                        timestamp=datetime.fromisoformat(item.get("updated_at", "").replace("Z", "+00:00")) if item.get("updated_at") else None,
                        content_type="text/plain",
                        raw_data=item
                    )
                    results.append(data_item)
                
                elif search_type == "code":
                    # Create code item
                    repo_name = item.get("repository", {}).get("full_name", "")
                    path = item.get("path", "")
                    
                    # Get file content
                    file_content = None
                    if params.get("include_content", True):
                        file_content = await self._get_file_content(repo_name, path)
                    
                    data_item = DataItem(
                        source_id=f"github_code_{repo_name.replace('/', '_')}_{path.replace('/', '_')}",
                        content=file_content or item.get("text_matches", [{}])[0].get("fragment", ""),
                        metadata={
                            "repo": repo_name,
                            "path": path,
                            "name": os.path.basename(path),
                            "search_score": item.get("score", 0)
                        },
                        url=item.get("html_url", ""),
                        content_type=self._get_content_type(path),
                        raw_data=item
                    )
                    results.append(data_item)
                
                elif search_type == "issues":
                    # Create issue item
                    repo_name = item.get("repository_url", "").split("/repos/")[1] if "repository_url" in item else ""
                    
                    data_item = DataItem(
                        source_id=f"github_issue_{repo_name.replace('/', '_')}_{item.get('number', '')}",
                        content=f"# {item.get('title', '')}\n\n{item.get('body', '')}",
                        metadata={
                            "repo": repo_name,
                            "issue_number": item.get("number", ""),
                            "title": item.get("title", ""),
                            "state": item.get("state", ""),
                            "user": item.get("user", {}).get("login", ""),
                            "labels": [label.get("name", "") for label in item.get("labels", [])],
                            "created_at": item.get("created_at", ""),
                            "updated_at": item.get("updated_at", ""),
                            "closed_at": item.get("closed_at", ""),
                            "is_pull_request": "pull_request" in item,
                            "search_score": item.get("score", 0)
                        },
                        url=item.get("html_url", ""),
                        timestamp=datetime.fromisoformat(item.get("updated_at", "").replace("Z", "+00:00")) if item.get("updated_at") else None,
                        content_type="text/markdown",
                        raw_data=item
                    )
                    results.append(data_item)
            
            return results
        except Exception as e:
            logger.error(f"Error searching GitHub {search_type} with query {query}: {e}")
            return []
