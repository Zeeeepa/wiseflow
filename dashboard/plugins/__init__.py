"""
Dashboard plugin integration for Wiseflow.

This module integrates the dashboard with the core plugin system.
"""

from typing import Dict, List, Any, Optional
import logging

from core.plugins.base import registry
from core.plugins.analyzers.entity_analyzer import EntityAnalyzer
from core.plugins.analyzers.trend_analyzer import TrendAnalyzer

logger = logging.getLogger(__name__)

class DashboardPluginManager:
    """Manager for dashboard plugins integration with core plugins."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(DashboardPluginManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the dashboard plugin manager."""
        if self._initialized:
            return
            
        self._initialized = True
        self.entity_analyzer = None
        self.trend_analyzer = None
        logger.info("Dashboard plugin manager initialized")
    
    def initialize(self) -> bool:
        """Initialize the dashboard plugin manager.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Initialize entity analyzer
            entity_analyzer_class = registry.get_analyzer('entity')
            if entity_analyzer_class:
                self.entity_analyzer = entity_analyzer_class()
                self.entity_analyzer.initialize()
                logger.info("Entity analyzer initialized for dashboard")
            else:
                logger.warning("Entity analyzer not found in registry")
            
            # Initialize trend analyzer
            trend_analyzer_class = registry.get_analyzer('trend')
            if trend_analyzer_class:
                self.trend_analyzer = trend_analyzer_class()
                self.trend_analyzer.initialize()
                logger.info("Trend analyzer initialized for dashboard")
            else:
                logger.warning("Trend analyzer not found in registry")
                
            return True
        except Exception as e:
            logger.error(f"Error initializing dashboard plugin manager: {str(e)}")
            return False
    
    def analyze_entities(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Analyze entities using the entity analyzer.
        
        Args:
            data: Data to analyze
            **kwargs: Additional parameters for analysis
            
        Returns:
            Dict[str, Any]: Entity analysis results
        """
        if not self.entity_analyzer:
            entity_analyzer_class = registry.get_analyzer('entity')
            if entity_analyzer_class:
                self.entity_analyzer = entity_analyzer_class()
                self.entity_analyzer.initialize()
            else:
                logger.error("Entity analyzer not available")
                return {"error": "Entity analyzer not available", "entities": []}
        
        try:
            return self.entity_analyzer.analyze(data, **kwargs)
        except Exception as e:
            logger.error(f"Error analyzing entities: {str(e)}")
            return {"error": str(e), "entities": []}
    
    def analyze_trends(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Analyze trends using the trend analyzer.
        
        Args:
            data: Data to analyze
            **kwargs: Additional parameters for analysis
            
        Returns:
            Dict[str, Any]: Trend analysis results
        """
        if not self.trend_analyzer:
            trend_analyzer_class = registry.get_analyzer('trend')
            if trend_analyzer_class:
                self.trend_analyzer = trend_analyzer_class()
                self.trend_analyzer.initialize()
            else:
                logger.error("Trend analyzer not available")
                return {"error": "Trend analyzer not available", "trends": []}
        
        try:
            return self.trend_analyzer.analyze(data, **kwargs)
        except Exception as e:
            logger.error(f"Error analyzing trends: {str(e)}")
            return {"error": str(e), "trends": []}
    
    def get_available_connectors(self) -> List[str]:
        """Get a list of available connectors.
        
        Returns:
            List[str]: List of connector names
        """
        return registry.list_connectors()
    
    def get_available_processors(self) -> List[str]:
        """Get a list of available processors.
        
        Returns:
            List[str]: List of processor names
        """
        return registry.list_processors()
    
    def get_available_analyzers(self) -> List[str]:
        """Get a list of available analyzers.
        
        Returns:
            List[str]: List of analyzer names
        """
        return registry.list_analyzers()
    
    def create_connector(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Create a connector instance.
        
        Args:
            name: Name of the connector
            config: Configuration for the connector
            
        Returns:
            ConnectorPlugin: Connector instance
        """
        connector_class = registry.get_connector(name)
        if not connector_class:
            logger.error(f"Connector {name} not found")
            return None
            
        try:
            connector = connector_class(config)
            connector.initialize()
            return connector
        except Exception as e:
            logger.error(f"Error creating connector {name}: {str(e)}")
            return None
    
    def create_processor(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Create a processor instance.
        
        Args:
            name: Name of the processor
            config: Configuration for the processor
            
        Returns:
            ProcessorPlugin: Processor instance
        """
        processor_class = registry.get_processor(name)
        if not processor_class:
            logger.error(f"Processor {name} not found")
            return None
            
        try:
            processor = processor_class(config)
            processor.initialize()
            return processor
        except Exception as e:
            logger.error(f"Error creating processor {name}: {str(e)}")
            return None
    
    def create_analyzer(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Create an analyzer instance.
        
        Args:
            name: Name of the analyzer
            config: Configuration for the analyzer
            
        Returns:
            AnalyzerPlugin: Analyzer instance
        """
        analyzer_class = registry.get_analyzer(name)
        if not analyzer_class:
            logger.error(f"Analyzer {name} not found")
            return None
            
        try:
            analyzer = analyzer_class(config)
            analyzer.initialize()
            return analyzer
        except Exception as e:
            logger.error(f"Error creating analyzer {name}: {str(e)}")
            return None

# Global instance
dashboard_plugin_manager = DashboardPluginManager()

