"""
Processor plugins for Wiseflow.

This module provides base classes for processor plugins.
"""

from typing import Dict, List, Any, Optional, Union
from abc import abstractmethod
from datetime import datetime

from core.plugins.base import PluginBase
from core.connectors import DataItem

class ProcessedData:
    """Represents processed data from a processor plugin."""
    
    def __init__(
        self,
        original_item: DataItem,
        processed_content: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        processing_info: Optional[Dict[str, Any]] = None
    ):
        """Initialize processed data."""
        self.original_item = original_item
        self.processed_content = processed_content
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now()
        self.processing_info = processing_info or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the processed data to a dictionary."""
        return {
            "original_item": self.original_item.to_dict() if self.original_item else None,
            "processed_content": self.processed_content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "processing_info": self.processing_info
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessedData':
        """Create processed data from a dictionary."""
        original_item = None
        if data.get("original_item"):
            original_item = DataItem.from_dict(data["original_item"])
            
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except (ValueError, TypeError):
                pass
                
        return cls(
            original_item=original_item,
            processed_content=data["processed_content"],
            metadata=data.get("metadata", {}),
            timestamp=timestamp,
            processing_info=data.get("processing_info", {})
        )


class ProcessorBase(PluginBase):
    """Base class for processor plugins."""
    
    name: str = "base_processor"
    description: str = "Base processor plugin"
    processor_type: str = "generic"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the processor with optional configuration."""
        super().__init__(config)
        
    @abstractmethod
    def process(self, data_item: DataItem, params: Optional[Dict[str, Any]] = None) -> ProcessedData:
        """
        Process a data item.
        
        Args:
            data_item: The data item to process
            params: Optional processing parameters
            
        Returns:
            ProcessedData: The processed data
        """
        pass
    
    def batch_process(self, data_items: List[DataItem], params: Optional[Dict[str, Any]] = None) -> List[ProcessedData]:
        """
        Process multiple data items.
        
        Args:
            data_items: The data items to process
            params: Optional processing parameters
            
        Returns:
            List[ProcessedData]: The processed data items
        """
        results = []
        for item in data_items:
            results.append(self.process(item, params))
        return results
    
    def initialize(self) -> bool:
        """Initialize the processor. Return True if successful, False otherwise."""
        return True

