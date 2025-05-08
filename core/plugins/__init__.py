"""
Plugin system for Wiseflow.

This module provides a plugin system for extending Wiseflow functionality.
"""

import os
import logging
import importlib
import inspect
from typing import Dict, List, Any, Optional, Union, Type, Callable

# Import the base plugin classes and plugin manager
from core.plugins.base import (
    BasePlugin,
    ConnectorPlugin,
    ProcessorPlugin,
    AnalyzerPlugin,
    PluginManager
)

logger = logging.getLogger(__name__)

# Global plugin manager instance
plugin_manager = PluginManager()

def get_plugin_manager() -> PluginManager:
    """
    Get the global plugin manager instance.
    
    Returns:
        PluginManager instance
    """
    return plugin_manager

def initialize_plugin_system() -> Dict[str, bool]:
    """
    Initialize the plugin system.
    
    This function initializes the plugin system and all available plugins.
    
    Returns:
        Dictionary mapping plugin names to initialization success status
    """
    # Register connector plugins
    from core.plugins.connectors import register_connector_plugins
    register_connector_plugins()
    
    # Load all plugins
    plugin_manager.load_all_plugins()
    
    # Initialize all plugins
    return plugin_manager.initialize_all_plugins()

def get_plugin(name: str) -> Optional[BasePlugin]:
    """
    Get a plugin by name.
    
    Args:
        name: Name of the plugin
        
    Returns:
        Plugin instance if found, None otherwise
    """
    return plugin_manager.get_plugin(name)

def get_all_plugins() -> Dict[str, BasePlugin]:
    """
    Get all plugins.
    
    Returns:
        Dictionary of plugin instances
    """
    return plugin_manager.get_all_plugins()

def register_plugin(plugin_class: Type[BasePlugin]) -> bool:
    """
    Register a plugin.
    
    Args:
        plugin_class: Plugin class to register
        
    Returns:
        True if registration was successful, False otherwise
    """
    return plugin_manager.register_plugin(plugin_class)

def unregister_plugin(name: str) -> bool:
    """
    Unregister a plugin.
    
    Args:
        name: Name of the plugin to unregister
        
    Returns:
        True if unregistration was successful, False otherwise
    """
    return plugin_manager.unregister_plugin(name)

# Export plugin classes and functions
__all__ = [
    'BasePlugin',
    'ConnectorPlugin',
    'ProcessorPlugin',
    'AnalyzerPlugin',
    'PluginManager',
    'plugin_manager',
    'get_plugin_manager',
    'initialize_plugin_system',
    'get_plugin',
    'get_all_plugins',
    'register_plugin',
    'unregister_plugin'
]
