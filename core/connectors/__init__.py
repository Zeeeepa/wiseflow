"""
Connectors for WiseFlow.

This module provides connectors for different data sources.
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import abc
import uuid

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

class ConnectorBase(abc.ABC):
    """Base class for data source connectors."""
    
    name: str = "base_connector"
    description: str = "Base connector class"
    source_type: str = "generic"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the connector with optional configuration."""
        self.config = config or {}
    
    @abc.abstractmethod
    def initialize(self) -> bool:
        """Initialize the connector. Return True if successful, False otherwise."""
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
    
    def shutdown(self) -> bool:
        """Shutdown the connector. Return True if successful, False otherwise."""
        return True

