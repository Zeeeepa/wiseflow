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
                return await self._collect_video(video_id, params)
            elif "channel_id" in params:
                # Collect data from a specific channel
                channel_id = params["channel_id"]
                return await self._collect_channel(channel_id, params)
            elif "playlist_id" in params:
                # Collect data from a specific playlist
                playlist_id = params["playlist_id"]
                return await self._collect_playlist(playlist_id, params)
            elif "search" in params:
                # Search for videos
                query = params["search"]
                return await self._search_videos(query, params)
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
        """Collect data from a YouTube URL."""
        try:
            # Parse the URL
            parsed_url = urlparse(url)
            
            # YouTube video URL
            if parsed_url.netloc in ["www.youtube.com", "youtube.com"] and parsed_url.path == "/watch":
                query_params = parse_qs(parsed_url.query)
                if "v" in query_params:
                    video_id = query_params["v"][0]
                    return await self._collect_video(video_id, params)
            
            # YouTube shortened URL
            elif parsed_url.netloc == "youtu.be":
                video_id = parsed_url.path.lstrip("/")
                return await self._collect_video(video_id, params)
            
            # YouTube channel URL
            elif parsed_url.netloc in ["www.youtube.com", "youtube.com"] and "/channel/" in parsed_url.path:
                channel_id = parsed_url.path.split("/channel/")[1]
                return await self._collect_channel(channel_id, params)
            
            # YouTube user URL
            elif parsed_url.netloc in ["www.youtube.com", "youtube.com"] and "/user/" in parsed_url.path:
                username = parsed_url.path.split("/user/")[1]
                # Get channel ID from username
                channel_id = await self._get_channel_id_from_username(username)
                if channel_id:
                    return await self._collect_channel(channel_id, params)
            
            # YouTube playlist URL
            elif parsed_url.netloc in ["www.youtube.com", "youtube.com"] and "/playlist" in parsed_url.path:
                query_params = parse_qs(parsed_url.query)
                if "list" in query_params:
                    playlist_id = query_params["list"][0]
                    return await self._collect_playlist(playlist_id, params)
            
            logger.error(f"Unsupported YouTube URL format: {url}")
            return []
        except Exception as e:
            logger.error(f"Error collecting data from YouTube URL {url}: {e}")
            return []
    
    async def _get_channel_id_from_username(self, username: str) -> Optional[str]:
        """Get channel ID from a username."""
        try:
            # Use the channels.list API to get the channel ID
            request = self.youtube.channels().list(
                part="id",
                forUsername=username
            )
            response = request.execute()
            
            if response.get("items"):
                return response["items"][0]["id"]
            else:
                logger.warning(f"No channel found for username: {username}")
                return None
        except Exception as e:
            logger.error(f"Error getting channel ID for username {username}: {e}")
            return None
    
    async def _collect_video(self, video_id: str, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from a specific YouTube video."""
        try:
            # Get video details
            request = self.youtube.videos().list(
                part="snippet,contentDetails,statistics,status",
                id=video_id
            )
            response = request.execute()
            
            if not response.get("items"):
                logger.warning(f"No video found with ID: {video_id}")
                return []
            
            video = response["items"][0]
            snippet = video["snippet"]
            content_details = video["contentDetails"]
            statistics = video["statistics"]
            status = video["status"]
            
            # Get video comments if requested
            comments = []
            if params.get("include_comments", True):
                comments = await self._get_video_comments(video_id, max_comments=params.get("max_comments", 10))
            
            # Get video transcript if requested
            transcript = ""
            if params.get("include_transcript", True):
                transcript = await self._get_video_transcript(video_id)
            
            # Create content
            content = f"# {snippet.get('title', '')}\n\n{snippet.get('description', '')}"
            
            if transcript:
                content += f"\n\n## Transcript\n\n{transcript}"
            
            if comments:
                content += "\n\n## Comments\n\n"
                for comment in comments:
                    content += f"### {comment.get('author', '')}\n\n{comment.get('text', '')}\n\n"
            
            # Parse published date
            published_at = None
            if snippet.get("publishedAt"):
                try:
                    published_at = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass
            
            # Create metadata
            metadata = {
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "channel_id": snippet.get("channelId", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "tags": snippet.get("tags", []),
                "category_id": snippet.get("categoryId", ""),
                "live_broadcast_content": snippet.get("liveBroadcastContent", ""),
                "duration": content_details.get("duration", ""),
                "dimension": content_details.get("dimension", ""),
                "definition": content_details.get("definition", ""),
                "caption": content_details.get("caption", ""),
                "licensed_content": content_details.get("licensedContent", False),
                "view_count": statistics.get("viewCount", 0),
                "like_count": statistics.get("likeCount", 0),
                "dislike_count": statistics.get("dislikeCount", 0),
                "favorite_count": statistics.get("favoriteCount", 0),
                "comment_count": statistics.get("commentCount", 0),
                "privacy_status": status.get("privacyStatus", ""),
                "upload_status": status.get("uploadStatus", ""),
                "embeddable": status.get("embeddable", True),
                "has_transcript": bool(transcript),
                "comment_data": comments
            }
            
            # Create data item
            item = DataItem(
                source_id=f"youtube_video_{video_id}",
                content=content,
                metadata=metadata,
                url=f"https://www.youtube.com/watch?v={video_id}",
                timestamp=published_at,
                content_type="text/markdown",
                raw_data=video
            )
            
            return [item]
        except Exception as e:
            logger.error(f"Error collecting data from YouTube video {video_id}: {e}")
            return []
    
    async def _get_video_comments(self, video_id: str, max_comments: int = 10) -> List[Dict[str, Any]]:
        """Get comments for a YouTube video."""
        try:
            # Get video comments
            request = self.youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=max_comments,
                order="relevance"
            )
            response = request.execute()
            
            comments = []
            for item in response.get("items", []):
                comment = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "author": comment.get("authorDisplayName", ""),
                    "author_channel_id": comment.get("authorChannelId", {}).get("value", ""),
                    "text": comment.get("textDisplay", ""),
                    "like_count": comment.get("likeCount", 0),
                    "published_at": comment.get("publishedAt", ""),
                    "updated_at": comment.get("updatedAt", "")
                })
            
            return comments
        except HttpError as e:
            if "commentsDisabled" in str(e):
                logger.warning(f"Comments are disabled for video {video_id}")
                return []
            else:
                logger.error(f"Error getting comments for YouTube video {video_id}: {e}")
                return []
        except Exception as e:
            logger.error(f"Error getting comments for YouTube video {video_id}: {e}")
            return []
    
    async def _get_video_transcript(self, video_id: str) -> str:
        """Get transcript for a YouTube video."""
        try:
            # YouTube doesn't provide a direct API for transcripts
            # This would typically require a third-party library like youtube_transcript_api
            # For now, we'll return an empty string
            logger.warning("YouTube transcript extraction not implemented yet")
            return ""
        except Exception as e:
            logger.error(f"Error getting transcript for YouTube video {video_id}: {e}")
            return ""
    
    async def _collect_channel(self, channel_id: str, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from a specific YouTube channel."""
        try:
            # Get channel details
            request = self.youtube.channels().list(
                part="snippet,contentDetails,statistics,brandingSettings",
                id=channel_id
            )
            response = request.execute()
            
            if not response.get("items"):
                logger.warning(f"No channel found with ID: {channel_id}")
                return []
            
            channel = response["items"][0]
            snippet = channel["snippet"]
            content_details = channel["contentDetails"]
            statistics = channel["statistics"]
            branding_settings = channel.get("brandingSettings", {})
            
            # Get channel videos if requested
            videos = []
            if params.get("include_videos", True):
                # Get uploads playlist ID
                uploads_playlist_id = content_details.get("relatedPlaylists", {}).get("uploads", "")
                if uploads_playlist_id:
                    videos = await self._get_playlist_videos(
                        uploads_playlist_id,
                        max_videos=params.get("max_videos", 10)
                    )
            
            # Create content
            content = f"# {snippet.get('title', '')}\n\n{snippet.get('description', '')}"
            
            if videos:
                content += "\n\n## Recent Videos\n\n"
                for video in videos:
                    video_snippet = video["snippet"]
                    content += f"### [{video_snippet.get('title', '')}](https://www.youtube.com/watch?v={video['id']})\n\n"
                    content += f"{video_snippet.get('description', '')}\n\n"
            
            # Parse published date
            published_at = None
            if snippet.get("publishedAt"):
                try:
                    published_at = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass
            
            # Create metadata
            metadata = {
                "channel_id": channel_id,
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "custom_url": snippet.get("customUrl", ""),
                "published_at": snippet.get("publishedAt", ""),
                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                "country": snippet.get("country", ""),
                "view_count": statistics.get("viewCount", 0),
                "subscriber_count": statistics.get("subscriberCount", 0),
                "hidden_subscriber_count": statistics.get("hiddenSubscriberCount", False),
                "video_count": statistics.get("videoCount", 0),
                "keywords": branding_settings.get("channel", {}).get("keywords", ""),
                "videos": [
                    {
                        "id": video["id"],
                        "title": video["snippet"].get("title", ""),
                        "published_at": video["snippet"].get("publishedAt", "")
                    }
                    for video in videos
                ]
            }
            
            # Create data item
            item = DataItem(
                source_id=f"youtube_channel_{channel_id}",
                content=content,
                metadata=metadata,
                url=f"https://www.youtube.com/channel/{channel_id}",
                timestamp=published_at,
                content_type="text/markdown",
                raw_data={"channel": channel, "videos": videos}
            )
            
            return [item]
        except Exception as e:
            logger.error(f"Error collecting data from YouTube channel {channel_id}: {e}")
            return []
    
    async def _collect_playlist(self, playlist_id: str, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from a specific YouTube playlist."""
        try:
            # Get playlist details
            request = self.youtube.playlists().list(
                part="snippet,contentDetails",
                id=playlist_id
            )
            response = request.execute()
            
            if not response.get("items"):
                logger.warning(f"No playlist found with ID: {playlist_id}")
                return []
            
            playlist = response["items"][0]
            snippet = playlist["snippet"]
            content_details = playlist["contentDetails"]
            
            # Get playlist videos
            videos = await self._get_playlist_videos(
                playlist_id,
                max_videos=params.get("max_videos", 10)
            )
            
            # Create content
            content = f"# {snippet.get('title', '')}\n\n{snippet.get('description', '')}"
            
            if videos:
                content += "\n\n## Videos\n\n"
                for video in videos:
                    video_snippet = video["snippet"]
                    content += f"### [{video_snippet.get('title', '')}](https://www.youtube.com/watch?v={video['id']})\n\n"
                    content += f"{video_snippet.get('description', '')}\n\n"
            
            # Parse published date
            published_at = None
            if snippet.get("publishedAt"):
                try:
                    published_at = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass
            
            # Create metadata
            metadata = {
                "playlist_id": playlist_id,
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "channel_id": snippet.get("channelId", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "item_count": content_details.get("itemCount", 0),
                "videos": [
                    {
                        "id": video["id"],
                        "title": video["snippet"].get("title", ""),
                        "published_at": video["snippet"].get("publishedAt", "")
                    }
                    for video in videos
                ]
            }
            
            # Create data item
            item = DataItem(
                source_id=f"youtube_playlist_{playlist_id}",
                content=content,
                metadata=metadata,
                url=f"https://www.youtube.com/playlist?list={playlist_id}",
                timestamp=published_at,
                content_type="text/markdown",
                raw_data={"playlist": playlist, "videos": videos}
            )
            
            return [item]
        except Exception as e:
            logger.error(f"Error collecting data from YouTube playlist {playlist_id}: {e}")
            return []
    
    async def _get_playlist_videos(self, playlist_id: str, max_videos: int = 10) -> List[Dict[str, Any]]:
        """Get videos from a YouTube playlist."""
        try:
            videos = []
            next_page_token = None
            
            while len(videos) < max_videos:
                # Get playlist items
                request = self.youtube.playlistItems().list(
                    part="snippet,contentDetails",
                    playlistId=playlist_id,
                    maxResults=min(50, max_videos - len(videos)),
                    pageToken=next_page_token
                )
                response = request.execute()
                
                # Process items
                for item in response.get("items", []):
                    video_id = item["contentDetails"]["videoId"]
                    videos.append({
                        "id": video_id,
                        "snippet": item["snippet"]
                    })
                
                # Check if there are more pages
                next_page_token = response.get("nextPageToken")
                if not next_page_token or len(videos) >= max_videos:
                    break
            
            return videos
        except Exception as e:
            logger.error(f"Error getting videos from YouTube playlist {playlist_id}: {e}")
            return []
    
    async def _search_videos(self, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """Search for YouTube videos."""
        try:
            # Set up search parameters
            max_results = params.get("max_results", 10)
            search_type = params.get("type", "video")
            order = params.get("order", "relevance")
            
            # Execute search
            request = self.youtube.search().list(
                part="snippet",
                q=query,
                type=search_type,
                order=order,
                maxResults=max_results
            )
            response = request.execute()
            
            # Process search results
            results = []
            for item in response.get("items", []):
                if item["id"]["kind"] == "youtube#video":
                    video_id = item["id"]["videoId"]
                    
                    # Get detailed video information if requested
                    if params.get("include_details", True):
                        video_items = await self._collect_video(video_id, params)
                        results.extend(video_items)
                    else:
                        # Create a simple data item with basic information
                        snippet = item["snippet"]
                        
                        # Parse published date
                        published_at = None
                        if snippet.get("publishedAt"):
                            try:
                                published_at = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
                            except (ValueError, TypeError):
                                pass
                        
                        # Create data item
                        data_item = DataItem(
                            source_id=f"youtube_video_{video_id}",
                            content=f"# {snippet.get('title', '')}\n\n{snippet.get('description', '')}",
                            metadata={
                                "video_id": video_id,
                                "title": snippet.get("title", ""),
                                "description": snippet.get("description", ""),
                                "channel_id": snippet.get("channelId", ""),
                                "channel_title": snippet.get("channelTitle", ""),
                                "published_at": snippet.get("publishedAt", ""),
                                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", "")
                            },
                            url=f"https://www.youtube.com/watch?v={video_id}",
                            timestamp=published_at,
                            content_type="text/markdown",
                            raw_data=item
                        )
                        
                        results.append(data_item)
                
                elif item["id"]["kind"] == "youtube#channel" and search_type in ["channel", "all"]:
                    channel_id = item["id"]["channelId"]
                    
                    # Get detailed channel information if requested
                    if params.get("include_details", True):
                        channel_items = await self._collect_channel(channel_id, params)
                        results.extend(channel_items)
                    else:
                        # Create a simple data item with basic information
                        snippet = item["snippet"]
                        
                        # Parse published date
                        published_at = None
                        if snippet.get("publishedAt"):
                            try:
                                published_at = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
                            except (ValueError, TypeError):
                                pass
                        
                        # Create data item
                        data_item = DataItem(
                            source_id=f"youtube_channel_{channel_id}",
                            content=f"# {snippet.get('title', '')}\n\n{snippet.get('description', '')}",
                            metadata={
                                "channel_id": channel_id,
                                "title": snippet.get("title", ""),
                                "description": snippet.get("description", ""),
                                "published_at": snippet.get("publishedAt", ""),
                                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", "")
                            },
                            url=f"https://www.youtube.com/channel/{channel_id}",
                            timestamp=published_at,
                            content_type="text/markdown",
                            raw_data=item
                        )
                        
                        results.append(data_item)
                
                elif item["id"]["kind"] == "youtube#playlist" and search_type in ["playlist", "all"]:
                    playlist_id = item["id"]["playlistId"]
                    
                    # Get detailed playlist information if requested
                    if params.get("include_details", True):
                        playlist_items = await self._collect_playlist(playlist_id, params)
                        results.extend(playlist_items)
                    else:
                        # Create a simple data item with basic information
                        snippet = item["snippet"]
                        
                        # Parse published date
                        published_at = None
                        if snippet.get("publishedAt"):
                            try:
                                published_at = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
                            except (ValueError, TypeError):
                                pass
                        
                        # Create data item
                        data_item = DataItem(
                            source_id=f"youtube_playlist_{playlist_id}",
                            content=f"# {snippet.get('title', '')}\n\n{snippet.get('description', '')}",
                            metadata={
                                "playlist_id": playlist_id,
                                "title": snippet.get("title", ""),
                                "description": snippet.get("description", ""),
                                "channel_id": snippet.get("channelId", ""),
                                "channel_title": snippet.get("channelTitle", ""),
                                "published_at": snippet.get("publishedAt", ""),
                                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", "")
                            },
                            url=f"https://www.youtube.com/playlist?list={playlist_id}",
                            timestamp=published_at,
                            content_type="text/markdown",
                            raw_data=item
                        )
                        
                        results.append(data_item)
            
            return results
        except Exception as e:
            logger.error(f"Error searching YouTube videos with query {query}: {e}")
            return []
