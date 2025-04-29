"""
Base classes for the Wiseflow plugin system.

This module provides the base classes that all plugins should inherit from.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union

class PluginBase(ABC):
    """Base class for all plugins."""
    
    name: str = "base_plugin"
    description: str = "Base plugin class"
    version: str = "0.1.0"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the plugin with optional configuration."""
        self.config = config or {}
        self.is_enabled = True
        
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the plugin. Return True if successful, False otherwise."""
        pass
    
    def enable(self) -> None:
        """Enable the plugin."""
        self.is_enabled = True
        
    def disable(self) -> None:
        """Disable the plugin."""
        self.is_enabled = False
    
    def get_config(self) -> Dict[str, Any]:
        """Get the plugin configuration."""
        return self.config
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """Set the plugin configuration."""
        self.config = config
        
    def __str__(self) -> str:
        """Return a string representation of the plugin."""
        return f"{self.name} (v{self.version}): {self.description}"

