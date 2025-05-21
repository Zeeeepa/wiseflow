"""
Enhanced caching module for crawl4ai.

This module provides a more sophisticated caching mechanism with TTL support,
configurable size limits, and cache invalidation strategies.
"""

import os
import time
import json
import sqlite3
import logging
import threading
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
import hashlib

from .errors import CacheError
from .models import CrawlResult

logger = logging.getLogger(__name__)

class EnhancedCache:
    """
    Enhanced cache implementation with TTL and size limits.
    
    This class provides a more sophisticated caching mechanism for crawl4ai,
    with support for TTL, size limits, and cache invalidation strategies.
    """
    
    def __init__(
        self,
        cache_dir: str,
        ttl: int = 86400,  # 24 hours in seconds
        max_size: int = 1000,  # Maximum number of items in cache
        cleanup_interval: int = 3600,  # 1 hour in seconds
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the enhanced cache.
        
        Args:
            cache_dir: Directory to store cache files.
            ttl: Time-to-live for cache entries in seconds.
            max_size: Maximum number of items in cache.
            cleanup_interval: Interval for cache cleanup in seconds.
            logger: Logger instance for logging.
        """
        self.cache_dir = cache_dir
        self.ttl = ttl
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval
        self.logger = logger or logging.getLogger(__name__)
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        
        # Initialize database
        self.db_path = os.path.join(cache_dir, "cache.db")
        self._init_db()
        
        # Start cleanup thread
        self._last_cleanup = time.time()
        self._cleanup_lock = threading.Lock()
        
        # Run initial cleanup
        self._cleanup_cache()
    
    def _init_db(self) -> None:
        """
        Initialize the cache database.
        
        This method creates the necessary tables in the SQLite database.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create cache metadata table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    url_hash TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    size INTEGER NOT NULL
                )
                """)
                
                # Create cache data table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_data (
                    url_hash TEXT PRIMARY KEY,
                    html TEXT,
                    markdown TEXT,
                    screenshot BLOB,
                    pdf BLOB,
                    media TEXT,
                    metadata TEXT,
                    redirected_url TEXT,
                    FOREIGN KEY (url_hash) REFERENCES cache_metadata (url_hash) ON DELETE CASCADE
                )
                """)
                
                # Create index on last_accessed for faster cleanup
                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_accessed ON cache_metadata (last_accessed)
                """)
                
                conn.commit()
        except sqlite3.Error as e:
            raise CacheError(f"Failed to initialize cache database: {e}", original_error=e)
    
    def _get_url_hash(self, url: str) -> str:
        """
        Get a hash of the URL for use as a cache key.
        
        Args:
            url: The URL to hash.
            
        Returns:
            A hash of the URL.
        """
        return hashlib.md5(url.encode()).hexdigest()
    
    def _check_cleanup(self) -> None:
        """
        Check if cache cleanup is needed and run it if necessary.
        """
        current_time = time.time()
        if current_time - self._last_cleanup > self.cleanup_interval:
            with self._cleanup_lock:
                if current_time - self._last_cleanup > self.cleanup_interval:
                    self._cleanup_cache()
                    self._last_cleanup = current_time
    
    def _cleanup_cache(self) -> None:
        """
        Clean up expired and excess cache entries.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Remove expired entries
                expiry_time = time.time() - self.ttl
                cursor.execute(
                    "DELETE FROM cache_metadata WHERE created_at < ?",
                    (expiry_time,)
                )
                expired_count = cursor.rowcount
                
                # Check cache size
                cursor.execute("SELECT COUNT(*) FROM cache_metadata")
                cache_size = cursor.fetchone()[0]
                
                # If cache is still too large, remove oldest entries
                if cache_size > self.max_size:
                    excess_count = cache_size - self.max_size
                    cursor.execute(
                        "DELETE FROM cache_metadata WHERE url_hash IN ("
                        "SELECT url_hash FROM cache_metadata ORDER BY last_accessed ASC LIMIT ?"
                        ")",
                        (excess_count,)
                    )
                    lru_count = cursor.rowcount
                else:
                    lru_count = 0
                
                conn.commit()
                
                self.logger.info(
                    f"Cache cleanup: removed {expired_count} expired entries and "
                    f"{lru_count} LRU entries. Current size: {cache_size - expired_count - lru_count}"
                )
        except sqlite3.Error as e:
            self.logger.error(f"Cache cleanup failed: {e}")
    
    async def get(self, url: str) -> Optional[CrawlResult]:
        """
        Get a cached result for a URL.
        
        Args:
            url: The URL to get the cached result for.
            
        Returns:
            The cached result, or None if not found or expired.
        """
        self._check_cleanup()
        
        url_hash = self._get_url_hash(url)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if URL is in cache and not expired
                cursor.execute(
                    "SELECT created_at FROM cache_metadata WHERE url_hash = ?",
                    (url_hash,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                created_at = row[0]
                if time.time() - created_at > self.ttl:
                    # Entry is expired, remove it
                    cursor.execute(
                        "DELETE FROM cache_metadata WHERE url_hash = ?",
                        (url_hash,)
                    )
                    conn.commit()
                    return None
                
                # Update last accessed time
                cursor.execute(
                    "UPDATE cache_metadata SET last_accessed = ? WHERE url_hash = ?",
                    (time.time(), url_hash)
                )
                
                # Get cache data
                cursor.execute(
                    "SELECT html, markdown, screenshot, pdf, media, metadata, redirected_url "
                    "FROM cache_data WHERE url_hash = ?",
                    (url_hash,)
                )
                data_row = cursor.fetchone()
                
                if not data_row:
                    return None
                
                html, markdown, screenshot, pdf, media_json, metadata_json, redirected_url = data_row
                
                # Parse JSON data
                try:
                    media = json.loads(media_json) if media_json else {}
                    metadata = json.loads(metadata_json) if metadata_json else {}
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse cached JSON data: {e}")
                    return None
                
                conn.commit()
                
                # Create CrawlResult
                result = CrawlResult(
                    url=url,
                    html=html,
                    markdown=markdown,
                    screenshot=screenshot,
                    pdf=pdf,
                    media=media,
                    metadata=metadata,
                    redirected_url=redirected_url or url,
                    success=bool(html),
                )
                
                return result
        except sqlite3.Error as e:
            self.logger.error(f"Cache get failed: {e}")
            return None
    
    async def set(self, result: CrawlResult) -> bool:
        """
        Cache a crawl result.
        
        Args:
            result: The crawl result to cache.
            
        Returns:
            True if the result was cached successfully, False otherwise.
        """
        if not result or not result.url:
            return False
        
        self._check_cleanup()
        
        url_hash = self._get_url_hash(result.url)
        
        try:
            # Serialize media and metadata to JSON
            media_json = json.dumps(result.media) if result.media else None
            metadata_json = json.dumps(result.metadata) if result.metadata else None
            
            # Calculate size (approximate)
            size = (
                len(result.html or "") +
                len(result.markdown or "") +
                len(media_json or "") +
                len(metadata_json or "") +
                len(result.screenshot or b"") +
                len(result.pdf or b"")
            )
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Insert or replace metadata
                cursor.execute(
                    "INSERT OR REPLACE INTO cache_metadata "
                    "(url_hash, url, created_at, last_accessed, size) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (url_hash, result.url, time.time(), time.time(), size)
                )
                
                # Insert or replace data
                cursor.execute(
                    "INSERT OR REPLACE INTO cache_data "
                    "(url_hash, html, markdown, screenshot, pdf, media, metadata, redirected_url) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        url_hash,
                        result.html,
                        result.markdown,
                        result.screenshot,
                        result.pdf,
                        media_json,
                        metadata_json,
                        result.redirected_url
                    )
                )
                
                conn.commit()
                
                return True
        except (sqlite3.Error, json.JSONDecodeError) as e:
            self.logger.error(f"Cache set failed: {e}")
            return False
    
    async def invalidate(self, url: str) -> bool:
        """
        Invalidate a cached result.
        
        Args:
            url: The URL to invalidate.
            
        Returns:
            True if the result was invalidated successfully, False otherwise.
        """
        url_hash = self._get_url_hash(url)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "DELETE FROM cache_metadata WHERE url_hash = ?",
                    (url_hash,)
                )
                
                conn.commit()
                
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"Cache invalidation failed: {e}")
            return False
    
    async def clear(self) -> bool:
        """
        Clear the entire cache.
        
        Returns:
            True if the cache was cleared successfully, False otherwise.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM cache_metadata")
                
                conn.commit()
                
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Cache clear failed: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            A dictionary containing cache statistics.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute("SELECT COUNT(*) FROM cache_metadata")
                total_count = cursor.fetchone()[0]
                
                # Get total size
                cursor.execute("SELECT SUM(size) FROM cache_metadata")
                total_size = cursor.fetchone()[0] or 0
                
                # Get oldest entry
                cursor.execute(
                    "SELECT MIN(created_at) FROM cache_metadata"
                )
                oldest_timestamp = cursor.fetchone()[0]
                oldest_date = datetime.fromtimestamp(oldest_timestamp) if oldest_timestamp else None
                
                # Get newest entry
                cursor.execute(
                    "SELECT MAX(created_at) FROM cache_metadata"
                )
                newest_timestamp = cursor.fetchone()[0]
                newest_date = datetime.fromtimestamp(newest_timestamp) if newest_timestamp else None
                
                return {
                    "count": total_count,
                    "size_bytes": total_size,
                    "size_mb": total_size / (1024 * 1024) if total_size else 0,
                    "oldest_entry": oldest_date.isoformat() if oldest_date else None,
                    "newest_entry": newest_date.isoformat() if newest_date else None,
                    "ttl_seconds": self.ttl,
                    "max_size": self.max_size,
                    "cleanup_interval_seconds": self.cleanup_interval,
                }
        except sqlite3.Error as e:
            self.logger.error(f"Cache stats failed: {e}")
            return {
                "error": str(e),
                "count": 0,
                "size_bytes": 0,
                "size_mb": 0,
                "oldest_entry": None,
                "newest_entry": None,
                "ttl_seconds": self.ttl,
                "max_size": self.max_size,
                "cleanup_interval_seconds": self.cleanup_interval,
            }

