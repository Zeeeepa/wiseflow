"""
YouTube connector for Wiseflow.

This module provides a connector for YouTube videos and channels.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import uuid
import asyncio
from datetime import datetime
import os
import re
import json
from urllib.parse import urlparse, parse_qs

import aiohttp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.plugins import PluginBase
from core.connectors import ConnectorBase, DataItem

logger = logging.getLogger(__name__)

class YouTubeConnector(ConnectorBase):
    """Connector for YouTube videos and channels."""
    
    name: str = "youtube_connector"
    description: str = "Connector for YouTube videos and channels"
    source_type: str = "youtube"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the YouTube connector."""
        super().__init__(config)
        self.api_key = self.config.get("api_key", os.environ.get("YOUTUBE_API_KEY", ""))
        self.youtube = None
        self.semaphore = asyncio.Semaphore(self.config.get("concurrency", 5))
        
    def initialize(self) -> bool:
        """Initialize the connector."""
        try:
            if not self.api_key:
                logger.warning("No YouTube API key provided. API functionality will be limited.")
                return False
            
            # Initialize the YouTube API client
            self.youtube = build('youtube', 'v3', developerKey=self.api_key)
            
            logger.info("Initialized YouTube connector")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize YouTube connector: {e}")
            return False
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from YouTube."""
        params = params or {}
        
        if not self.youtube and not self.initialize():
            logger.error("YouTube API client not initialized")
            return []
        
        # Determine what to collect
        if "video_id" in params:
            # Collect data from a specific video
            video_id = params["video_id"]
            return await self._collect_video(video_id, params)
        elif "channel_id" in params:
            # Collect data from a channel
            channel_id = params["channel_id"]
            return await self._collect_channel(channel_id, params)
        elif "playlist_id" in params:
            # Collect data from a playlist
            playlist_id = params["playlist_id"]
            return await self._collect_playlist(playlist_id, params)
        elif "search" in params:
            # Search for videos
            query = params["search"]
            return await self._search_videos(query, params)
        else:
            logger.error("No video_id, channel_id, playlist_id, or search query provided for YouTube connector")
            return []
    
    async def _collect_video(self, video_id: str, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from a specific video."""
        async with self.semaphore:
            try:
                # Get video details
                video_response = self.youtube.videos().list(
                    part="snippet,contentDetails,statistics",
                    id=video_id
                ).execute()
                
                if not video_response.get("items"):
                    logger.warning(f"No video found with ID: {video_id}")
                    return []
                
                video = video_response["items"][0]
                snippet = video["snippet"]
                
                # Get video transcript if requested
                transcript = None
                if params.get("include_transcript", True):
                    transcript = await self._get_transcript(video_id)
                
                # Create a data item for the video
                item = DataItem(
                    source_id=f"youtube_video_{video_id}",
                    content=transcript or snippet.get("description", ""),
                    metadata={
                        "video_id": video_id,
                        "title": snippet.get("title", ""),
                        "channel_id": snippet.get("channelId", ""),
                        "channel_title": snippet.get("channelTitle", ""),
                        "published_at": snippet.get("publishedAt", ""),
                        "description": snippet.get("description", ""),
                        "tags": snippet.get("tags", []),
                        "category_id": snippet.get("categoryId", ""),
                        "duration": video.get("contentDetails", {}).get("duration", ""),
                        "view_count": video.get("statistics", {}).get("viewCount", ""),
                        "like_count": video.get("statistics", {}).get("likeCount", ""),
                        "comment_count": video.get("statistics", {}).get("commentCount", ""),
                        "has_transcript": transcript is not None,
                        "type": "video"
                    },
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    content_type="video/transcript" if transcript else "text/plain",
                    timestamp=datetime.fromisoformat(snippet.get("publishedAt", datetime.now().isoformat()).replace("Z", "+00:00")) if snippet.get("publishedAt") else datetime.now()
                )
                
                return [item]
            except HttpError as e:
                logger.error(f"YouTube API error for video {video_id}: {e}")
                return []
            except Exception as e:
                logger.error(f"Error collecting data from video {video_id}: {e}")
                return []
    
    async def _collect_channel(self, channel_id: str, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from a channel."""
        try:
            # Get channel details
            channel_response = self.youtube.channels().list(
                part="snippet,contentDetails,statistics",
                id=channel_id
            ).execute()
            
            if not channel_response.get("items"):
                logger.warning(f"No channel found with ID: {channel_id}")
                return []
            
            channel = channel_response["items"][0]
            snippet = channel["snippet"]
            
            # Create a data item for the channel
            channel_item = DataItem(
                source_id=f"youtube_channel_{channel_id}",
                content=snippet.get("description", ""),
                metadata={
                    "channel_id": channel_id,
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "country": snippet.get("country", ""),
                    "view_count": channel.get("statistics", {}).get("viewCount", ""),
                    "subscriber_count": channel.get("statistics", {}).get("subscriberCount", ""),
                    "video_count": channel.get("statistics", {}).get("videoCount", ""),
                    "type": "channel"
                },
                url=f"https://www.youtube.com/channel/{channel_id}",
                content_type="text/plain",
                timestamp=datetime.fromisoformat(snippet.get("publishedAt", datetime.now().isoformat()).replace("Z", "+00:00")) if snippet.get("publishedAt") else datetime.now()
            )
            
            results = [channel_item]
            
            # Get channel videos if requested
            if params.get("include_videos", True):
                # Get the uploads playlist ID
                uploads_playlist_id = channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", "")
                
                if uploads_playlist_id:
                    # Collect videos from the uploads playlist
                    max_videos = params.get("max_videos", 10)
                    videos = await self._get_playlist_videos(uploads_playlist_id, max_results=max_videos)
                    
                    # Process each video
                    for video in videos:
                        video_id = video["snippet"]["resourceId"]["videoId"]
                        video_items = await self._collect_video(video_id, params)
                        results.extend(video_items)
            
            return results
        except HttpError as e:
            logger.error(f"YouTube API error for channel {channel_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error collecting data from channel {channel_id}: {e}")
            return []
    
    async def _collect_playlist(self, playlist_id: str, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from a playlist."""
        try:
            # Get playlist details
            playlist_response = self.youtube.playlists().list(
                part="snippet",
                id=playlist_id
            ).execute()
            
            if not playlist_response.get("items"):
                logger.warning(f"No playlist found with ID: {playlist_id}")
                return []
            
            playlist = playlist_response["items"][0]
            snippet = playlist["snippet"]
            
            # Create a data item for the playlist
            playlist_item = DataItem(
                source_id=f"youtube_playlist_{playlist_id}",
                content=snippet.get("description", ""),
                metadata={
                    "playlist_id": playlist_id,
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "channel_id": snippet.get("channelId", ""),
                    "channel_title": snippet.get("channelTitle", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "type": "playlist"
                },
                url=f"https://www.youtube.com/playlist?list={playlist_id}",
                content_type="text/plain",
                timestamp=datetime.fromisoformat(snippet.get("publishedAt", datetime.now().isoformat()).replace("Z", "+00:00")) if snippet.get("publishedAt") else datetime.now()
            )
            
            results = [playlist_item]
            
            # Get playlist videos if requested
            if params.get("include_videos", True):
                max_videos = params.get("max_videos", 10)
                videos = await self._get_playlist_videos(playlist_id, max_results=max_videos)
                
                # Process each video
                for video in videos:
                    video_id = video["snippet"]["resourceId"]["videoId"]
                    video_items = await self._collect_video(video_id, params)
                    results.extend(video_items)
            
            return results
        except HttpError as e:
            logger.error(f"YouTube API error for playlist {playlist_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error collecting data from playlist {playlist_id}: {e}")
            return []
    
    async def _search_videos(self, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """Search for videos and collect data."""
        try:
            # Search for videos
            search_response = self.youtube.search().list(
                q=query,
                part="id,snippet",
                maxResults=params.get("max_results", 5),
                type="video"
            ).execute()
            
            if not search_response.get("items"):
                logger.warning(f"No videos found for query: {query}")
                return []
            
            results = []
            
            # Process each video
            for item in search_response["items"]:
                video_id = item["id"]["videoId"]
                video_items = await self._collect_video(video_id, params)
                results.extend(video_items)
            
            return results
        except HttpError as e:
            logger.error(f"YouTube API error for search query {query}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching videos with query {query}: {e}")
            return []
    
    async def _get_playlist_videos(self, playlist_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get videos from a playlist."""
        try:
            # Get playlist items
            playlist_items_response = self.youtube.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=max_results
            ).execute()
            
            return playlist_items_response.get("items", [])
        except HttpError as e:
            logger.error(f"YouTube API error for playlist {playlist_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting videos from playlist {playlist_id}: {e}")
            return []
    
    async def _get_transcript(self, video_id: str) -> Optional[str]:
        """Get the transcript of a video using a third-party service."""
        async with self.semaphore:
            try:
                # Use a third-party service to get the transcript
                # This is a simplified example and might need to be replaced with a more reliable method
                url = f"https://youtubetranscript.com/?server_vid={video_id}"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            html = await response.text()
                            
                            # Extract transcript from HTML (simplified)
                            transcript_match = re.search(r'<div class="transcript-text">(.*?)</div>', html, re.DOTALL)
                            if transcript_match:
                                transcript_html = transcript_match.group(1)
                                # Remove HTML tags
                                transcript = re.sub(r'<[^>]+>', '', transcript_html)
                                return transcript.strip()
                
                # If the above method fails, try an alternative approach
                # For example, using YouTube's official API for captions (requires additional permissions)
                
                return None
            except Exception as e:
                logger.error(f"Error getting transcript for video {video_id}: {e}")
                return None
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """Extract video ID from a YouTube URL."""
        if not url:
            return None
        
        # Handle youtu.be URLs
        if "youtu.be" in url:
            path = urlparse(url).path
            return path.strip("/")
        
        # Handle youtube.com URLs
        parsed_url = urlparse(url)
        if "youtube.com" in parsed_url.netloc:
            query_params = parse_qs(parsed_url.query)
            return query_params.get("v", [None])[0]
        
        return None
    
    @staticmethod
    def extract_channel_id(url: str) -> Optional[str]:
        """Extract channel ID from a YouTube URL."""
        if not url:
            return None
        
        parsed_url = urlparse(url)
        if "youtube.com" in parsed_url.netloc:
            path = parsed_url.path
            
            # Handle /channel/CHANNEL_ID format
            if path.startswith("/channel/"):
                return path.split("/")[2]
            
            # Handle /c/CHANNEL_NAME or /user/USERNAME format
            # These require additional API calls to resolve to channel IDs
            
        return None
    
    @staticmethod
    def extract_playlist_id(url: str) -> Optional[str]:
        """Extract playlist ID from a YouTube URL."""
        if not url:
            return None
        
        parsed_url = urlparse(url)
        if "youtube.com" in parsed_url.netloc:
            query_params = parse_qs(parsed_url.query)
            return query_params.get("list", [None])[0]
        
        return None
