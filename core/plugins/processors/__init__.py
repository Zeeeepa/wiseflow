"""
Base classes for data processors in Wiseflow.

This module provides the base classes for data processors, which are responsible
for processing data from various sources.
"""

import abc
import logging
import traceback
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from core.plugins.base import PluginBase
from core.connectors import DataItem
from core.event_system import EventType, publish_sync, create_resource_event

logger = logging.getLogger(__name__)

class ProcessedData:
    """
    Container for processed data.
    
    This class provides a standardized way to represent processed data,
    with metadata and the original data item.
    """
    
    def __init__(
        self,
        original_item: DataItem,
        processed_content: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize processed data.
        
        Args:
            original_item: Original data item that was processed
            processed_content: List of processed content items
            metadata: Additional metadata about the processing
        """
        self.original_item = original_item
        self.processed_content = processed_content
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the processed data to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the processed data
        """
        return {
            "original_item": self.original_item.to_dict(),
            "processed_content": self.processed_content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessedData':
        """
        Create processed data from a dictionary.
        
        Args:
            data: Dictionary representation of processed data
            
        Returns:
            ProcessedData: New processed data instance
        """
        return cls(
            original_item=DataItem.from_dict(data["original_item"]),
            processed_content=data["processed_content"],
            metadata=data["metadata"]
        )
    
    def __str__(self) -> str:
        """String representation of the processed data."""
        return f"ProcessedData(items={len(self.processed_content)}, source={self.original_item.source_id})"


class ProcessorBase(PluginBase):
    """
    Base class for data processors.
    
    This class provides a foundation for implementing processors for various data types,
    with support for error handling and resource monitoring.
    """
    
    name: str = "base_processor"
    description: str = "Base processor for data"
    processor_type: str = "base"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the processor.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config or {})
        self.error_count = 0
        self.last_run_time = None
    
    @abc.abstractmethod
    def process(self, data_item: DataItem, params: Optional[Dict[str, Any]] = None) -> ProcessedData:
        """
        Process a data item.
        
        Args:
            data_item: Data item to process
            params: Optional parameters for processing
            
        Returns:
            ProcessedData: Processed data
        """
        pass
    
    async def process_async(self, data_item: DataItem, params: Optional[Dict[str, Any]] = None) -> ProcessedData:
        """
        Asynchronous version of process method.
        
        By default, this creates a wrapper around the synchronous process method.
        Processors that support native async operations should override this method.
        
        Args:
            data_item: Data item to process
            params: Optional parameters for processing
            
        Returns:
            ProcessedData: Processed data
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.process(data_item, params))
    
    def batch_process(self, data_items: List[DataItem], params: Optional[Dict[str, Any]] = None) -> List[ProcessedData]:
        """
        Process multiple data items.
        
        Args:
            data_items: List of data items to process
            params: Optional parameters for processing
            
        Returns:
            List[ProcessedData]: List of processed data
        """
        results = []
        for item in data_items:
            try:
                result = self.process(item, params)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing item {item.source_id}: {e}")
                logger.error(traceback.format_exc())
                self.error_count += 1
                
                # Create error result
                error_result = ProcessedData(
                    original_item=item,
                    processed_content=[],
                    metadata={
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
                results.append(error_result)
        
        self.update_last_run()
        return results
    
    async def batch_process_async(self, data_items: List[DataItem], params: Optional[Dict[str, Any]] = None) -> List[ProcessedData]:
        """
        Process multiple data items asynchronously.
        
        Args:
            data_items: List of data items to process
            params: Optional parameters for processing
            
        Returns:
            List[ProcessedData]: List of processed data
        """
        import asyncio
        tasks = [self.process_async(item, params) for item in data_items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing item {data_items[i].source_id}: {result}")
                self.error_count += 1
                
                # Create error result
                error_result = ProcessedData(
                    original_item=data_items[i],
                    processed_content=[],
                    metadata={
                        "error": str(result),
                        "error_type": type(result).__name__
                    }
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        self.update_last_run()
        return processed_results
    
    def update_last_run(self) -> None:
        """Update the last run timestamp."""
        self.last_run_time = datetime.now()
    
    def validate_config(self) -> bool:
        """
        Validate the processor configuration.
        
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
        Get the status of the processor.
        
        Returns:
            Dict[str, Any]: Status information
        """
        return {
            "name": self.name,
            "description": self.description,
            "processor_type": self.processor_type,
            "initialized": self.initialized,
            "error_count": self.error_count,
            "last_run": self.last_run_time.isoformat() if self.last_run_time else None,
            "config": {
                k: v for k, v in self.config.items() 
                if k not in ["api_key", "password", "token", "secret"]  # Don't include sensitive info
            }
        }
    
    def _publish_processing_success(self, item_count: int) -> None:
        """Publish processor success event."""
        try:
            event = create_processor_event(
                EventType.DATA_PROCESSED,
                self.name,
                {
                    "processor_type": self.processor_type,
                    "item_count": item_count,
                    "timestamp": datetime.now().isoformat()
                }
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish processor success event: {e}")
    
    def _publish_processing_error(self, error_message: str) -> None:
        """Publish processor error event."""
        try:
            event = create_processor_event(
                EventType.PROCESSOR_ERROR,
                self.name,
                {
                    "processor_type": self.processor_type,
                    "error": error_message,
                    "timestamp": datetime.now().isoformat()
                }
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish processor error event: {e}")


def create_processor_event(event_type: EventType, processor_name: str, data: Optional[Dict[str, Any]] = None) -> Any:
    """
    Create a processor event.
    
    Args:
        event_type: Type of event
        processor_name: Name of the processor
        data: Additional event data
        
    Returns:
        Event: Processor event
    """
    from core.event_system import Event
    
    data = data or {}
    data["processor_name"] = processor_name
    
    return Event(event_type, data, "processor_manager")

