"""
YouTube connector plugin for fetching data from YouTube videos and channels.
"""

import os
import time
from typing import Any, Dict, List, Optional, Union
import requests
import logging
import re
from urllib.parse import parse_qs, urlparse

from core.plugins.base import ConnectorPlugin

logger = logging.getLogger(__name__)


class YouTubeConnector(ConnectorPlugin):
    """Connector for fetching data from YouTube videos and channels."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the YouTube connector.
        
        Args:
            config: Configuration dictionary with the following keys:
                - api_key: YouTube Data API key
                - rate_limit_pause: Seconds to pause when rate limited (default: 60)
                - max_retries: Maximum number of retries for API calls (default: 3)
        """
        super().__init__(config)
        self.api_key = self.config.get('api_key', os.environ.get('YOUTUBE_API_KEY'))
        self.rate_limit_pause = self.config.get('rate_limit_pause', 60)
        self.max_retries = self.config.get('max_retries', 3)
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.session = None
        
    def initialize(self) -> bool:
        """Initialize the YouTube connector.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        if not self.validate_config():
            logger.error("Invalid YouTube connector configuration")
            return False
        
        self.session = requests.Session()
        self.initialized = True
        return True
        
    def validate_config(self) -> bool:
        """Validate the connector configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        if not self.api_key:
            logger.error("YouTube API key is required")
            return False
        
        return True
        
    def connect(self) -> bool:
        """Connect to YouTube API.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        if not self.initialized:
            return self.initialize()
        return True
        
    def disconnect(self) -> bool:
        """Disconnect from YouTube API.
        
        Returns:
            bool: True if disconnection was successful, False otherwise
        """
        if self.session:
            self.session.close()
            self.session = None
        
        self.initialized = False
        return True
        
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to the YouTube API with retry logic.
        
        Args:
            endpoint: API endpoint to call
            params: Query parameters for the request
            
        Returns:
            Dict[str, Any]: Response data
            
        Raises:
            Exception: If the request fails after max retries
        """
        if not self.session:
            self.connect()
            
        url = f"{self.base_url}/{endpoint}"
        params['key'] = self.api_key
        retries = 0
        
        while retries < self.max_retries:
            try:
                response = self.session.get(url, params=params)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 403 and 'quota' in response.text.lower():
                    logger.warning(f"YouTube API quota exceeded. Pausing for {self.rate_limit_pause} seconds.")
                    time.sleep(self.rate_limit_pause)
                    retries += 1
                else:
                    logger.error(f"YouTube API error: {response.status_code} - {response.text}")
                    raise Exception(f"YouTube API error: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"Error making YouTube API request: {str(e)}")
                retries += 1
                if retries >= self.max_retries:
                    raise
                time.sleep(2 ** retries)  # Exponential backoff
                
        raise Exception(f"Failed to make YouTube API request after {self.max_retries} retries")
        
    def _extract_video_id(self, video_url: str) -> str:
        """Extract video ID from YouTube URL.
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            str: Video ID
            
        Raises:
            ValueError: If video ID cannot be extracted
        """
        # Handle different URL formats
        if 'youtu.be/' in video_url:
            return video_url.split('youtu.be/')[-1].split('?')[0]
        elif 'youtube.com/watch' in video_url:
            parsed_url = urlparse(video_url)
            return parse_qs(parsed_url.query).get('v', [''])[0]
        elif 'youtube.com/embed/' in video_url:
            return video_url.split('youtube.com/embed/')[-1].split('?')[0]
        elif re.match(r'^[a-zA-Z0-9_-]{11}$', video_url):
            return video_url  # Already a video ID
        else:
            raise ValueError(f"Could not extract video ID from URL: {video_url}")
            
    def _extract_channel_id(self, channel_url: str) -> str:
        """Extract channel ID from YouTube URL.
        
        Args:
            channel_url: YouTube channel URL
            
        Returns:
            str: Channel ID
            
        Raises:
            ValueError: If channel ID cannot be extracted
        """
        # Handle different URL formats
        if 'youtube.com/channel/' in channel_url:
            return channel_url.split('youtube.com/channel/')[-1].split('?')[0].split('/')[0]
        elif 'youtube.com/c/' or 'youtube.com/user/' in channel_url:
            # Need to make an API call to resolve custom URL to channel ID
            return self._resolve_channel_id(channel_url)
        elif re.match(r'^UC[a-zA-Z0-9_-]{22}$', channel_url):
            return channel_url  # Already a channel ID
        else:
            raise ValueError(f"Could not extract channel ID from URL: {channel_url}")
            
    def _resolve_channel_id(self, channel_url: str) -> str:
        """Resolve custom channel URL to channel ID.
        
        Args:
            channel_url: YouTube channel URL
            
        Returns:
            str: Channel ID
            
        Raises:
            ValueError: If channel ID cannot be resolved
        """
        # Extract the custom name from URL
        if 'youtube.com/c/' in channel_url:
            custom_name = channel_url.split('youtube.com/c/')[-1].split('?')[0].split('/')[0]
        elif 'youtube.com/user/' in channel_url:
            custom_name = channel_url.split('youtube.com/user/')[-1].split('?')[0].split('/')[0]
        else:
            raise ValueError(f"Not a valid custom channel URL: {channel_url}")
            
        # Search for the channel
        search_params = {
            'part': 'snippet',
            'type': 'channel',
            'q': custom_name,
            'maxResults': 1
        }
        
        result = self._make_request('search', search_params)
        items = result.get('items', [])
        
        if not items:
            raise ValueError(f"Could not resolve channel ID for URL: {channel_url}")
            
        return items[0]['snippet']['channelId']
        
    def fetch_data(self, query: str, **kwargs) -> Dict[str, Any]:
        """Fetch data from YouTube based on query.
        
        Args:
            query: Query string, video URL, or channel URL
            **kwargs: Additional parameters:
                - query_type: Type of query ('video', 'channel', 'search', 'comments')
                - max_results: Maximum number of results to return
                - page_token: Token for pagination
                
        Returns:
            Dict[str, Any]: Dictionary containing the fetched data
        """
        if not self.initialized:
            self.initialize()
            
        query_type = kwargs.get('query_type', 'search')
        max_results = min(kwargs.get('max_results', 50), 50)  # YouTube API limit
        page_token = kwargs.get('page_token')
        
        if query_type == 'video':
            # Get video details
            try:
                video_id = self._extract_video_id(query)
            except ValueError:
                # If not a URL, assume it's a direct video ID
                video_id = query
                
            params = {
                'part': 'snippet,contentDetails,statistics',
                'id': video_id
            }
            
            return self._make_request('videos', params)
            
        elif query_type == 'channel':
            # Get channel details
            try:
                channel_id = self._extract_channel_id(query)
            except ValueError:
                # If not a URL, assume it's a direct channel ID
                channel_id = query
                
            params = {
                'part': 'snippet,contentDetails,statistics',
                'id': channel_id
            }
            
            return self._make_request('channels', params)
            
        elif query_type == 'search':
            # Search videos, channels, or playlists
            params = {
                'part': 'snippet',
                'q': query,
                'maxResults': max_results,
                'type': kwargs.get('type', 'video')  # video, channel, playlist
            }
            
            if page_token:
                params['pageToken'] = page_token
                
            return self._make_request('search', params)
            
        elif query_type == 'comments':
            # Get video comments
            try:
                video_id = self._extract_video_id(query)
            except ValueError:
                # If not a URL, assume it's a direct video ID
                video_id = query
                
            params = {
                'part': 'snippet',
                'videoId': video_id,
                'maxResults': max_results,
                'order': kwargs.get('order', 'relevance')  # relevance, time
            }
            
            if page_token:
                params['pageToken'] = page_token
                
            return self._make_request('commentThreads', params)
            
        elif query_type == 'channel_videos':
            # Get videos from a channel
            try:
                channel_id = self._extract_channel_id(query)
            except ValueError:
                # If not a URL, assume it's a direct channel ID
                channel_id = query
                
            # First, get the channel's uploads playlist ID
            channel_params = {
                'part': 'contentDetails',
                'id': channel_id
            }
            
            channel_data = self._make_request('channels', channel_params)
            uploads_playlist_id = channel_data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Then, get the videos from that playlist
            playlist_params = {
                'part': 'snippet',
                'playlistId': uploads_playlist_id,
                'maxResults': max_results
            }
            
            if page_token:
                playlist_params['pageToken'] = page_token
                
            return self._make_request('playlistItems', playlist_params)
            
        else:
            raise ValueError(f"Unsupported query type: {query_type}")

