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
from urllib.parse import quote_plus, parse_qs, urlparse

from core.plugins import PluginBase
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
        self.api_key = self.config.get("api_key", os.environ.get("YOUTUBE_API_KEY", ""))
        self.api_base_url = "https://www.googleapis.com/youtube/v3"
        self.semaphore = asyncio.Semaphore(self.config.get("concurrency", 5))
        self.session = None
        
    def initialize(self) -> bool:
        """Initialize the connector."""
        try:
            if not self.api_key:
                logger.warning("No YouTube API key provided. API requests will fail.")
                return False
            
            logger.info("Initialized YouTube connector")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize YouTube connector: {e}")
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
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from YouTube."""
        params = params or {}
        
        try:
            # Create session
            await self._create_session()
            
            # Determine what to collect
            if "video_id" in params:
                # Collect a specific video
                video_id = params["video_id"]
                return await self._collect_video(video_id)
            elif "channel_id" in params:
                # Collect videos from a specific channel
                channel_id = params["channel_id"]
                return await self._collect_channel_videos(channel_id, params)
            elif "playlist_id" in params:
                # Collect videos from a specific playlist
                playlist_id = params["playlist_id"]
                return await self._collect_playlist_videos(playlist_id, params)
            elif "search" in params:
                # Search for videos
                query = params["search"]
                return await self._search_videos(query, params)
            elif "url" in params:
                # Extract video ID from URL
                url = params["url"]
                video_id = self._extract_video_id(url)
                if video_id:
                    return await self._collect_video(video_id)
                else:
                    logger.error(f"Could not extract video ID from URL: {url}")
                    return []
            else:
                logger.error("No video_id, channel_id, playlist_id, search, or url parameter provided for YouTube connector")
                return []
        finally:
            # Close session
            await self._close_session()
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from a YouTube URL."""
        if "youtu.be" in url:
            # Short URL format
            return url.split("/")[-1].split("?")[0]
        elif "youtube.com/watch" in url:
            # Standard URL format
            parsed_url = urlparse(url)
            return parse_qs(parsed_url.query).get("v", [None])[0]
        elif "youtube.com/embed" in url:
            # Embed URL format
            return url.split("/")[-1].split("?")[0]
        else:
            return None
    
    async def _collect_video(self, video_id: str) -> List[DataItem]:
        """Collect information about a specific video."""
        try:
            # Get video information
            url = f"{self.api_base_url}/videos?id={video_id}&key={self.api_key}&part=snippet,contentDetails,statistics,status"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get video info for {video_id}: {response.status}")
                        return []
                    
                    video_data = await response.json()
                    if not video_data.get("items"):
                        logger.error(f"No video found with ID: {video_id}")
                        return []
                    
                    video = video_data["items"][0]
            
            # Get video comments
            comments = []
            try:
                comments_url = f"{self.api_base_url}/commentThreads?videoId={video_id}&key={self.api_key}&part=snippet&maxResults=50"
                async with self.semaphore:
                    async with self.session.get(comments_url) as response:
                        if response.status == 200:
                            comments_data = await response.json()
                            comments = comments_data.get("items", [])
            except Exception as e:
                logger.warning(f"Error getting comments for video {video_id}: {e}")
            
            # Extract video information
            snippet = video.get("snippet", {})
            content_details = video.get("contentDetails", {})
            statistics = video.get("statistics", {})
            
            title = snippet.get("title", "")
            description = snippet.get("description", "")
            channel_title = snippet.get("channelTitle", "")
            published_at = snippet.get("publishedAt", "")
            
            # Create content
            content = f"# {title}\n\n"
            content += f"**Channel:** {channel_title}\n"
            content += f"**Published:** {published_at}\n\n"
            
            if description:
                content += f"## Description\n\n{description}\n\n"
            
            # Add comments
            if comments:
                content += "## Top Comments\n\n"
                for comment_thread in comments[:10]:  # Limit to top 10 comments
                    comment = comment_thread.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                    author = comment.get("authorDisplayName", "")
                    text = comment.get("textDisplay", "")
                    content += f"**{author}:** {text}\n\n"
            
            # Create metadata
            metadata = {
                "title": title,
                "description": description,
                "channel_title": channel_title,
                "channel_id": snippet.get("channelId", ""),
                "published_at": published_at,
                "tags": snippet.get("tags", []),
                "category_id": snippet.get("categoryId", ""),
                "duration": content_details.get("duration", ""),
                "view_count": int(statistics.get("viewCount", 0)),
                "like_count": int(statistics.get("likeCount", 0)),
                "comment_count": int(statistics.get("commentCount", 0)),
                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", "")
            }
            
            # Create data item
            item = DataItem(
                source_id=f"youtube_video_{video_id}",
                content=content,
                metadata=metadata,
                url=f"https://www.youtube.com/watch?v={video_id}",
                timestamp=datetime.fromisoformat(published_at.replace("Z", "+00:00")) if published_at else None,
                content_type="text/markdown",
                raw_data={"video": video, "comments": comments}
            )
            
            return [item]
        except Exception as e:
            logger.error(f"Error collecting video {video_id}: {e}")
            return []
    
    async def _collect_channel_videos(self, channel_id: str, params: Dict[str, Any]) -> List[DataItem]:
        """Collect videos from a specific channel."""
        try:
            # Get channel information
            channel_url = f"{self.api_base_url}/channels?id={channel_id}&key={self.api_key}&part=snippet,statistics,contentDetails"
            async with self.semaphore:
                async with self.session.get(channel_url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get channel info for {channel_id}: {response.status}")
                        return []
                    
                    channel_data = await response.json()
                    if not channel_data.get("items"):
                        logger.error(f"No channel found with ID: {channel_id}")
                        return []
                    
                    channel = channel_data["items"][0]
            
            # Get channel's videos
            max_results = params.get("max_results", 10)
            uploads_playlist_id = channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", "")
            
            if not uploads_playlist_id:
                logger.error(f"Could not find uploads playlist for channel {channel_id}")
                return []
            
            # Get videos from uploads playlist
            playlist_url = f"{self.api_base_url}/playlistItems?playlistId={uploads_playlist_id}&key={self.api_key}&part=snippet,contentDetails&maxResults={max_results}"
            async with self.semaphore:
                async with self.session.get(playlist_url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get videos for channel {channel_id}: {response.status}")
                        return []
                    
                    playlist_data = await response.json()
                    videos = playlist_data.get("items", [])
            
            # Extract channel information
            snippet = channel.get("snippet", {})
            statistics = channel.get("statistics", {})
            
            title = snippet.get("title", "")
            description = snippet.get("description", "")
            
            # Create channel content
            channel_content = f"# {title}\n\n"
            if description:
                channel_content += f"{description}\n\n"
            
            channel_content += f"**Subscribers:** {statistics.get('subscriberCount', 'N/A')}\n"
            channel_content += f"**Videos:** {statistics.get('videoCount', 'N/A')}\n"
            channel_content += f"**Views:** {statistics.get('viewCount', 'N/A')}\n\n"
            
            channel_content += f"## Recent Videos ({len(videos)})\n\n"
            for video in videos:
                video_snippet = video.get("snippet", {})
                video_title = video_snippet.get("title", "")
                video_published = video_snippet.get("publishedAt", "")
                video_id = video.get("contentDetails", {}).get("videoId", "")
                channel_content += f"- [{video_title}](https://www.youtube.com/watch?v={video_id}) - {video_published}\n"
            
            # Create channel metadata
            channel_metadata = {
                "title": title,
                "description": description,
                "published_at": snippet.get("publishedAt", ""),
                "subscriber_count": int(statistics.get("subscriberCount", 0)),
                "video_count": int(statistics.get("videoCount", 0)),
                "view_count": int(statistics.get("viewCount", 0)),
                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                "videos": [{
                    "id": video.get("contentDetails", {}).get("videoId", ""),
                    "title": video.get("snippet", {}).get("title", ""),
                    "published_at": video.get("snippet", {}).get("publishedAt", "")
                } for video in videos]
            }
            
            # Create channel data item
            channel_item = DataItem(
                source_id=f"youtube_channel_{channel_id}",
                content=channel_content,
                metadata=channel_metadata,
                url=f"https://www.youtube.com/channel/{channel_id}",
                timestamp=datetime.fromisoformat(snippet.get("publishedAt", "").replace("Z", "+00:00")) if snippet.get("publishedAt") else None,
                content_type="text/markdown",
                raw_data={"channel": channel, "videos": videos}
            )
            
            # Collect individual videos if requested
            if params.get("include_video_details", False):
                results = [channel_item]
                for video in videos:
                    video_id = video.get("contentDetails", {}).get("videoId", "")
                    if video_id:
                        video_items = await self._collect_video(video_id)
                        results.extend(video_items)
                return results
            else:
                return [channel_item]
        except Exception as e:
            logger.error(f"Error collecting videos for channel {channel_id}: {e}")
            return []
    
    async def _collect_playlist_videos(self, playlist_id: str, params: Dict[str, Any]) -> List[DataItem]:
        """Collect videos from a specific playlist."""
        try:
            # Get playlist information
            playlist_url = f"{self.api_base_url}/playlists?id={playlist_id}&key={self.api_key}&part=snippet,contentDetails"
            async with self.semaphore:
                async with self.session.get(playlist_url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get playlist info for {playlist_id}: {response.status}")
                        return []
                    
                    playlist_data = await response.json()
                    if not playlist_data.get("items"):
                        logger.error(f"No playlist found with ID: {playlist_id}")
                        return []
                    
                    playlist = playlist_data["items"][0]
            
            # Get playlist videos
            max_results = params.get("max_results", 10)
            videos_url = f"{self.api_base_url}/playlistItems?playlistId={playlist_id}&key={self.api_key}&part=snippet,contentDetails&maxResults={max_results}"
            async with self.semaphore:
                async with self.session.get(videos_url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get videos for playlist {playlist_id}: {response.status}")
                        return []
                    
                    videos_data = await response.json()
                    videos = videos_data.get("items", [])
            
            # Extract playlist information
            snippet = playlist.get("snippet", {})
            content_details = playlist.get("contentDetails", {})
            
            title = snippet.get("title", "")
            description = snippet.get("description", "")
            channel_title = snippet.get("channelTitle", "")
            
            # Create playlist content
            playlist_content = f"# {title}\n\n"
            playlist_content += f"**Channel:** {channel_title}\n"
            playlist_content += f"**Videos:** {content_details.get('itemCount', 'N/A')}\n\n"
            
            if description:
                playlist_content += f"{description}\n\n"
            
            playlist_content += f"## Videos ({len(videos)})\n\n"
            for video in videos:
                video_snippet = video.get("snippet", {})
                video_title = video_snippet.get("title", "")
                video_published = video_snippet.get("publishedAt", "")
                video_id = video.get("contentDetails", {}).get("videoId", "")
                playlist_content += f"- [{video_title}](https://www.youtube.com/watch?v={video_id}) - {video_published}\n"
            
            # Create playlist metadata
            playlist_metadata = {
                "title": title,
                "description": description,
                "channel_title": channel_title,
                "channel_id": snippet.get("channelId", ""),
                "published_at": snippet.get("publishedAt", ""),
                "video_count": content_details.get("itemCount", 0),
                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                "videos": [{
                    "id": video.get("contentDetails", {}).get("videoId", ""),
                    "title": video.get("snippet", {}).get("title", ""),
                    "published_at": video.get("snippet", {}).get("publishedAt", "")
                } for video in videos]
            }
            
            # Create playlist data item
            playlist_item = DataItem(
                source_id=f"youtube_playlist_{playlist_id}",
                content=playlist_content,
                metadata=playlist_metadata,
                url=f"https://www.youtube.com/playlist?list={playlist_id}",
                timestamp=datetime.fromisoformat(snippet.get("publishedAt", "").replace("Z", "+00:00")) if snippet.get("publishedAt") else None,
                content_type="text/markdown",
                raw_data={"playlist": playlist, "videos": videos}
            )
            
            # Collect individual videos if requested
            if params.get("include_video_details", False):
                results = [playlist_item]
                for video in videos:
                    video_id = video.get("contentDetails", {}).get("videoId", "")
                    if video_id:
                        video_items = await self._collect_video(video_id)
                        results.extend(video_items)
                return results
            else:
                return [playlist_item]
        except Exception as e:
            logger.error(f"Error collecting videos for playlist {playlist_id}: {e}")
            return []
    
    async def _search_videos(self, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """Search for videos."""
        try:
            # Set up search parameters
            max_results = params.get("max_results", 10)
            order = params.get("order", "relevance")  # relevance, date, rating, title, videoCount, viewCount
            type = params.get("type", "video")  # video, channel, playlist
            
            # Build query parameters
            query_params = f"q={quote_plus(query)}&key={self.api_key}&part=snippet&maxResults={max_results}&order={order}&type={type}"
            
            # Add optional parameters
            if params.get("published_after"):
                query_params += f"&publishedAfter={params['published_after']}"
            if params.get("published_before"):
                query_params += f"&publishedBefore={params['published_before']}"
            if params.get("channel_id"):
                query_params += f"&channelId={params['channel_id']}"
            if params.get("video_duration"):
                query_params += f"&videoDuration={params['video_duration']}"  # any, long, medium, short
            
            # Search for videos
            url = f"{self.api_base_url}/search?{query_params}"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to search videos with query {query}: {response.status}")
                        return []
                    
                    search_data = await response.json()
                    items = search_data.get("items", [])
            
            # Process search results
            results = []
            for item in items:
                item_id = item.get("id", {})
                snippet = item.get("snippet", {})
                
                if item_id.get("kind") == "youtube#video":
                    # This is a video
                    video_id = item_id.get("videoId", "")
                    if params.get("include_video_details", False):
                        # Collect full video details
                        video_items = await self._collect_video(video_id)
                        results.extend(video_items)
                    else:
                        # Create a simple data item with search result
                        title = snippet.get("title", "")
                        description = snippet.get("description", "")
                        channel_title = snippet.get("channelTitle", "")
                        published_at = snippet.get("publishedAt", "")
                        
                        # Create content
                        content = f"# {title}\n\n"
                        content += f"**Channel:** {channel_title}\n"
                        content += f"**Published:** {published_at}\n\n"
                        
                        if description:
                            content += f"{description}\n\n"
                        
                        # Create metadata
                        metadata = {
                            "title": title,
                            "description": description,
                            "channel_title": channel_title,
                            "channel_id": snippet.get("channelId", ""),
                            "published_at": published_at,
                            "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                            "search_query": query
                        }
                        
                        # Create data item
                        item = DataItem(
                            source_id=f"youtube_video_{video_id}",
                            content=content,
                            metadata=metadata,
                            url=f"https://www.youtube.com/watch?v={video_id}",
                            timestamp=datetime.fromisoformat(published_at.replace("Z", "+00:00")) if published_at else None,
                            content_type="text/markdown",
                            raw_data=item
                        )
                        
                        results.append(item)
                
                elif item_id.get("kind") == "youtube#channel" and type != "video":
                    # This is a channel
                    channel_id = item_id.get("channelId", "")
                    if params.get("include_channel_details", False):
                        # Collect full channel details
                        channel_items = await self._collect_channel_videos(channel_id, params)
                        results.extend(channel_items)
                    else:
                        # Create a simple data item with search result
                        title = snippet.get("title", "")
                        description = snippet.get("description", "")
                        published_at = snippet.get("publishedAt", "")
                        
                        # Create content
                        content = f"# {title}\n\n"
                        if description:
                            content += f"{description}\n\n"
                        
                        # Create metadata
                        metadata = {
                            "title": title,
                            "description": description,
                            "published_at": published_at,
                            "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                            "search_query": query
                        }
                        
                        # Create data item
                        item = DataItem(
                            source_id=f"youtube_channel_{channel_id}",
                            content=content,
                            metadata=metadata,
                            url=f"https://www.youtube.com/channel/{channel_id}",
                            timestamp=datetime.fromisoformat(published_at.replace("Z", "+00:00")) if published_at else None,
                            content_type="text/markdown",
                            raw_data=item
                        )
                        
                        results.append(item)
                
                elif item_id.get("kind") == "youtube#playlist" and type != "video":
                    # This is a playlist
                    playlist_id = item_id.get("playlistId", "")
                    if params.get("include_playlist_details", False):
                        # Collect full playlist details
                        playlist_items = await self._collect_playlist_videos(playlist_id, params)
                        results.extend(playlist_items)
                    else:
                        # Create a simple data item with search result
                        title = snippet.get("title", "")
                        description = snippet.get("description", "")
                        channel_title = snippet.get("channelTitle", "")
                        published_at = snippet.get("publishedAt", "")
                        
                        # Create content
                        content = f"# {title}\n\n"
                        content += f"**Channel:** {channel_title}\n"
                        content += f"**Published:** {published_at}\n\n"
                        
                        if description:
                            content += f"{description}\n\n"
                        
                        # Create metadata
                        metadata = {
                            "title": title,
                            "description": description,
                            "channel_title": channel_title,
                            "channel_id": snippet.get("channelId", ""),
                            "published_at": published_at,
                            "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                            "search_query": query
                        }
                        
                        # Create data item
                        item = DataItem(
                            source_id=f"youtube_playlist_{playlist_id}",
                            content=content,
                            metadata=metadata,
                            url=f"https://www.youtube.com/playlist?list={playlist_id}",
                            timestamp=datetime.fromisoformat(published_at.replace("Z", "+00:00")) if published_at else None,
                            content_type="text/markdown",
                            raw_data=item
                        )
                        
                        results.append(item)
            
            return results
        except Exception as e:
            logger.error(f"Error searching videos with query {query}: {e}")
            return []

