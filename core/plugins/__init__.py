"""
Plugin system for WiseFlow.

This module provides a plugin system for extending WiseFlow functionality.
"""

import logging
import traceback
from typing import Dict, Any, Optional, List, Type, Union

# Import the base plugin classes and plugin manager
from core.plugins.base import (
    BasePlugin,
    ConnectorPlugin,
    ProcessorPlugin,
    AnalyzerPlugin,
    PluginManager,
    PluginState,
    PluginSecurityLevel,
    PluginMetadata
)

# Import the plugin loader functions
from core.plugins.loader import (
    get_plugin_manager,
    load_all_plugins,
    initialize_all_plugins,
    get_plugin,
    get_processor,
    get_analyzer,
    get_connector,
    get_all_processors,
    get_all_analyzers,
    get_all_connectors,
    reload_plugin,
    save_plugin_configs
)

# Import plugin security manager
from core.plugins.security import security_manager

# Import plugin compatibility manager
from core.plugins.compatibility import compatibility_manager

# Import plugin lifecycle manager
from core.plugins.lifecycle import (
    lifecycle_manager,
    LifecycleEvent
)

# Import plugin resource manager
from core.plugins.resources import (
    resource_manager,
    ResourceLimit,
    ResourceUsage
)

# Import plugin isolation manager
from core.plugins.isolation import isolation_manager

# Import plugin validation manager
from core.plugins.validation import validation_manager

logger = logging.getLogger(__name__)

# Get the global plugin manager instance
plugin_manager = get_plugin_manager()

# Export the plugin classes and functions
__all__ = [
    # Base classes
    'BasePlugin',
    'ConnectorPlugin',
    'ProcessorPlugin',
    'AnalyzerPlugin',
    'PluginManager',
    'PluginState',
    'PluginSecurityLevel',
    'PluginMetadata',
    
    # Plugin manager
    'plugin_manager',
    'get_plugin_manager',
    
    # Loader functions
    'load_all_plugins',
    'initialize_all_plugins',
    'get_plugin',
    'get_processor',
    'get_analyzer',
    'get_connector',
    'get_all_processors',
    'get_all_analyzers',
    'get_all_connectors',
    'reload_plugin',
    'save_plugin_configs',
    
    # Security
    'security_manager',
    
    # Compatibility
    'compatibility_manager',
    
    # Lifecycle
    'lifecycle_manager',
    'LifecycleEvent',
    
    # Resources
    'resource_manager',
    'ResourceLimit',
    'ResourceUsage',
    
    # Isolation
    'isolation_manager',
    
    # Validation
    'validation_manager',
    
    # Convenience functions
    'initialize_plugin_system'
]

def initialize_plugin_system() -> Dict[str, bool]:
    """
    Initialize the plugin system.
    
    This function loads and initializes all available plugins.
    
    Returns:
        Dictionary mapping plugin names to initialization success status
    """
    try:
        # Configure security manager
        security_manager.set_security_enabled(True)
        
        # Configure compatibility manager
        compatibility_manager.set_system_version("4.0.0")
        
        # Start resource monitoring
        resource_manager.start_monitoring()
        
        # Configure isolation manager
        isolation_manager.set_isolation_enabled(True)
        isolation_manager.set_timeout_enabled(True)
        
        # Configure validation manager
        validation_manager.set_validation_enabled(True)
        
        # Load all plugins
        logger.info("Loading all plugins...")
        plugin_classes = load_all_plugins()
        logger.info(f"Loaded {len(plugin_classes)} plugin classes")
        
        # Initialize all plugins
        logger.info("Initializing all plugins...")
        init_results = initialize_all_plugins()
        
        # Log initialization results
        success_count = sum(1 for success in init_results.values() if success)
        logger.info(f"Successfully initialized {success_count} of {len(init_results)} plugins")
        
        # Log failed initializations
        for plugin_name, success in init_results.items():
            if not success:
                plugin = get_plugin(plugin_name)
                error_msg = plugin.error if plugin and hasattr(plugin, 'error') else "Unknown error"
                logger.error(f"Failed to initialize plugin {plugin_name}: {error_msg}")
        
        return init_results
    except Exception as e:
        logger.error(f"Error initializing plugin system: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return {}
