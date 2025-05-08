"""
Plugin system initialization for Wiseflow.

This module provides functions to initialize the plugin system.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List

from core.plugins import initialize_plugin_system, get_plugin_manager
from core.plugins.base import BasePlugin

logger = logging.getLogger(__name__)

def initialize_plugins() -> Dict[str, bool]:
    """
    Initialize the plugin system.
    
    This function initializes the plugin system and all available plugins.
    
    Returns:
        Dictionary mapping plugin names to initialization success status
    """
    logger.info("Initializing plugin system...")
    
    # Initialize the plugin system
    results = initialize_plugin_system()
    
    # Log results
    success_count = sum(1 for success in results.values() if success)
    logger.info(f"Initialized {success_count} out of {len(results)} plugins")
    
    # Log failed plugins
    failed_plugins = [name for name, success in results.items() if not success]
    if failed_plugins:
        logger.warning(f"Failed to initialize plugins: {', '.join(failed_plugins)}")
    
    return results

async def initialize_plugins_async() -> Dict[str, bool]:
    """
    Initialize the plugin system asynchronously.
    
    This function initializes the plugin system and all available plugins asynchronously.
    
    Returns:
        Dictionary mapping plugin names to initialization success status
    """
    logger.info("Initializing plugin system asynchronously...")
    
    # Run initialization in a separate thread to avoid blocking
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, initialize_plugins)
    
    return results

def get_initialized_plugins() -> Dict[str, BasePlugin]:
    """
    Get all initialized plugins.
    
    Returns:
        Dictionary of initialized plugin instances
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Get all initialized plugins
    return manager.get_all_plugins()

def get_plugin_by_name(name: str) -> Optional[BasePlugin]:
    """
    Get a plugin by name.
    
    Args:
        name: Name of the plugin
        
    Returns:
        Plugin instance if found and initialized, None otherwise
    """
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Get the plugin
    return manager.get_plugin(name)

def shutdown_plugins() -> Dict[str, bool]:
    """
    Shutdown all initialized plugins.
    
    Returns:
        Dictionary mapping plugin names to shutdown success status
    """
    logger.info("Shutting down plugins...")
    
    # Get the plugin manager
    manager = get_plugin_manager()
    
    # Shutdown all plugins
    results = manager.shutdown_all_plugins()
    
    # Log results
    success_count = sum(1 for success in results.values() if success)
    logger.info(f"Shut down {success_count} out of {len(results)} plugins")
    
    return results

async def shutdown_plugins_async() -> Dict[str, bool]:
    """
    Shutdown all initialized plugins asynchronously.
    
    Returns:
        Dictionary mapping plugin names to shutdown success status
    """
    logger.info("Shutting down plugins asynchronously...")
    
    # Run shutdown in a separate thread to avoid blocking
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, shutdown_plugins)
    
    return results

