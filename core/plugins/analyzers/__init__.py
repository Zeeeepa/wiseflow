"""
Analyzers for Wiseflow.

This module provides base classes for data analyzers.
"""

from typing import Dict, List, Any, Optional, Union
from abc import abstractmethod
import logging
from datetime import datetime

from core.plugins import PluginBase
from core.plugins.processors import ProcessedData

logger = logging.getLogger(__name__)

class AnalysisResult:
    """Represents analysis results from an analyzer."""
    
    def __init__(
        self,
        processed_data: Optional[ProcessedData] = None,
        analysis_content: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        """Initialize analysis result."""
        self.processed_data = processed_data
        self.analysis_content = analysis_content
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the analysis result to a dictionary."""
        return {
            "processed_data": self.processed_data.to_dict() if self.processed_data else None,
            "analysis_content": self.analysis_content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisResult':
        """Create analysis result from a dictionary."""
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except (ValueError, TypeError):
                pass
                
        processed_data = None
        if data.get("processed_data"):
            try:
                from core.plugins.processors import ProcessedData
                processed_data = ProcessedData.from_dict(data["processed_data"])
            except Exception as e:
                logger.error(f"Error creating ProcessedData from dictionary: {e}")
        
        return cls(
            processed_data=processed_data,
            analysis_content=data.get("analysis_content"),
            metadata=data.get("metadata", {}),
            timestamp=timestamp
        )


class AnalyzerBase(PluginBase):
    """Base class for data analyzers."""
    
    name: str = "base_analyzer"
    description: str = "Base analyzer class"
    analyzer_type: str = "generic"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the analyzer with optional configuration."""
        super().__init__(config)
        
    @abstractmethod
    def analyze(self, processed_data: ProcessedData, params: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """Analyze processed data."""
        pass
    
    def initialize(self) -> bool:
        """Initialize the analyzer. Return True if successful, False otherwise."""
        try:
            # Perform any necessary initialization
            logger.info(f"Initialized analyzer: {self.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize analyzer {self.name}: {e}")
            return False
