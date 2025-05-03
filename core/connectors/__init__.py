"""
Data source connectors for Wiseflow.

This module provides base classes for data source connectors.
"""

from typing import Dict, List, Any, Optional, Union, Awaitable
from abc import abstractmethod
import logging
from datetime import datetime
import asyncio

from core.plugins import PluginBase

logger = logging.getLogger(__name__)

class DataItem:
    """Represents a single item of data collected from a source."""
    
    def __init__(
        self,
        source_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        url: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        content_type: str = "text",
        language: Optional[str] = None,
        raw_data: Optional[Any] = None
    ):
        """Initialize a data item."""
        self.source_id = source_id
        self.content = content
        self.metadata = metadata or {}
        self.url = url
        self.timestamp = timestamp or datetime.now()
        self.content_type = content_type
        self.language = language
        self.raw_data = raw_data
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the data item to a dictionary."""
        return {
            "source_id": self.source_id,
            "content": self.content,
            "metadata": self.metadata,
            "url": self.url,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "content_type": self.content_type,
            "language": self.language
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataItem':
        """Create a data item from a dictionary."""
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except (ValueError, TypeError):
                pass
                
        return cls(
            source_id=data["source_id"],
            content=data["content"],
            metadata=data.get("metadata", {}),
            url=data.get("url"),
            timestamp=timestamp,
            content_type=data.get("content_type", "text"),
            language=data.get("language")
        )


class ConnectorBase(PluginBase):
    """Base class for data source connectors."""
    
    name: str = "base_connector"
    description: str = "Base connector class"
    source_type: str = "generic"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the connector with optional configuration."""
        super().__init__(config)
        self.last_run: Optional[datetime] = None
        self.error_count: int = 0
        self.max_retries: int = config.get("max_retries", 3) if config else 3
        self.retry_delay: float = config.get("retry_delay", 1.0) if config else 1.0
        
    @abstractmethod
    def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from the source."""
        pass
    
    async def collect_async(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """
        Asynchronous version of collect method.
        
        By default, this creates a wrapper around the synchronous collect method.
        Connectors that support native async operations should override this method.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.collect, params)
    
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
                return result
            except Exception as e:
                attempt += 1
                self.error_count += 1
                last_error = e
                logger.warning(f"Collection attempt {attempt} failed for {self.name}: {e}")
                
                if attempt < self.max_retries:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
        
        # If we get here, all retries failed
        logger.error(f"Collection failed after {self.max_retries} attempts for {self.name}: {last_error}")
        raise last_error
    
    def initialize(self) -> bool:
        """Initialize the connector. Return True if successful, False otherwise."""
        try:
            # Perform any necessary initialization
            logger.info(f"Initialized connector: {self.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize connector {self.name}: {e}")
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
            ]
            
            # Only include keys that are in the whitelist
            for key in safe_keys:
                if key in self.config:
                    safe_config[key] = self.config[key]
            
            # Add any custom safe keys defined by the connector
            if hasattr(self, "safe_config_keys") and isinstance(self.safe_config_keys, list):
                for key in self.safe_config_keys:
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

# Import connectors
from core.connectors.web import WebConnector
from core.connectors.academic import AcademicConnector
from core.connectors.github import GitHubConnector
from core.connectors.youtube import YouTubeConnector
from core.connectors.code_search import CodeSearchConnector

# Register available connectors
AVAILABLE_CONNECTORS = {
    "web": WebConnector,
    "academic": AcademicConnector,
    "github": GitHubConnector,
    "youtube": YouTubeConnector,
    "code_search": CodeSearchConnector
}

def get_connector(connector_type: str, config: Optional[Dict[str, Any]] = None) -> Optional[ConnectorBase]:
    """Get a connector instance by type."""
    if connector_type not in AVAILABLE_CONNECTORS:
        logger.error(f"Unknown connector type: {connector_type}")
        return None
    
    connector_class = AVAILABLE_CONNECTORS[connector_type]
    connector = connector_class(config)
    return connector

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
