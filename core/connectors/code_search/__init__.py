"""
Code Search connector for Wiseflow.

This module provides a connector for searching and retrieving code from various sources.
"""

from typing import Dict, List, Any, Optional, Union, Tuple
import logging
import uuid
import asyncio
from datetime import datetime, timedelta
import os
import re
import json
import tempfile
import hashlib
from urllib.parse import urlparse, quote_plus
import time
from functools import lru_cache

import aiohttp
import requests
from aiohttp import ClientTimeout
from aiohttp_retry import RetryClient, ExponentialRetry

from core.plugins import PluginBase
from core.connectors import ConnectorBase, DataItem
from core.utils.error_handling import handle_exceptions, ConnectionError, DataProcessingError, WiseflowError
from core.crawl4ai.cache_context import CacheMode, CacheContext

logger = logging.getLogger(__name__)

# Cache configuration
DEFAULT_CACHE_TTL = 3600  # 1 hour in seconds
DEFAULT_CACHE_SIZE = 1024  # Maximum number of items in the LRU cache

class CodeSearchError(WiseflowError):
    """Error raised when code search operations fail."""
    pass

class CodeSearchRateLimitError(CodeSearchError):
    """Error raised when code search rate limits are exceeded."""
    def __init__(self, message: str, service: str, retry_after: Optional[int] = None, **kwargs):
        details = {
            "service": service,
            "retry_after": retry_after,
            **kwargs
        }
        super().__init__(message, details)

class CodeSearchConnector(ConnectorBase):
    """Connector for code search."""
    
    name: str = "code_search_connector"
    description: str = "Connector for searching and retrieving code from various sources"
    source_type: str = "code_search"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the code search connector."""
        super().__init__(config)
        
        # Configure concurrency
        self.concurrency = self.config.get("concurrency", 5)
        self.semaphore = asyncio.Semaphore(self.concurrency)
        self.session = None
        self.retry_client = None
        
        # Configure timeouts
        self.timeout = self.config.get("timeout", 30)  # seconds
        
        # Configure API keys
        self.github_token = self.config.get("github_token", os.environ.get("GITHUB_TOKEN", ""))
        self.gitlab_token = self.config.get("gitlab_token", os.environ.get("GITLAB_TOKEN", ""))
        self.bitbucket_token = self.config.get("bitbucket_token", os.environ.get("BITBUCKET_TOKEN", ""))
        self.sourcegraph_token = self.config.get("sourcegraph_token", os.environ.get("SOURCEGRAPH_TOKEN", ""))
        
        # Configure API endpoints
        self.sourcegraph_url = self.config.get("sourcegraph_url", "https://sourcegraph.com")
        
        # Configure caching
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.cache_ttl = self.config.get("cache_ttl", DEFAULT_CACHE_TTL)
        self.cache_size = self.config.get("cache_size", DEFAULT_CACHE_SIZE)
        self.cache_dir = self.config.get("cache_dir", os.path.join(tempfile.gettempdir(), "wiseflow", "code_search_cache"))
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Configure rate limiting
        self.rate_limits = {
            "github": self.config.get("github_rate_limit", 30),  # requests per minute
            "gitlab": self.config.get("gitlab_rate_limit", 30),
            "bitbucket": self.config.get("bitbucket_rate_limit", 30),
            "sourcegraph": self.config.get("sourcegraph_rate_limit", 30)
        }
        
        # Service-specific configurations
        self.service_configs = {
            "github": self.config.get("github_config", {}),
            "gitlab": self.config.get("gitlab_config", {}),
            "bitbucket": self.config.get("bitbucket_config", {}),
            "sourcegraph": self.config.get("sourcegraph_config", {})
        }
        
        # Initialize cache
        self._init_cache()
        
        # Track rate limit state
        self.rate_limit_state = {
            "github": {"reset_at": datetime.now(), "remaining": self.rate_limits["github"]},
            "gitlab": {"reset_at": datetime.now(), "remaining": self.rate_limits["gitlab"]},
            "bitbucket": {"reset_at": datetime.now(), "remaining": self.rate_limits["bitbucket"]},
            "sourcegraph": {"reset_at": datetime.now(), "remaining": self.rate_limits["sourcegraph"]}
        }
    
    def _init_cache(self) -> None:
        """Initialize the cache system."""
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Clear expired cache files
        self._clear_expired_cache()
    
    def _clear_expired_cache(self) -> None:
        """Clear expired cache files."""
        try:
            now = datetime.now()
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.isfile(filepath):
                    # Check if the file has expired metadata
                    try:
                        with open(filepath, 'r') as f:
                            cache_data = json.load(f)
                            expires_at = datetime.fromisoformat(cache_data.get("expires_at", "2000-01-01T00:00:00"))
                            if now > expires_at:
                                os.remove(filepath)
                                logger.debug(f"Removed expired cache file: {filename}")
                    except (json.JSONDecodeError, KeyError, ValueError, FileNotFoundError):
                        # If we can't read the file or it's invalid, remove it
                        try:
                            os.remove(filepath)
                            logger.debug(f"Removed invalid cache file: {filename}")
                        except (FileNotFoundError, PermissionError):
                            pass
        except Exception as e:
            logger.warning(f"Error clearing expired cache: {e}")
    
    def _get_cache_key(self, service: str, query: str, params: Dict[str, Any]) -> str:
        """Generate a cache key for the given query and parameters."""
        # Create a string representation of the parameters
        param_str = json.dumps(params, sort_keys=True)
        
        # Create a hash of the service, query, and parameters
        key_data = f"{service}:{query}:{param_str}".encode('utf-8')
        return hashlib.md5(key_data).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> str:
        """Get the file path for a cache key."""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    async def _get_from_cache(self, service: str, query: str, params: Dict[str, Any]) -> Optional[List[DataItem]]:
        """Get results from cache if available and not expired."""
        if not self.cache_enabled:
            return None
        
        cache_key = self._get_cache_key(service, query, params)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as f:
                    cache_data = json.load(f)
                
                # Check if cache has expired
                expires_at = datetime.fromisoformat(cache_data.get("expires_at", "2000-01-01T00:00:00"))
                if datetime.now() > expires_at:
                    logger.debug(f"Cache expired for {service} query: {query}")
                    return None
                
                # Deserialize the cached items
                items = []
                for item_data in cache_data.get("items", []):
                    items.append(DataItem.from_dict(item_data))
                
                logger.debug(f"Cache hit for {service} query: {query}")
                return items
        except (json.JSONDecodeError, KeyError, ValueError, FileNotFoundError) as e:
            logger.debug(f"Cache error for {service} query: {query} - {e}")
        
        logger.debug(f"Cache miss for {service} query: {query}")
        return None
    
    async def _save_to_cache(self, service: str, query: str, params: Dict[str, Any], items: List[DataItem]) -> None:
        """Save results to cache."""
        if not self.cache_enabled:
            return
        
        cache_key = self._get_cache_key(service, query, params)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            # Prepare cache data
            cache_data = {
                "service": service,
                "query": query,
                "params": params,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(seconds=self.cache_ttl)).isoformat(),
                "items": [item.to_dict() for item in items]
            }
            
            # Write to cache file
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)
            
            logger.debug(f"Saved to cache: {service} query: {query}")
        except Exception as e:
            logger.warning(f"Error saving to cache: {e}")
    
    def initialize(self) -> bool:
        """Initialize the connector."""
        try:
            logger.info("Initialized code search connector")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize code search connector: {e}")
            return False
    
    async def _create_session(self):
        """Create an aiohttp session if it doesn't exist."""
        if self.session is None or self.session.closed:
            # Create a session with timeout
            timeout = ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # Create a retry client
            retry_options = ExponentialRetry(
                attempts=3,
                start_timeout=0.5,
                max_timeout=10.0,
                factor=2.0,
                statuses=[500, 502, 503, 504]
            )
            self.retry_client = RetryClient(client_session=self.session, retry_options=retry_options)
        
        return self.session
    
    async def _close_session(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            self.retry_client = None
    
    async def _update_rate_limit_state(self, service: str, response: aiohttp.ClientResponse) -> None:
        """Update rate limit state based on response headers."""
        try:
            now = datetime.now()
            
            if service == "github":
                # GitHub rate limit headers
                remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
                reset_at_timestamp = int(response.headers.get("X-RateLimit-Reset", 0))
                reset_at = datetime.fromtimestamp(reset_at_timestamp)
                
                self.rate_limit_state["github"] = {
                    "remaining": remaining,
                    "reset_at": reset_at
                }
                
                logger.debug(f"GitHub rate limit: {remaining} requests remaining, resets at {reset_at}")
            
            elif service == "gitlab":
                # GitLab rate limit headers
                remaining = int(response.headers.get("RateLimit-Remaining", 0))
                reset_at_timestamp = int(response.headers.get("RateLimit-Reset", 0))
                reset_at = datetime.fromtimestamp(reset_at_timestamp)
                
                self.rate_limit_state["gitlab"] = {
                    "remaining": remaining,
                    "reset_at": reset_at
                }
                
                logger.debug(f"GitLab rate limit: {remaining} requests remaining, resets at {reset_at}")
            
            # Add other services as needed
        
        except (ValueError, KeyError, TypeError) as e:
            logger.debug(f"Error updating rate limit state for {service}: {e}")
    
    async def _check_rate_limit(self, service: str) -> Tuple[bool, Optional[int]]:
        """
        Check if we're within rate limits for the service.
        
        Returns:
            Tuple of (can_proceed, retry_after_seconds)
        """
        state = self.rate_limit_state.get(service, {})
        remaining = state.get("remaining", 1)
        reset_at = state.get("reset_at", datetime.now())
        
        if remaining <= 0:
            now = datetime.now()
            if now < reset_at:
                # Calculate seconds until reset
                retry_after = int((reset_at - now).total_seconds()) + 1
                logger.warning(f"{service} rate limit exceeded. Retry after {retry_after} seconds")
                return False, retry_after
        
        return True, None
    
    async def _make_request(self, service: str, url: str, headers: Dict[str, str], params: Optional[Dict[str, Any]] = None) -> Tuple[Any, aiohttp.ClientResponse]:
        """
        Make a request with rate limit handling and retries.
        
        Returns:
            Tuple of (response_data, response_object)
        """
        await self._create_session()
        
        # Check rate limits
        can_proceed, retry_after = await self._check_rate_limit(service)
        if not can_proceed:
            raise CodeSearchRateLimitError(
                f"{service} rate limit exceeded",
                service=service,
                retry_after=retry_after
            )
        
        # Make the request with retry client
        async with self.semaphore:
            try:
                async with self.retry_client.get(url, headers=headers, params=params) as response:
                    # Update rate limit state
                    await self._update_rate_limit_state(service, response)
                    
                    # Handle rate limiting
                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", 60))
                        raise CodeSearchRateLimitError(
                            f"{service} rate limit exceeded",
                            service=service,
                            retry_after=retry_after,
                            status_code=response.status
                        )
                    
                    # Handle other errors
                    if response.status >= 400:
                        error_text = await response.text()
                        raise CodeSearchError(
                            f"{service} API error: {response.status}",
                            details={
                                "service": service,
                                "status_code": response.status,
                                "url": url,
                                "error_text": error_text
                            }
                        )
                    
                    # Parse response
                    if response.content_type == 'application/json':
                        data = await response.json()
                    else:
                        data = await response.text()
                    
                    return data, response
            
            except aiohttp.ClientError as e:
                raise ConnectionError(f"Connection error for {service}: {e}", {
                    "service": service,
                    "url": url
                })
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from code search sources."""
        params = params or {}
        
        try:
            # Create session
            await self._create_session()
            
            # Determine what to collect
            if "source" in params:
                source = params["source"].lower()
                
                if source == "github":
                    return await self._search_github(params)
                elif source == "gitlab":
                    return await self._search_gitlab(params)
                elif source == "bitbucket":
                    return await self._search_bitbucket(params)
                elif source == "sourcegraph":
                    return await self._search_sourcegraph(params)
                else:
                    logger.error(f"Unsupported code search source: {source}")
                    return []
            elif "query" in params:
                # Search across all configured sources
                return await self._search_all_sources(params)
            else:
                logger.error("No source or query parameter provided for code search connector")
                return []
        except Exception as e:
            logger.error(f"Error in code search collect: {e}")
            raise
        finally:
            # Close session
            await self._close_session()
    
    async def _search_all_sources(self, params: Dict[str, Any]) -> List[DataItem]:
        """Search for code across all configured sources."""
        query = params.get("query", "")
        if not query:
            logger.error("No query provided for code search")
            return []
        
        # Determine which sources to search
        sources = params.get("sources", ["github", "sourcegraph"])
        
        # Check cache first if enabled
        cache_mode = CacheMode[params.get("cache_mode", "ENABLED").upper()] if "cache_mode" in params else CacheMode.ENABLED
        cache_context = CacheContext(f"code_search:{query}", cache_mode)
        
        if cache_context.should_read():
            cached_results = await self._get_from_cache("all", query, params)
            if cached_results:
                return cached_results
        
        # Execute searches in parallel
        tasks = []
        for source in sources:
            source_params = params.copy()
            source_params["source"] = source
            
            if source == "github" and self.github_token:
                tasks.append(self._search_github(source_params))
            elif source == "gitlab" and self.gitlab_token:
                tasks.append(self._search_gitlab(source_params))
            elif source == "bitbucket" and self.bitbucket_token:
                tasks.append(self._search_bitbucket(source_params))
            elif source == "sourcegraph" and self.sourcegraph_token:
                tasks.append(self._search_sourcegraph(source_params))
        
        # Gather results
        results = []
        if tasks:
            search_results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in search_results:
                if isinstance(result, Exception):
                    logger.error(f"Error in code search: {result}")
                else:
                    results.extend(result)
        
        # Cache results if needed
        if cache_context.should_write() and results:
            await self._save_to_cache("all", query, params, results)
        
        return results
    
    async def _search_github(self, params: Dict[str, Any]) -> List[DataItem]:
        """Search for code on GitHub."""
        query = params.get("query", "")
        max_results = params.get("max_results", 10)
        
        if not query:
            logger.error("No query provided for GitHub code search")
            return []
        
        if not self.github_token:
            logger.warning("No GitHub token provided. API rate limits will be restricted.")
        
        # Check cache first if enabled
        cache_mode = CacheMode[params.get("cache_mode", "ENABLED").upper()] if "cache_mode" in params else CacheMode.ENABLED
        cache_context = CacheContext(f"github:{query}", cache_mode)
        
        if cache_context.should_read():
            cached_results = await self._get_from_cache("github", query, params)
            if cached_results:
                return cached_results
        
        try:
            # Construct GitHub API URL
            url = "https://api.github.com/search/code"
            
            # Set up headers
            headers = {
                "Accept": "application/vnd.github.v3+json"
            }
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            
            # Set up parameters
            api_params = {
                "q": query,
                "per_page": min(max_results, 100)
            }
            
            # Add language filter if provided
            if "language" in params:
                api_params["q"] += f" language:{params['language']}"
            
            # Add repository filter if provided
            if "repo" in params:
                api_params["q"] += f" repo:{params['repo']}"
            
            # Add path filter if provided
            if "path" in params:
                api_params["q"] += f" path:{params['path']}"
            
            # Add extension filter if provided
            if "extension" in params:
                api_params["q"] += f" extension:{params['extension']}"
            
            # Add sorting if provided
            if "sort" in params:
                api_params["sort"] = params["sort"]
            
            # Add order if provided
            if "order" in params:
                api_params["order"] = params["order"]
            
            # Execute search
            search_data, response = await self._make_request("github", url, headers, api_params)
            items = search_data.get("items", [])
            
            if not items:
                logger.info("No GitHub code search results found")
                return []
            
            # Process results
            results = []
            for item in items:
                # Extract metadata
                repo_name = item.get("repository", {}).get("full_name", "")
                path = item.get("path", "")
                name = item.get("name", "")
                url = item.get("html_url", "")
                
                # Get file content
                content = await self._get_github_file_content(repo_name, path)
                
                # Create metadata
                metadata = {
                    "repo": repo_name,
                    "path": path,
                    "name": name,
                    "url": url,
                    "source": "github"
                }
                
                # Create data item
                data_item = DataItem(
                    source_id=f"github_code_{uuid.uuid4().hex[:8]}",
                    content=content or "",
                    metadata=metadata,
                    url=url,
                    content_type=self._get_content_type(path),
                    raw_data=item
                )
                
                results.append(data_item)
            
            # Cache results if needed
            if cache_context.should_write():
                await self._save_to_cache("github", query, params, results)
            
            logger.info(f"Collected {len(results)} items from GitHub code search")
            return results
            
        except Exception as e:
            logger.error(f"Error searching GitHub code: {e}")
            if isinstance(e, CodeSearchRateLimitError):
                # Re-raise rate limit errors for proper handling
                raise
            raise CodeSearchError(f"GitHub search error: {str(e)}", {
                "query": query,
                "service": "github"
            })
    
    async def _get_github_file_content(self, repo: str, path: str) -> Optional[str]:
        """Get the content of a file from GitHub."""
        try:
            # Construct GitHub API URL
            url = f"https://api.github.com/repos/{repo}/contents/{path}"
            
            # Set up headers
            headers = {
                "Accept": "application/vnd.github.v3+json"
            }
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            
            # Get file content
            data, _ = await self._make_request("github", url, headers)
            
            # Decode content
            if isinstance(data, dict) and data.get("content"):
                import base64
                content = base64.b64decode(data["content"]).decode("utf-8")
                return content
            
            return None
        except Exception as e:
            logger.error(f"Error getting GitHub file content for {repo}/{path}: {e}")
            return None
    
    async def _search_gitlab(self, params: Dict[str, Any]) -> List[DataItem]:
        """Search for code on GitLab."""
        query = params.get("query", "")
        max_results = params.get("max_results", 10)
        
        if not query:
            logger.error("No query provided for GitLab code search")
            return []
        
        if not self.gitlab_token:
            logger.warning("No GitLab token provided. API functionality will be limited.")
            return []
        
        # Check cache first if enabled
        cache_mode = CacheMode[params.get("cache_mode", "ENABLED").upper()] if "cache_mode" in params else CacheMode.ENABLED
        cache_context = CacheContext(f"gitlab:{query}", cache_mode)
        
        if cache_context.should_read():
            cached_results = await self._get_from_cache("gitlab", query, params)
            if cached_results:
                return cached_results
        
        try:
            # Construct GitLab API URL
            base_url = "https://gitlab.com/api/v4"
            
            # Set up headers
            headers = {
                "PRIVATE-TOKEN": self.gitlab_token
            }
            
            # Set up parameters
            api_params = {
                "search": query,
                "scope": params.get("scope", "blobs"),
                "per_page": min(max_results, 100)
            }
            
            # Add project ID if provided
            if "project_id" in params:
                url = f"{base_url}/projects/{params['project_id']}/search"
            else:
                url = f"{base_url}/search"
            
            # Execute search
            search_data, response = await self._make_request("gitlab", url, headers, api_params)
            
            if not search_data:
                logger.info("No GitLab code search results found")
                return []
            
            # Process results
            results = []
            for item in search_data:
                # Extract metadata
                project_id = item.get("project_id", "")
                path = item.get("path", "")
                ref = item.get("ref", "")
                filename = os.path.basename(path)
                
                # Get file content
                content = await self._get_gitlab_file_content(project_id, path, ref)
                
                # Create metadata
                metadata = {
                    "project_id": project_id,
                    "path": path,
                    "ref": ref,
                    "name": filename,
                    "source": "gitlab"
                }
                
                # Create data item
                data_item = DataItem(
                    source_id=f"gitlab_code_{uuid.uuid4().hex[:8]}",
                    content=content or "",
                    metadata=metadata,
                    url=f"https://gitlab.com/api/v4/projects/{project_id}/repository/files/{quote_plus(path)}/raw?ref={ref}",
                    content_type=self._get_content_type(path),
                    raw_data=item
                )
                
                results.append(data_item)
            
            # Cache results if needed
            if cache_context.should_write():
                await self._save_to_cache("gitlab", query, params, results)
            
            logger.info(f"Collected {len(results)} items from GitLab code search")
            return results
            
        except Exception as e:
            logger.error(f"Error searching GitLab code: {e}")
            return []
    
    async def _get_gitlab_file_content(self, project_id: str, path: str, ref: str) -> Optional[str]:
        """Get the content of a file from GitLab."""
        try:
            # Construct GitLab API URL
            url = f"https://gitlab.com/api/v4/projects/{project_id}/repository/files/{quote_plus(path)}/raw"
            
            # Set up headers
            headers = {
                "PRIVATE-TOKEN": self.gitlab_token
            }
            
            # Set up parameters
            params = {
                "ref": ref
            }
            
            # Get file content
            content, _ = await self._make_request("gitlab", url, headers, params)
            
            # If content is already a string, return it
            if isinstance(content, str):
                return content
            
            # If content is bytes, decode it
            if isinstance(content, bytes):
                return content.decode("utf-8")
            
            return None
        except Exception as e:
            logger.error(f"Error getting GitLab file content for {project_id}/{path}: {e}")
            return None
    
    async def _search_bitbucket(self, params: Dict[str, Any]) -> List[DataItem]:
        """Search for code on Bitbucket."""
        query = params.get("query", "")
        max_results = params.get("max_results", 10)
        
        if not query:
            logger.error("No query provided for Bitbucket code search")
            return []
        
        if not self.bitbucket_token:
            logger.warning("No Bitbucket token provided. API functionality will be limited.")
            return []
        
        # Check cache first if enabled
        cache_mode = CacheMode[params.get("cache_mode", "ENABLED").upper()] if "cache_mode" in params else CacheMode.ENABLED
        cache_context = CacheContext(f"bitbucket:{query}", cache_mode)
        
        if cache_context.should_read():
            cached_results = await self._get_from_cache("bitbucket", query, params)
            if cached_results:
                return cached_results
        
        try:
            # Bitbucket Cloud API doesn't have a direct code search endpoint
            # We'll use the code search API for Bitbucket Server if available
            # Otherwise, we'll use a workaround for Bitbucket Cloud
            
            if params.get("server_url"):
                # Bitbucket Server implementation
                return await self._search_bitbucket_server(params)
            else:
                # Bitbucket Cloud implementation
                # This is a workaround since Bitbucket Cloud doesn't have a code search API
                # We'll search repositories and then search within each repository
                
                # First, search for repositories
                workspace = params.get("workspace")
                if not workspace:
                    logger.error("Workspace parameter is required for Bitbucket Cloud code search")
                    return []
                
                # Construct Bitbucket API URL for repository search
                url = f"https://api.bitbucket.org/2.0/repositories/{workspace}"
                
                # Set up headers
                headers = {
                    "Authorization": f"Bearer {self.bitbucket_token}",
                    "Accept": "application/json"
                }
                
                # Set up parameters
                api_params = {
                    "q": f"name ~ \"{query}\"",
                    "pagelen": min(max_results, 50)
                }
                
                # Execute repository search
                repo_data, _ = await self._make_request("bitbucket", url, headers, api_params)
                repos = repo_data.get("values", [])
                
                if not repos:
                    logger.info("No Bitbucket repositories found matching the query")
                    return []
                
                # Now search within each repository
                results = []
                for repo in repos[:5]:  # Limit to 5 repositories to avoid too many requests
                    repo_slug = repo.get("slug")
                    repo_name = repo.get("name")
                    
                    # Get repository contents
                    contents_url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/src"
                    
                    try:
                        contents_data, _ = await self._make_request("bitbucket", contents_url, headers)
                        
                        # Process files in the repository
                        await self._process_bitbucket_directory(
                            workspace, 
                            repo_slug, 
                            repo_name,
                            "", 
                            contents_data, 
                            query, 
                            results, 
                            max_depth=2  # Limit depth to avoid too many requests
                        )
                    except Exception as e:
                        logger.warning(f"Error processing repository {repo_name}: {e}")
                
                # Cache results if needed
                if cache_context.should_write():
                    await self._save_to_cache("bitbucket", query, params, results)
                
                logger.info(f"Collected {len(results)} items from Bitbucket code search")
                return results
                
        except Exception as e:
            logger.error(f"Error searching Bitbucket code: {e}")
            if isinstance(e, CodeSearchRateLimitError):
                # Re-raise rate limit errors for proper handling
                raise
            raise CodeSearchError(f"Bitbucket search error: {str(e)}", {
                "query": query,
                "service": "bitbucket"
            })
    
    async def _search_bitbucket_server(self, params: Dict[str, Any]) -> List[DataItem]:
        """Search for code on Bitbucket Server."""
        query = params.get("query", "")
        server_url = params.get("server_url")
        max_results = params.get("max_results", 10)
        
        # Construct Bitbucket Server API URL
        url = f"{server_url}/rest/api/1.0/search/code"
        
        # Set up headers
        headers = {
            "Authorization": f"Bearer {self.bitbucket_token}",
            "Accept": "application/json"
        }
        
        # Set up parameters
        api_params = {
            "query": query,
            "limit": min(max_results, 100)
        }
        
        # Add project filter if provided
        if "project" in params:
            api_params["project"] = params["project"]
        
        # Add repository filter if provided
        if "repository" in params:
            api_params["repository"] = params["repository"]
        
        # Execute search
        search_data, _ = await self._make_request("bitbucket", url, headers, api_params)
        
        # Process results
        results = []
        for item in search_data.get("values", []):
            file = item.get("file", {})
            path = file.get("path", "")
            repo = item.get("repository", {})
            project = repo.get("project", {})
            
            # Get file content
            content = await self._get_bitbucket_file_content(
                server_url,
                project.get("key", ""),
                repo.get("slug", ""),
                path
            )
            
            # Create metadata
            metadata = {
                "project": project.get("key", ""),
                "repository": repo.get("slug", ""),
                "path": path,
                "name": os.path.basename(path),
                "source": "bitbucket_server"
            }
            
            # Create data item
            data_item = DataItem(
                source_id=f"bitbucket_code_{uuid.uuid4().hex[:8]}",
                content=content or "",
                metadata=metadata,
                url=f"{server_url}/projects/{project.get('key', '')}/repos/{repo.get('slug', '')}/browse/{path}",
                content_type=self._get_content_type(path),
                raw_data=item
            )
            
            results.append(data_item)
        
        return results
    
    async def _process_bitbucket_directory(
        self, 
        workspace: str, 
        repo_slug: str, 
        repo_name: str,
        path: str, 
        contents_data: Dict[str, Any], 
        query: str, 
        results: List[DataItem], 
        max_depth: int = 2,
        current_depth: int = 0
    ) -> None:
        """Process a Bitbucket directory recursively to find matching files."""
        if current_depth > max_depth:
            return
        
        # Set up headers
        headers = {
            "Authorization": f"Bearer {self.bitbucket_token}",
            "Accept": "application/json"
        }
        
        for item in contents_data.get("values", []):
            item_type = item.get("type")
            item_path = item.get("path", "")
            
            if item_type == "commit_file":
                # This is a file, check if it matches the query
                try:
                    # Get file content
                    file_url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/src/master/{item_path}"
                    content, _ = await self._make_request("bitbucket", file_url, headers)
                    
                    # Check if content contains the query
                    if isinstance(content, str) and query.lower() in content.lower():
                        # Create metadata
                        metadata = {
                            "workspace": workspace,
                            "repository": repo_slug,
                            "repository_name": repo_name,
                            "path": item_path,
                            "name": os.path.basename(item_path),
                            "source": "bitbucket"
                        }
                        
                        # Create data item
                        data_item = DataItem(
                            source_id=f"bitbucket_code_{uuid.uuid4().hex[:8]}",
                            content=content,
                            metadata=metadata,
                            url=f"https://bitbucket.org/{workspace}/{repo_slug}/src/master/{item_path}",
                            content_type=self._get_content_type(item_path),
                            raw_data=item
                        )
                        
                        results.append(data_item)
                except Exception as e:
                    logger.debug(f"Error processing file {item_path}: {e}")
            
            elif item_type == "commit_directory" and current_depth < max_depth:
                # This is a directory, process it recursively
                try:
                    dir_url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/src/master/{item_path}"
                    dir_data, _ = await self._make_request("bitbucket", dir_url, headers)
                    
                    await self._process_bitbucket_directory(
                        workspace, 
                        repo_slug, 
                        repo_name,
                        item_path, 
                        dir_data, 
                        query, 
                        results, 
                        max_depth,
                        current_depth + 1
                    )
                except Exception as e:
                    logger.debug(f"Error processing directory {item_path}: {e}")
    
    async def _get_bitbucket_file_content(
        self, 
        server_url: Optional[str], 
        project: str, 
        repo: str, 
        path: str
    ) -> Optional[str]:
        """Get the content of a file from Bitbucket."""
        try:
            # Set up headers
            headers = {
                "Authorization": f"Bearer {self.bitbucket_token}",
                "Accept": "application/json"
            }
            
            if server_url:
                # Bitbucket Server
                url = f"{server_url}/rest/api/1.0/projects/{project}/repos/{repo}/raw/{path}"
            else:
                # Bitbucket Cloud
                url = f"https://api.bitbucket.org/2.0/repositories/{project}/{repo}/src/master/{path}"
            
            # Get file content
            content, _ = await self._make_request("bitbucket", url, headers)
            
            # If content is already a string, return it
            if isinstance(content, str):
                return content
            
            # If content is bytes, decode it
            if isinstance(content, bytes):
                return content.decode("utf-8")
            
            return None
        except Exception as e:
            logger.error(f"Error getting Bitbucket file content for {project}/{repo}/{path}: {e}")
            return None
    
    async def _search_sourcegraph(self, params: Dict[str, Any]) -> List[DataItem]:
        """Search for code on Sourcegraph."""
        query = params.get("query", "")
        max_results = params.get("max_results", 10)
        
        if not query:
            logger.error("No query provided for Sourcegraph code search")
            return []
        
        # Check cache first if enabled
        cache_mode = CacheMode[params.get("cache_mode", "ENABLED").upper()] if "cache_mode" in params else CacheMode.ENABLED
        cache_context = CacheContext(f"sourcegraph:{query}", cache_mode)
        
        if cache_context.should_read():
            cached_results = await self._get_from_cache("sourcegraph", query, params)
            if cached_results:
                return cached_results
        
        try:
            # Construct Sourcegraph GraphQL API URL
            url = f"{self.sourcegraph_url}/.api/graphql"
            
            # Set up headers
            headers = {}
            if self.sourcegraph_token:
                headers["Authorization"] = f"token {self.sourcegraph_token}"
            
            # Construct GraphQL query
            graphql_query = {
                "query": """
                query Search($query: String!, $limit: Int!) {
                    search(query: $query, version: V2) {
                        results(first: $limit) {
                            results {
                                ... on FileMatch {
                                    repository {
                                        name
                                    }
                                    file {
                                        path
                                        url
                                        content
                                    }
                                    lineMatches {
                                        lineNumber
                                        offsetAndLengths
                                        preview
                                    }
                                }
                            }
                        }
                    }
                }
                """,
                "variables": {
                    "query": query,
                    "limit": max_results
                }
            }
            
            # Execute search
            async with self.semaphore:
                async with self.session.post(url, json=graphql_query, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise CodeSearchError(
                            f"Sourcegraph API error: {response.status}",
                            details={
                                "status_code": response.status,
                                "error_text": error_text
                            }
                        )
                    
                    data = await response.json()
                    results_data = data.get("data", {}).get("search", {}).get("results", {}).get("results", [])
                    
                    if not results_data:
                        logger.info("No Sourcegraph code search results found")
                        return []
            
            # Process results
            results = []
            for item in results_data:
                # Extract metadata
                repo_name = item.get("repository", {}).get("name", "")
                file_data = item.get("file", {})
                path = file_data.get("path", "")
                url = file_data.get("url", "")
                content = file_data.get("content", "")
                line_matches = item.get("lineMatches", [])
                
                # Create metadata
                metadata = {
                    "repo": repo_name,
                    "path": path,
                    "name": os.path.basename(path),
                    "url": url,
                    "line_matches": [
                        {
                            "line_number": match.get("lineNumber"),
                            "preview": match.get("preview")
                        }
                        for match in line_matches
                    ],
                    "source": "sourcegraph"
                }
                
                # Create data item
                data_item = DataItem(
                    source_id=f"sourcegraph_code_{uuid.uuid4().hex[:8]}",
                    content=content or "",
                    metadata=metadata,
                    url=url,
                    content_type=self._get_content_type(path),
                    raw_data=item
                )
                
                results.append(data_item)
            
            # Cache results if needed
            if cache_context.should_write():
                await self._save_to_cache("sourcegraph", query, params, results)
            
            logger.info(f"Collected {len(results)} items from Sourcegraph code search")
            return results
            
        except Exception as e:
            logger.error(f"Error searching Sourcegraph code: {e}")
            if isinstance(e, CodeSearchRateLimitError):
                # Re-raise rate limit errors for proper handling
                raise
            raise CodeSearchError(f"Sourcegraph search error: {str(e)}", {
                "query": query,
                "service": "sourcegraph"
            })
    
    def _get_content_type(self, path: str) -> str:
        """Determine the content type based on the file extension."""
        ext = os.path.splitext(path)[1].lower()
        
        # Map of file extensions to MIME types
        mime_types = {
            ".py": "text/x-python",
            ".js": "text/javascript",
            ".jsx": "text/javascript",
            ".ts": "text/typescript",
            ".tsx": "text/typescript",
            ".html": "text/html",
            ".htm": "text/html",
            ".css": "text/css",
            ".scss": "text/css",
            ".sass": "text/css",
            ".less": "text/css",
            ".json": "application/json",
            ".xml": "application/xml",
            ".md": "text/markdown",
            ".markdown": "text/markdown",
            ".java": "text/x-java",
            ".c": "text/x-c",
            ".cpp": "text/x-c++",
            ".h": "text/x-c",
            ".hpp": "text/x-c++",
            ".go": "text/x-go",
            ".rb": "text/x-ruby",
            ".php": "text/x-php",
            ".rs": "text/x-rust",
            ".swift": "text/x-swift",
            ".kt": "text/x-kotlin",
            ".kts": "text/x-kotlin",
            ".dart": "text/x-dart",
            ".sh": "text/x-shellscript",
            ".bash": "text/x-shellscript",
            ".yaml": "text/x-yaml",
            ".yml": "text/x-yaml",
            ".toml": "text/x-toml",
            ".sql": "text/x-sql",
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".graphql": "text/x-graphql",
            ".proto": "text/x-protobuf",
            ".vue": "text/x-vue",
            ".svelte": "text/x-svelte",
            ".tf": "text/x-terraform",
            ".hcl": "text/x-hcl",
            ".dockerfile": "text/x-dockerfile",
            ".r": "text/x-r",
            ".scala": "text/x-scala",
            ".clj": "text/x-clojure",
            ".ex": "text/x-elixir",
            ".exs": "text/x-elixir",
            ".erl": "text/x-erlang",
            ".hs": "text/x-haskell",
            ".lua": "text/x-lua",
            ".pl": "text/x-perl",
            ".ps1": "text/x-powershell",
            ".groovy": "text/x-groovy",
            ".gradle": "text/x-gradle",
            ".ini": "text/x-ini",
            ".cfg": "text/x-ini",
            ".conf": "text/x-ini"
        }
        
        return mime_types.get(ext, "text/plain")
    
    async def search(self, query: str, **kwargs) -> List[DataItem]:
        """
        Search for code across configured sources.
        
        This is a convenience method that wraps the collect method.
        
        Args:
            query: Search query string
            **kwargs: Additional parameters:
                - sources: List of sources to search (default: ["github", "sourcegraph"])
                - max_results: Maximum number of results to return per source
                - language: Programming language filter
                - cache_mode: Caching mode (ENABLED, DISABLED, READ_ONLY, WRITE_ONLY)
                - timeout: Request timeout in seconds
                
        Returns:
            List of DataItem objects containing search results
        """
        params = {
            "query": query,
            **kwargs
        }
        
        return await self.collect(params)
    
    async def get_file_content(self, url: str, **kwargs) -> Optional[str]:
        """
        Get the content of a file from a URL.
        
        Args:
            url: URL of the file
            **kwargs: Additional parameters
                
        Returns:
            File content as a string, or None if the file could not be retrieved
        """
        try:
            # Create session if needed
            await self._create_session()
            
            # Determine the service from the URL
            service = None
            if "github.com" in url:
                service = "github"
                return await self._get_github_file_content_from_url(url)
            elif "gitlab.com" in url:
                service = "gitlab"
                return await self._get_gitlab_file_content_from_url(url)
            elif "bitbucket.org" in url:
                service = "bitbucket"
                return await self._get_bitbucket_file_content_from_url(url)
            elif "sourcegraph.com" in url or self.sourcegraph_url in url:
                service = "sourcegraph"
                return await self._get_sourcegraph_file_content_from_url(url)
            else:
                # Generic URL handling
                headers = {}
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.error(f"Error getting file content from {url}: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting file content from {url}: {e}")
            return None
        finally:
            # Don't close the session here, as it might be used by other operations
            pass
    
    async def _get_github_file_content_from_url(self, url: str) -> Optional[str]:
        """Get file content from a GitHub URL."""
        try:
            # Extract owner, repo, and path from GitHub URL
            match = re.search(r'github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)', url)
            if not match:
                logger.error(f"Invalid GitHub file URL: {url}")
                return None
                
            owner, repo, branch, path = match.groups()
            
            # Get file content using the API
            return await self._get_github_file_content(f"{owner}/{repo}", path)
        except Exception as e:
            logger.error(f"Error getting GitHub file content from URL {url}: {e}")
            return None
    
    async def _get_gitlab_file_content_from_url(self, url: str) -> Optional[str]:
        """Get file content from a GitLab URL."""
        try:
            # Extract project path and file path from GitLab URL
            match = re.search(r'gitlab\.com/([^/]+/[^/]+)/-/blob/([^/]+)/(.+)', url)
            if not match:
                logger.error(f"Invalid GitLab file URL: {url}")
                return None
                
            project_path, branch, file_path = match.groups()
            
            # Get project ID
            project_id = await self._get_gitlab_project_id(project_path)
            if not project_id:
                logger.error(f"Could not get project ID for {project_path}")
                return None
            
            # Get file content
            return await self._get_gitlab_file_content(project_id, file_path, branch)
        except Exception as e:
            logger.error(f"Error getting GitLab file content from URL {url}: {e}")
            return None
    
    async def _get_gitlab_project_id(self, project_path: str) -> Optional[str]:
        """Get GitLab project ID from project path."""
        try:
            # Construct GitLab API URL
            url = f"https://gitlab.com/api/v4/projects/{quote_plus(project_path)}"
            
            # Set up headers
            headers = {
                "PRIVATE-TOKEN": self.gitlab_token
            }
            
            # Get project data
            project_data, _ = await self._make_request("gitlab", url, headers)
            
            return str(project_data.get("id"))
        except Exception as e:
            logger.error(f"Error getting GitLab project ID for {project_path}: {e}")
            return None
    
    async def _get_bitbucket_file_content_from_url(self, url: str) -> Optional[str]:
        """Get file content from a Bitbucket URL."""
        try:
            # Extract workspace, repo, and path from Bitbucket URL
            match = re.search(r'bitbucket\.org/([^/]+)/([^/]+)/src/([^/]+)/(.+)', url)
            if not match:
                logger.error(f"Invalid Bitbucket file URL: {url}")
                return None
                
            workspace, repo, branch, path = match.groups()
            
            # Get file content
            return await self._get_bitbucket_file_content(None, workspace, repo, path)
        except Exception as e:
            logger.error(f"Error getting Bitbucket file content from URL {url}: {e}")
            return None
    
    async def _get_sourcegraph_file_content_from_url(self, url: str) -> Optional[str]:
        """Get file content from a Sourcegraph URL."""
        try:
            # Extract repository and path from Sourcegraph URL
            # This is more complex due to Sourcegraph's URL structure
            # We'll make a direct request to the URL
            headers = {}
            if self.sourcegraph_token:
                headers["Authorization"] = f"token {self.sourcegraph_token}"
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"Error getting Sourcegraph file content from {url}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting Sourcegraph file content from URL {url}: {e}")
            return None
