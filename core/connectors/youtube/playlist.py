"""
YouTube playlist collection functionality.

This module provides functionality to collect data from YouTube playlists.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from googleapiclient.errors import HttpError

from core.connectors import DataItem

from .utils import retry_async, generate_cache_key, parse_youtube_datetime
from .errors import handle_youtube_api_error
from .video import YouTubeVideoCollector
from .channel import YouTubeChannelCollector

logger = logging.getLogger(__name__)

class YouTubePlaylistCollector:
    """Collector for YouTube playlists."""
    
    def __init__(self, connector):
        """
        Initialize the playlist collector.
        
        Args:
            connector: YouTube connector instance
        """
        self.connector = connector
        self.youtube = connector.youtube
        self.semaphore = connector.semaphore
        self.rate_limiter = connector.rate_limiter
        self.cache = connector.cache
        self.config = connector.config
        self.video_collector = YouTubeVideoCollector(connector)
        self.channel_collector = YouTubeChannelCollector(connector)
    
    @retry_async(
        max_retries=3,
        retry_status_codes=[429, 500, 502, 503, 504],
        backoff_factor=2,
        max_backoff=60
    )
    async def collect_playlist(self, playlist_id: str, params: Dict[str, Any]) -> List[DataItem]:
        """
        Collect data from a specific YouTube playlist.
        
        Args:
            playlist_id: YouTube playlist ID
            params: Collection parameters
            
        Returns:
            List[DataItem]: Collected data items
        """
        try:
            # Check cache first
            if self.cache:
                cache_key = generate_cache_key("collect_playlist", playlist_id, params)
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
            
            # Acquire rate limiter
            await self.rate_limiter.acquire()
            
            # Get playlist details
            async with self.semaphore:
                request = self.youtube.playlists().list(
                    part="snippet,contentDetails,status",
                    id=playlist_id
                )
                response = request.execute()
            
            if not response.get("items"):
                logger.warning(f"No playlist found with ID: {playlist_id}")
                return []
            
            playlist = response["items"][0]
            snippet = playlist["snippet"]
            content_details = playlist["contentDetails"]
            status = playlist["status"]
            
            # Get playlist videos
            max_videos = params.get("max_videos", self.config["max_videos_per_playlist"])
            videos = await self.channel_collector._get_playlist_videos(playlist_id, max_videos)
            
            # Get detailed video information if requested
            video_items = []
            if params.get("include_video_details", True):
                for video in videos:
                    video_id = video["id"]
                    video_params = {
                        "include_comments": params.get("include_comments", False),
                        "include_transcript": params.get("include_transcript", False),
                        "max_comments": params.get("max_comments", 10)
                    }
                    items = await self.video_collector.collect_video(video_id, video_params)
                    video_items.extend(items)
            
            # Create content
            title = snippet.get("title", "")
            description = snippet.get("description", "")
            
            content = f"# {title}\\n\\n{description}"
            
            if videos:
                content += "\\n\\n## Videos\\n\\n"
                for video in videos:
                    video_title = video["snippet"].get("title", "")
                    video_id = video["id"]
                    content += f"- [{video_title}](https://www.youtube.com/watch?v={video_id})\\n"
            
            # Parse published date
            published_at = parse_youtube_datetime(snippet.get("publishedAt"))
            
            # Create metadata
            metadata = {
                "playlist_id": playlist_id,
                "title": title,
                "description": description,
                "channel_id": snippet.get("channelId", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "privacy_status": status.get("privacyStatus", ""),
                "item_count": content_details.get("itemCount", 0),
                "videos_fetched": len(videos),
                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
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
            
            result = [item] + video_items
            
            # Cache the result
            if self.cache:
                self.cache.set(cache_key, result)
            
            return result
        except HttpError as e:
            raise handle_youtube_api_error(e, "playlist", playlist_id)
        except Exception as e:
            logger.error(f"Error collecting data from YouTube playlist {playlist_id}: {e}")
            return []

