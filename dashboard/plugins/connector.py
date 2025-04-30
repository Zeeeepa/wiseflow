"""
Dashboard connector for integrating with the core plugin system.

This module provides connectors for fetching data from various sources
using the core plugin system.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import json
import os
from datetime import datetime

from dashboard.plugins import dashboard_plugin_manager

logger = logging.getLogger(__name__)

class DashboardConnector:
    """Base class for dashboard connectors."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the dashboard connector.
        
        Args:
            config: Configuration for the connector
        """
        self.config = config or {}
        self.name = self.__class__.__name__
        
    def fetch_data(self, query: str, **kwargs) -> Dict[str, Any]:
        """Fetch data from the source.
        
        Args:
            query: Query string
            **kwargs: Additional parameters
            
        Returns:
            Dict[str, Any]: Fetched data
        """
        raise NotImplementedError("Subclasses must implement fetch_data")

class PluginConnector(DashboardConnector):
    """Connector for fetching data using core plugins."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the plugin connector.
        
        Args:
            config: Configuration for the connector with the following keys:
                - connector_name: Name of the core connector to use
                - connector_config: Configuration for the core connector
        """
        super().__init__(config)
        self.connector_name = self.config.get('connector_name')
        self.connector_config = self.config.get('connector_config', {})
        self.connector = None
        
        if self.connector_name:
            self.connector = dashboard_plugin_manager.create_connector(
                self.connector_name, 
                self.connector_config
            )
    
    def fetch_data(self, query: str, **kwargs) -> Dict[str, Any]:
        """Fetch data using the core connector.
        
        Args:
            query: Query string
            **kwargs: Additional parameters
            
        Returns:
            Dict[str, Any]: Fetched data
        """
        if not self.connector:
            if not self.connector_name:
                logger.error("No connector name specified")
                return {"error": "No connector name specified"}
                
            self.connector = dashboard_plugin_manager.create_connector(
                self.connector_name, 
                self.connector_config
            )
            
            if not self.connector:
                logger.error(f"Failed to create connector: {self.connector_name}")
                return {"error": f"Failed to create connector: {self.connector_name}"}
        
        try:
            # Connect to the data source
            if not self.connector.connect():
                logger.error(f"Failed to connect to data source using {self.connector_name}")
                return {"error": f"Failed to connect to data source"}
            
            # Fetch data
            result = self.connector.fetch_data(query, **kwargs)
            
            # Disconnect
            self.connector.disconnect()
            
            return result
        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}")
            return {"error": str(e)}

class FileConnector(DashboardConnector):
    """Connector for fetching data from files."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the file connector.
        
        Args:
            config: Configuration for the connector with the following keys:
                - base_path: Base path for file operations
        """
        super().__init__(config)
        self.base_path = self.config.get('base_path', '')
    
    def fetch_data(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """Fetch data from a file.
        
        Args:
            file_path: Path to the file
            **kwargs: Additional parameters
            
        Returns:
            Dict[str, Any]: File contents
        """
        try:
            # Resolve the full path
            full_path = os.path.join(self.base_path, file_path)
            
            # Check if the file exists
            if not os.path.exists(full_path):
                logger.error(f"File not found: {full_path}")
                return {"error": f"File not found: {file_path}"}
            
            # Read the file
            with open(full_path, 'r', encoding='utf-8') as f:
                if full_path.endswith('.json'):
                    return json.load(f)
                else:
                    return {"content": f.read()}
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return {"error": str(e)}

class AnalysisConnector(DashboardConnector):
    """Connector for fetching analysis results."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the analysis connector.
        
        Args:
            config: Configuration for the connector with the following keys:
                - analyzer_name: Name of the analyzer to use
                - analyzer_config: Configuration for the analyzer
        """
        super().__init__(config)
        self.analyzer_name = self.config.get('analyzer_name')
        self.analyzer_config = self.config.get('analyzer_config', {})
        self.analyzer = None
        
        if self.analyzer_name:
            self.analyzer = dashboard_plugin_manager.create_analyzer(
                self.analyzer_name, 
                self.analyzer_config
            )
    
    def fetch_data(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Analyze data using the specified analyzer.
        
        Args:
            data: Data to analyze
            **kwargs: Additional parameters
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        if not self.analyzer:
            if not self.analyzer_name:
                logger.error("No analyzer name specified")
                return {"error": "No analyzer name specified"}
                
            self.analyzer = dashboard_plugin_manager.create_analyzer(
                self.analyzer_name, 
                self.analyzer_config
            )
            
            if not self.analyzer:
                logger.error(f"Failed to create analyzer: {self.analyzer_name}")
                return {"error": f"Failed to create analyzer: {self.analyzer_name}"}
        
        try:
            # Analyze the data
            return self.analyzer.analyze(data, **kwargs)
        except Exception as e:
            logger.error(f"Error analyzing data: {str(e)}")
            return {"error": str(e)}

def create_connector(connector_type: str, config: Optional[Dict[str, Any]] = None) -> DashboardConnector:
    """Create a dashboard connector.
    
    Args:
        connector_type: Type of connector to create
        config: Configuration for the connector
        
    Returns:
        DashboardConnector: Dashboard connector instance
    """
    if connector_type == 'plugin':
        return PluginConnector(config)
    elif connector_type == 'file':
        return FileConnector(config)
    elif connector_type == 'analysis':
        return AnalysisConnector(config)
    else:
        logger.error(f"Unknown connector type: {connector_type}")
        return None

