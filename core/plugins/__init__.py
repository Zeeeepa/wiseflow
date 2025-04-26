"""
Plugin system for Wiseflow.

This module provides the base classes and utilities for the plugin system.
"""

from typing import Dict, List, Type, Any, Optional, Set, Union, Tuple
import importlib
import os
import sys
import logging
import json
import inspect
import pkgutil
import importlib.util
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

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
        logger.info(f"Plugin {self.name} enabled")
        
    def disable(self) -> None:
        """Disable the plugin."""
        self.is_enabled = False
        logger.info(f"Plugin {self.name} disabled")
    
    def get_config(self) -> Dict[str, Any]:
        """Get the plugin configuration."""
        return self.config
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """Set the plugin configuration."""
        self.config = config
        
    def __str__(self) -> str:
        """Return a string representation of the plugin."""
        return f"{self.name} (v{self.version}): {self.description}"


class PluginRegistry:
    """Registry for plugin types and instances."""
    
    _instance = None
    
    def __new__(cls):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(PluginRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the plugin registry."""
        if self._initialized:
            return
            
        self._plugin_types: Dict[str, Type[PluginBase]] = {}
        self._plugin_instances: Dict[str, Dict[str, PluginBase]] = {}
        self._initialized = True
        
    def register_plugin_type(self, plugin_type: str, plugin_class: Type[PluginBase]) -> None:
        """Register a plugin type."""
        if plugin_type not in self._plugin_types:
            self._plugin_types[plugin_type] = plugin_class
            logger.debug(f"Registered plugin type: {plugin_type}")
        
    def get_plugin_type(self, plugin_type: str) -> Optional[Type[PluginBase]]:
        """Get a plugin type by name."""
        return self._plugin_types.get(plugin_type)
    
    def get_all_plugin_types(self) -> Dict[str, Type[PluginBase]]:
        """Get all registered plugin types."""
        return self._plugin_types.copy()
    
    def register_plugin_instance(self, plugin_type: str, plugin: PluginBase) -> None:
        """Register a plugin instance."""
        if plugin_type not in self._plugin_instances:
            self._plugin_instances[plugin_type] = {}
            
        self._plugin_instances[plugin_type][plugin.name] = plugin
        logger.debug(f"Registered plugin instance: {plugin.name} (type: {plugin_type})")
    
    def get_plugin_instance(self, plugin_type: str, plugin_name: str) -> Optional[PluginBase]:
        """Get a plugin instance by type and name."""
        if plugin_type in self._plugin_instances:
            return self._plugin_instances[plugin_type].get(plugin_name)
        return None
    
    def get_all_plugin_instances(self, plugin_type: Optional[str] = None) -> Dict[str, Dict[str, PluginBase]]:
        """Get all registered plugin instances, optionally filtered by type."""
        if plugin_type:
            return {plugin_type: self._plugin_instances.get(plugin_type, {}).copy()}
        return self._plugin_instances.copy()


class PluginManager:
    """Manager for loading and managing plugins."""
    
    def __init__(self, plugins_dir: Optional[str] = None, config_file: Optional[str] = None):
        """Initialize the plugin manager."""
        self.plugins_dir = plugins_dir or "plugins"
        self.config_file = config_file
        self.plugins: Dict[str, PluginBase] = {}
        self.registry = PluginRegistry()
        
        # Load plugin configurations if config file is provided
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    self.plugin_configs = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load plugin configurations from {config_file}: {e}")
    
    def discover_plugins(self) -> List[Tuple[str, str]]:
        """
        Discover available plugins in the plugins directory.
        
        Returns:
            List of tuples containing (module_path, plugin_type)
        """
        plugin_modules = []
        
        # Ensure the plugins directory exists in the Python path
        plugins_path = os.path.abspath(self.plugins_dir)
        
        # Validate the plugins directory
        if not os.path.exists(plugins_path):
            logger.error(f"Plugins directory does not exist: {plugins_path}")
            return []
            
        # Security check to prevent directory traversal
        if not plugins_path.startswith(os.path.abspath(os.getcwd())):
            logger.error(f"Plugins directory must be within current working directory")
            return []
        
        if plugins_path not in sys.path:
            sys.path.insert(0, os.path.dirname(plugins_path))
        
        # Walk through the plugins directory
        for root, dirs, files in os.walk(self.plugins_dir):
            # Skip __pycache__ directories
            if "__pycache__" in root:
                continue
                
            # Determine the plugin type from the directory structure
            rel_path = os.path.relpath(root, start=os.path.dirname(self.plugins_dir))
            if rel_path == ".":
                # Root plugins directory
                plugin_type = "general"
            else:
                # Subdirectory indicates plugin type
                plugin_type = os.path.basename(rel_path)
            
            # Look for Python files
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    # Convert file path to module path
                    module_path = os.path.join(root, file)
                    rel_module_path = os.path.relpath(module_path, start=os.path.dirname(self.plugins_dir))
                    import_path = os.path.splitext(rel_module_path)[0].replace(os.path.sep, ".")
                    
                    plugin_modules.append((import_path, plugin_type))
        
        # Also discover plugins in packages (directories with __init__.py)
        for _, name, is_pkg in pkgutil.iter_modules([self.plugins_dir]):
            if is_pkg and name not in ["__pycache__"]:
                # This is a package, check if it's a plugin type directory
                plugin_type = name
                package_path = os.path.join(self.plugins_dir, name)
                
                # Look for Python files in the package
                for _, module_name, _ in pkgutil.iter_modules([package_path]):
                    if not module_name.startswith("__"):
                        import_path = f"{os.path.basename(self.plugins_dir)}.{name}.{module_name}"
                        plugin_modules.append((import_path, plugin_type))
        
        return plugin_modules

    def load_plugin(self, module_path: str, plugin_type: str) -> Optional[PluginBase]:
        """
        Load a plugin from a module path.
        
        Args:
            module_path: Path to the module containing the plugin
            plugin_type: Type of the plugin
            
        Returns:
            Plugin instance if successful, None otherwise
        """
        try:
            # Import the module
            module = importlib.import_module(module_path)
            
            # Find plugin classes in the module
            plugin_classes = []
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, PluginBase) and 
                    obj is not PluginBase):
                    
                    plugin_classes.append(obj)
            
            if not plugin_classes:
                logger.warning(f"No plugin class found in module: {module_path}")
                return None
            
            # Create an instance of each plugin class
            for plugin_class in plugin_classes:
                # Get configuration for this plugin if available
                plugin_name = getattr(plugin_class, "name", plugin_class.__name__.lower())
                config = self.plugin_configs.get(plugin_name, {})
                
                # Create the plugin instance
                plugin = plugin_class(config)
                
                # Register the plugin
                self.plugins[plugin.name] = plugin
                self.registry.register_plugin_instance(plugin_type, plugin)
                
                logger.info(f"Loaded plugin: {plugin} (type: {plugin_type})")
                
                # Return the first plugin found (for backward compatibility)
                return plugin
                
        except Exception as e:
            logger.error(f"Failed to load plugin from {module_path}: {e}")
            return None
    
    def load_all_plugins(self) -> Dict[str, PluginBase]:
        """Discover and load all available plugins."""
        plugin_modules = self.discover_plugins()
        
        for module_path, plugin_type in plugin_modules:
            self.load_plugin(module_path, plugin_type)
            
        return self.plugins
    
    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """Get a plugin by name."""
        return self.plugins.get(name)
    
    def get_plugins_by_type(self, plugin_type: str) -> Dict[str, PluginBase]:
        """Get all plugins of a specific type."""
        plugin_instances = self.registry.get_all_plugin_instances(plugin_type)
        if plugin_type in plugin_instances:
            return plugin_instances[plugin_type]
        return {}
    
    def initialize_plugin(self, name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """Initialize a plugin with optional configuration."""
        plugin = self.get_plugin(name)
        if plugin:
            if config:
                plugin.set_config(config)
            return plugin.initialize()
        return False
    
    def initialize_all_plugins(self, configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, bool]:
        """Initialize all loaded plugins with optional configurations."""
        results = {}
        configs = configs or {}
        
        for name, plugin in self.plugins.items():
            config = configs.get(name)
            results[name] = self.initialize_plugin(name, config)
            
        return results
    
    def save_plugin_configs(self, config_file: Optional[str] = None) -> bool:
        """Save plugin configurations to a file."""
        config_file = config_file or self.config_file
        if not config_file:
            logger.warning("No config file specified for saving plugin configurations")
            return False
            
        try:
            # Collect configurations from all plugins
            configs = {}
            for name, plugin in self.plugins.items():
                configs[name] = plugin.get_config()
                
            # Save to file
            with open(config_file, 'w') as f:
                json.dump(configs, f, indent=2)
                
            logger.info(f"Saved plugin configurations to {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save plugin configurations to {config_file}: {e}")
            return False
    
    def reload_plugin(self, name: str) -> bool:
        """Reload a plugin."""
        plugin = self.get_plugin(name)
        if not plugin:
            logger.warning(f"Plugin {name} not found, cannot reload")
            return False
            
        try:
            # Get the module path and plugin type
            module = inspect.getmodule(plugin.__class__)
            if not module:
                logger.warning(f"Could not determine module for plugin {name}")
                return False
                
            module_path = module.__name__
            
            # Determine plugin type
            plugin_type = "general"
            for type_name, instances in self.registry.get_all_plugin_instances().items():
                if name in instances:
                    plugin_type = type_name
                    break
            
            # Save the configuration
            config = plugin.get_config()
            
            # Remove the old plugin
            del self.plugins[name]
            
            # Reload the module
            importlib.reload(module)
            
            # Load the plugin again
            new_plugin = self.load_plugin(module_path, plugin_type)
            if new_plugin:
                # Restore configuration
                new_plugin.set_config(config)
                
                # Initialize the plugin
                success = new_plugin.initialize()
                
                logger.info(f"Reloaded plugin: {new_plugin}")
                return success
                
            logger.warning(f"Failed to reload plugin {name}")
            return False
            
        except Exception as e:
            logger.error(f"Error reloading plugin {name}: {e}")
            return False
