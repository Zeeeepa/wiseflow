"""
Analyzer plugins for Wiseflow.

This module provides base classes for analyzer plugins.
"""

from typing import Dict, List, Any, Optional, Union
from abc import abstractmethod
from datetime import datetime

from core.plugins.base import PluginBase
from core.plugins.processors import ProcessedData

class AnalysisResult:
    """Represents analysis results from an analyzer plugin."""
    
    def __init__(
        self,
        processed_data: ProcessedData,
        analysis_content: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        analysis_info: Optional[Dict[str, Any]] = None
    ):
        """Initialize analysis result."""
        self.processed_data = processed_data
        self.analysis_content = analysis_content
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now()
        self.analysis_info = analysis_info or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the analysis result to a dictionary."""
        return {
            "processed_data": self.processed_data.to_dict() if self.processed_data else None,
            "analysis_content": self.analysis_content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "analysis_info": self.analysis_info
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisResult':
        """Create analysis result from a dictionary."""
        processed_data = None
        if data.get("processed_data"):
            processed_data = ProcessedData.from_dict(data["processed_data"])
            
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except (ValueError, TypeError):
                pass
                
        return cls(
            processed_data=processed_data,
            analysis_content=data["analysis_content"],
            metadata=data.get("metadata", {}),
            timestamp=timestamp,
            analysis_info=data.get("analysis_info", {})
        )


class AnalyzerBase(PluginBase):
    """Base class for analyzer plugins."""
    
    name: str = "base_analyzer"
    description: str = "Base analyzer plugin"
    analyzer_type: str = "generic"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the analyzer with optional configuration."""
        super().__init__(config)
        
    @abstractmethod
    def analyze(self, processed_data: ProcessedData, params: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Analyze processed data.
        
        Args:
            processed_data: The processed data to analyze
            params: Optional analysis parameters
            
        Returns:
            AnalysisResult: The analysis result
        """
        pass
    
    def batch_analyze(self, processed_data_items: List[ProcessedData], params: Optional[Dict[str, Any]] = None) -> List[AnalysisResult]:
        """
        Analyze multiple processed data items.
        
        Args:
            processed_data_items: The processed data items to analyze
            params: Optional analysis parameters
            
        Returns:
            List[AnalysisResult]: The analysis results
        """
        results = []
        for item in processed_data_items:
            results.append(self.analyze(item, params))
        return results
    
    def initialize(self) -> bool:
        """Initialize the analyzer. Return True if successful, False otherwise."""
        return True

