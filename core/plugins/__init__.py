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

# Import exceptions
from core.plugins.exceptions import (
    PluginError,
    PluginInitializationError,
    PluginValidationError,
    PluginInterfaceError,
    PluginLoadError,
    PluginDependencyError,
    PluginResourceError
)

logger = logging.getLogger(__name__)

# Export the plugin classes, manager, and exceptions
__all__ = [
    'BasePlugin',
    'ConnectorPlugin',
    'ProcessorPlugin',
    'AnalyzerPlugin',
    'PluginManager',
    'plugin_manager',
    'get_plugin_manager',
    'initialize_plugin_system',
    'PluginError',
    'PluginInitializationError',
    'PluginValidationError',
    'PluginInterfaceError',
    'PluginLoadError',
    'PluginDependencyError',
    'PluginResourceError'
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
        
    Raises:
        PluginLoadError: If plugin loading fails
        PluginInitializationError: If plugin initialization fails
    """
    try:
        # Load all plugins
        plugin_manager.load_all_plugins()
        
        # Initialize all plugins
        return plugin_manager.initialize_all_plugins()
    except (PluginLoadError, PluginInitializationError) as e:
        logger.error(f"Error initializing plugin system: {e}")
        # Re-raise the exception
        raise
    except Exception as e:
        logger.error(f"Unexpected error initializing plugin system: {e}")
        raise PluginInitializationError("plugin_system", str(e))
