"""
GitHub connector plugin for fetching data from GitHub repositories.
"""

import os
import time
import asyncio
from typing import Any, Dict, List, Optional, Union
import requests
import logging
from datetime import datetime

from core.connectors import ConnectorBase, DataItem
from core.event_system import EventType, publish_sync, create_connector_event

logger = logging.getLogger(__name__)


class GitHubConnector(ConnectorBase):
    """Connector for fetching data from GitHub repositories."""
    
    name = "github_connector"
    description = "Fetches data from GitHub repositories"
    source_type = "github"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the GitHub connector.
        
        Args:
            config: Configuration dictionary with the following keys:
                - api_token: GitHub API token (optional)
                - rate_limit_pause: Seconds to pause when rate limited (default: 60)
                - max_retries: Maximum number of retries for API calls (default: 3)
        """
        super().__init__(config or {})
        self.api_token = self.config.get('api_token', os.environ.get('GITHUB_API_TOKEN'))
        self.rate_limit_pause = self.config.get('rate_limit_pause', 60)
        self.max_retries = self.config.get('max_retries', 3)
        self.base_url = "https://api.github.com"
        self.session = None
        
    def initialize(self) -> bool:
        """Initialize the GitHub connector.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        if not self.validate_config():
            logger.error("Invalid GitHub connector configuration")
            return False
        
        try:
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
            
            # Test connection
            response = self.session.get(f"{self.base_url}/rate_limit")
            if response.status_code != 200:
                logger.error(f"Failed to connect to GitHub API: {response.status_code} - {response.text}")
                return False
                
            self._initialized = True
            logger.info("GitHub connector initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing GitHub connector: {e}")
            if self.session:
                self.session.close()
                self.session = None
            return False
        
    def validate_config(self) -> bool:
        """Validate the connector configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        # API token is optional but recommended
        if not self.api_token:
            logger.warning("No GitHub API token provided. Rate limits will be stricter.")
        
        # Validate rate limit pause
        if not isinstance(self.rate_limit_pause, (int, float)) or self.rate_limit_pause <= 0:
            logger.error("Invalid rate_limit_pause value. Must be a positive number.")
            return False
            
        # Validate max retries
        if not isinstance(self.max_retries, int) or self.max_retries <= 0:
            logger.error("Invalid max_retries value. Must be a positive integer.")
            return False
            
        return True
        
    def shutdown(self) -> bool:
        """Release resources and shutdown the connector.
        
        Returns:
            bool: True if shutdown was successful, False otherwise
        """
        try:
            if self.session:
                self.session.close()
                self.session = None
            
            self._initialized = False
            logger.info("GitHub connector shutdown successfully")
            return True
        except Exception as e:
            logger.error(f"Error shutting down GitHub connector: {e}")
            return False
        
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the GitHub API with retry logic.
        
        Args:
            endpoint: API endpoint to call
            params: Query parameters for the request
            
        Returns:
            Dict[str, Any]: Response data
            
        Raises:
            Exception: If the request fails after max retries
        """
        if not self._initialized:
            if not self.initialize():
                raise ConnectionError("Failed to initialize GitHub connector")
                
        if not self.session:
            if not self.initialize():
                raise ConnectionError("Failed to create session for GitHub connector")
            
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        retries = 0
        
        while retries < self.max_retries:
            try:
                response = self.session.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 403 and 'rate limit exceeded' in response.text.lower():
                    logger.warning(f"Rate limit exceeded. Pausing for {self.rate_limit_pause} seconds.")
                    time.sleep(self.rate_limit_pause)
                    retries += 1
                elif response.status_code == 404:
                    logger.error(f"Resource not found: {url}")
                    raise ValueError(f"GitHub resource not found: {endpoint}")
                else:
                    logger.error(f"GitHub API error: {response.status_code} - {response.text}")
                    raise Exception(f"GitHub API error: {response.status_code} - {response.text}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout for {url}. Retrying...")
                retries += 1
                if retries >= self.max_retries:
                    raise TimeoutError(f"GitHub API request timed out after {self.max_retries} retries")
                time.sleep(2 ** retries)  # Exponential backoff
                
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error for GitHub API request: {str(e)}")
                retries += 1
                if retries >= self.max_retries:
                    raise ConnectionError(f"Failed to connect to GitHub API after {self.max_retries} retries")
                time.sleep(2 ** retries)  # Exponential backoff
                
            except Exception as e:
                logger.error(f"Error making GitHub API request: {str(e)}")
                retries += 1
                if retries >= self.max_retries:
                    raise
                time.sleep(2 ** retries)  # Exponential backoff
                
        raise Exception(f"Failed to make GitHub API request after {self.max_retries} retries")
        
    def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from GitHub.
        
        Args:
            params: Parameters for the collection:
                - query: Query string or repository path
                - query_type: Type of query ('repo', 'code', 'issues', 'user')
                - Additional parameters specific to each query type
                
        Returns:
            List[DataItem]: List of collected data items
        """
        params = params or {}
        
        if not self._initialized:
            if not self.initialize():
                logger.error("Failed to initialize GitHub connector")
                return []
                
        query = params.get('query')
        if not query:
            logger.error("No query provided for GitHub connector")
            return []
            
        query_type = params.get('query_type', 'repo')
        
        try:
            if query_type == 'repo':
                return self._collect_repo_data(query, params)
            elif query_type == 'code':
                return self._collect_code_data(query, params)
            elif query_type == 'issues':
                return self._collect_issues_data(query, params)
            elif query_type == 'user':
                return self._collect_user_data(query, params)
            else:
                logger.error(f"Unsupported query type: {query_type}")
                return []
        except Exception as e:
            logger.error(f"Error collecting data from GitHub: {e}")
            return []
            
    def _collect_repo_data(self, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """Collect repository data.
        
        Args:
            query: Repository path in format 'owner/repo'
            params: Additional parameters
                
        Returns:
            List[DataItem]: Repository data items
        """
        # Format: owner/repo or full repo URL
        repo_path = query.split('github.com/')[-1].rstrip('/')
        if not '/' in repo_path:
            logger.error(f"Invalid repository path: {query}. Format should be 'owner/repo'")
            return []
            
        data_type = params.get('data_type', 'info')
        
        try:
            if data_type == 'info':
                # Get repository information
                data = self._make_request(f'repos/{repo_path}')
                
                # Create data item
                return [DataItem(
                    source_id=f"github_repo_{data['id']}",
                    content=f"# {data['name']}\n\n{data['description'] or ''}\n\n## Repository Information\n\n" +
                            f"- Owner: {data['owner']['login']}\n" +
                            f"- Stars: {data['stargazers_count']}\n" +
                            f"- Forks: {data['forks_count']}\n" +
                            f"- Open Issues: {data['open_issues_count']}\n" +
                            f"- Default Branch: {data['default_branch']}\n" +
                            f"- Created: {data['created_at']}\n" +
                            f"- Last Updated: {data['updated_at']}\n",
                    metadata={
                        "repo_id": data['id'],
                        "repo_name": data['name'],
                        "full_name": data['full_name'],
                        "owner": data['owner']['login'],
                        "stars": data['stargazers_count'],
                        "forks": data['forks_count'],
                        "open_issues": data['open_issues_count'],
                        "default_branch": data['default_branch'],
                        "created_at": data['created_at'],
                        "updated_at": data['updated_at'],
                        "language": data['language'],
                        "topics": data.get('topics', [])
                    },
                    url=data['html_url'],
                    timestamp=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')),
                    content_type="text/markdown",
                    raw_data=data
                )]
                
            elif data_type == 'contents':
                # Get repository contents
                path = params.get('path', '')
                ref = params.get('ref')
                
                api_params = {}
                if ref:
                    api_params['ref'] = ref
                    
                data = self._make_request(f'repos/{repo_path}/contents/{path}', api_params)
                
                # Handle directory vs file
                if isinstance(data, list):
                    # Directory listing
                    content = f"# Contents of {repo_path}/{path}\n\n"
                    for item in data:
                        content += f"- [{item['name']}]({item['html_url']}) ({item['type']})\n"
                        
                    return [DataItem(
                        source_id=f"github_contents_{repo_path}_{path}".replace('/', '_'),
                        content=content,
                        metadata={
                            "repo_path": repo_path,
                            "path": path,
                            "ref": ref,
                            "type": "directory",
                            "item_count": len(data)
                        },
                        url=f"https://github.com/{repo_path}/tree/{ref or 'master'}/{path}",
                        content_type="text/markdown",
                        raw_data=data
                    )]
                else:
                    # Single file
                    if data['encoding'] == 'base64' and data['content']:
                        import base64
                        file_content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
                    else:
                        file_content = "Content not available or not in base64 format"
                        
                    return [DataItem(
                        source_id=f"github_file_{repo_path}_{path}".replace('/', '_'),
                        content=file_content,
                        metadata={
                            "repo_path": repo_path,
                            "path": path,
                            "ref": ref,
                            "type": "file",
                            "size": data['size'],
                            "sha": data['sha']
                        },
                        url=data['html_url'],
                        content_type=self._get_content_type(path),
                        raw_data=data
                    )]
                    
            elif data_type == 'commits':
                # Get repository commits
                api_params = {
                    'per_page': min(params.get('per_page', 30), 100),
                    'page': params.get('page', 1)
                }
                
                if params.get('path'):
                    api_params['path'] = params.get('path')
                    
                if params.get('since'):
                    api_params['since'] = params.get('since')
                    
                if params.get('until'):
                    api_params['until'] = params.get('until')
                    
                data = self._make_request(f'repos/{repo_path}/commits', api_params)
                
                # Create data items for each commit
                items = []
                for commit in data:
                    commit_data = commit['commit']
                    
                    # Format commit message and details
                    content = f"# Commit: {commit['sha'][:7]}\n\n"
                    content += f"## Message\n\n{commit_data['message']}\n\n"
                    content += f"## Author\n\n{commit_data['author']['name']} <{commit_data['author']['email']}>\n\n"
                    content += f"## Date\n\n{commit_data['author']['date']}\n\n"
                    
                    # Create data item
                    items.append(DataItem(
                        source_id=f"github_commit_{commit['sha']}",
                        content=content,
                        metadata={
                            "repo_path": repo_path,
                            "commit_sha": commit['sha'],
                            "author_name": commit_data['author']['name'],
                            "author_email": commit_data['author']['email'],
                            "committer_name": commit_data['committer']['name'],
                            "committer_email": commit_data['committer']['email'],
                            "commit_date": commit_data['author']['date']
                        },
                        url=commit['html_url'],
                        timestamp=datetime.fromisoformat(commit_data['author']['date'].replace('Z', '+00:00')),
                        content_type="text/markdown",
                        raw_data=commit
                    ))
                    
                return items
                
            elif data_type == 'issues':
                # Get repository issues
                api_params = {
                    'state': params.get('state', 'open'),
                    'per_page': min(params.get('per_page', 30), 100),
                    'page': params.get('page', 1)
                }
                
                if params.get('labels'):
                    api_params['labels'] = params.get('labels')
                    
                data = self._make_request(f'repos/{repo_path}/issues', api_params)
                
                # Create data items for each issue
                items = []
                for issue in data:
                    # Skip pull requests
                    if 'pull_request' in issue:
                        continue
                        
                    # Format issue content
                    content = f"# Issue #{issue['number']}: {issue['title']}\n\n"
                    content += f"**State:** {issue['state']}\n\n"
                    if issue['labels']:
                        content += "**Labels:** " + ", ".join([label['name'] for label in issue['labels']]) + "\n\n"
                    content += f"**Created by:** {issue['user']['login']}\n\n"
                    content += f"**Created at:** {issue['created_at']}\n\n"
                    if issue['assignees']:
                        content += "**Assignees:** " + ", ".join([assignee['login'] for assignee in issue['assignees']]) + "\n\n"
                    content += f"## Description\n\n{issue['body'] or 'No description provided.'}\n\n"
                    
                    # Create data item
                    items.append(DataItem(
                        source_id=f"github_issue_{repo_path}_{issue['number']}".replace('/', '_'),
                        content=content,
                        metadata={
                            "repo_path": repo_path,
                            "issue_number": issue['number'],
                            "title": issue['title'],
                            "state": issue['state'],
                            "labels": [label['name'] for label in issue['labels']],
                            "author": issue['user']['login'],
                            "assignees": [assignee['login'] for assignee in issue['assignees']],
                            "created_at": issue['created_at'],
                            "updated_at": issue['updated_at'],
                            "comments": issue['comments']
                        },
                        url=issue['html_url'],
                        timestamp=datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00')),
                        content_type="text/markdown",
                        raw_data=issue
                    ))
                    
                return items
                
            elif data_type == 'pulls':
                # Get repository pull requests
                api_params = {
                    'state': params.get('state', 'open'),
                    'per_page': min(params.get('per_page', 30), 100),
                    'page': params.get('page', 1)
                }
                
                data = self._make_request(f'repos/{repo_path}/pulls', api_params)
                
                # Create data items for each pull request
                items = []
                for pr in data:
                    # Format PR content
                    content = f"# Pull Request #{pr['number']}: {pr['title']}\n\n"
                    content += f"**State:** {pr['state']}"
                    if pr['draft']:
                        content += " (Draft)"
                    content += "\n\n"
                    if pr['labels']:
                        content += "**Labels:** " + ", ".join([label['name'] for label in pr['labels']]) + "\n\n"
                    content += f"**Created by:** {pr['user']['login']}\n\n"
                    content += f"**Created at:** {pr['created_at']}\n\n"
                    content += f"**Branch:** {pr['head']['ref']} → {pr['base']['ref']}\n\n"
                    if pr['assignees']:
                        content += "**Assignees:** " + ", ".join([assignee['login'] for assignee in pr['assignees']]) + "\n\n"
                    content += f"## Description\n\n{pr['body'] or 'No description provided.'}\n\n"
                    
                    # Create data item
                    items.append(DataItem(
                        source_id=f"github_pr_{repo_path}_{pr['number']}".replace('/', '_'),
                        content=content,
                        metadata={
                            "repo_path": repo_path,
                            "pr_number": pr['number'],
                            "title": pr['title'],
                            "state": pr['state'],
                            "draft": pr['draft'],
                            "labels": [label['name'] for label in pr['labels']] if 'labels' in pr else [],
                            "author": pr['user']['login'],
                            "assignees": [assignee['login'] for assignee in pr['assignees']] if 'assignees' in pr else [],
                            "created_at": pr['created_at'],
                            "updated_at": pr['updated_at'],
                            "head_branch": pr['head']['ref'],
                            "base_branch": pr['base']['ref'],
                            "comments": pr['comments'],
                            "commits": pr['commits'],
                            "additions": pr['additions'],
                            "deletions": pr['deletions'],
                            "changed_files": pr['changed_files']
                        },
                        url=pr['html_url'],
                        timestamp=datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00')),
                        content_type="text/markdown",
                        raw_data=pr
                    ))
                    
                return items
                
            else:
                logger.error(f"Unsupported data type: {data_type}")
                return []
                
        except Exception as e:
            logger.error(f"Error collecting repository data: {e}")
            return []
            
    def _collect_code_data(self, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """Collect code search data.
        
        Args:
            query: Search query
            params: Additional parameters
                
        Returns:
            List[DataItem]: Code search data items
        """
        try:
            # Search code in repositories
            search_params = {
                'q': query,
                'sort': params.get('sort', 'best-match'),
                'order': params.get('order', 'desc'),
                'per_page': min(params.get('per_page', 30), 100),
                'page': params.get('page', 1)
            }
            
            data = self._make_request('search/code', search_params)
            
            # Create data items for each code result
            items = []
            for item in data.get('items', []):
                # Format content
                content = f"# Code Result: {item['name']}\n\n"
                content += f"**Repository:** {item['repository']['full_name']}\n\n"
                content += f"**Path:** {item['path']}\n\n"
                
                # Get file content if requested
                file_content = ""
                if params.get('include_content', False):
                    try:
                        file_data = self._make_request(item['url'])
                        if file_data.get('encoding') == 'base64' and file_data.get('content'):
                            import base64
                            file_content = base64.b64decode(file_data['content']).decode('utf-8', errors='replace')
                            content += f"## File Content\n\n```\n{file_content}\n```\n\n"
                    except Exception as e:
                        logger.warning(f"Failed to get file content: {e}")
                
                # Create data item
                items.append(DataItem(
                    source_id=f"github_code_{item['sha']}",
                    content=content,
                    metadata={
                        "repo_name": item['repository']['full_name'],
                        "path": item['path'],
                        "name": item['name'],
                        "sha": item['sha'],
                        "file_content": file_content if file_content else None
                    },
                    url=item['html_url'],
                    content_type="text/markdown",
                    raw_data=item
                ))
                
            return items
            
        except Exception as e:
            logger.error(f"Error collecting code search data: {e}")
            return []
            
    def _collect_issues_data(self, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """Collect issues search data.
        
        Args:
            query: Search query
            params: Additional parameters
                
        Returns:
            List[DataItem]: Issues search data items
        """
        try:
            # Search issues and pull requests
            search_params = {
                'q': query,
                'sort': params.get('sort', 'created'),
                'order': params.get('order', 'desc'),
                'per_page': min(params.get('per_page', 30), 100),
                'page': params.get('page', 1)
            }
            
            data = self._make_request('search/issues', search_params)
            
            # Create data items for each issue result
            items = []
            for item in data.get('items', []):
                # Determine if it's an issue or PR
                is_pr = 'pull_request' in item
                item_type = "Pull Request" if is_pr else "Issue"
                
                # Format content
                content = f"# {item_type} #{item['number']}: {item['title']}\n\n"
                content += f"**Repository:** {item['repository_url'].split('repos/')[1]}\n\n"
                content += f"**State:** {item['state']}\n\n"
                content += f"**Created by:** {item['user']['login']}\n\n"
                content += f"**Created at:** {item['created_at']}\n\n"
                if item['labels']:
                    content += "**Labels:** " + ", ".join([label['name'] for label in item['labels']]) + "\n\n"
                content += f"## Description\n\n{item['body'] or 'No description provided.'}\n\n"
                
                # Create data item
                items.append(DataItem(
                    source_id=f"github_{'pr' if is_pr else 'issue'}_{item['id']}",
                    content=content,
                    metadata={
                        "repo_url": item['repository_url'],
                        "number": item['number'],
                        "title": item['title'],
                        "state": item['state'],
                        "author": item['user']['login'],
                        "created_at": item['created_at'],
                        "updated_at": item['updated_at'],
                        "labels": [label['name'] for label in item['labels']],
                        "is_pr": is_pr
                    },
                    url=item['html_url'],
                    timestamp=datetime.fromisoformat(item['created_at'].replace('Z', '+00:00')),
                    content_type="text/markdown",
                    raw_data=item
                ))
                
            return items
            
        except Exception as e:
            logger.error(f"Error collecting issues search data: {e}")
            return []
            
    def _collect_user_data(self, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """Collect user data.
        
        Args:
            query: Username
            params: Additional parameters
                
        Returns:
            List[DataItem]: User data items
        """
        try:
            # Get user information
            data = self._make_request(f'users/{query}')
            
            # Format content
            content = f"# GitHub User: {data['login']}\n\n"
            if data.get('name'):
                content += f"**Name:** {data['name']}\n\n"
            if data.get('bio'):
                content += f"**Bio:** {data['bio']}\n\n"
            if data.get('company'):
                content += f"**Company:** {data['company']}\n\n"
            if data.get('location'):
                content += f"**Location:** {data['location']}\n\n"
            if data.get('email'):
                content += f"**Email:** {data['email']}\n\n"
            if data.get('blog'):
                content += f"**Website:** {data['blog']}\n\n"
            content += f"**Public Repositories:** {data['public_repos']}\n\n"
            content += f"**Followers:** {data['followers']}\n\n"
            content += f"**Following:** {data['following']}\n\n"
            content += f"**Created at:** {data['created_at']}\n\n"
            
            # Create data item
            return [DataItem(
                source_id=f"github_user_{data['id']}",
                content=content,
                metadata={
                    "username": data['login'],
                    "name": data.get('name'),
                    "bio": data.get('bio'),
                    "company": data.get('company'),
                    "location": data.get('location'),
                    "email": data.get('email'),
                    "website": data.get('blog'),
                    "public_repos": data['public_repos'],
                    "followers": data['followers'],
                    "following": data['following'],
                    "created_at": data['created_at']
                },
                url=data['html_url'],
                timestamp=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
                content_type="text/markdown",
                raw_data=data
            )]
            
        except Exception as e:
            logger.error(f"Error collecting user data: {e}")
            return []
            
    def _get_content_type(self, path: str) -> str:
        """Determine content type based on file extension.
        
        Args:
            path: File path
            
        Returns:
            str: Content type
        """
        ext = path.split('.')[-1].lower() if '.' in path else ''
        
        if ext in ['md', 'markdown']:
            return 'text/markdown'
        elif ext in ['py', 'js', 'java', 'c', 'cpp', 'cs', 'go', 'rb', 'php', 'sh', 'bat', 'ps1', 'ts', 'swift']:
            return 'text/plain'
        elif ext in ['json']:
            return 'application/json'
        elif ext in ['xml']:
            return 'application/xml'
        elif ext in ['html', 'htm']:
            return 'text/html'
        elif ext in ['css']:
            return 'text/css'
        elif ext in ['csv']:
            return 'text/csv'
        elif ext in ['txt']:
            return 'text/plain'
        else:
            return 'text/plain'
