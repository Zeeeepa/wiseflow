"""
GitHub connector for Wiseflow.

This module provides a connector for GitHub repositories, issues, and pull requests.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import uuid
import asyncio
from datetime import datetime
import os
import re
import json
import aiohttp
from urllib.parse import quote_plus

from core.connectors import ConnectorBase, DataItem
from core.utils.general_utils import extract_and_convert_dates

logger = logging.getLogger(__name__)

class GitHubConnector(ConnectorBase):
    """Connector for GitHub repositories, issues, and pull requests."""
    
    name: str = "github_connector"
    description: str = "Connector for GitHub repositories, issues, and pull requests"
    source_type: str = "github"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the GitHub connector."""
        super().__init__(config)
        self.config = config or {}
        self.api_token = self.config.get("github_token")
        self.semaphore = asyncio.Semaphore(self.config.get("concurrency", 3))
        
    def initialize(self) -> bool:
        """Initialize the connector."""
        try:
            # Check if token is provided
            if not self.api_token:
                logger.warning("No GitHub API token provided. Rate limits will be restricted.")
            else:
                logger.info("GitHub API token provided.")
                
            logger.info(f"Initialized GitHub connector with config: {self.config}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize GitHub connector: {e}")
            return False
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from GitHub."""
        params = params or {}
        
        # Get collection parameters
        collection_type = params.get("collection_type", "repository")
        owner = params.get("owner", "")
        repo = params.get("repo", "")
        
        if not owner:
            logger.error("No owner provided for GitHub connector")
            return []
        
        # Process based on collection type
        if collection_type == "repository":
            if not repo:
                return await self._list_repositories(owner, params)
            else:
                return await self._get_repository(owner, repo, params)
        elif collection_type == "issues":
            if not repo:
                logger.error("No repository provided for GitHub issues")
                return []
            return await self._get_issues(owner, repo, params)
        elif collection_type == "pull_requests":
            if not repo:
                logger.error("No repository provided for GitHub pull requests")
                return []
            return await self._get_pull_requests(owner, repo, params)
        else:
            logger.error(f"Unknown GitHub collection type: {collection_type}")
            return []
    
    async def _list_repositories(self, owner: str, params: Dict[str, Any]) -> List[DataItem]:
        """List repositories for a user or organization."""
        async with self.semaphore:
            try:
                logger.info(f"Listing repositories for {owner}")
                
                # Construct GitHub API URL
                url = f"https://api.github.com/users/{owner}/repos"
                
                # Set up parameters
                per_page = params.get("per_page", 30)
                page = params.get("page", 1)
                sort = params.get("sort", "updated")
                direction = params.get("direction", "desc")
                
                # Add query parameters
                url += f"?per_page={per_page}&page={page}&sort={sort}&direction={direction}"
                
                # Set up headers
                headers = {
                    "Accept": "application/vnd.github.v3+json"
                }
                if self.api_token:
                    headers["Authorization"] = f"token {self.api_token}"
                
                # Make the request
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            logger.error(f"GitHub API error: {response.status}")
                            return []
                        
                        repos_data = await response.json()
                
                # Process repositories
                results = []
                for repo_data in repos_data:
                    # Extract repository information
                    repo_name = repo_data.get("name", "")
                    repo_description = repo_data.get("description", "")
                    repo_url = repo_data.get("html_url", "")
                    repo_stars = repo_data.get("stargazers_count", 0)
                    repo_forks = repo_data.get("forks_count", 0)
                    repo_language = repo_data.get("language", "")
                    repo_created = repo_data.get("created_at", "")
                    repo_updated = repo_data.get("updated_at", "")
                    
                    # Create content
                    content = f"# {repo_name}\n\n"
                    if repo_description:
                        content += f"{repo_description}\n\n"
                    content += f"**URL**: {repo_url}\n"
                    content += f"**Stars**: {repo_stars}\n"
                    content += f"**Forks**: {repo_forks}\n"
                    if repo_language:
                        content += f"**Language**: {repo_language}\n"
                    content += f"**Created**: {repo_created}\n"
                    content += f"**Updated**: {repo_updated}\n"
                    
                    # Create metadata
                    metadata = {
                        "name": repo_name,
                        "description": repo_description,
                        "url": repo_url,
                        "stars": repo_stars,
                        "forks": repo_forks,
                        "language": repo_language,
                        "created_at": repo_created,
                        "updated_at": repo_updated,
                        "owner": owner
                    }
                    
                    # Create data item
                    item = DataItem(
                        source_id=f"github_repo_{owner}_{repo_name}",
                        content=content,
                        metadata=metadata,
                        url=repo_url,
                        content_type="text/markdown",
                        language="en"
                    )
                    
                    results.append(item)
                
                logger.info(f"Collected {len(results)} repositories for {owner}")
                return results
            except Exception as e:
                logger.error(f"Error listing GitHub repositories: {e}")
                return []
    
    async def _get_repository(self, owner: str, repo: str, params: Dict[str, Any]) -> List[DataItem]:
        """Get detailed information about a specific repository."""
        async with self.semaphore:
            try:
                logger.info(f"Getting repository {owner}/{repo}")
                
                # Construct GitHub API URL
                url = f"https://api.github.com/repos/{owner}/{repo}"
                
                # Set up headers
                headers = {
                    "Accept": "application/vnd.github.v3+json"
                }
                if self.api_token:
                    headers["Authorization"] = f"token {self.api_token}"
                
                # Make the request
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            logger.error(f"GitHub API error: {response.status}")
                            return []
                        
                        repo_data = await response.json()
                
                # Extract repository information
                repo_name = repo_data.get("name", "")
                repo_description = repo_data.get("description", "")
                repo_url = repo_data.get("html_url", "")
                repo_stars = repo_data.get("stargazers_count", 0)
                repo_forks = repo_data.get("forks_count", 0)
                repo_language = repo_data.get("language", "")
                repo_created = repo_data.get("created_at", "")
                repo_updated = repo_data.get("updated_at", "")
                repo_topics = repo_data.get("topics", [])
                repo_license = repo_data.get("license", {}).get("name", "")
                repo_open_issues = repo_data.get("open_issues_count", 0)
                repo_default_branch = repo_data.get("default_branch", "main")
                
                # Get README content if requested
                readme_content = ""
                if params.get("include_readme", True):
                    readme_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(readme_url, headers=headers) as response:
                            if response.status == 200:
                                readme_data = await response.json()
                                if "content" in readme_data:
                                    import base64
                                    readme_content = base64.b64decode(readme_data["content"]).decode("utf-8")
                
                # Create content
                content = f"# {repo_name}\n\n"
                if repo_description:
                    content += f"{repo_description}\n\n"
                content += f"**URL**: {repo_url}\n"
                content += f"**Stars**: {repo_stars}\n"
                content += f"**Forks**: {repo_forks}\n"
                if repo_language:
                    content += f"**Language**: {repo_language}\n"
                if repo_topics:
                    content += f"**Topics**: {', '.join(repo_topics)}\n"
                if repo_license:
                    content += f"**License**: {repo_license}\n"
                content += f"**Open Issues**: {repo_open_issues}\n"
                content += f"**Default Branch**: {repo_default_branch}\n"
                content += f"**Created**: {repo_created}\n"
                content += f"**Updated**: {repo_updated}\n\n"
                
                if readme_content:
                    content += f"## README\n\n{readme_content}\n"
                
                # Create metadata
                metadata = {
                    "name": repo_name,
                    "description": repo_description,
                    "url": repo_url,
                    "stars": repo_stars,
                    "forks": repo_forks,
                    "language": repo_language,
                    "created_at": repo_created,
                    "updated_at": repo_updated,
                    "topics": repo_topics,
                    "license": repo_license,
                    "open_issues": repo_open_issues,
                    "default_branch": repo_default_branch,
                    "owner": owner
                }
                
                # Create data item
                item = DataItem(
                    source_id=f"github_repo_{owner}_{repo_name}",
                    content=content,
                    metadata=metadata,
                    url=repo_url,
                    content_type="text/markdown",
                    language="en"
                )
                
                return [item]
            except Exception as e:
                logger.error(f"Error getting GitHub repository: {e}")
                return []
    
    async def _get_issues(self, owner: str, repo: str, params: Dict[str, Any]) -> List[DataItem]:
        """Get issues for a repository."""
        async with self.semaphore:
            try:
                logger.info(f"Getting issues for {owner}/{repo}")
                
                # Construct GitHub API URL
                url = f"https://api.github.com/repos/{owner}/{repo}/issues"
                
                # Set up parameters
                state = params.get("state", "open")
                per_page = params.get("per_page", 30)
                page = params.get("page", 1)
                sort = params.get("sort", "created")
                direction = params.get("direction", "desc")
                
                # Add query parameters
                url += f"?state={state}&per_page={per_page}&page={page}&sort={sort}&direction={direction}"
                
                # Set up headers
                headers = {
                    "Accept": "application/vnd.github.v3+json"
                }
                if self.api_token:
                    headers["Authorization"] = f"token {self.api_token}"
                
                # Make the request
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            logger.error(f"GitHub API error: {response.status}")
                            return []
                        
                        issues_data = await response.json()
                
                # Process issues
                results = []
                for issue_data in issues_data:
                    # Skip pull requests
                    if "pull_request" in issue_data:
                        continue
                    
                    # Extract issue information
                    issue_number = issue_data.get("number", 0)
                    issue_title = issue_data.get("title", "")
                    issue_body = issue_data.get("body", "")
                    issue_url = issue_data.get("html_url", "")
                    issue_state = issue_data.get("state", "")
                    issue_created = issue_data.get("created_at", "")
                    issue_updated = issue_data.get("updated_at", "")
                    issue_labels = [label.get("name", "") for label in issue_data.get("labels", [])]
                    issue_user = issue_data.get("user", {}).get("login", "")
                    
                    # Create content
                    content = f"# Issue #{issue_number}: {issue_title}\n\n"
                    if issue_body:
                        content += f"{issue_body}\n\n"
                    content += f"**URL**: {issue_url}\n"
                    content += f"**State**: {issue_state}\n"
                    content += f"**Created by**: {issue_user}\n"
                    content += f"**Created**: {issue_created}\n"
                    content += f"**Updated**: {issue_updated}\n"
                    if issue_labels:
                        content += f"**Labels**: {', '.join(issue_labels)}\n"
                    
                    # Create metadata
                    metadata = {
                        "number": issue_number,
                        "title": issue_title,
                        "state": issue_state,
                        "url": issue_url,
                        "created_at": issue_created,
                        "updated_at": issue_updated,
                        "labels": issue_labels,
                        "user": issue_user,
                        "repository": f"{owner}/{repo}"
                    }
                    
                    # Create data item
                    item = DataItem(
                        source_id=f"github_issue_{owner}_{repo}_{issue_number}",
                        content=content,
                        metadata=metadata,
                        url=issue_url,
                        content_type="text/markdown",
                        language="en"
                    )
                    
                    results.append(item)
                
                logger.info(f"Collected {len(results)} issues for {owner}/{repo}")
                return results
            except Exception as e:
                logger.error(f"Error getting GitHub issues: {e}")
                return []
    
    async def _get_pull_requests(self, owner: str, repo: str, params: Dict[str, Any]) -> List[DataItem]:
        """Get pull requests for a repository."""
        async with self.semaphore:
            try:
                logger.info(f"Getting pull requests for {owner}/{repo}")
                
                # Construct GitHub API URL
                url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
                
                # Set up parameters
                state = params.get("state", "open")
                per_page = params.get("per_page", 30)
                page = params.get("page", 1)
                sort = params.get("sort", "created")
                direction = params.get("direction", "desc")
                
                # Add query parameters
                url += f"?state={state}&per_page={per_page}&page={page}&sort={sort}&direction={direction}"
                
                # Set up headers
                headers = {
                    "Accept": "application/vnd.github.v3+json"
                }
                if self.api_token:
                    headers["Authorization"] = f"token {self.api_token}"
                
                # Make the request
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            logger.error(f"GitHub API error: {response.status}")
                            return []
                        
                        prs_data = await response.json()
                
                # Process pull requests
                results = []
                for pr_data in prs_data:
                    # Extract PR information
                    pr_number = pr_data.get("number", 0)
                    pr_title = pr_data.get("title", "")
                    pr_body = pr_data.get("body", "")
                    pr_url = pr_data.get("html_url", "")
                    pr_state = pr_data.get("state", "")
                    pr_created = pr_data.get("created_at", "")
                    pr_updated = pr_data.get("updated_at", "")
                    pr_user = pr_data.get("user", {}).get("login", "")
                    pr_base = pr_data.get("base", {}).get("ref", "")
                    pr_head = pr_data.get("head", {}).get("ref", "")
                    pr_merged = pr_data.get("merged", False)
                    
                    # Create content
                    content = f"# Pull Request #{pr_number}: {pr_title}\n\n"
                    if pr_body:
                        content += f"{pr_body}\n\n"
                    content += f"**URL**: {pr_url}\n"
                    content += f"**State**: {pr_state}\n"
                    content += f"**Created by**: {pr_user}\n"
                    content += f"**Created**: {pr_created}\n"
                    content += f"**Updated**: {pr_updated}\n"
                    content += f"**Base branch**: {pr_base}\n"
                    content += f"**Head branch**: {pr_head}\n"
                    content += f"**Merged**: {'Yes' if pr_merged else 'No'}\n"
                    
                    # Create metadata
                    metadata = {
                        "number": pr_number,
                        "title": pr_title,
                        "state": pr_state,
                        "url": pr_url,
                        "created_at": pr_created,
                        "updated_at": pr_updated,
                        "user": pr_user,
                        "base": pr_base,
                        "head": pr_head,
                        "merged": pr_merged,
                        "repository": f"{owner}/{repo}"
                    }
                    
                    # Create data item
                    item = DataItem(
                        source_id=f"github_pr_{owner}_{repo}_{pr_number}",
                        content=content,
                        metadata=metadata,
                        url=pr_url,
                        content_type="text/markdown",
                        language="en"
                    )
                    
                    results.append(item)
                
                logger.info(f"Collected {len(results)} pull requests for {owner}/{repo}")
                return results
            except Exception as e:
                logger.error(f"Error getting GitHub pull requests: {e}")
                return []
