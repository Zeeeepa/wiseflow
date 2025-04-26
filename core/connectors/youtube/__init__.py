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
import aiohttp
from urllib.parse import quote_plus, urlparse, parse_qs

from core.connectors import ConnectorBase, DataItem
from core.utils.general_utils import extract_and_convert_dates

logger = logging.getLogger(__name__)

class YouTubeConnector(ConnectorBase):
    """Connector for YouTube videos and channels."""
    
    name: str = "youtube_connector"
    description: str = "Connector for YouTube videos and channels"
    source_type: str = "youtube"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the YouTube connector."""
        super().__init__(config)
        self.config = config or {}
        self.api_key = self.config.get("youtube_api_key")
        self.semaphore = asyncio.Semaphore(self.config.get("concurrency", 3))
        
    def initialize(self) -> bool:
        """Initialize the connector."""
        try:
            # Check if API key is provided
            if not self.api_key:
                logger.warning("No YouTube API key provided. Some features may be limited.")
            else:
                logger.info("YouTube API key provided.")
                
            logger.info(f"Initialized YouTube connector with config: {self.config}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize YouTube connector: {e}")
            return False
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from YouTube."""
        params = params or {}
        
        # Get collection parameters
        collection_type = params.get("collection_type", "video")
        
        # Process based on collection type
        if collection_type == "video":
            video_id = params.get("video_id", "")
            if video_id:
                return await self._get_video(video_id, params)
            else:
                query = params.get("query", "")
                if query:
                    return await self._search_videos(query, params)
                else:
                    logger.error("No video_id or query provided for YouTube video collection")
                    return []
        elif collection_type == "channel":
            channel_id = params.get("channel_id", "")
            if channel_id:
                return await self._get_channel(channel_id, params)
            else:
                query = params.get("query", "")
                if query:
                    return await self._search_channels(query, params)
                else:
                    logger.error("No channel_id or query provided for YouTube channel collection")
                    return []
        elif collection_type == "playlist":
            playlist_id = params.get("playlist_id", "")
            if playlist_id:
                return await self._get_playlist(playlist_id, params)
            else:
                logger.error("No playlist_id provided for YouTube playlist collection")
                return []
        else:
            logger.error(f"Unknown YouTube collection type: {collection_type}")
            return []
    
    async def _get_video(self, video_id: str, params: Dict[str, Any]) -> List[DataItem]:
        """Get information about a specific YouTube video."""
        async with self.semaphore:
            try:
                logger.info(f"Getting YouTube video: {video_id}")
                
                # Check if video_id is a URL
                if "youtube.com" in video_id or "youtu.be" in video_id:
                    video_id = self._extract_video_id(video_id)
                
                if not video_id:
                    logger.error("Invalid YouTube video ID or URL")
                    return []
                
                # Construct YouTube API URL
                url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&part=snippet,contentDetails,statistics"
                
                if self.api_key:
                    url += f"&key={self.api_key}"
                
                # Make the request
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            logger.error(f"YouTube API error: {response.status}")
                            return []
                        
                        video_data = await response.json()
                
                # Check if video exists
                if not video_data.get("items"):
                    logger.error(f"YouTube video not found: {video_id}")
                    return []
                
                # Extract video information
                video_info = video_data["items"][0]
                snippet = video_info.get("snippet", {})
                content_details = video_info.get("contentDetails", {})
                statistics = video_info.get("statistics", {})
                
                title = snippet.get("title", "")
                description = snippet.get("description", "")
                channel_title = snippet.get("channelTitle", "")
                channel_id = snippet.get("channelId", "")
                published_at = snippet.get("publishedAt", "")
                tags = snippet.get("tags", [])
                category_id = snippet.get("categoryId", "")
                
                duration = content_details.get("duration", "")
                dimension = content_details.get("dimension", "")
                definition = content_details.get("definition", "")
                
                view_count = statistics.get("viewCount", 0)
                like_count = statistics.get("likeCount", 0)
                comment_count = statistics.get("commentCount", 0)
                
                # Get transcript if requested
                transcript = ""
                if params.get("include_transcript", False):
                    transcript = await self._get_transcript(video_id)
                
                # Create content
                content = f"# {title}\n\n"
                content += f"**Channel**: {channel_title}\n"
                content += f"**Published**: {published_at}\n"
                content += f"**Views**: {view_count}\n"
                content += f"**Likes**: {like_count}\n"
                content += f"**Comments**: {comment_count}\n\n"
                content += f"**Description**:\n{description}\n\n"
                
                if transcript:
                    content += f"**Transcript**:\n{transcript}\n"
                
                # Create metadata
                metadata = {
                    "title": title,
                    "description": description,
                    "channel_title": channel_title,
                    "channel_id": channel_id,
                    "published_at": published_at,
                    "tags": tags,
                    "category_id": category_id,
                    "duration": duration,
                    "dimension": dimension,
                    "definition": definition,
                    "view_count": view_count,
                    "like_count": like_count,
                    "comment_count": comment_count,
                    "video_id": video_id
                }
                
                # Create data item
                item = DataItem(
                    source_id=f"youtube_video_{video_id}",
                    content=content,
                    metadata=metadata,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    content_type="text/markdown",
                    language="en"
                )
                
                return [item]
            except Exception as e:
                logger.error(f"Error getting YouTube video: {e}")
                return []
    
    async def _search_videos(self, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """Search for YouTube videos."""
        async with self.semaphore:
            try:
                logger.info(f"Searching YouTube videos for: {query}")
                
                # Construct YouTube API URL
                url = f"https://www.googleapis.com/youtube/v3/search?q={quote_plus(query)}&part=snippet&type=video"
                
                # Set up parameters
                max_results = params.get("max_results", 10)
                url += f"&maxResults={max_results}"
                
                if self.api_key:
                    url += f"&key={self.api_key}"
                
                # Make the request
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            logger.error(f"YouTube API error: {response.status}")
                            return []
                        
                        search_data = await response.json()
                
                # Process search results
                results = []
                for item in search_data.get("items", []):
                    # Extract video information
                    video_id = item.get("id", {}).get("videoId", "")
                    snippet = item.get("snippet", {})
                    
                    title = snippet.get("title", "")
                    description = snippet.get("description", "")
                    channel_title = snippet.get("channelTitle", "")
                    channel_id = snippet.get("channelId", "")
                    published_at = snippet.get("publishedAt", "")
                    
                    # Create content
                    content = f"# {title}\n\n"
                    content += f"**Channel**: {channel_title}\n"
                    content += f"**Published**: {published_at}\n\n"
                    content += f"**Description**:\n{description}\n"
                    
                    # Create metadata
                    metadata = {
                        "title": title,
                        "description": description,
                        "channel_title": channel_title,
                        "channel_id": channel_id,
                        "published_at": published_at,
                        "video_id": video_id
                    }
                    
                    # Create data item
                    item = DataItem(
                        source_id=f"youtube_video_{video_id}",
                        content=content,
                        metadata=metadata,
                        url=f"https://www.youtube.com/watch?v={video_id}",
                        content_type="text/markdown",
                        language="en"
                    )
                    
                    results.append(item)
                
                logger.info(f"Found {len(results)} YouTube videos for query: {query}")
                return results
            except Exception as e:
                logger.error(f"Error searching YouTube videos: {e}")
                return []
    
    async def _get_channel(self, channel_id: str, params: Dict[str, Any]) -> List[DataItem]:
        """Get information about a specific YouTube channel."""
        async with self.semaphore:
            try:
                logger.info(f"Getting YouTube channel: {channel_id}")
                
                # Check if channel_id is a URL
                if "youtube.com" in channel_id:
                    channel_id = self._extract_channel_id(channel_id)
                
                if not channel_id:
                    logger.error("Invalid YouTube channel ID or URL")
                    return []
                
                # Construct YouTube API URL
                url = f"https://www.googleapis.com/youtube/v3/channels?id={channel_id}&part=snippet,statistics,contentDetails"
                
                if self.api_key:
                    url += f"&key={self.api_key}"
                
                # Make the request
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            logger.error(f"YouTube API error: {response.status}")
                            return []
                        
                        channel_data = await response.json()
                
                # Check if channel exists
                if not channel_data.get("items"):
                    logger.error(f"YouTube channel not found: {channel_id}")
                    return []
                
                # Extract channel information
                channel_info = channel_data["items"][0]
                snippet = channel_info.get("snippet", {})
                statistics = channel_info.get("statistics", {})
                content_details = channel_info.get("contentDetails", {})
                
                title = snippet.get("title", "")
                description = snippet.get("description", "")
                published_at = snippet.get("publishedAt", "")
                
                subscriber_count = statistics.get("subscriberCount", 0)
                video_count = statistics.get("videoCount", 0)
                view_count = statistics.get("viewCount", 0)
                
                uploads_playlist_id = content_details.get("relatedPlaylists", {}).get("uploads", "")
                
                # Get recent videos if requested
                recent_videos = []
                if params.get("include_videos", False) and uploads_playlist_id:
                    recent_videos = await self._get_playlist_videos(uploads_playlist_id, params.get("max_videos", 5))
                
                # Create content
                content = f"# {title}\n\n"
                content += f"**Subscribers**: {subscriber_count}\n"
                content += f"**Videos**: {video_count}\n"
                content += f"**Views**: {view_count}\n"
                content += f"**Created**: {published_at}\n\n"
                content += f"**Description**:\n{description}\n\n"
                
                if recent_videos:
                    content += "## Recent Videos\n\n"
                    for video in recent_videos:
                        content += f"- [{video['title']}](https://www.youtube.com/watch?v={video['video_id']})\n"
                
                # Create metadata
                metadata = {
                    "title": title,
                    "description": description,
                    "published_at": published_at,
                    "subscriber_count": subscriber_count,
                    "video_count": video_count,
                    "view_count": view_count,
                    "uploads_playlist_id": uploads_playlist_id,
                    "channel_id": channel_id,
                    "recent_videos": recent_videos
                }
                
                # Create data item
                item = DataItem(
                    source_id=f"youtube_channel_{channel_id}",
                    content=content,
                    metadata=metadata,
                    url=f"https://www.youtube.com/channel/{channel_id}",
                    content_type="text/markdown",
                    language="en"
                )
                
                return [item]
            except Exception as e:
                logger.error(f"Error getting YouTube channel: {e}")
                return []
    
    async def _search_channels(self, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """Search for YouTube channels."""
        async with self.semaphore:
            try:
                logger.info(f"Searching YouTube channels for: {query}")
                
                # Construct YouTube API URL
                url = f"https://www.googleapis.com/youtube/v3/search?q={quote_plus(query)}&part=snippet&type=channel"
                
                # Set up parameters
                max_results = params.get("max_results", 10)
                url += f"&maxResults={max_results}"
                
                if self.api_key:
                    url += f"&key={self.api_key}"
                
                # Make the request
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            logger.error(f"YouTube API error: {response.status}")
                            return []
                        
                        search_data = await response.json()
                
                # Process search results
                results = []
                for item in search_data.get("items", []):
                    # Extract channel information
                    channel_id = item.get("id", {}).get("channelId", "")
                    snippet = item.get("snippet", {})
                    
                    title = snippet.get("title", "")
                    description = snippet.get("description", "")
                    published_at = snippet.get("publishedAt", "")
                    
                    # Create content
                    content = f"# {title}\n\n"
                    content += f"**Published**: {published_at}\n\n"
                    content += f"**Description**:\n{description}\n"
                    
                    # Create metadata
                    metadata = {
                        "title": title,
                        "description": description,
                        "published_at": published_at,
                        "channel_id": channel_id
                    }
                    
                    # Create data item
                    item = DataItem(
                        source_id=f"youtube_channel_{channel_id}",
                        content=content,
                        metadata=metadata,
                        url=f"https://www.youtube.com/channel/{channel_id}",
                        content_type="text/markdown",
                        language="en"
                    )
                    
                    results.append(item)
                
                logger.info(f"Found {len(results)} YouTube channels for query: {query}")
                return results
            except Exception as e:
                logger.error(f"Error searching YouTube channels: {e}")
                return []
    
    async def _get_playlist(self, playlist_id: str, params: Dict[str, Any]) -> List[DataItem]:
        """Get information about a specific YouTube playlist."""
        async with self.semaphore:
            try:
                logger.info(f"Getting YouTube playlist: {playlist_id}")
                
                # Construct YouTube API URL for playlist details
                url = f"https://www.googleapis.com/youtube/v3/playlists?id={playlist_id}&part=snippet,contentDetails"
                
                if self.api_key:
                    url += f"&key={self.api_key}"
                
                # Make the request
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            logger.error(f"YouTube API error: {response.status}")
                            return []
                        
                        playlist_data = await response.json()
                
                # Check if playlist exists
                if not playlist_data.get("items"):
                    logger.error(f"YouTube playlist not found: {playlist_id}")
                    return []
                
                # Extract playlist information
                playlist_info = playlist_data["items"][0]
                snippet = playlist_info.get("snippet", {})
                content_details = playlist_info.get("contentDetails", {})
                
                title = snippet.get("title", "")
                description = snippet.get("description", "")
                channel_title = snippet.get("channelTitle", "")
                channel_id = snippet.get("channelId", "")
                published_at = snippet.get("publishedAt", "")
                
                item_count = content_details.get("itemCount", 0)
                
                # Get playlist videos
                videos = await self._get_playlist_videos(playlist_id, params.get("max_videos", 50))
                
                # Create content
                content = f"# {title}\n\n"
                content += f"**Channel**: {channel_title}\n"
                content += f"**Videos**: {item_count}\n"
                content += f"**Created**: {published_at}\n\n"
                
                if description:
                    content += f"**Description**:\n{description}\n\n"
                
                if videos:
                    content += "## Videos\n\n"
                    for video in videos:
                        content += f"- [{video['title']}](https://www.youtube.com/watch?v={video['video_id']})\n"
                
                # Create metadata
                metadata = {
                    "title": title,
                    "description": description,
                    "channel_title": channel_title,
                    "channel_id": channel_id,
                    "published_at": published_at,
                    "item_count": item_count,
                    "playlist_id": playlist_id,
                    "videos": videos
                }
                
                # Create data item
                item = DataItem(
                    source_id=f"youtube_playlist_{playlist_id}",
                    content=content,
                    metadata=metadata,
                    url=f"https://www.youtube.com/playlist?list={playlist_id}",
                    content_type="text/markdown",
                    language="en"
                )
                
                return [item]
            except Exception as e:
                logger.error(f"Error getting YouTube playlist: {e}")
                return []
    
    async def _get_playlist_videos(self, playlist_id: str, max_videos: int = 50) -> List[Dict[str, Any]]:
        """Get videos from a YouTube playlist."""
        try:
            logger.info(f"Getting videos from playlist: {playlist_id}")
            
            # Construct YouTube API URL
            url = f"https://www.googleapis.com/youtube/v3/playlistItems?playlistId={playlist_id}&part=snippet&maxResults={max_videos}"
            
            if self.api_key:
                url += f"&key={self.api_key}"
            
            # Make the request
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"YouTube API error: {response.status}")
                        return []
                    
                    playlist_items = await response.json()
            
            # Process playlist items
            videos = []
            for item in playlist_items.get("items", []):
                snippet = item.get("snippet", {})
                
                video_id = snippet.get("resourceId", {}).get("videoId", "")
                title = snippet.get("title", "")
                description = snippet.get("description", "")
                position = snippet.get("position", 0)
                published_at = snippet.get("publishedAt", "")
                
                videos.append({
                    "video_id": video_id,
                    "title": title,
                    "description": description,
                    "position": position,
                    "published_at": published_at
                })
            
            return videos
        except Exception as e:
            logger.error(f"Error getting playlist videos: {e}")
            return []
    
    async def _get_transcript(self, video_id: str) -> str:
        """Get transcript for a YouTube video."""
        try:
            logger.info(f"Getting transcript for video: {video_id}")
            
            # Note: YouTube doesn't provide an official API for transcripts
            # This is a placeholder implementation
            # In a real implementation, you would use a third-party service or scraping
            
            return "Transcript not available through the API. Consider using a third-party service."
        except Exception as e:
            logger.error(f"Error getting transcript: {e}")
            return ""
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from a YouTube URL."""
        try:
            parsed_url = urlparse(url)
            
            if parsed_url.netloc == "youtu.be":
                return parsed_url.path.lstrip("/")
            
            if parsed_url.netloc in ["www.youtube.com", "youtube.com"]:
                if parsed_url.path == "/watch":
                    query_params = parse_qs(parsed_url.query)
                    return query_params.get("v", [""])[0]
                
                if parsed_url.path.startswith("/embed/"):
                    return parsed_url.path.split("/")[2]
            
            return ""
        except Exception as e:
            logger.error(f"Error extracting video ID: {e}")
            return ""
    
    def _extract_channel_id(self, url: str) -> str:
        """Extract channel ID from a YouTube URL."""
        try:
            parsed_url = urlparse(url)
            
            if parsed_url.netloc in ["www.youtube.com", "youtube.com"]:
                path_parts = parsed_url.path.split("/")
                
                if len(path_parts) >= 3:
                    if path_parts[1] == "channel":
                        return path_parts[2]
            
            return ""
        except Exception as e:
            logger.error(f"Error extracting channel ID: {e}")
            return ""
