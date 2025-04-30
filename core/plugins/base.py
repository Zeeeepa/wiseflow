"""
Base plugin classes for Wiseflow plugin system.
This module defines the base classes for all plugin types in the system.
"""

import abc
from typing import Any, Dict, List, Optional, Union


class BasePlugin(abc.ABC):
    """Base class for all plugins in the system."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the plugin with optional configuration.
        
        Args:
            config: Optional configuration dictionary for the plugin
        """
        self.config = config or {}
        self.name = self.__class__.__name__
        self.initialized = False
        
    @abc.abstractmethod
    def initialize(self) -> bool:
        """Initialize the plugin with its configuration.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        pass
    
    def shutdown(self) -> bool:
        """Shutdown the plugin and release resources.
        
        Returns:
            bool: True if shutdown was successful, False otherwise
        """
        self.initialized = False
        return True
    
    def validate_config(self) -> bool:
        """Validate the plugin configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        return True


class ConnectorPlugin(BasePlugin):
    """Base class for data source connector plugins."""
    
    @abc.abstractmethod
    def connect(self) -> bool:
        """Connect to the data source.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def fetch_data(self, query: str, **kwargs) -> Dict[str, Any]:
        """Fetch data from the source based on query.
        
        Args:
            query: Query string to search for data
            **kwargs: Additional parameters for the query
            
        Returns:
            Dict[str, Any]: Dictionary containing the fetched data
        """
        pass
    
    @abc.abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from the data source.
        
        Returns:
            bool: True if disconnection was successful, False otherwise
        """
        pass


class ProcessorPlugin(BasePlugin):
    """Base class for data processor plugins."""
    
    @abc.abstractmethod
    def process(self, data: Any, **kwargs) -> Any:
        """Process the input data.
        
        Args:
            data: Input data to process
            **kwargs: Additional parameters for processing
            
        Returns:
            Any: Processed data
        """
        pass


class AnalyzerPlugin(BasePlugin):
    """Base class for data analyzer plugins."""
    
    @abc.abstractmethod
    def analyze(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Analyze the input data.
        
        Args:
            data: Input data to analyze
            **kwargs: Additional parameters for analysis
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        pass


class PluginRegistry:
    """Registry for managing plugins in the system."""
    
    def __init__(self):
        """Initialize the plugin registry."""
        self.connectors = {}
        self.processors = {}
        self.analyzers = {}
        
    def register_connector(self, name: str, connector_class: type) -> None:
        """Register a connector plugin.
        
        Args:
            name: Name of the connector
            connector_class: Class of the connector
        """
        if not issubclass(connector_class, ConnectorPlugin):
            raise TypeError(f"Connector {name} must be a subclass of ConnectorPlugin")
        self.connectors[name] = connector_class
        
    def register_processor(self, name: str, processor_class: type) -> None:
        """Register a processor plugin.
        
        Args:
            name: Name of the processor
            processor_class: Class of the processor
        """
        if not issubclass(processor_class, ProcessorPlugin):
            raise TypeError(f"Processor {name} must be a subclass of ProcessorPlugin")
        self.processors[name] = processor_class
        
    def register_analyzer(self, name: str, analyzer_class: type) -> None:
        """Register an analyzer plugin.
        
        Args:
            name: Name of the analyzer
            analyzer_class: Class of the analyzer
        """
        if not issubclass(analyzer_class, AnalyzerPlugin):
            raise TypeError(f"Analyzer {name} must be a subclass of AnalyzerPlugin")
        self.analyzers[name] = analyzer_class
        
    def get_connector(self, name: str) -> Optional[type]:
        """Get a connector plugin by name.
        
        Args:
            name: Name of the connector
            
        Returns:
            Optional[type]: Connector class if found, None otherwise
        """
        return self.connectors.get(name)
        
    def get_processor(self, name: str) -> Optional[type]:
        """Get a processor plugin by name.
        
        Args:
            name: Name of the processor
            
        Returns:
            Optional[type]: Processor class if found, None otherwise
        """
        return self.processors.get(name)
        
    def get_analyzer(self, name: str) -> Optional[type]:
        """Get an analyzer plugin by name.
        
        Args:
            name: Name of the analyzer
            
        Returns:
            Optional[type]: Analyzer class if found, None otherwise
        """
        return self.analyzers.get(name)
        
    def list_connectors(self) -> List[str]:
        """List all registered connectors.
        
        Returns:
            List[str]: List of connector names
        """
        return list(self.connectors.keys())
        
    def list_processors(self) -> List[str]:
        """List all registered processors.
        
        Returns:
            List[str]: List of processor names
        """
        return list(self.processors.keys())
        
    def list_analyzers(self) -> List[str]:
        """List all registered analyzers.
        
        Returns:
            List[str]: List of analyzer names
        """
        return list(self.analyzers.keys())


# Global plugin registry instance
registry = PluginRegistry()

