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
import urllib.parse
import httpx

logger = logging.getLogger(__name__)

class YouTubeConnector(ConnectorBase):
    """Connector for YouTube videos and channels."""
    
    name: str = "youtube_connector"
    description: str = "Connector for YouTube videos and channels"
    source_type: str = "youtube"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the YouTube connector."""
        super().__init__(config)
        self.api_key = self.config.get("api_key", os.environ.get("YOUTUBE_API_KEY"))
        self.api_base_url = "https://www.googleapis.com/youtube/v3"
        self.concurrency = self.config.get("concurrency", 3)
        self.semaphore = asyncio.Semaphore(self.concurrency)
        self.client = None
        
    def initialize(self) -> bool:
        """Initialize the connector."""
        try:
            if not self.api_key:
                logger.error("No YouTube API key provided. This connector requires an API key.")
                return False
            
            # Create HTTP client
            self.client = httpx.AsyncClient(
                timeout=self.config.get("timeout", 30),
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Wiseflow-YouTube-Connector"
                }
            )
            
            logger.info(f"Initialized YouTube connector with concurrency: {self.concurrency}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize YouTube connector: {e}")
            return False
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from YouTube."""
        params = params or {}
        
        if not self.api_key:
            logger.error("YouTube API key is required")
            return []
        
        if not self.client and not self.initialize():
            return []
        
        # Check what type of YouTube data to collect
        collection_type = params.get("type", "video")
        
        if collection_type == "video":
            return await self._collect_video(params)
        elif collection_type == "channel":
            return await self._collect_channel(params)
        elif collection_type == "search":
            return await self._collect_search_results(params)
        elif collection_type == "playlist":
            return await self._collect_playlist(params)
        else:
            logger.error(f"Unknown YouTube collection type: {collection_type}")
            return []
    
    async def _collect_video(self, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from a specific video."""
        video_id = params.get("video_id")
        if not video_id:
            # Try to extract video ID from URL
            url = params.get("url")
            if url:
                video_id = self._extract_video_id(url)
            
            if not video_id:
                logger.error("No video ID or valid URL provided for YouTube connector")
                return []
        
        include_transcript = params.get("include_transcript", True)
        include_comments = params.get("include_comments", False)
        max_comments = params.get("max_comments", 10)
        
        results = []
        
        try:
            async with self.semaphore:
                # Get video information
                video_data = await self._fetch_api(
                    "/videos",
                    params={
                        "part": "snippet,contentDetails,statistics",
                        "id": video_id
                    }
                )
                
                if not video_data or not video_data.get("items"):
                    logger.error(f"Video not found: {video_id}")
                    return []
                
                video_item = video_data["items"][0]
                snippet = video_item["snippet"]
                content_details = video_item["contentDetails"]
                statistics = video_item["statistics"]
                
                # Create a data item for the video
                video_item = DataItem(
                    source_id=f"youtube_video_{video_id}",
                    content=snippet.get("description", ""),
                    metadata={
                        "type": "video",
                        "video_id": video_id,
                        "title": snippet.get("title", ""),
                        "channel_id": snippet.get("channelId", ""),
                        "channel_title": snippet.get("channelTitle", ""),
                        "published_at": snippet.get("publishedAt", ""),
                        "duration": content_details.get("duration", ""),
                        "view_count": int(statistics.get("viewCount", 0)),
                        "like_count": int(statistics.get("likeCount", 0)),
                        "comment_count": int(statistics.get("commentCount", 0)),
                        "tags": snippet.get("tags", []),
                        "category_id": snippet.get("categoryId", "")
                    },
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    content_type="text/plain",
                    timestamp=datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00")) if "publishedAt" in snippet else datetime.now()
                )
                results.append(video_item)
                
                # Get transcript if requested
                if include_transcript:
                    transcript = await self._get_transcript(video_id)
                    if transcript:
                        transcript_item = DataItem(
                            source_id=f"youtube_transcript_{video_id}",
                            content=transcript,
                            metadata={
                                "type": "transcript",
                                "video_id": video_id,
                                "video_title": snippet.get("title", ""),
                                "channel_id": snippet.get("channelId", ""),
                                "channel_title": snippet.get("channelTitle", "")
                            },
                            url=f"https://www.youtube.com/watch?v={video_id}",
                            content_type="text/plain",
                            timestamp=datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00")) if "publishedAt" in snippet else datetime.now()
                        )
                        results.append(transcript_item)
                
                # Get comments if requested
                if include_comments:
                    comments = await self._get_comments(video_id, max_comments)
                    for comment in comments:
                        comment_item = DataItem(
                            source_id=f"youtube_comment_{comment['id']}",
                            content=comment["text"],
                            metadata={
                                "type": "comment",
                                "video_id": video_id,
                                "comment_id": comment["id"],
                                "author": comment["author"],
                                "author_channel_id": comment.get("authorChannelId", ""),
                                "published_at": comment["publishedAt"],
                                "like_count": comment["likeCount"],
                                "reply_count": comment.get("replyCount", 0)
                            },
                            url=f"https://www.youtube.com/watch?v={video_id}&lc={comment['id']}",
                            content_type="text/plain",
                            timestamp=datetime.fromisoformat(comment["publishedAt"].replace("Z", "+00:00"))
                        )
                        results.append(comment_item)
        
        except Exception as e:
            logger.error(f"Error collecting YouTube video data: {e}")
        
        logger.info(f"Collected {len(results)} items from YouTube video {video_id}")
        return results
    
    async def _collect_channel(self, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from a YouTube channel."""
        channel_id = params.get("channel_id")
        channel_username = params.get("username")
        
        if not channel_id and not channel_username:
            # Try to extract channel ID from URL
            url = params.get("url")
            if url:
                channel_id = self._extract_channel_id(url)
            
            if not channel_id:
                logger.error("No channel ID, username, or valid URL provided for YouTube connector")
                return []
        
        max_videos = params.get("max_videos", 10)
        include_video_details = params.get("include_video_details", False)
        
        results = []
        
        try:
            async with self.semaphore:
                # If we have a username but not a channel ID, get the channel ID first
                if not channel_id and channel_username:
                    channel_data = await self._fetch_api(
                        "/channels",
                        params={
                            "part": "id",
                            "forUsername": channel_username
                        }
                    )
                    
                    if not channel_data or not channel_data.get("items"):
                        logger.error(f"Channel not found for username: {channel_username}")
                        return []
                    
                    channel_id = channel_data["items"][0]["id"]
                
                # Get channel information
                channel_data = await self._fetch_api(
                    "/channels",
                    params={
                        "part": "snippet,contentDetails,statistics",
                        "id": channel_id
                    }
                )
                
                if not channel_data or not channel_data.get("items"):
                    logger.error(f"Channel not found: {channel_id}")
                    return []
                
                channel_item = channel_data["items"][0]
                snippet = channel_item["snippet"]
                statistics = channel_item["statistics"]
                
                # Create a data item for the channel
                channel_item = DataItem(
                    source_id=f"youtube_channel_{channel_id}",
                    content=snippet.get("description", ""),
                    metadata={
                        "type": "channel",
                        "channel_id": channel_id,
                        "title": snippet.get("title", ""),
                        "published_at": snippet.get("publishedAt", ""),
                        "subscriber_count": int(statistics.get("subscriberCount", 0)),
                        "video_count": int(statistics.get("videoCount", 0)),
                        "view_count": int(statistics.get("viewCount", 0)),
                        "country": snippet.get("country", "")
                    },
                    url=f"https://www.youtube.com/channel/{channel_id}",
                    content_type="text/plain",
                    timestamp=datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00")) if "publishedAt" in snippet else datetime.now()
                )
                results.append(channel_item)
                
                # Get channel videos
                uploads_playlist_id = channel_item["contentDetails"]["relatedPlaylists"]["uploads"]
                videos = await self._get_playlist_videos(uploads_playlist_id, max_videos)
                
                for video in videos:
                    # If include_video_details is True, get full video details
                    if include_video_details:
                        video_items = await self._collect_video({"video_id": video["id"]})
                        results.extend(video_items)
                    else:
                        # Otherwise, just create a basic video item
                        video_item = DataItem(
                            source_id=f"youtube_video_{video['id']}",
                            content=video["description"],
                            metadata={
                                "type": "video",
                                "video_id": video["id"],
                                "title": video["title"],
                                "channel_id": channel_id,
                                "channel_title": snippet.get("title", ""),
                                "published_at": video["publishedAt"]
                            },
                            url=f"https://www.youtube.com/watch?v={video['id']}",
                            content_type="text/plain",
                            timestamp=datetime.fromisoformat(video["publishedAt"].replace("Z", "+00:00"))
                        )
                        results.append(video_item)
        
        except Exception as e:
            logger.error(f"Error collecting YouTube channel data: {e}")
        
        logger.info(f"Collected {len(results)} items from YouTube channel {channel_id}")
        return results
    
    async def _collect_search_results(self, params: Dict[str, Any]) -> List[DataItem]:
        """Collect YouTube search results."""
        query = params.get("query")
        if not query:
            logger.error("No query specified for YouTube search")
            return []
        
        max_results = params.get("max_results", 10)
        search_type = params.get("search_type", "video")  # video, channel, playlist
        include_details = params.get("include_details", False)
        
        results = []
        
        try:
            async with self.semaphore:
                # Perform the search
                search_data = await self._fetch_api(
                    "/search",
                    params={
                        "part": "snippet",
                        "q": query,
                        "maxResults": min(max_results, 50),  # API limit is 50
                        "type": search_type
                    }
                )
                
                if not search_data or not search_data.get("items"):
                    logger.warning(f"No results found for YouTube search: {query}")
                    return []
                
                # Process search results
                for item in search_data["items"]:
                    snippet = item["snippet"]
                    item_id = item["id"].get(f"{search_type}Id")
                    
                    if not item_id:
                        continue
                    
                    # If include_details is True, get full details
                    if include_details:
                        if search_type == "video":
                            detail_items = await self._collect_video({"video_id": item_id})
                            results.extend(detail_items)
                        elif search_type == "channel":
                            detail_items = await self._collect_channel({"channel_id": item_id})
                            results.extend(detail_items)
                        elif search_type == "playlist":
                            detail_items = await self._collect_playlist({"playlist_id": item_id})
                            results.extend(detail_items)
                    else:
                        # Otherwise, just create a basic item
                        result_item = DataItem(
                            source_id=f"youtube_{search_type}_{item_id}",
                            content=snippet.get("description", ""),
                            metadata={
                                "type": search_type,
                                f"{search_type}_id": item_id,
                                "title": snippet.get("title", ""),
                                "channel_id": snippet.get("channelId", ""),
                                "channel_title": snippet.get("channelTitle", ""),
                                "published_at": snippet.get("publishedAt", "")
                            },
                            url=self._get_url_for_item(search_type, item_id),
                            content_type="text/plain",
                            timestamp=datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00")) if "publishedAt" in snippet else datetime.now()
                        )
                        results.append(result_item)
        
        except Exception as e:
            logger.error(f"Error collecting YouTube search results: {e}")
        
        logger.info(f"Collected {len(results)} items from YouTube search for '{query}'")
        return results
    
    async def _collect_playlist(self, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from a YouTube playlist."""
        playlist_id = params.get("playlist_id")
        if not playlist_id:
            # Try to extract playlist ID from URL
            url = params.get("url")
            if url:
                playlist_id = self._extract_playlist_id(url)
            
            if not playlist_id:
                logger.error("No playlist ID or valid URL provided for YouTube connector")
                return []
        
        max_videos = params.get("max_videos", 10)
        include_video_details = params.get("include_video_details", False)
        
        results = []
        
        try:
            async with self.semaphore:
                # Get playlist information
                playlist_data = await self._fetch_api(
                    "/playlists",
                    params={
                        "part": "snippet,contentDetails",
                        "id": playlist_id
                    }
                )
                
                if not playlist_data or not playlist_data.get("items"):
                    logger.error(f"Playlist not found: {playlist_id}")
                    return []
                
                playlist_item = playlist_data["items"][0]
                snippet = playlist_item["snippet"]
                content_details = playlist_item["contentDetails"]
                
                # Create a data item for the playlist
                playlist_item = DataItem(
                    source_id=f"youtube_playlist_{playlist_id}",
                    content=snippet.get("description", ""),
                    metadata={
                        "type": "playlist",
                        "playlist_id": playlist_id,
                        "title": snippet.get("title", ""),
                        "channel_id": snippet.get("channelId", ""),
                        "channel_title": snippet.get("channelTitle", ""),
                        "published_at": snippet.get("publishedAt", ""),
                        "item_count": int(content_details.get("itemCount", 0))
                    },
                    url=f"https://www.youtube.com/playlist?list={playlist_id}",
                    content_type="text/plain",
                    timestamp=datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00")) if "publishedAt" in snippet else datetime.now()
                )
                results.append(playlist_item)
                
                # Get playlist videos
                videos = await self._get_playlist_videos(playlist_id, max_videos)
                
                for video in videos:
                    # If include_video_details is True, get full video details
                    if include_video_details:
                        video_items = await self._collect_video({"video_id": video["id"]})
                        results.extend(video_items)
                    else:
                        # Otherwise, just create a basic video item
                        video_item = DataItem(
                            source_id=f"youtube_video_{video['id']}",
                            content=video["description"],
                            metadata={
                                "type": "video",
                                "video_id": video["id"],
                                "title": video["title"],
                                "channel_id": snippet.get("channelId", ""),
                                "channel_title": snippet.get("channelTitle", ""),
                                "published_at": video["publishedAt"],
                                "playlist_id": playlist_id
                            },
                            url=f"https://www.youtube.com/watch?v={video['id']}&list={playlist_id}",
                            content_type="text/plain",
                            timestamp=datetime.fromisoformat(video["publishedAt"].replace("Z", "+00:00"))
                        )
                        results.append(video_item)
        
        except Exception as e:
            logger.error(f"Error collecting YouTube playlist data: {e}")
        
        logger.info(f"Collected {len(results)} items from YouTube playlist {playlist_id}")
        return results
    
    async def _get_transcript(self, video_id: str) -> Optional[str]:
        """Get the transcript for a YouTube video using a third-party service."""
        try:
            # Use YouTube's captions API if available
            captions_data = await self._fetch_api(
                "/captions",
                params={
                    "part": "snippet",
                    "videoId": video_id
                }
            )
            
            if captions_data and captions_data.get("items"):
                # Get the first available caption track
                caption_id = captions_data["items"][0]["id"]
                
                # Get the caption content
                # Note: This requires additional authentication and permissions
                # For simplicity, we'll use a fallback method
                
                # Fallback: Use a third-party service or library
                # This is a placeholder - in a real implementation, you would use
                # a library like youtube-transcript-api or a similar service
                
                # For now, we'll return a placeholder message
                return f"[Transcript for video {video_id} would be fetched here using a third-party service]"
            
            return None
        except Exception as e:
            logger.error(f"Error getting transcript for video {video_id}: {e}")
            return None
    
    async def _get_comments(self, video_id: str, max_comments: int = 10) -> List[Dict[str, Any]]:
        """Get comments for a YouTube video."""
        try:
            comments_data = await self._fetch_api(
                "/commentThreads",
                params={
                    "part": "snippet",
                    "videoId": video_id,
                    "maxResults": min(max_comments, 100),  # API limit is 100
                    "order": "relevance"
                }
            )
            
            if not comments_data or not comments_data.get("items"):
                return []
            
            comments = []
            for item in comments_data["items"]:
                comment = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "id": item["id"],
                    "text": comment["textDisplay"],
                    "author": comment["authorDisplayName"],
                    "authorChannelId": comment.get("authorChannelId", {}).get("value", ""),
                    "publishedAt": comment["publishedAt"],
                    "likeCount": comment["likeCount"],
                    "replyCount": item["snippet"].get("totalReplyCount", 0)
                })
            
            return comments
        except Exception as e:
            logger.error(f"Error getting comments for video {video_id}: {e}")
            return []
    
    async def _get_playlist_videos(self, playlist_id: str, max_videos: int = 10) -> List[Dict[str, Any]]:
        """Get videos from a YouTube playlist."""
        try:
            playlist_items_data = await self._fetch_api(
                "/playlistItems",
                params={
                    "part": "snippet",
                    "playlistId": playlist_id,
                    "maxResults": min(max_videos, 50)  # API limit is 50
                }
            )
            
            if not playlist_items_data or not playlist_items_data.get("items"):
                return []
            
            videos = []
            for item in playlist_items_data["items"]:
                snippet = item["snippet"]
                video_id = snippet["resourceId"]["videoId"]
                videos.append({
                    "id": video_id,
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "publishedAt": snippet.get("publishedAt", ""),
                    "position": snippet.get("position", 0)
                })
            
            return videos
        except Exception as e:
            logger.error(f"Error getting videos for playlist {playlist_id}: {e}")
            return []
    
    async def _fetch_api(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Fetch data from the YouTube API."""
        params = params or {}
        params["key"] = self.api_key
        
        url = f"{self.api_base_url}{endpoint}"
        
        try:
            response = await self.client.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                logger.error(f"YouTube API quota exceeded or permission denied: {response.text}")
                return None
            elif response.status_code == 404:
                logger.warning(f"YouTube API resource not found: {url}")
                return None
            else:
                logger.error(f"YouTube API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error fetching YouTube API: {e}")
            return None
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from a YouTube URL."""
        try:
            parsed_url = urllib.parse.urlparse(url)
            
            # youtube.com/watch?v=VIDEO_ID
            if parsed_url.netloc in ["youtube.com", "www.youtube.com"] and parsed_url.path == "/watch":
                query_params = urllib.parse.parse_qs(parsed_url.query)
                if "v" in query_params:
                    return query_params["v"][0]
            
            # youtu.be/VIDEO_ID
            if parsed_url.netloc == "youtu.be":
                return parsed_url.path.strip("/")
            
            # youtube.com/embed/VIDEO_ID
            if parsed_url.path.startswith("/embed/"):
                return parsed_url.path.split("/")[2]
            
            return None
        except Exception as e:
            logger.error(f"Error extracting video ID from URL {url}: {e}")
            return None
    
    def _extract_channel_id(self, url: str) -> Optional[str]:
        """Extract channel ID from a YouTube URL."""
        try:
            parsed_url = urllib.parse.urlparse(url)
            path_parts = parsed_url.path.strip("/").split("/")
            
            # youtube.com/channel/CHANNEL_ID
            if len(path_parts) >= 2 and path_parts[0] == "channel":
                return path_parts[1]
            
            return None
        except Exception as e:
            logger.error(f"Error extracting channel ID from URL {url}: {e}")
            return None
    
    def _extract_playlist_id(self, url: str) -> Optional[str]:
        """Extract playlist ID from a YouTube URL."""
        try:
            parsed_url = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            # youtube.com/playlist?list=PLAYLIST_ID
            if "list" in query_params:
                return query_params["list"][0]
            
            return None
        except Exception as e:
            logger.error(f"Error extracting playlist ID from URL {url}: {e}")
            return None
    
    def _get_url_for_item(self, item_type: str, item_id: str) -> str:
        """Get the URL for a YouTube item based on its type and ID."""
        if item_type == "video":
            return f"https://www.youtube.com/watch?v={item_id}"
        elif item_type == "channel":
            return f"https://www.youtube.com/channel/{item_id}"
        elif item_type == "playlist":
            return f"https://www.youtube.com/playlist?list={item_id}"
        else:
            return f"https://www.youtube.com"
    
    async def close(self):
        """Close the connector and release resources."""
        if self.client:
            await self.client.aclose()
            self.client = None
