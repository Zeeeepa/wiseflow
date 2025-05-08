"""
Plugin loader utility for Wiseflow.

This module provides functions for loading and managing plugins.
"""

import os
import logging
import traceback
from typing import Dict, List, Any, Optional, Union, Type

from core.plugins.base import (
    BasePlugin,
    ConnectorPlugin,
    ProcessorPlugin,
    AnalyzerPlugin,
    PluginManager
)
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

# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None

def get_plugin_manager(plugins_dir: str = "core/plugins", config_file: str = "core/plugins/config.json") -> PluginManager:
    """
    Get the global plugin manager instance.
    
    Args:
        plugins_dir: Directory containing plugins
        config_file: Path to plugin configuration file
        
    Returns:
        PluginManager instance
    """
    global _plugin_manager
    
    if _plugin_manager is None:
        # Create a new plugin manager
        from core.plugins.base import plugin_manager
        _plugin_manager = plugin_manager
        
    return _plugin_manager

def load_all_plugins() -> Dict[str, Type[BasePlugin]]:
    """
    Load all available plugins.
    
    Returns:
        Dictionary of loaded plugin classes
        
    Raises:
        PluginLoadError: If plugin loading fails
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Load all plugins
    try:
        return manager.load_all_plugins()
    except PluginLoadError as e:
        logger.error(f"Error loading plugins: {e}")
        # Re-raise the exception
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading plugins: {e}")
        logger.debug(traceback.format_exc())
        raise PluginLoadError("all_plugins", str(e))

def initialize_all_plugins(configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, bool]:
    """
    Initialize all loaded plugins.
    
    Args:
        configs: Optional dictionary of plugin configurations
        
    Returns:
        Dictionary mapping plugin names to initialization success status
        
    Raises:
        PluginInitializationError: If plugin initialization fails
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Initialize all plugins
    try:
        return manager.initialize_all_plugins(configs)
    except PluginInitializationError as e:
        logger.error(f"Error initializing plugins: {e}")
        # Re-raise the exception
        raise
    except Exception as e:
        logger.error(f"Unexpected error initializing plugins: {e}")
        logger.debug(traceback.format_exc())
        raise PluginInitializationError("all_plugins", str(e))

def get_plugin(name: str) -> Optional[BasePlugin]:
    """
    Get a plugin by name.
    
    Args:
        name: Name of the plugin
        
    Returns:
        Plugin instance if found, None otherwise
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Get the plugin
    plugin = manager.get_plugin(name)
    
    if not plugin:
        logger.debug(f"Plugin '{name}' not found")
    
    return plugin

def get_processor(name: str) -> Optional[ProcessorPlugin]:
    """
    Get a processor plugin by name.
    
    Args:
        name: Name of the processor
        
    Returns:
        Processor plugin instance if found, None otherwise
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Get the plugin
    plugin = manager.get_plugin(name)
    
    # Check if it's a processor
    if plugin and isinstance(plugin, ProcessorPlugin):
        return plugin
    
    if plugin:
        logger.warning(f"Plugin '{name}' is not a processor plugin")
    else:
        logger.debug(f"Processor plugin '{name}' not found")
    
    return None

def get_analyzer(name: str) -> Optional[AnalyzerPlugin]:
    """
    Get an analyzer plugin by name.
    
    Args:
        name: Name of the analyzer
        
    Returns:
        Analyzer plugin instance if found, None otherwise
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Get the plugin
    plugin = manager.get_plugin(name)
    
    # Check if it's an analyzer
    if plugin and isinstance(plugin, AnalyzerPlugin):
        return plugin
    
    if plugin:
        logger.warning(f"Plugin '{name}' is not an analyzer plugin")
    else:
        logger.debug(f"Analyzer plugin '{name}' not found")
    
    return None

def get_connector(name: str) -> Optional[ConnectorPlugin]:
    """
    Get a connector plugin by name.
    
    Args:
        name: Name of the connector
        
    Returns:
        Connector plugin instance if found, None otherwise
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Get the plugin
    plugin = manager.get_plugin(name)
    
    # Check if it's a connector
    if plugin and isinstance(plugin, ConnectorPlugin):
        return plugin
    
    if plugin:
        logger.warning(f"Plugin '{name}' is not a connector plugin")
    else:
        logger.debug(f"Connector plugin '{name}' not found")
    
    return None

def get_all_processors() -> Dict[str, ProcessorPlugin]:
    """
    Get all processor plugins.
    
    Returns:
        Dictionary of processor plugins
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Get all processors
    return manager.get_plugins_by_type("processors")

def get_all_analyzers() -> Dict[str, AnalyzerPlugin]:
    """
    Get all analyzer plugins.
    
    Returns:
        Dictionary of analyzer plugins
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Get all analyzers
    return manager.get_plugins_by_type("analyzers")

def get_all_connectors() -> Dict[str, ConnectorPlugin]:
    """
    Get all connector plugins.
    
    Returns:
        Dictionary of connector plugins
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Get all connectors
    return manager.get_plugins_by_type("connectors")

def reload_plugin(name: str) -> bool:
    """
    Reload a plugin.
    
    Args:
        name: Name of the plugin to reload
        
    Returns:
        True if successful, False otherwise
        
    Raises:
        PluginLoadError: If plugin loading fails
        PluginInitializationError: If plugin initialization fails
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Reload the plugin
    try:
        return manager.reload_plugin(name)
    except (PluginLoadError, PluginInitializationError) as e:
        logger.error(f"Error reloading plugin '{name}': {e}")
        # Re-raise the exception
        raise
    except Exception as e:
        logger.error(f"Unexpected error reloading plugin '{name}': {e}")
        logger.debug(traceback.format_exc())
        raise PluginLoadError(name, str(e))

def save_plugin_configs(config_file: Optional[str] = None) -> bool:
    """
    Save plugin configurations to a file.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        True if successful, False otherwise
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Save plugin configurations
    return manager.save_plugin_configs(config_file)

def register_dependency(plugin_name: str, dependency_name: str) -> None:
    """
    Register a dependency between plugins.
    
    Args:
        plugin_name: Name of the plugin that depends on another
        dependency_name: Name of the plugin that is depended upon
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Register the dependency
    manager.register_dependency(plugin_name, dependency_name)

def register_shared_resource(resource_name: str, resource: Any) -> None:
    """
    Register a shared resource.
    
    Args:
        resource_name: Name of the resource
        resource: The resource object
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Register the shared resource
    manager.register_shared_resource(resource_name, resource)

def get_shared_resource(resource_name: str) -> Optional[Any]:
    """
    Get a shared resource.
    
    Args:
        resource_name: Name of the resource
        
    Returns:
        The resource object or None if not found
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Get the shared resource
    return manager.get_shared_resource(resource_name)

def release_shared_resource(resource_name: str) -> bool:
    """
    Release a reference to a shared resource.
    
    Args:
        resource_name: Name of the resource
        
    Returns:
        True if resource was released, False otherwise
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Release the shared resource
    return manager.release_shared_resource(resource_name)
