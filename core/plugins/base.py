"""
Base plugin classes for Wiseflow plugin system.
This module defines the base classes for all plugin types in the system.
"""

import abc
import inspect
import logging
import weakref
from typing import Any, Dict, List, Optional, Union, Set, Type, Callable

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

class BasePlugin(abc.ABC):
    """Base class for all plugins in the system."""
    
    name: str = "base_plugin"
    description: str = "Base plugin class"
    version: str = "0.1.0"
    required_methods: List[str] = ["initialize"]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the plugin with optional configuration.
        
        Args:
            config: Optional configuration dictionary for the plugin
        """
        self.config = config or {}
        self.name = self.__class__.__name__ if not hasattr(self, 'name') or not self.name else self.name
        self.initialized = False
        self.is_enabled = True
        self._resources = {}  # Track resources used by the plugin
        self._resource_refs = weakref.WeakValueDictionary()  # Weak references to shared resources
    
    @abc.abstractmethod
    def initialize(self) -> bool:
        """Initialize the plugin with its configuration.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        
        Raises:
            PluginInitializationError: If initialization fails
        """
        pass
    
    def shutdown(self) -> bool:
        """Shutdown the plugin and release resources.
        
        Returns:
            bool: True if shutdown was successful, False otherwise
        """
        # Release all resources
        self._release_all_resources()
        
        self.initialized = False
        return True
    
    def validate_config(self) -> bool:
        """Validate the plugin configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        
        Raises:
            PluginValidationError: If validation fails
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
            "initialized": self.initialized,
            "resource_count": len(self._resources)
        }
    
    def _register_resource(self, resource_name: str, resource: Any, shared: bool = False) -> None:
        """Register a resource used by the plugin.
        
        Args:
            resource_name: Name of the resource
            resource: The resource object
            shared: Whether the resource is shared with other plugins
        """
        self._resources[resource_name] = resource
        
        if shared:
            self._resource_refs[resource_name] = resource
            logger.debug(f"Registered shared resource '{resource_name}' for plugin '{self.name}'")
        else:
            logger.debug(f"Registered resource '{resource_name}' for plugin '{self.name}'")
    
    def _release_resource(self, resource_name: str) -> bool:
        """Release a resource used by the plugin.
        
        Args:
            resource_name: Name of the resource to release
            
        Returns:
            bool: True if resource was released, False otherwise
        """
        if resource_name not in self._resources:
            logger.warning(f"Resource '{resource_name}' not found for plugin '{self.name}'")
            return False
        
        resource = self._resources.pop(resource_name)
        
        # If resource has a close or cleanup method, call it
        if hasattr(resource, 'close') and callable(getattr(resource, 'close')):
            try:
                resource.close()
            except Exception as e:
                logger.error(f"Error closing resource '{resource_name}' for plugin '{self.name}': {e}")
                return False
        elif hasattr(resource, 'cleanup') and callable(getattr(resource, 'cleanup')):
            try:
                resource.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up resource '{resource_name}' for plugin '{self.name}': {e}")
                return False
        
        logger.debug(f"Released resource '{resource_name}' for plugin '{self.name}'")
        return True
    
    def _release_all_resources(self) -> bool:
        """Release all resources used by the plugin.
        
        Returns:
            bool: True if all resources were released, False otherwise
        """
        success = True
        
        # Make a copy of the keys since we'll be modifying the dictionary
        resource_names = list(self._resources.keys())
        
        for resource_name in resource_names:
            if not self._release_resource(resource_name):
                success = False
        
        return success
    
    @classmethod
    def validate_implementation(cls) -> bool:
        """Validate that the plugin implementation meets the requirements.
        
        Returns:
            bool: True if implementation is valid, False otherwise
        
        Raises:
            PluginInterfaceError: If implementation is invalid
        """
        missing_methods = []
        
        for method_name in cls.required_methods:
            if not hasattr(cls, method_name) or not callable(getattr(cls, method_name)):
                missing_methods.append(method_name)
        
        if missing_methods:
            raise PluginInterfaceError(cls.__name__, missing_methods)
        
        return True


class ConnectorPlugin(BasePlugin):
    """Base class for data source connector plugins."""
    
    required_methods = ["initialize", "connect", "fetch_data", "disconnect"]
    
    @abc.abstractmethod
    def connect(self) -> bool:
        """Connect to the data source.
        
        Returns:
            bool: True if connection was successful, False otherwise
        
        Raises:
            PluginError: If connection fails
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
        
        Raises:
            PluginError: If data fetching fails
        """
        pass
    
    @abc.abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from the data source.
        
        Returns:
            bool: True if disconnection was successful, False otherwise
        
        Raises:
            PluginError: If disconnection fails
        """
        pass


class ProcessorPlugin(BasePlugin):
    """Base class for data processor plugins."""
    
    required_methods = ["initialize", "process"]
    
    @abc.abstractmethod
    def process(self, data: Any, **kwargs) -> Any:
        """Process the input data.
        
        Args:
            data: Input data to process
            **kwargs: Additional parameters for processing
            
        Returns:
            Any: Processed data
        
        Raises:
            PluginError: If processing fails
        """
        pass


class AnalyzerPlugin(BasePlugin):
    """Base class for data analyzer plugins."""
    
    required_methods = ["initialize", "analyze"]
    
    @abc.abstractmethod
    def analyze(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Analyze the input data.
        
        Args:
            data: Input data to analyze
            **kwargs: Additional parameters for analysis
            
        Returns:
            Dict[str, Any]: Analysis results
        
        Raises:
            PluginError: If analysis fails
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
        
        # Plugin dependency tracking
        self.plugin_dependencies: Dict[str, List[str]] = {}
        self.plugin_dependents: Dict[str, List[str]] = {}
        
        # Resource tracking
        self.shared_resources: Dict[str, Any] = {}
        self.resource_reference_counts: Dict[str, int] = {}
        
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
            
        Raises:
            TypeError: If connector_class is not a subclass of ConnectorPlugin
            PluginInterfaceError: If connector implementation is invalid
        """
        if not issubclass(connector_class, ConnectorPlugin):
            raise TypeError(f"Connector {name} must be a subclass of ConnectorPlugin")
        
        # Validate the connector implementation
        try:
            connector_class.validate_implementation()
        except PluginInterfaceError as e:
            logger.error(f"Invalid connector implementation: {e}")
            raise
        
        self.connectors[name] = connector_class
        self.plugin_classes[name] = connector_class
        logger.debug(f"Registered connector plugin: {name}")
    
    def register_processor(self, name: str, processor_class: Type[ProcessorPlugin]) -> None:
        """Register a processor plugin.
        
        Args:
            name: Name of the processor
            processor_class: Class of the processor
            
        Raises:
            TypeError: If processor_class is not a subclass of ProcessorPlugin
            PluginInterfaceError: If processor implementation is invalid
        """
        if not issubclass(processor_class, ProcessorPlugin):
            raise TypeError(f"Processor {name} must be a subclass of ProcessorPlugin")
        
        # Validate the processor implementation
        try:
            processor_class.validate_implementation()
        except PluginInterfaceError as e:
            logger.error(f"Invalid processor implementation: {e}")
            raise
        
        self.processors[name] = processor_class
        self.plugin_classes[name] = processor_class
        logger.debug(f"Registered processor plugin: {name}")
    
    def register_analyzer(self, name: str, analyzer_class: Type[AnalyzerPlugin]) -> None:
        """Register an analyzer plugin.
        
        Args:
            name: Name of the analyzer
            analyzer_class: Class of the analyzer
            
        Raises:
            TypeError: If analyzer_class is not a subclass of AnalyzerPlugin
            PluginInterfaceError: If analyzer implementation is invalid
        """
        if not issubclass(analyzer_class, AnalyzerPlugin):
            raise TypeError(f"Analyzer {name} must be a subclass of AnalyzerPlugin")
        
        # Validate the analyzer implementation
        try:
            analyzer_class.validate_implementation()
        except PluginInterfaceError as e:
            logger.error(f"Invalid analyzer implementation: {e}")
            raise
        
        self.analyzers[name] = analyzer_class
        self.plugin_classes[name] = analyzer_class
        logger.debug(f"Registered analyzer plugin: {name}")
    
    def register_dependency(self, plugin_name: str, dependency_name: str) -> None:
        """Register a dependency between plugins.
        
        Args:
            plugin_name: Name of the plugin that depends on another
            dependency_name: Name of the plugin that is depended upon
        """
        if plugin_name not in self.plugin_dependencies:
            self.plugin_dependencies[plugin_name] = []
        
        if dependency_name not in self.plugin_dependencies[plugin_name]:
            self.plugin_dependencies[plugin_name].append(dependency_name)
        
        if dependency_name not in self.plugin_dependents:
            self.plugin_dependents[dependency_name] = []
        
        if plugin_name not in self.plugin_dependents[dependency_name]:
            self.plugin_dependents[dependency_name].append(plugin_name)
        
        logger.debug(f"Registered dependency: {plugin_name} depends on {dependency_name}")
    
    def register_shared_resource(self, resource_name: str, resource: Any) -> None:
        """Register a shared resource.
        
        Args:
            resource_name: Name of the resource
            resource: The resource object
        """
        self.shared_resources[resource_name] = resource
        self.resource_reference_counts[resource_name] = 0
        logger.debug(f"Registered shared resource: {resource_name}")
    
    def get_shared_resource(self, resource_name: str) -> Optional[Any]:
        """Get a shared resource.
        
        Args:
            resource_name: Name of the resource
            
        Returns:
            The resource object or None if not found
        """
        if resource_name in self.shared_resources:
            self.resource_reference_counts[resource_name] += 1
            return self.shared_resources[resource_name]
        
        return None
    
    def release_shared_resource(self, resource_name: str) -> bool:
        """Release a reference to a shared resource.
        
        Args:
            resource_name: Name of the resource
            
        Returns:
            True if resource was released, False otherwise
        """
        if resource_name not in self.shared_resources:
            logger.warning(f"Shared resource '{resource_name}' not found")
            return False
        
        if resource_name in self.resource_reference_counts:
            self.resource_reference_counts[resource_name] -= 1
            
            # If no more references, clean up the resource
            if self.resource_reference_counts[resource_name] <= 0:
                resource = self.shared_resources.pop(resource_name)
                del self.resource_reference_counts[resource_name]
                
                # If resource has a close or cleanup method, call it
                if hasattr(resource, 'close') and callable(getattr(resource, 'close')):
                    try:
                        resource.close()
                    except Exception as e:
                        logger.error(f"Error closing shared resource '{resource_name}': {e}")
                        return False
                elif hasattr(resource, 'cleanup') and callable(getattr(resource, 'cleanup')):
                    try:
                        resource.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up shared resource '{resource_name}': {e}")
                        return False
                
                logger.debug(f"Cleaned up shared resource: {resource_name}")
        
        return True
    
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
            
        Raises:
            PluginLoadError: If plugin loading fails
        """
        try:
            import importlib
            import inspect
            
            # Import the plugin module
            module = importlib.import_module(plugin_name)
            self.plugin_modules[plugin_name] = module
            
            # Find plugin classes in the module
            plugin_class = None
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
                    
                    # Validate the plugin implementation
                    try:
                        plugin_class.validate_implementation()
                    except PluginInterfaceError as e:
                        logger.error(f"Invalid plugin implementation: {e}")
                        continue
                    
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
            
            if not plugin_class:
                logger.warning(f"No plugin class found in {plugin_name}")
                return None
            
            return plugin_class
            
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}")
            raise PluginLoadError(plugin_name, cause=e)
    
    def load_all_plugins(self) -> Dict[str, Type[BasePlugin]]:
        """
        Load all available plugins.
        
        Returns:
            Dictionary of plugin classes
            
        Raises:
            PluginLoadError: If plugin loading fails
        """
        plugin_names = self.discover_plugins()
        load_errors = []
        
        for plugin_name in plugin_names:
            try:
                self.load_plugin(plugin_name)
            except PluginLoadError as e:
                load_errors.append(e)
                logger.error(f"Failed to load plugin {plugin_name}: {e}")
        
        if load_errors:
            logger.warning(f"Failed to load {len(load_errors)} plugins")
        
        logger.info(f"Loaded {len(self.plugin_classes)} plugin classes")
        return self.plugin_classes
    
    def resolve_dependencies(self, plugin_name: str) -> List[str]:
        """
        Resolve dependencies for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            List of plugin names that need to be initialized before this plugin
            
        Raises:
            PluginDependencyError: If dependencies cannot be resolved
        """
        if plugin_name not in self.plugin_dependencies:
            return []
        
        # Check for circular dependencies
        visited = set()
        path = []
        
        def check_circular(current, path):
            if current in visited:
                if current in path:
                    # Circular dependency detected
                    cycle_start = path.index(current)
                    cycle = path[cycle_start:] + [current]
                    raise PluginDependencyError(
                        plugin_name,
                        message=f"Circular dependency detected: {' -> '.join(cycle)}"
                    )
                return
            
            visited.add(current)
            path.append(current)
            
            if current in self.plugin_dependencies:
                for dep in self.plugin_dependencies[current]:
                    check_circular(dep, path.copy())
        
        # Check for circular dependencies
        check_circular(plugin_name, path)
        
        # Resolve dependencies in order
        resolved = []
        
        def resolve(current):
            if current in resolved:
                return
            
            if current in self.plugin_dependencies:
                for dep in self.plugin_dependencies[current]:
                    if dep not in self.plugin_classes:
                        raise PluginDependencyError(
                            current,
                            [dep],
                            f"Plugin {current} depends on {dep}, but {dep} is not loaded"
                        )
                    resolve(dep)
            
            resolved.append(current)
        
        resolve(plugin_name)
        
        # Remove the plugin itself from the list
        if plugin_name in resolved:
            resolved.remove(plugin_name)
        
        return resolved
    
    def initialize_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialize a plugin.
        
        Args:
            plugin_name: Name of the plugin to initialize
            config: Optional configuration for the plugin
            
        Returns:
            True if initialization was successful, False otherwise
            
        Raises:
            PluginInitializationError: If initialization fails
            PluginDependencyError: If dependencies cannot be resolved
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
            # Resolve dependencies
            dependencies = self.resolve_dependencies(plugin_name)
            
            # Initialize dependencies first
            for dependency in dependencies:
                if dependency not in self.plugins:
                    if not self.initialize_plugin(dependency):
                        raise PluginDependencyError(
                            plugin_name,
                            [dependency],
                            f"Failed to initialize dependency {dependency} for plugin {plugin_name}"
                        )
            
            # Get configuration
            if config is None:
                config = self.plugin_configs.get(plugin_name, {})
            
            # Create plugin instance
            plugin = plugin_class(config)
            
            # Validate configuration
            if not plugin.validate_config():
                raise PluginValidationError(plugin_name, "Plugin configuration validation failed")
            
            # Initialize plugin
            if not plugin.initialize():
                raise PluginInitializationError(plugin_name, "Plugin initialization failed")
            
            plugin.initialized = True
            self.plugins[plugin_name] = plugin
            logger.info(f"Initialized plugin: {plugin_name}")
            return True
            
        except (PluginInitializationError, PluginValidationError, PluginDependencyError) as e:
            logger.error(f"Error initializing plugin {plugin_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error initializing plugin {plugin_name}: {e}")
            raise PluginInitializationError(plugin_name, str(e))
    
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
        
        # Sort plugins by dependencies
        plugin_names = list(self.plugin_classes.keys())
        
        for plugin_name in plugin_names:
            try:
                config = configs.get(plugin_name, self.plugin_configs.get(plugin_name, {}))
                results[plugin_name] = self.initialize_plugin(plugin_name, config)
            except Exception as e:
                logger.error(f"Failed to initialize plugin {plugin_name}: {e}")
                results[plugin_name] = False
        
        success_count = sum(1 for success in results.values() if success)
        logger.info(f"Initialized {success_count} out of {len(results)} plugins")
        
        # Log failed plugins
        failed_plugins = [name for name, success in results.items() if not success]
        if failed_plugins:
            logger.warning(f"Failed to initialize plugins: {', '.join(failed_plugins)}")
        
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
        
        # Check if other plugins depend on this one
        if plugin_name in self.plugin_dependents:
            dependent_plugins = [dep for dep in self.plugin_dependents[plugin_name] if dep in self.plugins]
            if dependent_plugins:
                logger.warning(f"Cannot shutdown plugin {plugin_name} because it is depended upon by: {', '.join(dependent_plugins)}")
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
        
        # Shutdown plugins in reverse dependency order
        plugin_names = list(self.plugins.keys())
        
        # First, build a dependency graph
        dependency_graph = {}
        for name in plugin_names:
            dependency_graph[name] = []
            if name in self.plugin_dependents:
                for dep in self.plugin_dependents[name]:
                    if dep in plugin_names:
                        dependency_graph[name].append(dep)
        
        # Topological sort to get shutdown order
        shutdown_order = []
        visited = set()
        temp_visited = set()
        
        def visit(name):
            if name in visited:
                return
            if name in temp_visited:
                # Circular dependency, but we'll handle it
                return
            
            temp_visited.add(name)
            
            for dep in dependency_graph.get(name, []):
                visit(dep)
            
            temp_visited.remove(name)
            visited.add(name)
            shutdown_order.append(name)
        
        for name in plugin_names:
            if name not in visited:
                visit(name)
        
        # Shutdown plugins in order
        for plugin_name in shutdown_order:
            if plugin_name in self.plugins:
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
        try:
            plugin_class = self.load_plugin(plugin_name)
            if not plugin_class:
                logger.warning(f"Failed to load plugin class {plugin_name} for reload")
                return False
        except PluginLoadError as e:
            logger.error(f"Failed to load plugin {plugin_name} for reload: {e}")
            return False
        
        # Initialize plugin
        try:
            return self.initialize_plugin(plugin_name, config)
        except Exception as e:
            logger.error(f"Failed to initialize plugin {plugin_name} after reload: {e}")
            return False

# Global plugin manager instance
plugin_manager = PluginManager("core/plugins", "core/plugins/config.json")
