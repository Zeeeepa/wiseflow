"""
Code Search connector for Wiseflow.

This module provides a connector for searching and retrieving code from various sources.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import uuid
import asyncio
from datetime import datetime
import os
import re
import json
import tempfile
from urllib.parse import urlparse, quote_plus

import aiohttp
import requests

from core.connectors import ConnectorBase, DataItem
from .config import ConfigManager
from .cache import CacheManager
from .errors import (
    CodeSearchError, ServiceError, AuthenticationError, RateLimitError,
    ResourceNotFoundError, InvalidRequestError, NetworkError, TimeoutError,
    ServerError, async_handle_service_errors, async_retry_on_error
)
from .services import get_service

logger = logging.getLogger(__name__)

class CodeSearchConnector(ConnectorBase):
    """Connector for code search."""
    
    name: str = "code_search_connector"
    description: str = "Connector for searching and retrieving code from various sources"
    source_type: str = "code_search"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the code search connector."""
        super().__init__(config or {})
        
        # Initialize configuration
        self.config_manager = ConfigManager(config)
        self.config = self.config_manager.get_config()
        
        # Initialize cache
        self.cache_manager = CacheManager({
            "cache_enabled": self.config.cache_enabled,
            "cache_dir": self.config.cache_dir,
            "memory_cache_size": self.config.memory_cache_size,
            "disk_cache_size": self.config.disk_cache_size
        })
        
        # Initialize services
        self.services = {}
        self.semaphore = asyncio.Semaphore(self.config.concurrency)
        self.session = None
    
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
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _close_session(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def _get_service(self, service_name: str) -> Any:
        """
        Get a service adapter instance.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service adapter instance
        """
        if service_name not in self.services:
            # Get service configuration
            service_config = self.config_manager.get_service_config(service_name)
            
            # Create service instance
            service = get_service(service_name, service_config.__dict__)
            if service:
                # Set cache manager
                service.cache_manager = self.cache_manager
                self.services[service_name] = service
            else:
                raise InvalidRequestError(f"Unsupported service: {service_name}")
        
        return self.services[service_name]
    
    @async_handle_service_errors
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from code search sources."""
        params = params or {}
        
        try:
            # Create session
            await self._create_session()
            
            # Determine what to collect
            if "source" in params:
                source = params["source"].lower()
                return await self._search_source(source, params)
            elif "query" in params:
                # Search across all configured sources
                return await self._search_all_sources(params)
            else:
                logger.error("No source or query parameter provided for code search connector")
                return []
        finally:
            # Close session
            await self._close_session()
    
    async def _search_source(self, source: str, params: Dict[str, Any]) -> List[DataItem]:
        """
        Search for code in a specific source.
        
        Args:
            source: Source name
            params: Search parameters
            
        Returns:
            List[DataItem]: Search results
        """
        query = params.get("query", "")
        if not query:
            logger.error(f"No query provided for {source} code search")
            return []
        
        try:
            # Get service adapter
            service = await self._get_service(source)
            
            # Execute search with rate limiting
            async with self.semaphore:
                search_results = await service.search_code(query, **params)
            
            # Process results
            return await self._process_search_results(source, search_results, params)
        except Exception as e:
            logger.error(f"Error searching {source} code: {e}")
            return []
    
    async def _search_all_sources(self, params: Dict[str, Any]) -> List[DataItem]:
        """
        Search for code across all configured sources.
        
        Args:
            params: Search parameters
            
        Returns:
            List[DataItem]: Search results
        """
        query = params.get("query", "")
        if not query:
            logger.error("No query provided for code search")
            return []
        
        # Determine which sources to search
        sources = params.get("sources", [self.config.default_service])
        
        # Execute searches in parallel
        tasks = []
        for source in sources:
            source_params = params.copy()
            source_params["source"] = source
            tasks.append(self._search_source(source, source_params))
        
        # Gather results
        results = []
        if tasks:
            search_results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in search_results:
                if isinstance(result, Exception):
                    logger.error(f"Error in code search: {result}")
                else:
                    results.extend(result)
        
        return results
    
    async def _process_search_results(
        self, 
        source: str, 
        search_results: Dict[str, Any],
        params: Dict[str, Any]
    ) -> List[DataItem]:
        """
        Process search results into DataItems.
        
        Args:
            source: Source name
            search_results: Search results from the service
            params: Search parameters
            
        Returns:
            List[DataItem]: Processed search results
        """
        results = []
        
        # Process based on source
        if source == "github":
            items = search_results.get("items", [])
            
            for item in items:
                # Extract metadata
                repo_name = item.get("repository", {}).get("full_name", "")
                path = item.get("path", "")
                name = item.get("name", "")
                url = item.get("html_url", "")
                
                # Get file content if requested
                content = ""
                if params.get("include_content", False):
                    try:
                        service = await self._get_service(source)
                        content = await service.get_file_content(url)
                    except Exception as e:
                        logger.warning(f"Error getting file content for {url}: {e}")
                
                # Create metadata
                metadata = {
                    "repo": repo_name,
                    "path": path,
                    "name": name,
                    "url": url,
                    "source": source
                }
                
                # Create data item
                item = DataItem(
                    source_id=f"{source}_code_{uuid.uuid4().hex[:8]}",
                    content=content,
                    metadata=metadata,
                    url=url,
                    content_type=self._get_content_type(path),
                    raw_data=item
                )
                
                results.append(item)
        
        elif source == "gitlab":
            items = search_results
            
            for item in items:
                # Extract metadata
                project_id = item.get("project_id", "")
                path = item.get("path", "")
                ref = item.get("ref", "")
                filename = os.path.basename(path)
                
                # Create URL
                url = f"https://gitlab.com/api/v4/projects/{project_id}/repository/files/{quote_plus(path)}/raw?ref={ref}"
                
                # Get file content if requested
                content = ""
                if params.get("include_content", False):
                    try:
                        service = await self._get_service(source)
                        content = await service.get_file_content(url)
                    except Exception as e:
                        logger.warning(f"Error getting file content for {url}: {e}")
                
                # Create metadata
                metadata = {
                    "project_id": project_id,
                    "path": path,
                    "ref": ref,
                    "name": filename,
                    "url": url,
                    "source": source
                }
                
                # Create data item
                item = DataItem(
                    source_id=f"{source}_code_{uuid.uuid4().hex[:8]}",
                    content=content,
                    metadata=metadata,
                    url=url,
                    content_type=self._get_content_type(path),
                    raw_data=item
                )
                
                results.append(item)
        
        elif source == "bitbucket":
            items = search_results.get("values", [])
            
            for item in items:
                # Extract metadata
                path = item.get("path", "")
                name = os.path.basename(path)
                url = item.get("links", {}).get("self", {}).get("href", "")
                
                # Get file content if requested
                content = ""
                if params.get("include_content", False):
                    try:
                        service = await self._get_service(source)
                        content = await service.get_file_content(url)
                    except Exception as e:
                        logger.warning(f"Error getting file content for {url}: {e}")
                
                # Create metadata
                metadata = {
                    "path": path,
                    "name": name,
                    "url": url,
                    "source": source
                }
                
                # Create data item
                item = DataItem(
                    source_id=f"{source}_code_{uuid.uuid4().hex[:8]}",
                    content=content,
                    metadata=metadata,
                    url=url,
                    content_type=self._get_content_type(path),
                    raw_data=item
                )
                
                results.append(item)
        
        elif source == "sourcegraph":
            try:
                items = search_results.get("data", {}).get("search", {}).get("results", {}).get("results", [])
                
                for item in items:
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
                        "source": source
                    }
                    
                    # Create data item
                    item = DataItem(
                        source_id=f"{source}_code_{uuid.uuid4().hex[:8]}",
                        content=content,
                        metadata=metadata,
                        url=url,
                        content_type=self._get_content_type(path),
                        raw_data=item
                    )
                    
                    results.append(item)
            except (KeyError, TypeError) as e:
                logger.error(f"Error processing Sourcegraph results: {e}")
        
        elif source == "searchcode":
            items = search_results.get("results", [])
            
            for item in items:
                # Extract metadata
                repo = item.get("repo", "")
                path = item.get("path", "")
                filename = item.get("filename", "")
                url = item.get("url", "")
                
                # Get file content if requested
                content = ""
                if params.get("include_content", False):
                    try:
                        service = await self._get_service(source)
                        content = await service.get_file_content(url)
                    except Exception as e:
                        logger.warning(f"Error getting file content for {url}: {e}")
                
                # Create metadata
                metadata = {
                    "repo": repo,
                    "path": path,
                    "name": filename,
                    "url": url,
                    "source": source
                }
                
                # Create data item
                item = DataItem(
                    source_id=f"{source}_code_{uuid.uuid4().hex[:8]}",
                    content=content,
                    metadata=metadata,
                    url=url,
                    content_type=self._get_content_type(path),
                    raw_data=item
                )
                
                results.append(item)
        
        logger.info(f"Collected {len(results)} items from {source} code search")
        return results
    
    def _get_content_type(self, path: str) -> str:
        """
        Determine the content type based on the file extension.
        
        Args:
            path: File path
            
        Returns:
            str: Content type
        """
        ext = os.path.splitext(path)[1].lower()
        
        if ext in [".py"]:
            return "text/x-python"
        elif ext in [".js"]:
            return "text/javascript"
        elif ext in [".ts"]:
            return "text/typescript"
        elif ext in [".html", ".htm"]:
            return "text/html"
        elif ext in [".css"]:
            return "text/css"
        elif ext in [".json"]:
            return "application/json"
        elif ext in [".xml"]:
            return "application/xml"
        elif ext in [".md", ".markdown"]:
            return "text/markdown"
        elif ext in [".java"]:
            return "text/x-java"
        elif ext in [".c", ".cpp", ".h", ".hpp"]:
            return "text/x-c"
        elif ext in [".go"]:
            return "text/x-go"
        elif ext in [".rb"]:
            return "text/x-ruby"
        elif ext in [".php"]:
            return "text/x-php"
        elif ext in [".rs"]:
            return "text/x-rust"
        elif ext in [".swift"]:
            return "text/x-swift"
        elif ext in [".kt", ".kts"]:
            return "text/x-kotlin"
        elif ext in [".dart"]:
            return "text/x-dart"
        elif ext in [".sh", ".bash"]:
            return "text/x-shellscript"
        elif ext in [".yaml", ".yml"]:
            return "text/x-yaml"
        elif ext in [".toml"]:
            return "text/x-toml"
        elif ext in [".sql"]:
            return "text/x-sql"
        elif ext in [".txt"]:
            return "text/plain"
        else:
            return "text/plain"
"""

