"""
Plugin system for WiseFlow.

This module provides a plugin system for extending WiseFlow functionality.
"""

import logging
from typing import Dict, Any, Optional, List, Type, Union

# Import the base plugin classes and plugin manager
from core.plugins.base import (
    BasePlugin,
    ConnectorPlugin,
    ProcessorPlugin,
    AnalyzerPlugin,
    PluginManager,
    plugin_manager
)

logger = logging.getLogger(__name__)

# Export the plugin classes and manager
__all__ = [
    'BasePlugin',
    'ConnectorPlugin',
    'ProcessorPlugin',
    'AnalyzerPlugin',
    'PluginManager',
    'plugin_manager',
    'get_plugin_manager',
    'initialize_plugin_system'
]

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
    
    This function loads and initializes all available plugins.
    
    Returns:
        Dictionary mapping plugin names to initialization success status
    """
    # Load all plugins
    plugin_manager.load_all_plugins()
    
    # Initialize all plugins
    return plugin_manager.initialize_all_plugins()
