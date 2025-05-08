"""
Base plugin classes for Wiseflow plugin system.
This module defines the base classes for all plugin types in the system.
"""

import abc
import logging
import inspect
import hashlib
import importlib
import os
import sys
import json
import time
import threading
import traceback
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union, Set, Type, Callable, Tuple

from core.utils.error_handling import PluginError, handle_exceptions
from core.event_system import EventType, Event, subscribe, unsubscribe, publish_sync

logger = logging.getLogger(__name__)

class PluginState(Enum):
    """Plugin states for lifecycle management."""
    UNLOADED = auto()
    LOADED = auto()
    INITIALIZED = auto()
    ACTIVE = auto()
    DISABLED = auto()
    ERROR = auto()
    UNINSTALLED = auto()

class PluginSecurityLevel(Enum):
    """Security levels for plugins."""
    LOW = 0      # Minimal restrictions
    MEDIUM = 1   # Standard restrictions
    HIGH = 2     # Maximum restrictions

class PluginMetadata:
    """Metadata for plugins."""
    
    def __init__(
        self,
        name: str,
        version: str,
        description: str = "",
        author: str = "",
        website: str = "",
        license: str = "",
        min_system_version: str = "0.1.0",
        max_system_version: str = "",
        dependencies: Optional[Dict[str, str]] = None,
        security_level: PluginSecurityLevel = PluginSecurityLevel.MEDIUM
    ):
        """
        Initialize plugin metadata.
        
        Args:
            name: Plugin name
            version: Plugin version
            description: Plugin description
            author: Plugin author
            website: Plugin website
            license: Plugin license
            min_system_version: Minimum system version required
            max_system_version: Maximum system version supported
            dependencies: Dictionary of plugin dependencies (name -> version)
            security_level: Security level for the plugin
        """
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.website = website
        self.license = license
        self.min_system_version = min_system_version
        self.max_system_version = max_system_version
        self.dependencies = dependencies or {}
        self.security_level = security_level
        self.load_time = None
        self.init_time = None
        self.file_hash = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "website": self.website,
            "license": self.license,
            "min_system_version": self.min_system_version,
            "max_system_version": self.max_system_version,
            "dependencies": self.dependencies,
            "security_level": self.security_level.name,
            "load_time": self.load_time,
            "init_time": self.init_time,
            "file_hash": self.file_hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginMetadata':
        """Create metadata from dictionary."""
        security_level = PluginSecurityLevel[data.get("security_level", "MEDIUM")]
        
        metadata = cls(
            name=data.get("name", ""),
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            website=data.get("website", ""),
            license=data.get("license", ""),
            min_system_version=data.get("min_system_version", "0.1.0"),
            max_system_version=data.get("max_system_version", ""),
            dependencies=data.get("dependencies", {}),
            security_level=security_level
        )
        
        metadata.load_time = data.get("load_time")
        metadata.init_time = data.get("init_time")
        metadata.file_hash = data.get("file_hash")
        
        return metadata

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
        self.state = PluginState.UNLOADED
        self.error = None
        self.metadata = PluginMetadata(
            name=self.name,
            version=self.version,
            description=self.description
        )
        self._event_handlers = {}
        self._resources = {}
        self._lock = threading.RLock()
    
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
        try:
            # Shutdown plugin with isolation
            from core.plugins.isolation import isolation_manager
            
            @isolation_manager.isolate(self.name)
            def _shutdown_plugin(plugin):
                return plugin.shutdown()
            
            if _shutdown_plugin(self):
                # Release resources
                from core.plugins.resources import resource_manager
                resource_manager.release_resources(self.name)
                
                # Trigger lifecycle event
                from core.plugins.lifecycle import lifecycle_manager
                lifecycle_manager.on_plugin_shutdown(self)
                
                # Remove plugin
                del self.plugins[self.name]
                
                logger.info(f"Shutdown plugin: {self.name}")
                return True
            else:
                logger.warning(f"Failed to shutdown plugin: {self.name}")
                return False
        except Exception as e:
            logger.error(f"Error shutting down plugin {self.name}: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            
            # Trigger lifecycle error event
            from core.plugins.lifecycle import lifecycle_manager
            lifecycle_manager.on_plugin_error(self, e)
            
            return False
    
    def validate_config(self) -> bool:
        """Validate the plugin configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        return True
    
    def enable(self) -> None:
        """Enable the plugin."""
        with self._lock:
            self.is_enabled = True
            if self.initialized and self.state != PluginState.ERROR:
                self.state = PluginState.ACTIVE
    
    def disable(self) -> None:
        """Disable the plugin."""
        with self._lock:
            self.is_enabled = False
            if self.state != PluginState.ERROR:
                self.state = PluginState.DISABLED
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the plugin.
        
        Returns:
            Dictionary with plugin status information
        """
        with self._lock:
            return {
                "name": self.name,
                "description": self.description,
                "version": self.version,
                "is_enabled": self.is_enabled,
                "initialized": self.initialized,
                "state": self.state.name,
                "error": self.error,
                "metadata": self.metadata.to_dict() if hasattr(self, "metadata") else None,
                "resources": self._get_resource_usage()
            }
    
    def _subscribe_to_event(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Event type to subscribe to
            handler: Event handler function
        """
        with self._lock:
            if event_type not in self._event_handlers:
                self._event_handlers[event_type] = []
            
            # Store the handler
            self._event_handlers[event_type].append(handler)
            
            # Subscribe to the event
            subscribe(event_type, handler, source=self.name)
    
    def _unsubscribe_from_event(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Event type to unsubscribe from
            handler: Event handler function
        """
        with self._lock:
            if event_type in self._event_handlers and handler in self._event_handlers[event_type]:
                # Remove the handler
                self._event_handlers[event_type].remove(handler)
                
                # Unsubscribe from the event
                unsubscribe(event_type, handler)
    
    def _unsubscribe_from_all_events(self) -> None:
        """Unsubscribe from all events."""
        from core.event_system import unsubscribe_by_source
        unsubscribe_by_source(self.name)
        self._event_handlers = {}
    
    def _register_resource(self, resource_type: str, resource: Any) -> None:
        """
        Register a resource used by the plugin.
        
        Args:
            resource_type: Type of resource
            resource: Resource object
        """
        with self._lock:
            if resource_type not in self._resources:
                self._resources[resource_type] = []
            
            self._resources[resource_type].append(resource)
    
    def _release_resources(self) -> None:
        """Release all resources used by the plugin."""
        with self._lock:
            for resource_type, resources in self._resources.items():
                for resource in resources:
                    try:
                        # Try to close or release the resource
                        if hasattr(resource, "close"):
                            resource.close()
                        elif hasattr(resource, "release"):
                            resource.release()
                        elif hasattr(resource, "shutdown"):
                            resource.shutdown()
                    except Exception as e:
                        logger.warning(f"Error releasing resource {resource_type} in plugin {self.name}: {e}")
            
            # Clear resources
            self._resources = {}
    
    def _get_resource_usage(self) -> Dict[str, Any]:
        """
        Get resource usage information.
        
        Returns:
            Dictionary with resource usage information
        """
        with self._lock:
            usage = {}
            
            for resource_type, resources in self._resources.items():
                usage[resource_type] = len(resources)
            
            return usage
    
    def __str__(self) -> str:
        """String representation of the plugin."""
        return f"{self.name} v{self.version} ({self.state.name})"

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
    
    def initialize(self) -> bool:
        """Initialize the connector plugin.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Validate configuration
            if not self.validate_config():
                logger.warning(f"Invalid configuration for connector plugin {self.name}")
                self.error = "Invalid configuration"
                self.state = PluginState.ERROR
                return False
            
            # Update state
            self.initialized = True
            self.state = PluginState.INITIALIZED
            
            # Subscribe to relevant events
            self._subscribe_to_event(EventType.SYSTEM_SHUTDOWN, self._handle_system_shutdown)
            
            # Set state to active if enabled
            if self.is_enabled:
                self.state = PluginState.ACTIVE
            
            return True
        except Exception as e:
            logger.error(f"Error initializing connector plugin {self.name}: {e}")
            self.error = str(e)
            self.state = PluginState.ERROR
            return False
    
    def _handle_system_shutdown(self, event: Event) -> None:
        """Handle system shutdown event."""
        try:
            # Disconnect from data source
            if self.state == PluginState.ACTIVE:
                self.disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting connector plugin {self.name} during shutdown: {e}")


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
    
    def initialize(self) -> bool:
        """Initialize the processor plugin.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Validate configuration
            if not self.validate_config():
                logger.warning(f"Invalid configuration for processor plugin {self.name}")
                self.error = "Invalid configuration"
                self.state = PluginState.ERROR
                return False
            
            # Update state
            self.initialized = True
            self.state = PluginState.INITIALIZED
            
            # Subscribe to relevant events
            self._subscribe_to_event(EventType.SYSTEM_SHUTDOWN, self._handle_system_shutdown)
            
            # Set state to active if enabled
            if self.is_enabled:
                self.state = PluginState.ACTIVE
            
            return True
        except Exception as e:
            logger.error(f"Error initializing processor plugin {self.name}: {e}")
            self.error = str(e)
            self.state = PluginState.ERROR
            return False
    
    def _handle_system_shutdown(self, event: Event) -> None:
        """Handle system shutdown event."""
        try:
            # Clean up resources
            self._release_resources()
        except Exception as e:
            logger.warning(f"Error cleaning up processor plugin {self.name} during shutdown: {e}")


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
    
    def initialize(self) -> bool:
        """Initialize the analyzer plugin.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Validate configuration
            if not self.validate_config():
                logger.warning(f"Invalid configuration for analyzer plugin {self.name}")
                self.error = "Invalid configuration"
                self.state = PluginState.ERROR
                return False
            
            # Update state
            self.initialized = True
            self.state = PluginState.INITIALIZED
            
            # Subscribe to relevant events
            self._subscribe_to_event(EventType.SYSTEM_SHUTDOWN, self._handle_system_shutdown)
            
            # Set state to active if enabled
            if self.is_enabled:
                self.state = PluginState.ACTIVE
            
            return True
        except Exception as e:
            logger.error(f"Error initializing analyzer plugin {self.name}: {e}")
            self.error = str(e)
            self.state = PluginState.ERROR
            return False
    
    def _handle_system_shutdown(self, event: Event) -> None:
        """Handle system shutdown event."""
        try:
            # Clean up resources
            self._release_resources()
        except Exception as e:
            logger.warning(f"Error cleaning up analyzer plugin {self.name} during shutdown: {e}")


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
        
        # Plugin security settings
        self.security_enabled = True
        self.allowed_modules = set([
            "os", "sys", "time", "datetime", "json", "logging", 
            "math", "random", "re", "collections", "itertools",
            "functools", "typing", "enum", "abc", "copy", "uuid"
        ])
        self.restricted_modules = set([
            "subprocess", "socket", "shutil", "pickle", "marshal",
            "multiprocessing", "ctypes", "importlib"
        ])
        
        # Plugin version compatibility
        self.system_version = "4.0.0"  # Should be obtained from system config
        
        # Thread lock for thread safety
        self._lock = threading.RLock()
        
        logger.info(f"Plugin manager initialized with plugins directory: {plugins_dir}")
    
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
        with self._lock:
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
        with self._lock:
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
        with self._lock:
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
        
        with self._lock:
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
    
    def _calculate_file_hash(self, module_path: str) -> Optional[str]:
        """
        Calculate a hash of the plugin file for security verification.
        
        Args:
            module_path: Path to the module file
            
        Returns:
            Hash string or None if file not found
        """
        try:
            import hashlib
            
            if not os.path.exists(module_path):
                return None
            
            with open(module_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            return file_hash
        except Exception as e:
            logger.warning(f"Error calculating file hash for {module_path}: {e}")
            return None
    
    def _check_plugin_security(self, module: Any) -> Tuple[bool, str]:
        """
        Check plugin security.
        
        Args:
            module: Plugin module
            
        Returns:
            Tuple of (is_secure, reason)
        """
        if not self.security_enabled:
            return True, ""
        
        try:
            # Check imported modules
            for name, obj in inspect.getmembers(module):
                if inspect.ismodule(obj):
                    module_name = obj.__name__.split('.')[0]
                    if module_name in self.restricted_modules:
                        return False, f"Plugin imports restricted module: {module_name}"
            
            # Check for potentially dangerous attributes
            for name, obj in inspect.getmembers(module):
                if name.startswith('__') and name.endswith('__') and name not in ['__name__', '__doc__', '__file__']:
                    if callable(obj):
                        return False, f"Plugin contains potentially dangerous dunder method: {name}"
            
            return True, ""
        except Exception as e:
            logger.warning(f"Error checking plugin security: {e}")
            return False, f"Security check error: {str(e)}"
    
    def _check_version_compatibility(self, metadata: PluginMetadata) -> Tuple[bool, str]:
        """
        Check if plugin version is compatible with system version.
        
        Args:
            metadata: Plugin metadata
            
        Returns:
            Tuple of (is_compatible, reason)
        """
        from packaging import version
        
        try:
            # Check minimum system version
            if metadata.min_system_version:
                if version.parse(self.system_version) < version.parse(metadata.min_system_version):
                    return False, f"Plugin requires system version {metadata.min_system_version} or higher"
            
            # Check maximum system version
            if metadata.max_system_version:
                if version.parse(self.system_version) > version.parse(metadata.max_system_version):
                    return False, f"Plugin requires system version {metadata.max_system_version} or lower"
            
            return True, ""
        except Exception as e:
            logger.warning(f"Error checking version compatibility: {e}")
            return True, ""  # Default to compatible if check fails
    
    @handle_exceptions(
        error_types=[Exception],
        default_message="Failed to load plugin",
        log_error=True
    )
    def load_plugin(self, plugin_name: str) -> Optional[Type[BasePlugin]]:
        """
        Load a plugin by name.
        
        Args:
            plugin_name: Name of the plugin to load
            
        Returns:
            Plugin class or None if not found
        """
        with self._lock:
            try:
                import importlib
                import inspect
                import sys
                
                # Import the plugin module
                module = importlib.import_module(plugin_name)
                self.plugin_modules[plugin_name] = module
                
                # Calculate file hash for security
                module_path = getattr(module, '__file__', None)
                file_hash = self._calculate_file_hash(module_path) if module_path else None
                
                # Check plugin security
                is_secure, security_reason = self._check_plugin_security(module)
                if not is_secure:
                    logger.warning(f"Plugin {plugin_name} failed security check: {security_reason}")
                    return None
                
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
                        
                        # Create metadata if not present
                        if not hasattr(plugin_class, "metadata") or plugin_class.metadata is None:
                            plugin_class.metadata = PluginMetadata(
                                name=plugin_class.name,
                                version=getattr(plugin_class, "version", "0.1.0"),
                                description=getattr(plugin_class, "description", "")
                            )
                        
                        # Update metadata
                        plugin_class.metadata.load_time = time.time()
                        plugin_class.metadata.file_hash = file_hash
                        
                        # Check version compatibility
                        is_compatible, compat_reason = self._check_version_compatibility(plugin_class.metadata)
                        if not is_compatible:
                            logger.warning(f"Plugin {plugin_name} is not compatible: {compat_reason}")
                            return None
                        
                        # Validate plugin class
                        from core.plugins.validation import validation_manager
                        is_valid, validation_errors = validation_manager.validate_plugin_class(plugin_class)
                        if not is_valid:
                            logger.warning(f"Plugin {plugin_name} failed validation: {', '.join(validation_errors)}")
                            return None
                        
                        # Register the plugin class
                        self.plugin_classes[plugin_name] = plugin_class
                        
                        # Register by type
                        if issubclass(plugin_class, ConnectorPlugin):
                            self.register_connector(plugin_name, plugin_class)
                        elif issubclass(plugin_class, ProcessorPlugin):
                            self.register_processor(plugin_name, plugin_class)
                        elif issubclass(plugin_class, AnalyzerPlugin):
                            self.register_analyzer(plugin_name, plugin_class)
                        
                        # Trigger lifecycle event
                        from core.plugins.lifecycle import lifecycle_manager
                        lifecycle_manager.on_plugin_load(plugin_class)
                        
                        logger.info(f"Loaded plugin class: {plugin_name} from {plugin_name}")
                        return plugin_class
                
                logger.warning(f"No plugin class found in {plugin_name}")
                return None
            except Exception as e:
                logger.error(f"Error loading plugin {plugin_name}: {e}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
                return None
    
    def load_all_plugins(self) -> Dict[str, Type[BasePlugin]]:
        """
        Load all available plugins.
        
        Returns:
            Dictionary of plugin classes
        """
        with self._lock:
            plugin_names = self.discover_plugins()
            
            for plugin_name in plugin_names:
                self.load_plugin(plugin_name)
            
            logger.info(f"Loaded {len(self.plugin_classes)} plugin classes")
            return self.plugin_classes
    
    @handle_exceptions(
        error_types=[Exception],
        default_message="Failed to initialize plugin",
        log_error=True
    )
    def initialize_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialize a plugin.
        
        Args:
            plugin_name: Name of the plugin to initialize
            config: Optional configuration for the plugin
            
        Returns:
            True if initialization was successful, False otherwise
        """
        with self._lock:
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
                
                # Update plugin state
                plugin.state = PluginState.LOADED
                
                # Initialize plugin with isolation
                from core.plugins.isolation import isolation_manager
                
                @isolation_manager.isolate(plugin_name)
                def _initialize_plugin(plugin):
                    return plugin.initialize()
                
                if _initialize_plugin(plugin):
                    plugin.initialized = True
                    plugin.state = PluginState.INITIALIZED
                    
                    # Update metadata
                    if hasattr(plugin, "metadata"):
                        plugin.metadata.init_time = time.time()
                    
                    # Store plugin instance
                    self.plugins[plugin_name] = plugin
                    
                    # Set to active if enabled
                    if plugin.is_enabled:
                        plugin.state = PluginState.ACTIVE
                    
                    # Trigger lifecycle event
                    from core.plugins.lifecycle import lifecycle_manager
                    lifecycle_manager.on_plugin_initialize(plugin)
                    
                    logger.info(f"Initialized plugin: {plugin_name}")
                    return True
                else:
                    logger.warning(f"Failed to initialize plugin: {plugin_name}")
                    return False
            except Exception as e:
                logger.error(f"Error initializing plugin {plugin_name}: {e}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
                
                # Trigger lifecycle error event
                from core.plugins.lifecycle import lifecycle_manager
                dummy_plugin = type('DummyPlugin', (), {
                    'name': plugin_name,
                    'version': getattr(plugin_class, 'version', '0.1.0'),
                    'description': getattr(plugin_class, 'description', ''),
                    'state': PluginState.ERROR,
                    'error': str(e)
                })
                lifecycle_manager.on_plugin_error(dummy_plugin, e)
                
                return False
    
    def initialize_all_plugins(self, configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, bool]:
        """
        Initialize all loaded plugins.
        
        Args:
            configs: Optional dictionary of plugin configurations
            
        Returns:
            Dictionary mapping plugin names to initialization success status
        """
        with self._lock:
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
        with self._lock:
            return self.plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, BasePlugin]:
        """
        Get all initialized plugins.
        
        Returns:
            Dictionary of plugin instances
        """
        with self._lock:
            return self.plugins.copy()
    
    def get_plugins_by_type(self, plugin_type: str) -> Dict[str, BasePlugin]:
        """
        Get plugins by type.
        
        Args:
            plugin_type: Type of plugins to get ('connectors', 'processors', 'analyzers')
            
        Returns:
            Dictionary of plugin instances of the specified type
        """
        with self._lock:
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
    
    def get_plugins_by_base(self, base_class: Type) -> Dict[str, BasePlugin]:
        """
        Get plugins by base class.
        
        Args:
            base_class: Base class of plugins to get
            
        Returns:
            Dictionary of plugin instances of the specified base class
        """
        with self._lock:
            return {name: plugin for name, plugin in self.plugins.items() 
                   if isinstance(plugin, base_class)}
    
    @handle_exceptions(
        error_types=[Exception],
        default_message="Failed to shutdown plugin",
        log_error=True
    )
    def shutdown_plugin(self, plugin_name: str) -> bool:
        """
        Shutdown a plugin.
        
        Args:
            plugin_name: Name of the plugin to shutdown
            
        Returns:
            True if shutdown was successful, False otherwise
        """
        with self._lock:
            plugin = self.plugins.get(plugin_name)
            if not plugin:
                logger.warning(f"Plugin {plugin_name} not found")
                return False
            
            try:
                # Shutdown plugin with isolation
                from core.plugins.isolation import isolation_manager
                
                @isolation_manager.isolate(plugin_name)
                def _shutdown_plugin(plugin):
                    return plugin.shutdown()
                
                if _shutdown_plugin(plugin):
                    # Release resources
                    from core.plugins.resources import resource_manager
                    resource_manager.release_resources(plugin_name)
                    
                    # Trigger lifecycle event
                    from core.plugins.lifecycle import lifecycle_manager
                    lifecycle_manager.on_plugin_shutdown(plugin)
                    
                    # Remove plugin
                    del self.plugins[plugin_name]
                    
                    logger.info(f"Shutdown plugin: {plugin_name}")
                    return True
                else:
                    logger.warning(f"Failed to shutdown plugin: {plugin_name}")
                    return False
            except Exception as e:
                logger.error(f"Error shutting down plugin {plugin_name}: {e}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
                
                # Trigger lifecycle error event
                from core.plugins.lifecycle import lifecycle_manager
                lifecycle_manager.on_plugin_error(plugin, e)
                
                return False
    
    def shutdown_all_plugins(self) -> Dict[str, bool]:
        """
        Shutdown all initialized plugins.
        
        Returns:
            Dictionary mapping plugin names to shutdown success status
        """
        with self._lock:
            results = {}
            
            for plugin_name in list(self.plugins.keys()):
                results[plugin_name] = self.shutdown_plugin(plugin_name)
            
            return results
    
    @handle_exceptions(
        error_types=[Exception],
        default_message="Failed to reload plugin",
        log_error=True
    )
    def reload_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Reload a plugin.
        
        Args:
            plugin_name: Name of the plugin to reload
            config: Optional configuration for the plugin
            
        Returns:
            True if reload was successful, False otherwise
        """
        with self._lock:
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
                    logger.debug(f"Traceback: {traceback.format_exc()}")
                    return False
            
            # Re-load plugin class
            plugin_class = self.load_plugin(plugin_name)
            if not plugin_class:
                logger.warning(f"Failed to load plugin class {plugin_name} for reload")
                return False
            
            # Initialize plugin
            return self.initialize_plugin(plugin_name, config)
    
    def get_plugin_status(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Dictionary with plugin status or None if plugin not found
        """
        with self._lock:
            plugin = self.plugins.get(plugin_name)
            if not plugin:
                return None
            
            return plugin.get_status()
    
    def get_all_plugin_statuses(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the status of all plugins.
        
        Returns:
            Dictionary mapping plugin names to status dictionaries
        """
        with self._lock:
            return {name: plugin.get_status() for name, plugin in self.plugins.items()}
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """
        Enable a plugin.
        
        Args:
            plugin_name: Name of the plugin to enable
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            plugin = self.plugins.get(plugin_name)
            if not plugin:
                logger.warning(f"Plugin {plugin_name} not found")
                return False
            
            # Enable the plugin
            plugin.enable()
            
            # Trigger lifecycle event if state changed to ACTIVE
            if plugin.state == PluginState.ACTIVE:
                from core.plugins.lifecycle import lifecycle_manager
                lifecycle_manager.on_plugin_activate(plugin)
            
            logger.info(f"Enabled plugin: {plugin_name}")
            return True
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """
        Disable a plugin.
        
        Args:
            plugin_name: Name of the plugin to disable
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            plugin = self.plugins.get(plugin_name)
            if not plugin:
                logger.warning(f"Plugin {plugin_name} not found")
                return False
            
            # Disable the plugin
            plugin.disable()
            
            # Trigger lifecycle event if state changed to DISABLED
            if plugin.state == PluginState.DISABLED:
                from core.plugins.lifecycle import lifecycle_manager
                lifecycle_manager.on_plugin_deactivate(plugin)
            
            logger.info(f"Disabled plugin: {plugin_name}")
            return True
    
    def set_security_enabled(self, enabled: bool) -> None:
        """
        Enable or disable plugin security checks.
        
        Args:
            enabled: Whether security checks should be enabled
        """
        with self._lock:
            self.security_enabled = enabled
            logger.info(f"Plugin security checks {'enabled' if enabled else 'disabled'}")
    
    def add_allowed_module(self, module_name: str) -> None:
        """
        Add a module to the allowed modules list.
        
        Args:
            module_name: Name of the module to allow
        """
        with self._lock:
            self.allowed_modules.add(module_name)
            if module_name in self.restricted_modules:
                self.restricted_modules.remove(module_name)
    
    def add_restricted_module(self, module_name: str) -> None:
        """
        Add a module to the restricted modules list.
        
        Args:
            module_name: Name of the module to restrict
        """
        with self._lock:
            self.restricted_modules.add(module_name)
            if module_name in self.allowed_modules:
                self.allowed_modules.remove(module_name)
    
    def set_system_version(self, version: str) -> None:
        """
        Set the system version for plugin compatibility checks.
        
        Args:
            version: System version string
        """
        with self._lock:
            self.system_version = version
            logger.info(f"System version set to {version} for plugin compatibility checks")

# Global plugin manager instance
plugin_manager = PluginManager("core/plugins", "core/plugins/config.json")
