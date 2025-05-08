"""
Plugin lifecycle management module for Wiseflow.

This module provides utilities for managing plugin lifecycles.
"""

import logging
import time
from typing import Dict, Any, Optional, List, Type, Callable
from enum import Enum, auto

from core.plugins.base import PluginState, BasePlugin
from core.event_system import EventType, Event, publish_sync

logger = logging.getLogger(__name__)

class LifecycleEvent(Enum):
    """Lifecycle events for plugins."""
    LOAD = auto()
    INITIALIZE = auto()
    ACTIVATE = auto()
    DEACTIVATE = auto()
    SHUTDOWN = auto()
    ERROR = auto()

class PluginLifecycleManager:
    """
    Plugin lifecycle manager.
    
    This class provides functionality to manage plugin lifecycles.
    """
    
    def __init__(self):
        """Initialize the plugin lifecycle manager."""
        self.lifecycle_hooks: Dict[LifecycleEvent, List[Callable]] = {
            event: [] for event in LifecycleEvent
        }
    
    def register_hook(self, event: LifecycleEvent, hook: Callable) -> None:
        """
        Register a lifecycle hook.
        
        Args:
            event: Lifecycle event
            hook: Hook function to call
        """
        if event not in self.lifecycle_hooks:
            self.lifecycle_hooks[event] = []
        
        self.lifecycle_hooks[event].append(hook)
    
    def unregister_hook(self, event: LifecycleEvent, hook: Callable) -> None:
        """
        Unregister a lifecycle hook.
        
        Args:
            event: Lifecycle event
            hook: Hook function to remove
        """
        if event in self.lifecycle_hooks and hook in self.lifecycle_hooks[event]:
            self.lifecycle_hooks[event].remove(hook)
    
    def trigger_hooks(self, event: LifecycleEvent, plugin: BasePlugin) -> None:
        """
        Trigger lifecycle hooks for an event.
        
        Args:
            event: Lifecycle event
            plugin: Plugin instance
        """
        if event in self.lifecycle_hooks:
            for hook in self.lifecycle_hooks[event]:
                try:
                    hook(plugin)
                except Exception as e:
                    logger.warning(f"Error in lifecycle hook for {event.name}: {e}")
    
    def on_plugin_load(self, plugin_class: Type[BasePlugin]) -> None:
        """
        Handle plugin load event.
        
        Args:
            plugin_class: Plugin class that was loaded
        """
        logger.debug(f"Plugin class loaded: {plugin_class.__name__}")
        
        # Create a dummy instance for the hooks
        dummy_plugin = type('DummyPlugin', (), {
            'name': getattr(plugin_class, 'name', plugin_class.__name__),
            'version': getattr(plugin_class, 'version', '0.1.0'),
            'description': getattr(plugin_class, 'description', ''),
            'state': PluginState.LOADED
        })
        
        # Trigger hooks
        self.trigger_hooks(LifecycleEvent.LOAD, dummy_plugin)
        
        # Publish event
        try:
            event = Event(
                EventType.CUSTOM,
                {
                    "action": "plugin_loaded",
                    "plugin_name": dummy_plugin.name,
                    "plugin_version": dummy_plugin.version,
                    "timestamp": time.time()
                },
                "plugin_manager"
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Error publishing plugin load event: {e}")
    
    def on_plugin_initialize(self, plugin: BasePlugin) -> None:
        """
        Handle plugin initialize event.
        
        Args:
            plugin: Plugin instance that was initialized
        """
        logger.debug(f"Plugin initialized: {plugin.name}")
        
        # Trigger hooks
        self.trigger_hooks(LifecycleEvent.INITIALIZE, plugin)
        
        # Publish event
        try:
            event = Event(
                EventType.CUSTOM,
                {
                    "action": "plugin_initialized",
                    "plugin_name": plugin.name,
                    "plugin_version": plugin.version,
                    "timestamp": time.time()
                },
                "plugin_manager"
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Error publishing plugin initialize event: {e}")
    
    def on_plugin_activate(self, plugin: BasePlugin) -> None:
        """
        Handle plugin activate event.
        
        Args:
            plugin: Plugin instance that was activated
        """
        logger.debug(f"Plugin activated: {plugin.name}")
        
        # Trigger hooks
        self.trigger_hooks(LifecycleEvent.ACTIVATE, plugin)
        
        # Publish event
        try:
            event = Event(
                EventType.CUSTOM,
                {
                    "action": "plugin_activated",
                    "plugin_name": plugin.name,
                    "plugin_version": plugin.version,
                    "timestamp": time.time()
                },
                "plugin_manager"
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Error publishing plugin activate event: {e}")
    
    def on_plugin_deactivate(self, plugin: BasePlugin) -> None:
        """
        Handle plugin deactivate event.
        
        Args:
            plugin: Plugin instance that was deactivated
        """
        logger.debug(f"Plugin deactivated: {plugin.name}")
        
        # Trigger hooks
        self.trigger_hooks(LifecycleEvent.DEACTIVATE, plugin)
        
        # Publish event
        try:
            event = Event(
                EventType.CUSTOM,
                {
                    "action": "plugin_deactivated",
                    "plugin_name": plugin.name,
                    "plugin_version": plugin.version,
                    "timestamp": time.time()
                },
                "plugin_manager"
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Error publishing plugin deactivate event: {e}")
    
    def on_plugin_shutdown(self, plugin: BasePlugin) -> None:
        """
        Handle plugin shutdown event.
        
        Args:
            plugin: Plugin instance that was shut down
        """
        logger.debug(f"Plugin shut down: {plugin.name}")
        
        # Trigger hooks
        self.trigger_hooks(LifecycleEvent.SHUTDOWN, plugin)
        
        # Publish event
        try:
            event = Event(
                EventType.CUSTOM,
                {
                    "action": "plugin_shutdown",
                    "plugin_name": plugin.name,
                    "plugin_version": plugin.version,
                    "timestamp": time.time()
                },
                "plugin_manager"
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Error publishing plugin shutdown event: {e}")
    
    def on_plugin_error(self, plugin: BasePlugin, error: Exception) -> None:
        """
        Handle plugin error event.
        
        Args:
            plugin: Plugin instance that encountered an error
            error: The error that occurred
        """
        logger.debug(f"Plugin error: {plugin.name} - {error}")
        
        # Trigger hooks
        self.trigger_hooks(LifecycleEvent.ERROR, plugin)
        
        # Publish event
        try:
            event = Event(
                EventType.CUSTOM,
                {
                    "action": "plugin_error",
                    "plugin_name": plugin.name,
                    "plugin_version": plugin.version,
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "timestamp": time.time()
                },
                "plugin_manager"
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Error publishing plugin error event: {e}")

# Global lifecycle manager instance
lifecycle_manager = PluginLifecycleManager()

