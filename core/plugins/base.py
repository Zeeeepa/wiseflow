"""
Base plugin classes for Wiseflow plugin system.
This module defines the base classes for all plugin types in the system.
"""

import abc
import logging
from typing import Any, Dict, List, Optional, Union, Set, Type

logger = logging.getLogger(__name__)

class BasePlugin(abc.ABC):
    """Base class for all plugins in the system."""
    
    name: str = "base_plugin"
    description: str = "Base plugin class"
    version: str = "0.1.0"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the plugin with optional configuration.
        
        Args:
            config: Optional configuration dictionary for the plugin
        """
        self.config = config or {}
        self.name = self.__class__.__name__ if not hasattr(self, 'name') or not self.name else self.name
        self.initialized = False
        self.is_enabled = True
    
    @abc.abstractmethod
    def initialize(self) -> bool:
        """Initialize the plugin with its configuration.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        pass
    
    def shutdown(self) -> bool:
        """Shutdown the plugin and release resources.
        
        Returns:
            bool: True if shutdown was successful, False otherwise
        """
        self.initialized = False
        return True
    
    def validate_config(self) -> bool:
        """Validate the plugin configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
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
            "is_enabled": self.is_enabled,
            "initialized": self.initialized
        }


class ConnectorPlugin(BasePlugin):
    """Base class for data source connector plugins."""
    
    @abc.abstractmethod
    def connect(self) -> bool:
        """Connect to the data source.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def fetch_data(self, query: str, **kwargs) -> Dict[str, Any]:
        """Fetch data from the source based on query.
        
        Args:
            query: Query string to search for data
            **kwargs: Additional parameters for the query
            
        Returns:
            Dict[str, Any]: Dictionary containing the fetched data
        """
        pass
    
    @abc.abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from the data source.
        
        Returns:
            bool: True if disconnection was successful, False otherwise
        """
        pass


class ProcessorPlugin(BasePlugin):
    """Base class for data processor plugins."""
    
    @abc.abstractmethod
    def process(self, data: Any, **kwargs) -> Any:
        """Process the input data.
        
        Args:
            data: Input data to process
            **kwargs: Additional parameters for processing
            
        Returns:
            Any: Processed data
        """
        pass


class AnalyzerPlugin(BasePlugin):
    """Base class for data analyzer plugins."""
    
    @abc.abstractmethod
    def analyze(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Analyze the input data.
        
        Args:
            data: Input data to analyze
            **kwargs: Additional parameters for analysis
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        pass


class PluginManager:
    """
    Plugin manager for Wiseflow.
    
    This class provides functionality to load, initialize, and manage plugins.
    """
    
    def __init__(self, plugins_dir: str = "plugins", config_file: Optional[str] = None):
        """
        Initialize the plugin manager.
        
        Args:
            plugins_dir: Directory containing plugins
            config_file: Optional path to plugin configuration file
        """
        self.plugins_dir = plugins_dir
        self.config_file = config_file
        self.plugins: Dict[str, BasePlugin] = {}
        self.plugin_classes: Dict[str, Type[BasePlugin]] = {}
        self.plugin_modules: Dict[str, Any] = {}
        self.loaded_paths: Set[str] = set()
        
        # Plugin type registries
        self.connectors: Dict[str, Type[ConnectorPlugin]] = {}
        self.processors: Dict[str, Type[ProcessorPlugin]] = {}
        self.analyzers: Dict[str, Type[AnalyzerPlugin]] = {}
        
        # Load plugin configurations if config file is provided
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        if config_file:
            self._load_plugin_configs()
    
    def _load_plugin_configs(self) -> None:
        """Load plugin configurations from the config file."""
        if not self.config_file:
            return
        
        try:
            import json
            import os
            
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.plugin_configs = json.load(f)
                logger.info(f"Loaded plugin configurations from {self.config_file}")
            else:
                logger.warning(f"Plugin configuration file {self.config_file} not found")
        except Exception as e:
            logger.error(f"Error loading plugin configurations: {e}")
    
    def save_plugin_configs(self, config_file: Optional[str] = None) -> bool:
        """
        Save plugin configurations to a file.
        
        Args:
            config_file: Path to configuration file, defaults to the one provided in constructor
            
        Returns:
            True if successful, False otherwise
        """
        config_file = config_file or self.config_file
        if not config_file:
            logger.warning("No configuration file specified for saving plugin configurations")
            return False
        
        try:
            import json
            import os
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            
            # Save configurations
            with open(config_file, 'w') as f:
                json.dump(self.plugin_configs, f, indent=2)
            
            logger.info(f"Saved plugin configurations to {config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving plugin configurations: {e}")
            return False
    
    def register_connector(self, name: str, connector_class: Type[ConnectorPlugin]) -> None:
        """Register a connector plugin.
        
        Args:
            name: Name of the connector
            connector_class: Class of the connector
        """
        if not issubclass(connector_class, ConnectorPlugin):
            raise TypeError(f"Connector {name} must be a subclass of ConnectorPlugin")
        self.connectors[name] = connector_class
        self.plugin_classes[name] = connector_class
        logger.debug(f"Registered connector plugin: {name}")
    
    def register_processor(self, name: str, processor_class: Type[ProcessorPlugin]) -> None:
        """Register a processor plugin.
        
        Args:
            name: Name of the processor
            processor_class: Class of the processor
        """
        if not issubclass(processor_class, ProcessorPlugin):
            raise TypeError(f"Processor {name} must be a subclass of ProcessorPlugin")
        self.processors[name] = processor_class
        self.plugin_classes[name] = processor_class
        logger.debug(f"Registered processor plugin: {name}")
    
    def register_analyzer(self, name: str, analyzer_class: Type[AnalyzerPlugin]) -> None:
        """Register an analyzer plugin.
        
        Args:
            name: Name of the analyzer
            analyzer_class: Class of the analyzer
        """
        if not issubclass(analyzer_class, AnalyzerPlugin):
            raise TypeError(f"Analyzer {name} must be a subclass of AnalyzerPlugin")
        self.analyzers[name] = analyzer_class
        self.plugin_classes[name] = analyzer_class
        logger.debug(f"Registered analyzer plugin: {name}")
    
    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins.
        
        Returns:
            List of plugin names
        """
        import os
        import sys
        import pkgutil
        
        plugin_names = []
        
        # Add plugins directory to path if it exists
        if os.path.isdir(self.plugins_dir):
            plugins_path = os.path.abspath(self.plugins_dir)
            if plugins_path not in sys.path:
                sys.path.insert(0, plugins_path)
            
            # Discover plugins in the plugins directory
            for _, name, is_pkg in pkgutil.iter_modules([plugins_path]):
                if is_pkg:
                    plugin_names.append(name)
        
        # Discover plugins in core modules
        core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core")
        if os.path.isdir(core_path):
            for _, name, is_pkg in pkgutil.iter_modules([core_path]):
                if is_pkg and name not in ["utils", "tests"]:
                    plugin_names.append(f"core.{name}")
        
        logger.info(f"Discovered {len(plugin_names)} potential plugins: {', '.join(plugin_names)}")
        return plugin_names
    
    def load_plugin(self, plugin_name: str) -> Optional[Type[BasePlugin]]:
        """
        Load a plugin by name.
        
        Args:
            plugin_name: Name of the plugin to load
            
        Returns:
            Plugin class or None if not found
        """
        try:
            import importlib
            import inspect
            
            # Import the plugin module
            module = importlib.import_module(plugin_name)
            self.plugin_modules[plugin_name] = module
            
            # Find plugin classes in the module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BasePlugin) and 
                    obj is not BasePlugin and
                    obj is not ConnectorPlugin and
                    obj is not ProcessorPlugin and
                    obj is not AnalyzerPlugin and
                    hasattr(obj, "name")):
                    
                    # Register the plugin class
                    plugin_class = obj
                    plugin_name = plugin_class.name
                    self.plugin_classes[plugin_name] = plugin_class
                    
                    # Register by type
                    if issubclass(plugin_class, ConnectorPlugin):
                        self.register_connector(plugin_name, plugin_class)
                    elif issubclass(plugin_class, ProcessorPlugin):
                        self.register_processor(plugin_name, plugin_class)
                    elif issubclass(plugin_class, AnalyzerPlugin):
                        self.register_analyzer(plugin_name, plugin_class)
                    
                    logger.info(f"Loaded plugin class: {plugin_name} from {plugin_name}")
                    return plugin_class
            
            logger.warning(f"No plugin class found in {plugin_name}")
            return None
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}")
            return None
    
    def load_all_plugins(self) -> Dict[str, Type[BasePlugin]]:
        """
        Load all available plugins.
        
        Returns:
            Dictionary of plugin classes
        """
        plugin_names = self.discover_plugins()
        
        for plugin_name in plugin_names:
            self.load_plugin(plugin_name)
        
        logger.info(f"Loaded {len(self.plugin_classes)} plugin classes")
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
            # Get configuration
            if config is None:
                config = self.plugin_configs.get(plugin_name, {})
            
            # Create plugin instance
            plugin = plugin_class(config)
            
            # Initialize plugin
            if plugin.initialize():
                plugin.initialized = True
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
            config = configs.get(plugin_name, self.plugin_configs.get(plugin_name, {}))
            results[plugin_name] = self.initialize_plugin(plugin_name, config)
        
        logger.info(f"Initialized {sum(1 for success in results.values() if success)} out of {len(results)} plugins")
        return results
    
    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """
        Get a plugin by name.
        
        Args:
            plugin_name: Name of the plugin to get
            
        Returns:
            Plugin instance or None if not found
        """
        return self.plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, BasePlugin]:
        """
        Get all initialized plugins.
        
        Returns:
            Dictionary of plugin instances
        """
        return self.plugins.copy()
    
    def get_plugins_by_type(self, plugin_type: str) -> Dict[str, BasePlugin]:
        """
        Get plugins by type.
        
        Args:
            plugin_type: Type of plugins to get ('connectors', 'processors', 'analyzers')
            
        Returns:
            Dictionary of plugin instances of the specified type
        """
        if plugin_type == "connectors":
            return {name: plugin for name, plugin in self.plugins.items() 
                   if isinstance(plugin, ConnectorPlugin)}
        elif plugin_type == "processors":
            return {name: plugin for name, plugin in self.plugins.items() 
                   if isinstance(plugin, ProcessorPlugin)}
        elif plugin_type == "analyzers":
            return {name: plugin for name, plugin in self.plugins.items() 
                   if isinstance(plugin, AnalyzerPlugin)}
        else:
            logger.warning(f"Unknown plugin type: {plugin_type}")
            return {}
    
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
                import importlib
                
                module_name = self.plugin_modules[plugin_name].__name__
                importlib.reload(self.plugin_modules[plugin_name])
                logger.info(f"Reloaded plugin module: {module_name}")
            except Exception as e:
                logger.error(f"Error reloading plugin module {plugin_name}: {e}")
                return False
        
        # Re-load plugin class
        plugin_class = self.load_plugin(plugin_name)
        if not plugin_class:
            logger.warning(f"Failed to load plugin class {plugin_name} for reload")
            return False
        
        # Initialize plugin
        return self.initialize_plugin(plugin_name, config)

# Global plugin manager instance
plugin_manager = PluginManager("core/plugins", "core/plugins/config.json")
