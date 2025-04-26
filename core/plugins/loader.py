"""
Plugin loader utility for Wiseflow.

This module provides functions for loading and managing plugins.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union, Type

from core.plugins import PluginBase, PluginManager
from core.plugins.processors import ProcessorBase
from core.plugins.analyzers import AnalyzerBase

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
        _plugin_manager = PluginManager(plugins_dir, config_file)
        
    return _plugin_manager

def load_all_plugins(plugins_dir: str = "core/plugins", config_file: str = "core/plugins/config.json") -> Dict[str, PluginBase]:
    """
    Load all available plugins.
    
    Args:
        plugins_dir: Directory containing plugins
        config_file: Path to plugin configuration file
        
    Returns:
        Dictionary of loaded plugins
    """
    # Get the plugin manager
    plugin_manager = get_plugin_manager(plugins_dir, config_file)
    
    # Load all plugins
    plugins = plugin_manager.load_all_plugins()
    
    # Initialize all plugins
    plugin_manager.initialize_all_plugins()
    
    return plugins

def get_processor(name: str) -> Optional[ProcessorBase]:
    """
    Get a processor plugin by name.
    
    Args:
        name: Name of the processor
        
    Returns:
        Processor plugin instance if found, None otherwise
    """
    plugin_manager = get_plugin_manager()
    
    # Try to get the plugin directly
    plugin = plugin_manager.get_plugin(name)
    if plugin and isinstance(plugin, ProcessorBase):
        return plugin
    
    # Try to get the plugin from the registry
    processors = plugin_manager.get_plugins_by_type("processors")
    return processors.get(name)

def get_analyzer(name: str) -> Optional[AnalyzerBase]:
    """
    Get an analyzer plugin by name.
    
    Args:
        name: Name of the analyzer
        
    Returns:
        Analyzer plugin instance if found, None otherwise
    """
    plugin_manager = get_plugin_manager()
    
    # Try to get the plugin directly
    plugin = plugin_manager.get_plugin(name)
    if plugin and isinstance(plugin, AnalyzerBase):
        return plugin
    
    # Try to get the plugin from the registry
    analyzers = plugin_manager.get_plugins_by_type("analyzers")
    return analyzers.get(name)

def get_all_processors() -> Dict[str, ProcessorBase]:
    """
    Get all processor plugins.
    
    Returns:
        Dictionary of processor plugins
    """
    plugin_manager = get_plugin_manager()
    return plugin_manager.get_plugins_by_type("processors")

def get_all_analyzers() -> Dict[str, AnalyzerBase]:
    """
    Get all analyzer plugins.
    
    Returns:
        Dictionary of analyzer plugins
    """
    plugin_manager = get_plugin_manager()
    return plugin_manager.get_plugins_by_type("analyzers")

def reload_plugin(name: str) -> bool:
    """
    Reload a plugin.
    
    Args:
        name: Name of the plugin to reload
        
    Returns:
        True if successful, False otherwise
    """
    plugin_manager = get_plugin_manager()
    return plugin_manager.reload_plugin(name)

def save_plugin_configs(config_file: Optional[str] = None) -> bool:
    """
    Save plugin configurations to a file.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        True if successful, False otherwise
    """
    plugin_manager = get_plugin_manager()
    return plugin_manager.save_plugin_configs(config_file)
