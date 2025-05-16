"""
YouTube search functionality.

This module provides functionality to search for YouTube videos, channels, and playlists.
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
from .playlist import YouTubePlaylistCollector

logger = logging.getLogger(__name__)

class YouTubeSearchCollector:
    """Collector for YouTube search results."""
    
    def __init__(self, connector):
        """
        Initialize the search collector.
        
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
        self.playlist_collector = YouTubePlaylistCollector(connector)
    
    @retry_async(
        max_retries=3,
        retry_status_codes=[429, 500, 502, 503, 504],
        backoff_factor=2,
        max_backoff=60
    )
    async def search_videos(self, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """
        Search for YouTube videos.
        
        Args:
            query: Search query
            params: Search parameters
            
        Returns:
            List[DataItem]: Search results
        """
        try:
            # Check cache first
            if self.cache:
                cache_key = generate_cache_key("search_videos", query, params)
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
            
            # Acquire rate limiter
            await self.rate_limiter.acquire()
            
            # Set up search parameters
            max_results = params.get("max_results", 10)
            search_type = params.get("type", "video")
            order = params.get("order", "relevance")
            published_after = params.get("published_after")
            published_before = params.get("published_before")
            region_code = params.get("region_code")
            language = params.get("language")
            
            # Build search request
            search_params = {
                "part": "snippet",
                "q": query,
                "type": search_type,
                "order": order,
                "maxResults": min(50, max_results)
            }
            
            if published_after:
                search_params["publishedAfter"] = published_after
            
            if published_before:
                search_params["publishedBefore"] = published_before
            
            if region_code:
                search_params["regionCode"] = region_code
            
            if language:
                search_params["relevanceLanguage"] = language
            
            # Execute search
            async with self.semaphore:
                request = self.youtube.search().list(**search_params)
                response = request.execute()
            
            # Process search results
            results = []
            
            for item in response.get("items", []):
                if item["id"]["kind"] == "youtube#video" and search_type in ["video", "all"]:
                    video_id = item["id"]["videoId"]
                    
                    # Get detailed video information if requested
                    if params.get("include_details", True):
                        video_items = await self.video_collector.collect_video(video_id, params)
                        results.extend(video_items)
                    else:
                        # Create a simple data item with basic information
                        snippet = item["snippet"]
                        
                        # Parse published date
                        published_at = parse_youtube_datetime(snippet.get("publishedAt"))
                        
                        # Create data item
                        data_item = DataItem(
                            source_id=f"youtube_video_{video_id}",
                            content=f"# {snippet.get('title', '')}\\n\\n{snippet.get('description', '')}",
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
                        channel_items = await self.channel_collector.collect_channel(channel_id, params)
                        results.extend(channel_items)
                    else:
                        # Create a simple data item with basic information
                        snippet = item["snippet"]
                        
                        # Parse published date
                        published_at = parse_youtube_datetime(snippet.get("publishedAt"))
                        
                        # Create data item
                        data_item = DataItem(
                            source_id=f"youtube_channel_{channel_id}",
                            content=f"# {snippet.get('title', '')}\\n\\n{snippet.get('description', '')}",
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
                        playlist_items = await self.playlist_collector.collect_playlist(playlist_id, params)
                        results.extend(playlist_items)
                    else:
                        # Create a simple data item with basic information
                        snippet = item["snippet"]
                        
                        # Parse published date
                        published_at = parse_youtube_datetime(snippet.get("publishedAt"))
                        
                        # Create data item
                        data_item = DataItem(
                            source_id=f"youtube_playlist_{playlist_id}",
                            content=f"# {snippet.get('title', '')}\\n\\n{snippet.get('description', '')}",
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
            
            # Limit results to max_results
            if len(results) > max_results:
                results = results[:max_results]
            
            # Cache the result
            if self.cache:
                self.cache.set(cache_key, results)
            
            return results
        except HttpError as e:
            raise handle_youtube_api_error(e, "search", query)
        except Exception as e:
            logger.error(f"Error searching YouTube videos with query {query}: {e}")
            return []

