"""
Plugin system for WiseFlow.

This module provides a plugin system for extending WiseFlow functionality.
"""

import os
import sys
import importlib
import inspect
import logging
import pkgutil
from typing import Dict, Any, Optional, List, Type, Union, Set
import abc

logger = logging.getLogger(__name__)

class PluginBase(abc.ABC):
    """Base class for all plugins."""
    
    name: str = "base_plugin"
    description: str = "Base plugin class"
    version: str = "0.1.0"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the plugin.
        
        Args:
            config: Optional configuration for the plugin
        """
        self.config = config or {}
        self.is_enabled = True
    
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        return True
    
    def shutdown(self) -> bool:
        """
        Shutdown the plugin.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        return True
    
    def enable(self) -> None:
        """Enable the plugin."""
        self.is_enabled = True
    
    def disable(self) -> None:
        """Disable the plugin."""
        self.is_enabled = False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the plugin.
        
        Returns:
            Dictionary with plugin status information
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "is_enabled": self.is_enabled
        }

class PluginManager:
    """
    Plugin manager for WiseFlow.
    
    This class provides functionality to load, initialize, and manage plugins.
    """
    
    def __init__(self, plugins_dir: str = "plugins"):
        """
        Initialize the plugin manager.
        
        Args:
            plugins_dir: Directory containing plugins
        """
        self.plugins_dir = plugins_dir
        self.plugins: Dict[str, PluginBase] = {}
        self.plugin_classes: Dict[str, Type[PluginBase]] = {}
        self.plugin_modules: Dict[str, Any] = {}
        self.loaded_paths: Set[str] = set()
    
    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins.
        
        Returns:
            List of plugin names
        """
        plugin_names = []
        
        # Add plugins directory to path if it exists
        if os.path.isdir(self.plugins_dir):
            sys.path.insert(0, os.path.abspath(self.plugins_dir))
        
        # Discover plugins in the plugins directory
        for _, name, is_pkg in pkgutil.iter_modules([self.plugins_dir]):
            if is_pkg:
                plugin_names.append(name)
        
        # Discover plugins in core modules
        for _, name, is_pkg in pkgutil.iter_modules(["core"]):
            if is_pkg and name not in ["utils", "tests"]:
                plugin_names.append(f"core.{name}")
        
        return plugin_names
    
    def load_plugin(self, plugin_name: str) -> Optional[Type[PluginBase]]:
        """
        Load a plugin by name.
        
        Args:
            plugin_name: Name of the plugin to load
            
        Returns:
            Plugin class or None if not found
        """
        try:
            # Import the plugin module
            module = importlib.import_module(plugin_name)
            self.plugin_modules[plugin_name] = module
            
            # Find plugin classes in the module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, PluginBase) and 
                    obj is not PluginBase and
                    hasattr(obj, "name")):
                    
                    # Register the plugin class
                    plugin_class = obj
                    self.plugin_classes[plugin_class.name] = plugin_class
                    logger.info(f"Loaded plugin class: {plugin_class.name} from {plugin_name}")
                    return plugin_class
            
            logger.warning(f"No plugin class found in {plugin_name}")
            return None
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}")
            return None
    
    def load_all_plugins(self) -> Dict[str, Type[PluginBase]]:
        """
        Load all available plugins.
        
        Returns:
            Dictionary of plugin classes
        """
        plugin_names = self.discover_plugins()
        
        for plugin_name in plugin_names:
            self.load_plugin(plugin_name)
        
        return self.plugin_classes
    
    def initialize_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialize a plugin.
        
        Args:
            plugin_name: Name of the plugin to initialize
            config: Optional configuration for the plugin
            
        Returns:
            True if initialization was successful, False otherwise
        """
        # Check if plugin is already initialized
        if plugin_name in self.plugins:
            logger.warning(f"Plugin {plugin_name} is already initialized")
            return True
        
        # Check if plugin class is loaded
        plugin_class = self.plugin_classes.get(plugin_name)
        if not plugin_class:
            logger.warning(f"Plugin class {plugin_name} not found")
            return False
        
        try:
            # Create plugin instance
            plugin = plugin_class(config)
            
            # Initialize plugin
            if plugin.initialize():
                self.plugins[plugin_name] = plugin
                logger.info(f"Initialized plugin: {plugin_name}")
                return True
            else:
                logger.warning(f"Failed to initialize plugin: {plugin_name}")
                return False
        except Exception as e:
            logger.error(f"Error initializing plugin {plugin_name}: {e}")
            return False
    
    def initialize_all_plugins(self, configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, bool]:
        """
        Initialize all loaded plugins.
        
        Args:
            configs: Optional dictionary of plugin configurations
            
        Returns:
            Dictionary mapping plugin names to initialization success status
        """
        configs = configs or {}
        results = {}
        
        for plugin_name, plugin_class in self.plugin_classes.items():
            config = configs.get(plugin_name, {})
            results[plugin_name] = self.initialize_plugin(plugin_name, config)
        
        return results
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        """
        Get a plugin by name.
        
        Args:
            plugin_name: Name of the plugin to get
            
        Returns:
            Plugin instance or None if not found
        """
        return self.plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, PluginBase]:
        """
        Get all initialized plugins.
        
        Returns:
            Dictionary of plugin instances
        """
        return self.plugins.copy()
    
    def shutdown_plugin(self, plugin_name: str) -> bool:
        """
        Shutdown a plugin.
        
        Args:
            plugin_name: Name of the plugin to shutdown
            
        Returns:
            True if shutdown was successful, False otherwise
        """
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            logger.warning(f"Plugin {plugin_name} not found")
            return False
        
        try:
            # Shutdown plugin
            if plugin.shutdown():
                del self.plugins[plugin_name]
                logger.info(f"Shutdown plugin: {plugin_name}")
                return True
            else:
                logger.warning(f"Failed to shutdown plugin: {plugin_name}")
                return False
        except Exception as e:
            logger.error(f"Error shutting down plugin {plugin_name}: {e}")
            return False
    
    def shutdown_all_plugins(self) -> Dict[str, bool]:
        """
        Shutdown all initialized plugins.
        
        Returns:
            Dictionary mapping plugin names to shutdown success status
        """
        results = {}
        
        for plugin_name in list(self.plugins.keys()):
            results[plugin_name] = self.shutdown_plugin(plugin_name)
        
        return results
    
    def reload_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Reload a plugin.
        
        Args:
            plugin_name: Name of the plugin to reload
            config: Optional configuration for the plugin
            
        Returns:
            True if reload was successful, False otherwise
        """
        # Shutdown plugin if initialized
        if plugin_name in self.plugins:
            if not self.shutdown_plugin(plugin_name):
                logger.warning(f"Failed to shutdown plugin {plugin_name} for reload")
                return False
        
        # Reload plugin module
        if plugin_name in self.plugin_modules:
            try:
                module_name = self.plugin_modules[plugin_name].__name__
                importlib.reload(self.plugin_modules[plugin_name])
                logger.info(f"Reloaded plugin module: {module_name}")
            except Exception as e:
                logger.error(f"Error reloading plugin module {module_name}: {e}")
                return False
        
        # Re-load plugin class
        plugin_class = self.load_plugin(plugin_name)
        if not plugin_class:
            logger.warning(f"Failed to load plugin class {plugin_name} for reload")
            return False
        
        # Initialize plugin
        return self.initialize_plugin(plugin_name, config)

