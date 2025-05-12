\"\"\"
Base connector interface for data mining tasks.
This module defines the base interface that all connectors must implement.
\"\"\"\n
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union

class ConnectorError(Exception):
    """Base exception for connector errors."""
    pass

class ConnectionError(ConnectorError):
    """Exception raised when a connection cannot be established."""
    pass

class FetchError(ConnectorError):
    """Exception raised when data fetching fails."""
    pass

class ValidationError(ConnectorError):
    """Exception raised when input validation fails."""
    pass

class BaseConnector(ABC):
    """
    Base connector interface for data mining tasks.
    
    All connectors must implement this interface to ensure consistent
    behavior across different data sources.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the connector with configuration.
        
        Args:
            config: Configuration dictionary for the connector
        """
        self.config = config or {}
        self.is_initialized = False
        self.is_connected = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the connector with the provided configuration.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish a connection to the data source.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Disconnect from the data source.
        
        Returns:
            bool: True if disconnection was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def fetch_data(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch data from the data source.
        
        Args:
            query: Query string for the data source
            **kwargs: Additional parameters for the query
            
        Returns:
            Dict[str, Any]: Dictionary containing the fetched data
        """
        pass
    
    @abstractmethod
    def validate_query(self, query: str, **kwargs) -> bool:
        """
        Validate a query before execution.
        
        Args:
            query: Query string to validate
            **kwargs: Additional parameters for the query
            
        Returns:
            bool: True if the query is valid, False otherwise
        """
        pass
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of the connector.
        
        Returns:
            Dict[str, Any]: Dictionary containing the connector capabilities
        """
        return {
            "supports_pagination": False,
            "supports_filtering": False,
            "supports_sorting": False,
            "supports_aggregation": False,
            "max_results_per_query": 100,
            "rate_limit": None
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the connector.
        
        Returns:
            Dict[str, Any]: Dictionary containing the connector status
        """
        return {
            "is_initialized": self.is_initialized,
            "is_connected": self.is_connected,
            "config": {k: v for k, v in self.config.items() if k not in ["api_key", "password", "token", "secret"]}
        }
    
    def validate_config(self, config: Dict[str, Any] = None) -> bool:
        """
        Validate the configuration.
        
        Args:
            config: Configuration dictionary to validate (uses self.config if None)
            
        Returns:
            bool: True if the configuration is valid, False otherwise
        """
        # Default implementation - subclasses should override this
        return True

