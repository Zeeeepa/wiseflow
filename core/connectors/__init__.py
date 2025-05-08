"""
Connectors for WiseFlow.

This module provides connectors for different data sources.
"""

from typing import Dict, List, Any, Optional, Union, Awaitable
import abc
import asyncio
import uuid
import logging
from datetime import datetime
import time
from ratelimit import limits, sleep_and_retry

from core.plugins.base import PluginBase
from core.event_system import (
    EventType, Event, publish_sync,
    create_connector_event, create_resource_event
)
from core.utils.decorators import handle_exceptions

logger = logging.getLogger(__name__)

class DataItem:
    """
    Data item representing content from a data source.
    
    This class provides a standardized way to represent content from different sources,
    with metadata and type information.
    """
    
    def __init__(
        self,
        source_id: Optional[str] = None,
        content: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        url: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        content_type: str = "text/plain",
        raw_data: Any = None
    ):
        """
        Initialize a data item.
        
        Args:
            source_id: Identifier for the source
            content: Content of the item
            metadata: Additional metadata
            url: URL of the content
            timestamp: Timestamp of the content
            content_type: MIME type of the content
            raw_data: Raw data from the source
        """
        self.source_id = source_id or str(uuid.uuid4())
        self.content = content
        self.metadata = metadata or {}
        self.url = url
        self.timestamp = timestamp or datetime.now()
        self.content_type = content_type
        self.raw_data = raw_data
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the data item to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the data item
        """
        return {
            "source_id": self.source_id,
            "content": self.content,
            "metadata": self.metadata,
            "url": self.url,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "content_type": self.content_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataItem':
        """
        Create a data item from a dictionary.
        
        Args:
            data: Dictionary representation of a data item
            
        Returns:
            DataItem: New data item instance
        """
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            source_id=data.get("source_id"),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            url=data.get("url"),
            timestamp=timestamp,
            content_type=data.get("content_type", "text/plain"),
            raw_data=data.get("raw_data")
        )
    
    def __str__(self) -> str:
        """String representation of the data item."""
        return f"DataItem(source_id={self.source_id}, url={self.url})"


class ConnectorBase(PluginBase):
    """
    Base class for data source connectors.
    
    This class provides a foundation for implementing connectors to various data sources,
    with support for rate limiting, retry logic, and async operations.
    """
    
    name: str = "base_connector"
    description: str = "Base connector for data sources"
    source_type: str = "base"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the connector.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config or {})
        # Configure rate limits from config
        self.rate_limit = self.config.get('rate_limit', 60)  # requests per minute
        self.max_connections = self.config.get('max_connections', 10)
        self.connection_pool = None
        self.retry_count = self.config.get('retry_count', 3)
        self.retry_delay = self.config.get('retry_delay', 5)  # seconds
        self._initialized = False
        self.error_count = 0
        self.last_run_time = None
        self.session = None
    
    @sleep_and_retry
    @limits(calls=60, period=60)  # default 60 calls per 60 seconds
    def _rate_limited_request(self, *args, **kwargs):
        """
        Make a rate-limited request.
        
        This method is decorated with rate limiting to prevent overloading the data source.
        """
        # Implementation depends on the specific connector
        pass
    
    @abc.abstractmethod
    def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """
        Collect data from the source.
        
        Args:
            params: Optional parameters for the collection
            
        Returns:
            List[DataItem]: List of collected data items
        """
        pass
    
    async def collect_async(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """
        Asynchronous version of collect method.
        
        By default, this creates a wrapper around the synchronous collect method.
        Connectors that support native async operations should override this method.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.collect(params))
    
    @handle_exceptions(error_types=[Exception], default_message="Failed to collect data with retry", log_error=True)
    async def collect_with_retry(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """
        Collect data with automatic retry on failure.
        
        Args:
            params: Parameters for the collection operation
            
        Returns:
            List of collected data items
            
        Raises:
            Exception: If collection fails after all retries
        """
        attempt = 0
        last_error = None
        
        while attempt < self.retry_count:
            try:
                # Use the async version for better integration
                result = await self.collect_async(params)
                self.update_last_run()
                
                # Publish success event
                self._publish_collection_success(len(result))
                
                return result
            except Exception as e:
                attempt += 1
                self.error_count += 1
                last_error = e
                logger.warning(f"Collection attempt {attempt} failed for {self.name}: {e}")
                
                # Publish error event
                self._publish_collection_error(str(e), attempt)
                
                if attempt < self.retry_count:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
        
        # If we get here, all retries failed
        error_message = f"Collection failed after {self.retry_count} attempts for {self.name}: {last_error}"
        logger.error(error_message)
        raise ConnectionError(error_message, {"last_error": str(last_error)})
    
    def initialize(self) -> bool:
        """Initialize the connector. Return True if successful, False otherwise."""
        try:
            # Perform any necessary initialization
            logger.info(f"Initialized connector: {self.name}")
            
            # Publish initialization event
            self._publish_initialization_success()
            
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize connector {self.name}: {e}")
            
            # Publish error event
            self._publish_initialization_error(str(e))
            
            return False
    
    async def initialize_async(self) -> bool:
        """
        Asynchronous initialization for connectors that require async setup.
        
        By default, this creates a wrapper around the synchronous initialize method.
        Connectors that require async initialization should override this method.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.initialize)
    
    def shutdown(self) -> bool:
        """Shutdown the connector and release resources. Return True if successful, False otherwise."""
        try:
            # Close any open connections or resources
            if self.session:
                self.session.close()
                self.session = None
            
            self._initialized = False
            logger.info(f"Shutdown connector: {self.name}")
            return True
        except Exception as e:
            logger.error(f"Error shutting down connector {self.name}: {e}")
            return False
    
    def update_last_run(self) -> None:
        """Update the last run timestamp."""
        self.last_run_time = datetime.now()
    
    def _publish_initialization_success(self) -> None:
        """Publish connector initialization success event."""
        try:
            event = create_connector_event(
                EventType.CONNECTOR_INITIALIZED,
                self.name,
                {"source_type": self.source_type}
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish connector initialization event: {e}")
    
    def _publish_initialization_error(self, error_message: str) -> None:
        """Publish connector initialization error event."""
        try:
            event = create_connector_event(
                EventType.CONNECTOR_ERROR,
                self.name,
                {
                    "source_type": self.source_type,
                    "error": error_message,
                    "phase": "initialization"
                }
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish connector error event: {e}")
    
    def _publish_collection_success(self, item_count: int) -> None:
        """Publish connector collection success event."""
        try:
            event = create_connector_event(
                EventType.DATA_COLLECTED,
                self.name,
                {
                    "source_type": self.source_type,
                    "item_count": item_count,
                    "timestamp": datetime.now().isoformat()
                }
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish connector collection event: {e}")
    
    def _publish_collection_error(self, error_message: str, attempt: int) -> None:
        """Publish connector collection error event."""
        try:
            event = create_connector_event(
                EventType.CONNECTOR_ERROR,
                self.name,
                {
                    "source_type": self.source_type,
                    "error": error_message,
                    "phase": "collection",
                    "attempt": attempt,
                    "max_retries": self.retry_count
                }
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish connector error event: {e}")
    
    def validate_config(self) -> bool:
        """
        Validate the connector configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        # Basic validation - subclasses should override for specific validation
        if not isinstance(self.config, dict):
            logger.error(f"Invalid configuration for {self.name}: config must be a dictionary")
            return False
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the connector.
        
        Returns:
            Dict[str, Any]: Status information
        """
        return {
            "name": self.name,
            "description": self.description,
            "source_type": self.source_type,
            "initialized": self._initialized,
            "error_count": self.error_count,
            "last_run": self.last_run_time.isoformat() if self.last_run_time else None,
            "config": {
                k: v for k, v in self.config.items() 
                if k not in ["api_key", "password", "token", "secret"]  # Don't include sensitive info
            }
        }


async def initialize_all_connectors(connectors: Dict[str, ConnectorBase]) -> Dict[str, bool]:
    """
    Initialize all connectors asynchronously.
    
    Args:
        connectors: Dictionary of connector instances
        
    Returns:
        Dictionary mapping connector names to initialization success status
    """
    results = {}
    initialization_tasks = []
    
    for name, connector in connectors.items():
        initialization_tasks.append(initialize_connector(name, connector))
    
    results_list = await asyncio.gather(*initialization_tasks, return_exceptions=True)
    
    for name, result in results_list:
        if isinstance(result, Exception):
            logger.error(f"Error initializing connector {name}: {result}")
            results[name] = False
        else:
            results[name] = result
    
    return results

async def initialize_connector(name: str, connector: ConnectorBase) -> tuple[str, bool]:
    """
    Initialize a single connector asynchronously.
    
    Args:
        name: Name of the connector
        connector: Connector instance
        
    Returns:
        Tuple of (name, success)
    """
    try:
        success = await connector.initialize_async()
        return name, success
    except Exception as e:
        return name, e
