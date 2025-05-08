"""
Connectors for Wiseflow.

This module provides connectors for various data sources.
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable
import time
from ratelimit import limits, sleep_and_retry

from core.plugins.base import BasePlugin
from core.event_system import (
    EventType, Event, publish_sync,
    create_connector_event
)

logger = logging.getLogger(__name__)

class DataItem:
    """
    Data item from a connector.
    
    This class represents a data item from a connector, including the content,
    metadata, and source information.
    
    Attributes:
        content: The content of the data item
        content_type: The type of content
        metadata: Additional metadata
        source: The source of the data item
        source_type: The type of source
        timestamp: The timestamp when the data item was created
        id: The unique ID of the data item
    """
    
    def __init__(
        self,
        content: str,
        content_type: str = "text/plain",
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        source_type: Optional[str] = None,
        timestamp: Optional[str] = None,
        id: Optional[str] = None
    ):
        """Initialize a data item."""
        self.content = content
        self.content_type = content_type
        self.metadata = metadata or {}
        self.source = source
        self.source_type = source_type
        self.timestamp = timestamp or datetime.now().isoformat()
        self.id = id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "content_type": self.content_type,
            "metadata": self.metadata,
            "source": self.source,
            "source_type": self.source_type,
            "timestamp": self.timestamp,
            "id": self.id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataItem":
        """Create from dictionary."""
        return cls(
            content=data["content"],
            content_type=data.get("content_type", "text/plain"),
            metadata=data.get("metadata", {}),
            source=data.get("source"),
            source_type=data.get("source_type"),
            timestamp=data.get("timestamp"),
            id=data.get("id")
        )


class ConnectorBase(BasePlugin):
    """
    Base class for data source connectors.
    
    This class provides a base implementation for data source connectors,
    including rate limiting, retrying, and error handling.
    
    Attributes:
        name: The name of the connector
        description: A description of the connector
        source_type: The type of source
        config: Configuration for the connector
        rate_limit: The rate limit for the connector
        retry_count: The number of retries for failed requests
        retry_delay: The delay between retries
    """
    
    name = "base_connector"
    description = "Base connector"
    source_type = "base"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the connector."""
        self.config = config or {}
        self.rate_limit = self.config.get('rate_limit', 60)  # requests per minute
        self.retry_count = self.config.get('retry_count', 3)
        self.retry_delay = self.config.get('retry_delay', 5)  # seconds
        self._initialized = False
        self.error_count = 0
        self.last_run = None
    
    @sleep_and_retry
    @limits(calls=60, period=60)  # default 60 calls per 60 seconds
    def _rate_limited_request(self, func, *args, **kwargs):
        """Make a rate-limited request."""
        return func(*args, **kwargs)
    
    def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """
        Collect data from the source.
        
        Args:
            params: Parameters for the collection
            
        Returns:
            List of data items
        """
        raise NotImplementedError("Subclasses must implement collect()")
    
    async def collect_async(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """
        Collect data from the source asynchronously.
        
        Args:
            params: Parameters for the collection
            
        Returns:
            List of data items
        """
        # Default implementation runs the synchronous version in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.collect, params)
    
    async def collect_with_retry(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """
        Collect data from the source with retry.
        
        Args:
            params: Parameters for the collection
            
        Returns:
            List of data items
        """
        retry_count = 0
        while retry_count < self.retry_count:
            try:
                return await self.collect_async(params)
            except Exception as e:
                retry_count += 1
                logger.warning(f"Error collecting data from {self.name}: {e}, retrying ({retry_count}/{self.retry_count})...")
                if retry_count < self.retry_count:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to collect data from {self.name} after {self.retry_count} retries")
                    raise
    
    def initialize(self) -> bool:
        """
        Initialize the connector.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Publish initialization event
            self._publish_initialization_success()
            
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize connector {self.name}: {e}")
            self._publish_initialization_failure(str(e))
            return False
    
    async def initialize_async(self) -> bool:
        """
        Initialize the connector asynchronously.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        # Default implementation runs the synchronous version in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.initialize)
    
    def shutdown(self) -> bool:
        """Shutdown the connector. Return True if successful, False otherwise."""
        self._initialized = False
        return True
    
    def update_last_run(self) -> None:
        """Update the last run timestamp."""
        self.last_run = datetime.now()
    
    def _publish_initialization_success(self) -> None:
        """Publish connector initialization success event."""
        try:
            event = create_connector_event(
                EventType.CONNECTOR_INITIALIZED,
                self.name,
                self.source_type,
                status="success"
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish connector initialization success event: {e}")
    
    def _publish_initialization_failure(self, error: str) -> None:
        """Publish connector initialization failure event."""
        try:
            event = create_connector_event(
                EventType.CONNECTOR_INITIALIZED,
                self.name,
                self.source_type,
                status="failure",
                error=error
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish connector initialization failure event: {e}")
    
    def _publish_collection_success(self, count: int) -> None:
        """Publish connector collection success event."""
        try:
            event = create_connector_event(
                EventType.CONNECTOR_COLLECTED,
                self.name,
                self.source_type,
                status="success",
                count=count
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish connector collection success event: {e}")
    
    def _publish_collection_failure(self, error: str) -> None:
        """Publish connector collection failure event."""
        try:
            event = create_connector_event(
                EventType.CONNECTOR_COLLECTED,
                self.name,
                self.source_type,
                status="failure",
                error=error
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish connector collection failure event: {e}")
