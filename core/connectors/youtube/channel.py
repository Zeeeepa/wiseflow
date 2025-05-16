"""
YouTube channel collection functionality.

This module provides functionality to collect data from YouTube channels.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from googleapiclient.errors import HttpError

from core.connectors import DataItem

from .utils import retry_async, generate_cache_key, paginate, parse_youtube_datetime
from .errors import handle_youtube_api_error
from .video import YouTubeVideoCollector

logger = logging.getLogger(__name__)

class YouTubeChannelCollector:
    """Collector for YouTube channels."""
    
    def __init__(self, connector):
        """
        Initialize the channel collector.
        
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
    
    @retry_async(
        max_retries=3,
        retry_status_codes=[429, 500, 502, 503, 504],
        backoff_factor=2,
        max_backoff=60
    )
    async def collect_channel(self, channel_id: str, params: Dict[str, Any]) -> List[DataItem]:
        """
        Collect data from a specific YouTube channel.
        
        Args:
            channel_id: YouTube channel ID
            params: Collection parameters
            
        Returns:
            List[DataItem]: Collected data items
        """
        try:
            # Check cache first
            if self.cache:
                cache_key = generate_cache_key("collect_channel", channel_id, params)
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
            
            # Acquire rate limiter
            await self.rate_limiter.acquire()
            
            # Get channel details
            async with self.semaphore:
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
            video_items = []
            
            if params.get("include_videos", True):
                max_videos = params.get("max_videos", self.config["max_videos_per_channel"])
                
                # Get uploads playlist ID
                uploads_playlist_id = content_details.get("relatedPlaylists", {}).get("uploads")
                
                if uploads_playlist_id:
                    # Get videos from uploads playlist
                    videos = await self._get_playlist_videos(uploads_playlist_id, max_videos)
                    
                    # Get detailed video information if requested
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
            
            if branding_settings.get("channel", {}).get("keywords"):
                content += f"\\n\\n## Keywords\\n\\n{branding_settings['channel']['keywords']}"
            
            # Parse published date
            published_at = parse_youtube_datetime(snippet.get("publishedAt"))
            
            # Create metadata
            metadata = {
                "channel_id": channel_id,
                "title": title,
                "description": description,
                "published_at": snippet.get("publishedAt", ""),
                "country": snippet.get("country", ""),
                "view_count": int(statistics.get("viewCount", 0)),
                "subscriber_count": int(statistics.get("subscriberCount", 0)),
                "hidden_subscriber_count": statistics.get("hiddenSubscriberCount", False),
                "video_count": int(statistics.get("videoCount", 0)),
                "keywords": branding_settings.get("channel", {}).get("keywords", ""),
                "uploads_playlist_id": content_details.get("relatedPlaylists", {}).get("uploads", ""),
                "videos_fetched": len(videos),
                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", "")
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
            
            result = [item] + video_items
            
            # Cache the result
            if self.cache:
                self.cache.set(cache_key, result)
            
            return result
        except HttpError as e:
            raise handle_youtube_api_error(e, "channel", channel_id)
        except Exception as e:
            logger.error(f"Error collecting data from YouTube channel {channel_id}: {e}")
            return []
    
    @retry_async(
        max_retries=3,
        retry_status_codes=[429, 500, 502, 503, 504],
        backoff_factor=2,
        max_backoff=60
    )
    async def _get_playlist_videos(self, playlist_id: str, max_videos: int = 50) -> List[Dict[str, Any]]:
        """
        Get videos from a YouTube playlist.
        
        Args:
            playlist_id: YouTube playlist ID
            max_videos: Maximum number of videos to retrieve
            
        Returns:
            List[Dict[str, Any]]: Playlist videos
        """
        try:
            # Check cache first
            if self.cache:
                cache_key = generate_cache_key("get_playlist_videos", playlist_id, max_videos)
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
            
            # Acquire rate limiter
            await self.rate_limiter.acquire()
            
            videos = []
            next_page_token = None
            
            while len(videos) < max_videos:
                # Get playlist items
                async with self.semaphore:
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
                    
                    if len(videos) >= max_videos:
                        break
                
                # Check if there are more pages
                next_page_token = response.get("nextPageToken")
                if not next_page_token or len(videos) >= max_videos:
                    break
            
            # Cache the result
            if self.cache:
                self.cache.set(cache_key, videos)
            
            return videos
        except HttpError as e:
            raise handle_youtube_api_error(e, "playlist", playlist_id)
        except Exception as e:
            logger.error(f"Error getting videos from YouTube playlist {playlist_id}: {e}")
            return []

