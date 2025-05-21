"""
YouTube connector for Wiseflow.

This module provides a connector for YouTube videos and channels.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import asyncio
from datetime import datetime

from core.connectors import ConnectorBase, DataItem

from .config import load_config
from .utils import RateLimiter, Cache, extract_youtube_id
from .errors import YouTubeConnectorError, YouTubeAPIError
from .connector import YouTubeConnector
from .video import YouTubeVideoCollector
from .channel import YouTubeChannelCollector
from .playlist import YouTubePlaylistCollector
from .search import YouTubeSearchCollector
from .transcript import get_video_transcript, TranscriptFormat

logger = logging.getLogger(__name__)

__all__ = [
    'YouTubeConnector',
    'YouTubeVideoCollector',
    'YouTubeChannelCollector',
    'YouTubePlaylistCollector',
    'YouTubeSearchCollector',
    'YouTubeConnectorError',
    'YouTubeAPIError',
    'TranscriptFormat',
    'get_video_transcript'
]

