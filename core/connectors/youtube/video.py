"""
YouTube video collection functionality.

This module provides functionality to collect data from YouTube videos.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from googleapiclient.errors import HttpError

from core.connectors import DataItem

from .utils import retry_async, generate_cache_key, format_duration, parse_youtube_datetime
from .errors import handle_youtube_api_error, YouTubeCommentsDisabledError
from .transcript import get_video_transcript, TranscriptFormat

logger = logging.getLogger(__name__)

class YouTubeVideoCollector:
    """Collector for YouTube videos."""
    
    def __init__(self, connector):
        """
        Initialize the video collector.
        
        Args:
            connector: YouTube connector instance
        """
        self.connector = connector
        self.youtube = connector.youtube
        self.semaphore = connector.semaphore
        self.rate_limiter = connector.rate_limiter
        self.cache = connector.cache
        self.config = connector.config
    
    @retry_async(
        max_retries=3,
        retry_status_codes=[429, 500, 502, 503, 504],
        backoff_factor=2,
        max_backoff=60
    )
    async def collect_video(self, video_id: str, params: Dict[str, Any]) -> List[DataItem]:
        """
        Collect data from a specific YouTube video.
        
        Args:
            video_id: YouTube video ID
            params: Collection parameters
            
        Returns:
            List[DataItem]: Collected data items
        """
        try:
            # Check cache first
            if self.cache:
                cache_key = generate_cache_key("collect_video", video_id, params)
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
            
            # Acquire rate limiter
            await self.rate_limiter.acquire()
            
            # Get video details
            async with self.semaphore:
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
            if params.get("include_comments", self.config["include_comments"]):
                max_comments = params.get("max_comments", self.config["max_comments_per_video"])
                comments = await self._get_video_comments(video_id, max_comments)
            
            # Get video transcript if requested
            transcript = ""
            if params.get("include_transcript", self.config["include_transcript"]):
                transcript_format = params.get("transcript_format", TranscriptFormat.PLAIN)
                try:
                    transcript = await get_video_transcript(video_id, transcript_format)
                except Exception as e:
                    logger.warning(f"Failed to get transcript for video {video_id}: {e}")
            
            # Create content
            content = f"# {snippet.get('title', '')}\\n\\n{snippet.get('description', '')}"
            
            if transcript:
                content += f"\\n\\n## Transcript\\n\\n{transcript}"
            
            if comments:
                content += "\\n\\n## Comments\\n\\n"
                for comment in comments:
                    content += f"### {comment.get('author', '')}\\n\\n{comment.get('text', '')}\\n\\n"
            
            # Parse published date
            published_at = parse_youtube_datetime(snippet.get("publishedAt"))
            
            # Format duration
            duration_seconds = format_duration(content_details.get("duration", ""))
            
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
                "duration_seconds": duration_seconds,
                "dimension": content_details.get("dimension", ""),
                "definition": content_details.get("definition", ""),
                "caption": content_details.get("caption", ""),
                "licensed_content": content_details.get("licensedContent", False),
                "view_count": int(statistics.get("viewCount", 0)),
                "like_count": int(statistics.get("likeCount", 0)),
                "dislike_count": int(statistics.get("dislikeCount", 0)) if "dislikeCount" in statistics else 0,
                "favorite_count": int(statistics.get("favoriteCount", 0)),
                "comment_count": int(statistics.get("commentCount", 0)),
                "privacy_status": status.get("privacyStatus", ""),
                "upload_status": status.get("uploadStatus", ""),
                "embeddable": status.get("embeddable", False),
                "public_stats_viewable": status.get("publicStatsViewable", False),
                "has_transcript": bool(transcript),
                "comment_count_fetched": len(comments)
            }
            
            # Create data item
            item = DataItem(
                source_id=f"youtube_video_{video_id}",
                content=content,
                metadata=metadata,
                url=f"https://www.youtube.com/watch?v={video_id}",
                timestamp=published_at,
                content_type="text/markdown",
                raw_data={"video": video, "comments": comments}
            )
            
            result = [item]
            
            # Cache the result
            if self.cache:
                self.cache.set(cache_key, result)
            
            return result
        except HttpError as e:
            raise handle_youtube_api_error(e, "video", video_id)
        except Exception as e:
            logger.error(f"Error collecting data from YouTube video {video_id}: {e}")
            return []
    
    @retry_async(
        max_retries=3,
        retry_status_codes=[429, 500, 502, 503, 504],
        backoff_factor=2,
        max_backoff=60
    )
    async def _get_video_comments(self, video_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """
        Get comments for a YouTube video.
        
        Args:
            video_id: YouTube video ID
            max_comments: Maximum number of comments to retrieve
            
        Returns:
            List[Dict[str, Any]]: Video comments
        """
        try:
            # Check cache first
            if self.cache:
                cache_key = generate_cache_key("get_video_comments", video_id, max_comments)
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
            
            # Acquire rate limiter
            await self.rate_limiter.acquire()
            
            comments = []
            next_page_token = None
            
            while len(comments) < max_comments:
                # Get video comments
                async with self.semaphore:
                    request = self.youtube.commentThreads().list(
                        part="snippet",
                        videoId=video_id,
                        maxResults=min(100, max_comments - len(comments)),
                        pageToken=next_page_token,
                        order="relevance"
                    )
                    response = request.execute()
                
                # Process comments
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
                    
                    if len(comments) >= max_comments:
                        break
                
                # Check if there are more pages
                next_page_token = response.get("nextPageToken")
                if not next_page_token or len(comments) >= max_comments:
                    break
            
            # Cache the result
            if self.cache:
                self.cache.set(cache_key, comments)
            
            return comments
        except HttpError as e:
            if "commentsDisabled" in str(e):
                logger.warning(f"Comments are disabled for video {video_id}")
                return []
            else:
                raise handle_youtube_api_error(e, "video_comments", video_id)
        except Exception as e:
            logger.error(f"Error getting comments for YouTube video {video_id}: {e}")
            return []

