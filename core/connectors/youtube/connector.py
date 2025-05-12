"""
YouTube connector implementation.

This module provides the main YouTube connector implementation.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import os

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.plugins import PluginBase
from core.connectors import ConnectorBase, DataItem

from .config import load_config
from .utils import RateLimiter, Cache, generate_cache_key, retry_async, extract_youtube_id, format_duration, parse_youtube_datetime, paginate
from .errors import YouTubeConnectorError, YouTubeAPIError, YouTubeResourceNotFoundError, YouTubeCommentsDisabledError, handle_youtube_api_error
from .transcript import get_video_transcript, TranscriptFormat
from .video import YouTubeVideoCollector
from .channel import YouTubeChannelCollector
from .playlist import YouTubePlaylistCollector
from .search import YouTubeSearchCollector

logger = logging.getLogger(__name__)

class YouTubeConnector(ConnectorBase):
    """Connector for YouTube videos and channels."""
    
    name: str = "youtube_connector"
    description: str = "Connector for YouTube videos and channels"
    source_type: str = "youtube"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the YouTube connector.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        self.config = load_config(config)
        self.api_key = self.config["api_key"]
        self.youtube = None
        self.semaphore = asyncio.Semaphore(self.config["concurrency"])
        self.rate_limiter = RateLimiter(
            self.config["rate_limit_per_second"],
            self.config["rate_limit_per_day"]
        )
        self.cache = Cache(ttl=self.config["cache_ttl"]) if self.config["cache_enabled"] else None
        
        # Initialize collectors
        self.video_collector = None
        self.channel_collector = None
        self.playlist_collector = None
        self.search_collector = None
    
    def initialize(self) -> bool:
        """
        Initialize the connector.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            if not self.api_key:
                logger.warning("No YouTube API key provided. API functionality will be limited.")
                return False
            
            # Initialize the YouTube API client
            self.youtube = build(
                self.config["api_service_name"],
                self.config["api_version"],
                developerKey=self.api_key
            )
            
            # Initialize collectors
            self.video_collector = YouTubeVideoCollector(self)
            self.channel_collector = YouTubeChannelCollector(self)
            self.playlist_collector = YouTubePlaylistCollector(self)
            self.search_collector = YouTubeSearchCollector(self)
            
            logger.info("Initialized YouTube connector")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize YouTube connector: {e}")
            return False
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """
        Collect data from YouTube.
        
        Args:
            params: Collection parameters
            
        Returns:
            List[DataItem]: Collected data items
        """
        params = params or {}
        
        try:
            # Check if API key is available
            if not self.api_key:
                logger.error("No YouTube API key provided. Cannot collect data.")
                return []
            
            # Initialize YouTube API client if not already initialized
            if not self.youtube:
                if not self.initialize():
                    return []
            
            # Determine what to collect
            if "video_id" in params:
                # Collect data from a specific video
                video_id = params["video_id"]
                return await self.video_collector.collect_video(video_id, params)
            elif "channel_id" in params:
                # Collect data from a specific channel
                channel_id = params["channel_id"]
                return await self.channel_collector.collect_channel(channel_id, params)
            elif "playlist_id" in params:
                # Collect data from a specific playlist
                playlist_id = params["playlist_id"]
                return await self.playlist_collector.collect_playlist(playlist_id, params)
            elif "search" in params:
                # Search for videos
                query = params["search"]
                return await self.search_collector.search_videos(query, params)
            elif "url" in params:
                # Extract ID from URL and collect data
                url = params["url"]
                return await self._collect_from_url(url, params)
            else:
                logger.error("No video_id, channel_id, playlist_id, search, or url parameter provided for YouTube connector")
                return []
        except Exception as e:
            logger.error(f"Error collecting data from YouTube: {e}")
            return []
    
    async def _collect_from_url(self, url: str, params: Dict[str, Any]) -> List[DataItem]:
        """
        Collect data from a YouTube URL.
        
        Args:
            url: YouTube URL
            params: Collection parameters
            
        Returns:
            List[DataItem]: Collected data items
        """
        try:
            # Extract YouTube ID from URL
            youtube_id = extract_youtube_id(url)
            
            if youtube_id["type"] == "video":
                return await self.video_collector.collect_video(youtube_id["id"], params)
            elif youtube_id["type"] == "channel":
                return await self.channel_collector.collect_channel(youtube_id["id"], params)
            elif youtube_id["type"] == "user":
                # Get channel ID from username
                channel_id = await self._get_channel_id_from_username(youtube_id["id"])
                if channel_id:
                    return await self.channel_collector.collect_channel(channel_id, params)
            elif youtube_id["type"] == "playlist":
                return await self.playlist_collector.collect_playlist(youtube_id["id"], params)
            else:
                logger.error(f"Unsupported YouTube URL format: {url}")
                return []
        except Exception as e:
            logger.error(f"Error collecting data from YouTube URL {url}: {e}")
            return []
    
    @retry_async(
        max_retries=3,
        retry_status_codes=[429, 500, 502, 503, 504],
        backoff_factor=2,
        max_backoff=60
    )
    async def _get_channel_id_from_username(self, username: str) -> Optional[str]:
        """
        Get channel ID from a username.
        
        Args:
            username: YouTube username
            
        Returns:
            Optional[str]: Channel ID or None if not found
        """
        try:
            # Check cache first
            if self.cache:
                cache_key = generate_cache_key("get_channel_id_from_username", username)
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
            
            # Acquire rate limiter
            await self.rate_limiter.acquire()
            
            # Use the channels.list API to get the channel ID
            async with self.semaphore:
                request = self.youtube.channels().list(
                    part="id",
                    forUsername=username
                )
                response = request.execute()
            
            if response.get("items"):
                channel_id = response["items"][0]["id"]
                
                # Cache the result
                if self.cache:
                    self.cache.set(cache_key, channel_id)
                
                return channel_id
            else:
                logger.warning(f"No channel found for username: {username}")
                return None
        except HttpError as e:
            raise handle_youtube_api_error(e, "channel", username)
        except Exception as e:
            logger.error(f"Error getting channel ID for username {username}: {e}")
            return None
