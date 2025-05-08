#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Initialization module for Wiseflow.

This module handles system initialization and shutdown procedures.
"""

import os
import asyncio
import signal
import logging
import time
from typing import Dict, Any, Optional, List, Callable, Awaitable

from core.imports import (
    config,
    logger,
    with_context,
    handle_exceptions,
    ErrorHandler,
    async_error_handler,
    WiseflowError,
    ConfigurationError,
    ResourceError,
    EventType,
    Event,
    publish,
    publish_sync,
    ResourceMonitor,
    PluginManager,
    PbTalker,
    initialize_all_connectors,
    ConnectorBase
)

# Import plugin system components
from core.plugins.security import security_manager
from core.plugins.compatibility import compatibility_manager
from core.plugins.lifecycle import lifecycle_manager
from core.plugins.resources import resource_manager

class WiseflowSystem:
    """
    Main system class for Wiseflow.
    
    This class handles initialization, shutdown, and overall system management.
    """
    
    _instance = None
    
    def __new__(cls):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(WiseflowSystem, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the system."""
        if self._initialized:
            return
            
        self.logger = logger.bind(component="WiseflowSystem")
        self.plugin_manager = PluginManager()
        self.pb = PbTalker(self.logger)
        self.resource_monitor = ResourceMonitor(
            check_interval=10.0,
            warning_threshold=75.0,
            critical_threshold=90.0
        )
        
        self.connectors = {}
        self.shutdown_handlers = []
        self.is_shutting_down = False
        self._initialized = True
        
        # Configure plugin system components
        self._configure_plugin_system()
        
        self.logger.info("Wiseflow system initialized")
    
    def _configure_plugin_system(self) -> None:
        """Configure the plugin system components."""
        # Set system version for compatibility checks
        compatibility_manager.set_system_version(config.get("SYSTEM_VERSION", "4.0.0"))
        
        # Configure security manager
        security_manager.set_security_enabled(config.get("PLUGIN_SECURITY_ENABLED", True))
        
        # Start resource monitoring
        if config.get("PLUGIN_RESOURCE_MONITORING_ENABLED", True):
            resource_manager.start_monitoring()
        
        # Register shutdown handler for plugin system
        self.register_shutdown_handler(self._shutdown_plugin_system)
    
    def _shutdown_plugin_system(self) -> None:
        """Shutdown the plugin system."""
        try:
            # Stop resource monitoring
            resource_manager.stop_monitoring()
            
            # Shutdown all plugins
            self.plugin_manager.shutdown_all_plugins()
            
            self.logger.info("Plugin system shutdown complete")
        except Exception as e:
            self.logger.error(f"Error shutting down plugin system: {e}")

    @handle_exceptions(
        error_types=[Exception],
        default_message="Failed to start Wiseflow system",
        log_error=True,
        reraise=False,
        save_to_file=True
    )
    async def start(self) -> bool:
        """
        Start the Wiseflow system.
        
        Returns:
            bool: True if startup was successful, False otherwise
        """
        self.logger.info("Starting Wiseflow system...")
        
        try:
            # Register signal handlers for graceful shutdown
            self._register_signal_handlers()
            
            # Start resource monitoring
            await self.resource_monitor.start()
            
            # Load plugins
            self._load_plugins()
            
            # Initialize connectors
            await self._initialize_connectors()
            
            # Publish system startup event
            startup_event = Event(
                EventType.SYSTEM_STARTUP,
                data={
                    "version": "4.0.0", 
                    "config": config.get("PROJECT_DIR", ""),
                    "timestamp": time.time()
                },
                source="system"
            )
            await publish(startup_event)
            
            self.logger.info("Wiseflow system started successfully")
            return True
            
        except Exception as e:
            error_context = {
                "component": "WiseflowSystem",
                "method": "start",
                "error": str(e)
            }
            with_context(**error_context).error(f"Error starting Wiseflow system: {e}")
            with_context(**error_context).debug(f"Traceback:\n{traceback.format_exc()}")
            return False
    
    async def shutdown(self, reason: str = "normal") -> None:
        """
        Shutdown the Wiseflow system.
        
        Args:
            reason: Reason for shutdown
        """
        if self.is_shutting_down:
            return
            
        self.is_shutting_down = True
        self.logger.info(f"Shutting down Wiseflow system (reason: {reason})...")
        
        # Use error handler to catch and log any exceptions during shutdown
        async with ErrorHandler(
            error_types=[Exception],
            log_error=True,
            context={"component": "WiseflowSystem", "method": "shutdown", "reason": reason}
        ) as handler:
            # Publish system shutdown event
            shutdown_event = Event(
                EventType.SYSTEM_SHUTDOWN,
                data={
                    "reason": reason,
                    "timestamp": time.time()
                },
                source="system"
            )
            await publish(shutdown_event)
            
            # Execute all registered shutdown handlers
            for handler in self.shutdown_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler()
                    else:
                        handler()
                except Exception as e:
                    self.logger.error(f"Error in shutdown handler: {e}")
            
            # Stop resource monitoring
            await self.resource_monitor.stop()
        
        self.logger.info("Wiseflow system shutdown complete")
    
    def register_shutdown_handler(self, handler: Callable[[], Any]) -> None:
        """
        Register a function to be called during system shutdown.
        
        Args:
            handler: Function to call during shutdown
        """
        self.shutdown_handlers.append(handler)
    
    def _register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        def signal_handler(sig, frame):
            self.logger.info(f"Received signal {sig}")
            asyncio.create_task(self.shutdown(f"signal_{sig}"))
        
        # Register for SIGINT (Ctrl+C) and SIGTERM
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    @handle_exceptions(
        error_types=[Exception],
        default_message="Failed to load plugins",
        log_error=True
    )
    def _load_plugins(self) -> None:
        """Load and initialize plugins."""
        self.logger.info("Loading plugins...")
        plugins = self.plugin_manager.load_all_plugins()
        self.logger.info(f"Loaded {len(plugins)} plugins")
        
        # Initialize plugins with configurations
        configs = {}  # Load configurations from database or config files
        results = self.plugin_manager.initialize_all_plugins(configs)
        
        for name, success in results.items():
            if success:
                self.logger.info(f"Initialized plugin: {name}")
            else:
                self.logger.warning(f"Failed to initialize plugin: {name}")
    
    @handle_exceptions(
        error_types=[Exception],
        default_message="Failed to initialize connectors",
        log_error=True
    )
    async def _initialize_connectors(self) -> None:
        """Initialize data source connectors."""
        self.logger.info("Initializing connectors...")
        
        # Get connector plugins
        connector_plugins = self.plugin_manager.get_plugins_by_type("connectors")
        
        # Add them to our connectors dictionary
        for name, plugin in connector_plugins.items():
            if isinstance(plugin, ConnectorBase):
                self.connectors[name] = plugin
        
        # Initialize all connectors
        if self.connectors:
            results = await initialize_all_connectors(self.connectors)
            
            for name, success in results.items():
                if success:
                    self.logger.info(f"Initialized connector: {name}")
                else:
                    self.logger.warning(f"Failed to initialize connector: {name}")
        else:
            self.logger.warning("No connectors found")

# Create a singleton instance
wiseflow_system = WiseflowSystem()

async def initialize_system() -> bool:
    """
    Initialize the Wiseflow system.
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    return await wiseflow_system.start()

async def shutdown_system(reason: str = "normal") -> None:
    """
    Shutdown the Wiseflow system.
    
    Args:
        reason: Reason for shutdown
    """
    await wiseflow_system.shutdown(reason)

def register_shutdown_handler(handler: Callable[[], Any]) -> None:
    """
    Register a function to be called during system shutdown.
    
    Args:
        handler: Function to call during shutdown
    """
    wiseflow_system.register_shutdown_handler(handler)
