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

from core.plugins import PluginBase
from core.event_system import (
    EventType, Event, publish_sync,
    create_connector_event
)
from core.utils.error_handling import handle_exceptions, ConnectionError

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
    def from_dict(cls, data: Dict[str, Any]) -> "DataItem":
        """
        Create a data item from a dictionary.
        
        Args:
            data: Dictionary representation of a data item
            
        Returns:
            DataItem: Data item created from the dictionary
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
            content_type=data.get("content_type", "text/plain")
        )


class ConnectorBase(PluginBase):
    """Base class for data source connectors."""
    
    name: str = "base_connector"
    description: str = "Base connector for data sources"
    source_type: str = "base"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the connector with optional configuration."""
        super().__init__(config)
        self.last_run: Optional[datetime] = None
        self.error_count: int = 0
        self.max_retries: int = config.get("max_retries", 3) if config else 3
        self.retry_delay: float = config.get("retry_delay", 1.0) if config else 1.0
        self.safe_config_keys: List[str] = []
        
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
        return await loop.run_in_executor(None, self.collect, params)
    
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
        
        while attempt < self.max_retries:
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
                
                if attempt < self.max_retries:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
        
        # If we get here, all retries failed
        error_message = f"Collection failed after {self.max_retries} attempts for {self.name}: {last_error}"
        logger.error(error_message)
        raise ConnectionError(error_message, {"last_error": str(last_error)})
    
    def initialize(self) -> bool:
        """Initialize the connector. Return True if successful, False otherwise."""
        try:
            # Perform any necessary initialization
            logger.info(f"Initialized connector: {self.name}")
            
            # Publish initialization event
            self._publish_initialization_success()
            
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
    
    def update_last_run(self) -> None:
        """Update the last run timestamp."""
        self.last_run = datetime.now()
        
    def get_last_run(self) -> Optional[datetime]:
        """Get the last run timestamp."""
        return self.last_run
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the connector.
        
        Returns:
            Dictionary with status information
        """
        # Use a whitelist approach for config to avoid exposing sensitive information
        safe_config = {}
        if self.config:
            # Define a whitelist of safe keys to include
            safe_keys = [
                "name", "type", "enabled", "url", "base_url", "endpoint", 
                "timeout", "max_retries", "retry_delay", "cache_enabled",
                "max_results", "language", "format", "source", "category",
                "tags", "description", "version", "author", "website",
                "license", "max_concurrent_requests", "user_agent"
            ] + self.safe_config_keys
            
            # Only include keys that are in the whitelist
            for key in safe_keys:
                if key in self.config:
                    safe_config[key] = self.config[key]
        
        return {
            "name": self.name,
            "type": self.source_type,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "error_count": self.error_count,
            "is_enabled": self.is_enabled,
            "config": safe_config
        }
    
    def shutdown(self) -> bool:
        """Shutdown the connector. Return True if successful, False otherwise."""
        return True
    
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
                    "max_retries": self.max_retries
                }
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish connector error event: {e}")


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

