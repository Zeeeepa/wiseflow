"""
Transcript extraction for YouTube videos.

This module provides functionality to extract transcripts from YouTube videos.
"""

import logging
import json
import re
from typing import List, Dict, Any, Optional, Union
import aiohttp

from .errors import YouTubeTranscriptError

logger = logging.getLogger(__name__)

class TranscriptFormat:
    """Transcript format options."""
    
    PLAIN = "plain"
    TIMESTAMPED = "timestamped"
    SRT = "srt"
    VTT = "vtt"


async def get_video_transcript(video_id: str, format: str = TranscriptFormat.PLAIN) -> str:
    """
    Get transcript for a YouTube video.
    
    Args:
        video_id: YouTube video ID
        format: Transcript format (plain, timestamped, srt, vtt)
        
    Returns:
        str: Video transcript
        
    Raises:
        YouTubeTranscriptError: If transcript extraction fails
    """
    try:
        # Get transcript data
        transcript_data = await _fetch_transcript_data(video_id)
        
        if not transcript_data:
            raise YouTubeTranscriptError(video_id, "No transcript available")
        
        # Format transcript
        if format == TranscriptFormat.PLAIN:
            return _format_transcript_plain(transcript_data)
        elif format == TranscriptFormat.TIMESTAMPED:
            return _format_transcript_timestamped(transcript_data)
        elif format == TranscriptFormat.SRT:
            return _format_transcript_srt(transcript_data)
        elif format == TranscriptFormat.VTT:
            return _format_transcript_vtt(transcript_data)
        else:
            raise ValueError(f"Unsupported transcript format: {format}")
    
    except YouTubeTranscriptError:
        # Re-raise YouTubeTranscriptError
        raise
    except Exception as e:
        # Wrap other exceptions
        logger.error(f"Error getting transcript for video {video_id}: {e}")
        raise YouTubeTranscriptError(video_id, str(e))


async def _fetch_transcript_data(video_id: str) -> List[Dict[str, Any]]:
    """
    Fetch transcript data for a YouTube video.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        List[Dict[str, Any]]: Transcript data
        
    Raises:
        YouTubeTranscriptError: If transcript extraction fails
    """
    # Note: In a production environment, you would use a library like youtube_transcript_api
    # This implementation uses a workaround to fetch transcripts without additional dependencies
    
    try:
        # First, fetch the video page to get the transcript data
        async with aiohttp.ClientSession() as session:
            # Get video page
            url = f"https://www.youtube.com/watch?v={video_id}"
            async with session.get(url) as response:
                if response.status != 200:
                    raise YouTubeTranscriptError(
                        video_id, 
                        f"Failed to fetch video page: HTTP {response.status}"
                    )
                
                html = await response.text()
            
            # Extract transcript data from the page
            transcript_data = _extract_transcript_from_html(html)
            
            if not transcript_data:
                # Try alternative method using timedtext API
                transcript_data = await _fetch_transcript_from_timedtext(session, video_id, html)
            
            return transcript_data
    
    except YouTubeTranscriptError:
        # Re-raise YouTubeTranscriptError
        raise
    except Exception as e:
        # Wrap other exceptions
        logger.error(f"Error fetching transcript data for video {video_id}: {e}")
        raise YouTubeTranscriptError(video_id, str(e))


def _extract_transcript_from_html(html: str) -> List[Dict[str, Any]]:
    """
    Extract transcript data from YouTube video page HTML.
    
    Args:
        html: YouTube video page HTML
        
    Returns:
        List[Dict[str, Any]]: Transcript data
    """
    # Look for transcript data in the page
    transcript_regex = r'\"captionTracks\":\s*(\[.*?\])'
    match = re.search(transcript_regex, html)
    
    if not match:
        return []
    
    try:
        caption_tracks = json.loads(match.group(1))
        
        if not caption_tracks:
            return []
        
        # Get the first available transcript URL
        transcript_url = None
        for track in caption_tracks:
            if "baseUrl" in track:
                transcript_url = track["baseUrl"]
                break
        
        if not transcript_url:
            return []
        
        # We found a transcript URL, but we need to fetch it separately
        # This would be done in _fetch_transcript_from_timedtext
        # For now, return an empty list to trigger the alternative method
        return []
    
    except Exception as e:
        logger.warning(f"Error extracting transcript data from HTML: {e}")
        return []


async def _fetch_transcript_from_timedtext(
    session: aiohttp.ClientSession, 
    video_id: str, 
    html: str
) -> List[Dict[str, Any]]:
    """
    Fetch transcript from YouTube timedtext API.
    
    Args:
        session: aiohttp ClientSession
        video_id: YouTube video ID
        html: YouTube video page HTML
        
    Returns:
        List[Dict[str, Any]]: Transcript data
        
    Raises:
        YouTubeTranscriptError: If transcript extraction fails
    """
    # Extract timedtext URL from HTML
    timedtext_regex = r'\"captionTracks\":\s*(\[.*?\])'
    match = re.search(timedtext_regex, html)
    
    if not match:
        raise YouTubeTranscriptError(video_id, "No transcript available")
    
    try:
        caption_tracks = json.loads(match.group(1))
        
        if not caption_tracks:
            raise YouTubeTranscriptError(video_id, "No caption tracks available")
        
        # Get the first available transcript URL
        transcript_url = None
        for track in caption_tracks:
            if "baseUrl" in track:
                transcript_url = track["baseUrl"]
                break
        
        if not transcript_url:
            raise YouTubeTranscriptError(video_id, "No transcript URL found")
        
        # Fetch transcript XML
        async with session.get(transcript_url) as response:
            if response.status != 200:
                raise YouTubeTranscriptError(
                    video_id, 
                    f"Failed to fetch transcript: HTTP {response.status}"
                )
            
            xml = await response.text()
        
        # Parse transcript XML
        transcript_data = _parse_transcript_xml(xml)
        
        if not transcript_data:
            raise YouTubeTranscriptError(video_id, "Failed to parse transcript XML")
        
        return transcript_data
    
    except YouTubeTranscriptError:
        # Re-raise YouTubeTranscriptError
        raise
    except Exception as e:
        # Wrap other exceptions
        logger.error(f"Error fetching transcript from timedtext for video {video_id}: {e}")
        raise YouTubeTranscriptError(video_id, str(e))


def _parse_transcript_xml(xml: str) -> List[Dict[str, Any]]:
    """
    Parse transcript XML from YouTube timedtext API.
    
    Args:
        xml: Transcript XML
        
    Returns:
        List[Dict[str, Any]]: Transcript data
    """
    # Simple regex-based parsing for demonstration
    # In production, use a proper XML parser
    transcript_data = []
    
    # Extract text elements with start and duration attributes
    pattern = r'<text start="([\d\.]+)" dur="([\d\.]+)".*?>(.*?)</text>'
    matches = re.findall(pattern, xml, re.DOTALL)
    
    for match in matches:
        start = float(match[0])
        duration = float(match[1])
        text = match[2]
        
        # Clean up text (remove HTML tags)
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'")
        
        transcript_data.append({
            "start": start,
            "duration": duration,
            "text": text
        })
    
    return transcript_data


def _format_transcript_plain(transcript_data: List[Dict[str, Any]]) -> str:
    """
    Format transcript as plain text.
    
    Args:
        transcript_data: Transcript data
        
    Returns:
        str: Formatted transcript
    """
    return " ".join(item["text"] for item in transcript_data)


def _format_transcript_timestamped(transcript_data: List[Dict[str, Any]]) -> str:
    """
    Format transcript with timestamps.
    
    Args:
        transcript_data: Transcript data
        
    Returns:
        str: Formatted transcript
    """
    lines = []
    
    for item in transcript_data:
        start_time = _format_timestamp(item["start"])
        lines.append(f"[{start_time}] {item['text']}")
    
    return "\n".join(lines)


def _format_transcript_srt(transcript_data: List[Dict[str, Any]]) -> str:
    """
    Format transcript as SRT.
    
    Args:
        transcript_data: Transcript data
        
    Returns:
        str: Formatted transcript
    """
    lines = []
    
    for i, item in enumerate(transcript_data):
        start_time = _format_timestamp_srt(item["start"])
        end_time = _format_timestamp_srt(item["start"] + item["duration"])
        
        lines.append(f"{i+1}")
        lines.append(f"{start_time} --> {end_time}")
        lines.append(f"{item['text']}")
        lines.append("")
    
    return "\n".join(lines)


def _format_transcript_vtt(transcript_data: List[Dict[str, Any]]) -> str:
    """
    Format transcript as VTT.
    
    Args:
        transcript_data: Transcript data
        
    Returns:
        str: Formatted transcript
    """
    lines = ["WEBVTT", ""]
    
    for item in transcript_data:
        start_time = _format_timestamp_vtt(item["start"])
        end_time = _format_timestamp_vtt(item["start"] + item["duration"])
        
        lines.append(f"{start_time} --> {end_time}")
        lines.append(f"{item['text']}")
        lines.append("")
    
    return "\n".join(lines)


def _format_timestamp(seconds: float) -> str:
    """
    Format timestamp as HH:MM:SS.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        str: Formatted timestamp
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _format_timestamp_srt(seconds: float) -> str:
    """
    Format timestamp as HH:MM:SS,mmm for SRT.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        str: Formatted timestamp
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_int = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{seconds_int:02d},{milliseconds:03d}"


def _format_timestamp_vtt(seconds: float) -> str:
    """
    Format timestamp as HH:MM:SS.mmm for VTT.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        str: Formatted timestamp
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_int = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{seconds_int:02d}.{milliseconds:03d}"

