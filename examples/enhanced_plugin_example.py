"""
Enhanced plugin example for Wiseflow.

This example demonstrates the improved plugin system with lifecycle management,
resource management, error isolation, and event integration.
"""

import os
import sys
import logging
import time
from typing import Dict, Any, Optional

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.plugins import (
    BasePlugin,
    ConnectorPlugin,
    ProcessorPlugin,
    AnalyzerPlugin,
    PluginState,
    PluginSecurityLevel,
    PluginMetadata,
    plugin_manager,
    security_manager,
    compatibility_manager,
    lifecycle_manager,
    resource_manager,
    isolation_manager,
    validation_manager,
    ResourceLimit
)
from core.event_system import EventType, Event, subscribe, publish_sync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class EnhancedExamplePlugin(BasePlugin):
    """Enhanced example plugin demonstrating new features."""
    
    name = "enhanced_example_plugin"
    version = "1.0.0"
    description = "Enhanced example plugin demonstrating new features"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the plugin."""
        super().__init__(config)
        
        # Set plugin metadata
        self.metadata = PluginMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
            author="Wiseflow Team",
            website="https://example.com/wiseflow",
            license="MIT",
            min_system_version="4.0.0",
            max_system_version="5.0.0",
            dependencies={},
            security_level=PluginSecurityLevel.MEDIUM
        )
        
        # Store resources
        self.file_resource = None
        self.data = {}
    
    def initialize(self) -> bool:
        """Initialize the plugin."""
        logger.info(f"Initializing {self.name}...")
        
        try:
            # Subscribe to events
            self._subscribe_to_event(EventType.SYSTEM_STARTUP, self._handle_system_startup)
            self._subscribe_to_event(EventType.SYSTEM_SHUTDOWN, self._handle_system_shutdown)
            
            # Create a resource
            self.file_resource = open("enhanced_example_plugin.log", "w")
            self._register_resource("file", self.file_resource)
            
            # Write initialization message
            self.file_resource.write(f"Plugin {self.name} initialized at {time.time()}\n")
            self.file_resource.flush()
            
            # Publish initialization event
            event = Event(
                EventType.CUSTOM,
                {
                    "action": "plugin_custom_init",
                    "plugin_name": self.name,
                    "timestamp": time.time()
                },
                self.name
            )
            publish_sync(event)
            
            logger.info(f"Plugin {self.name} initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing plugin {self.name}: {e}")
            self.error = str(e)
            return False
    
    def shutdown(self) -> bool:
        """Shutdown the plugin."""
        logger.info(f"Shutting down {self.name}...")
        
        try:
            # Write shutdown message
            if self.file_resource and not self.file_resource.closed:
                self.file_resource.write(f"Plugin {self.name} shutdown at {time.time()}\n")
                self.file_resource.flush()
            
            # Unsubscribe from events and release resources
            return super().shutdown()
        except Exception as e:
            logger.error(f"Error shutting down plugin {self.name}: {e}")
            self.error = str(e)
            return False
    
    def _handle_system_startup(self, event: Event) -> None:
        """Handle system startup event."""
        logger.info(f"Plugin {self.name} received system startup event: {event.data}")
        
        # Store event data
        self.data["system_startup"] = event.data
        
        # Write to resource
        if self.file_resource and not self.file_resource.closed:
            self.file_resource.write(f"System startup event received at {time.time()}\n")
            self.file_resource.flush()
    
    def _handle_system_shutdown(self, event: Event) -> None:
        """Handle system shutdown event."""
        logger.info(f"Plugin {self.name} received system shutdown event: {event.data}")
        
        # Store event data
        self.data["system_shutdown"] = event.data
        
        # Write to resource
        if self.file_resource and not self.file_resource.closed:
            self.file_resource.write(f"System shutdown event received at {time.time()}\n")
            self.file_resource.flush()
    
    def process_data(self, data: Any) -> Any:
        """Process data with error isolation."""
        # This method is wrapped with error isolation when called through the plugin manager
        logger.info(f"Processing data: {data}")
        
        # Simulate processing
        processed_data = {
            "original": data,
            "processed_by": self.name,
            "timestamp": time.time()
        }
        
        return processed_data

def main():
    """Run the enhanced plugin example."""
    logger.info("Starting enhanced plugin example...")
    
    # Configure plugin system components
    security_manager.set_security_enabled(True)
    compatibility_manager.set_system_version("4.0.0")
    isolation_manager.set_isolation_enabled(True)
    validation_manager.set_validation_enabled(True)
    
    # Set resource limits
    resource_manager.set_resource_limit(
        "enhanced_example_plugin",
        ResourceLimit(
            max_memory=1024 * 1024 * 10,  # 10 MB
            max_cpu_percent=10.0,
            max_file_handles=5,
            max_threads=2
        )
    )
    
    # Register lifecycle hooks
    def on_plugin_activate(plugin):
        logger.info(f"Custom hook: Plugin {plugin.name} activated")
    
    lifecycle_manager.register_hook(
        lifecycle_manager.LifecycleEvent.ACTIVATE,
        on_plugin_activate
    )
    
    # Register the plugin
    plugin_class = EnhancedExamplePlugin
    plugin_manager.plugin_classes[plugin_class.name] = plugin_class
    
    # Initialize the plugin
    success = plugin_manager.initialize_plugin(plugin_class.name)
    if success:
        logger.info(f"Plugin {plugin_class.name} initialized successfully")
        
        # Get the plugin instance
        plugin = plugin_manager.get_plugin(plugin_class.name)
        
        # Get plugin status
        status = plugin.get_status()
        logger.info(f"Plugin status: {status}")
        
        # Process data with error isolation
        try:
            result = isolation_manager.isolate(plugin_class.name)(plugin.process_data)("test data")
            logger.info(f"Processing result: {result}")
        except Exception as e:
            logger.error(f"Error processing data: {e}")
        
        # Disable the plugin
        plugin_manager.disable_plugin(plugin_class.name)
        logger.info(f"Plugin {plugin_class.name} disabled")
        
        # Enable the plugin
        plugin_manager.enable_plugin(plugin_class.name)
        logger.info(f"Plugin {plugin_class.name} enabled")
        
        # Shutdown the plugin
        plugin_manager.shutdown_plugin(plugin_class.name)
        logger.info(f"Plugin {plugin_class.name} shutdown")
    else:
        logger.error(f"Failed to initialize plugin {plugin_class.name}")
    
    logger.info("Enhanced plugin example completed")

if __name__ == "__main__":
    main()

