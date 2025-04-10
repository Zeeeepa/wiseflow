"""
GitHub connector for Wiseflow.

This module provides a connector for GitHub repositories.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import uuid
import asyncio
from datetime import datetime
import os
import re
import base64
from urllib.parse import urlparse

import aiohttp

from core.plugins import PluginBase
from core.connectors import ConnectorBase, DataItem

logger = logging.getLogger(__name__)

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
        
    def initialize(self) -> bool:
        """Initialize the connector."""
        try:
            if not self.api_token:
                logger.warning("No GitHub API token provided. Rate limits will be restricted.")
            
            logger.info("Initialized GitHub connector")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize GitHub connector: {e}")
            return False
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from GitHub repositories."""
        params = params or {}
        
        # Create a session for API requests
        self.session = aiohttp.ClientSession()
        
        try:
            # Determine what to collect
            if "repo" in params:
                # Collect data from a specific repository
                repo = params["repo"]
                return await self._collect_repo(repo, params)
            elif "user" in params:
                # Collect data from a user's repositories
                user = params["user"]
                return await self._collect_user_repos(user, params)
            elif "search" in params:
                # Search for repositories
                query = params["search"]
                return await self._search_repos(query, params)
            else:
                logger.error("No repository, user, or search query provided for GitHub connector")
                return []
        finally:
            # Close the session
            await self.session.close()
            self.session = None
    
    async def _collect_repo(self, repo: str, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from a specific repository."""
        results = []
        
        # Determine what to collect from the repository
        collect_readme = params.get("collect_readme", True)
        collect_files = params.get("collect_files", False)
        collect_issues = params.get("collect_issues", False)
        collect_commits = params.get("collect_commits", False)
        max_files = params.get("max_files", 10)
        max_issues = params.get("max_issues", 10)
        max_commits = params.get("max_commits", 10)
        
        # Get repository information
        repo_info = await self._get_repo_info(repo)
        if not repo_info:
            return []
        
        # Collect README
        if collect_readme:
            readme = await self._get_repo_readme(repo)
            if readme:
                item = DataItem(
                    source_id=f"github_readme_{uuid.uuid4().hex[:8]}",
                    content=readme["content"],
                    metadata={
                        "repo": repo,
                        "path": readme["path"],
                        "type": "readme",
                        "sha": readme.get("sha", ""),
                        "repo_info": repo_info
                    },
                    url=f"https://github.com/{repo}",
                    content_type="text/markdown",
                    timestamp=datetime.now()
                )
                results.append(item)
        
        # Collect files
        if collect_files:
            files = await self._get_repo_files(repo, max_files=max_files)
            for file in files:
                if file.get("content"):
                    item = DataItem(
                        source_id=f"github_file_{uuid.uuid4().hex[:8]}",
                        content=file["content"],
                        metadata={
                            "repo": repo,
                            "path": file["path"],
                            "type": "file",
                            "sha": file.get("sha", ""),
                            "size": file.get("size", 0),
                            "repo_info": repo_info
                        },
                        url=f"https://github.com/{repo}/blob/master/{file['path']}",
                        content_type=self._get_content_type(file["path"]),
                        timestamp=datetime.now()
                    )
                    results.append(item)
        
        # Collect issues
        if collect_issues:
            issues = await self._get_repo_issues(repo, max_issues=max_issues)
            for issue in issues:
                item = DataItem(
                    source_id=f"github_issue_{uuid.uuid4().hex[:8]}",
                    content=issue["body"],
                    metadata={
                        "repo": repo,
                        "issue_number": issue["number"],
                        "title": issue["title"],
                        "state": issue["state"],
                        "user": issue["user"]["login"],
                        "created_at": issue["created_at"],
                        "updated_at": issue["updated_at"],
                        "comments": issue["comments"],
                        "type": "issue",
                        "repo_info": repo_info
                    },
                    url=issue["html_url"],
                    content_type="text/markdown",
                    timestamp=datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
                )
                results.append(item)
        
        # Collect commits
        if collect_commits:
            commits = await self._get_repo_commits(repo, max_commits=max_commits)
            for commit in commits:
                commit_info = commit["commit"]
                item = DataItem(
                    source_id=f"github_commit_{uuid.uuid4().hex[:8]}",
                    content=commit_info["message"],
                    metadata={
                        "repo": repo,
                        "sha": commit["sha"],
                        "author": commit_info["author"]["name"],
                        "author_email": commit_info["author"]["email"],
                        "committer": commit_info["committer"]["name"],
                        "committer_email": commit_info["committer"]["email"],
                        "date": commit_info["author"]["date"],
                        "type": "commit",
                        "repo_info": repo_info
                    },
                    url=commit["html_url"],
                    content_type="text/plain",
                    timestamp=datetime.fromisoformat(commit_info["author"]["date"].replace("Z", "+00:00"))
                )
                results.append(item)
        
        return results
    
    async def _collect_user_repos(self, user: str, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from a user's repositories."""
        results = []
        
        # Get user's repositories
        repos = await self._get_user_repos(user)
        
        # Collect data from each repository
        tasks = []
        for repo in repos[:params.get("max_repos", 5)]:
            repo_name = repo["full_name"]
            tasks.append(self._collect_repo(repo_name, params))
        
        # Gather results
        repo_results = await asyncio.gather(*tasks)
        for items in repo_results:
            results.extend(items)
        
        return results
    
    async def _search_repos(self, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """Search for repositories and collect data."""
        results = []
        
        # Search for repositories
        repos = await self._search_github_repos(query, max_results=params.get("max_results", 5))
        
        # Collect data from each repository
        tasks = []
        for repo in repos:
            repo_name = repo["full_name"]
            tasks.append(self._collect_repo(repo_name, params))
        
        # Gather results
        repo_results = await asyncio.gather(*tasks)
        for items in repo_results:
            results.extend(items)
        
        return results
    
    async def _get_repo_info(self, repo: str) -> Optional[Dict[str, Any]]:
        """Get information about a repository."""
        async with self.semaphore:
            try:
                url = f"{self.api_base_url}/repos/{repo}"
                headers = self._get_headers()
                
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to get repository info for {repo}: {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Error getting repository info for {repo}: {e}")
                return None
    
    async def _get_repo_readme(self, repo: str) -> Optional[Dict[str, Any]]:
        """Get the README file of a repository."""
        async with self.semaphore:
            try:
                url = f"{self.api_base_url}/repos/{repo}/readme"
                headers = self._get_headers()
                
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = base64.b64decode(data["content"]).decode("utf-8")
                        return {
                            "path": data["path"],
                            "sha": data["sha"],
                            "content": content
                        }
                    else:
                        logger.warning(f"Failed to get README for {repo}: {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Error getting README for {repo}: {e}")
                return None
    
    async def _get_repo_files(self, repo: str, path: str = "", max_files: int = 10) -> List[Dict[str, Any]]:
        """Get files from a repository."""
        async with self.semaphore:
            try:
                url = f"{self.api_base_url}/repos/{repo}/contents/{path}"
                headers = self._get_headers()
                
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        items = await response.json()
                        
                        # Filter out directories and large files
                        files = []
                        for item in items:
                            if item["type"] == "file" and item["size"] < 100000:  # Skip files larger than 100KB
                                # Get file content
                                file_content = await self._get_file_content(repo, item["path"])
                                if file_content:
                                    item["content"] = file_content
                                    files.append(item)
                                
                                if len(files) >= max_files:
                                    break
                        
                        return files
                    else:
                        logger.warning(f"Failed to get files for {repo}/{path}: {response.status}")
                        return []
            except Exception as e:
                logger.error(f"Error getting files for {repo}/{path}: {e}")
                return []
    
    async def _get_file_content(self, repo: str, path: str) -> Optional[str]:
        """Get the content of a file."""
        async with self.semaphore:
            try:
                url = f"{self.api_base_url}/repos/{repo}/contents/{path}"
                headers = self._get_headers()
                
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("content"):
                            return base64.b64decode(data["content"]).decode("utf-8")
                        else:
                            logger.warning(f"No content found for {repo}/{path}")
                            return None
                    else:
                        logger.warning(f"Failed to get content for {repo}/{path}: {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Error getting content for {repo}/{path}: {e}")
                return None
    
    async def _get_repo_issues(self, repo: str, max_issues: int = 10) -> List[Dict[str, Any]]:
        """Get issues from a repository."""
        async with self.semaphore:
            try:
                url = f"{self.api_base_url}/repos/{repo}/issues"
                headers = self._get_headers()
                params = {
                    "state": "all",
                    "per_page": max_issues
                }
                
                async with self.session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"Failed to get issues for {repo}: {response.status}")
                        return []
            except Exception as e:
                logger.error(f"Error getting issues for {repo}: {e}")
                return []
    
    async def _get_repo_commits(self, repo: str, max_commits: int = 10) -> List[Dict[str, Any]]:
        """Get commits from a repository."""
        async with self.semaphore:
            try:
                url = f"{self.api_base_url}/repos/{repo}/commits"
                headers = self._get_headers()
                params = {
                    "per_page": max_commits
                }
                
                async with self.session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"Failed to get commits for {repo}: {response.status}")
                        return []
            except Exception as e:
                logger.error(f"Error getting commits for {repo}: {e}")
                return []
    
    async def _get_user_repos(self, user: str) -> List[Dict[str, Any]]:
        """Get repositories from a user."""
        async with self.semaphore:
            try:
                url = f"{self.api_base_url}/users/{user}/repos"
                headers = self._get_headers()
                params = {
                    "sort": "updated",
                    "direction": "desc",
                    "per_page": 100
                }
                
                async with self.session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"Failed to get repositories for user {user}: {response.status}")
                        return []
            except Exception as e:
                logger.error(f"Error getting repositories for user {user}: {e}")
                return []
    
    async def _search_github_repos(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for repositories on GitHub."""
        async with self.semaphore:
            try:
                url = f"{self.api_base_url}/search/repositories"
                headers = self._get_headers()
                params = {
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": max_results
                }
                
                async with self.session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("items", [])
                    else:
                        logger.warning(f"Failed to search repositories with query '{query}': {response.status}")
                        return []
            except Exception as e:
                logger.error(f"Error searching repositories with query '{query}': {e}")
                return []
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Wiseflow-GitHub-Connector"
        }
        
        if self.api_token:
            headers["Authorization"] = f"token {self.api_token}"
        
        return headers
    
    def _get_content_type(self, path: str) -> str:
        """Get the content type based on file extension."""
        ext = os.path.splitext(path)[1].lower()
        
        if ext in [".md", ".markdown"]:
            return "text/markdown"
        elif ext in [".py"]:
            return "text/python"
        elif ext in [".js"]:
            return "text/javascript"
        elif ext in [".html", ".htm"]:
            return "text/html"
        elif ext in [".css"]:
            return "text/css"
        elif ext in [".json"]:
            return "application/json"
        elif ext in [".xml"]:
            return "application/xml"
        elif ext in [".yaml", ".yml"]:
            return "application/yaml"
        elif ext in [".txt"]:
            return "text/plain"
        else:
            return "text/plain"
