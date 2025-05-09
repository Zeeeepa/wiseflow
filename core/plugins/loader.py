"""
Plugin loader for Wiseflow.

This module provides functions for loading plugins.
"""

import os
import importlib
import inspect
import logging
from typing import Dict, List, Any, Optional, Union, Type

# Import the base plugin classes and plugin manager
# Avoid circular imports by importing from base directly
from core.plugins.base import (
    BasePlugin,
    ConnectorPlugin,
    ProcessorPlugin,
    AnalyzerPlugin,
    PluginManager,
    plugin_manager
)

logger = logging.getLogger(__name__)

def get_plugin_manager() -> PluginManager:
    """
    Get the global plugin manager instance.
    
    Returns:
        PluginManager instance
    """
    return plugin_manager

def load_all_plugins() -> Dict[str, Type[BasePlugin]]:
    """
    Load all plugins.
    
    Returns:
        Dictionary of plugin classes
    """
    return plugin_manager.load_all_plugins()

def load_plugin_from_module(module_name: str) -> List[Type[BasePlugin]]:
    """
    Load plugins from a module.
    
    Args:
        module_name: Name of the module to load plugins from
        
    Returns:
        List of plugin classes
    """
    try:
        module = importlib.import_module(module_name)
        
        # Find all plugin classes in the module
        plugin_classes = []
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, BasePlugin) and obj != BasePlugin:
                plugin_classes.append(obj)
        
        return plugin_classes
    except ImportError as e:
        logger.error(f"Failed to import module {module_name}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading plugins from module {module_name}: {e}")
        return []

def load_plugin_from_file(file_path: str) -> List[Type[BasePlugin]]:
    """
    Load plugins from a file.
    
    Args:
        file_path: Path to the file to load plugins from
        
    Returns:
        List of plugin classes
    """
    try:
        # Convert file path to module name
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # Load the module
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            logger.error(f"Failed to load module from file {file_path}")
            return []
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find all plugin classes in the module
        plugin_classes = []
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, BasePlugin) and obj != BasePlugin:
                plugin_classes.append(obj)
        
        return plugin_classes
    except ImportError as e:
        logger.error(f"Failed to import module from file {file_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading plugins from file {file_path}: {e}")
        return []

def initialize_all_plugins(configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, bool]:
    """
    Initialize all loaded plugins.
    
    Args:
        configs: Optional dictionary of plugin configurations
        
    Returns:
        Dictionary mapping plugin names to initialization success status
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Initialize all plugins
    return manager.initialize_all_plugins(configs)

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
    return manager.get_plugin(name)

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
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Reload the plugin
    return manager.reload_plugin(name)

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
