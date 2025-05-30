"""
Tests for the plugin system.
"""

import unittest
import os
import tempfile
import json
import threading
import time
from unittest.mock import patch, MagicMock

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
from core.plugins.security import security_manager
from core.plugins.compatibility import compatibility_manager
from core.plugins.lifecycle import lifecycle_manager, LifecycleEvent
from core.plugins.resources import resource_manager, ResourceLimit
from core.plugins.isolation import isolation_manager
from core.plugins.validation import validation_manager
from core.event_system import EventType, Event

class TestBasePlugin(unittest.TestCase):
    """Tests for the BasePlugin class."""
    
    def test_init(self):
        """Test initialization of BasePlugin."""
        # Create a concrete implementation of BasePlugin for testing
        class TestPlugin(BasePlugin):
            name = "test_plugin"
            description = "Test plugin"
            version = "1.0.0"
            
            def initialize(self) -> bool:
                self.initialized = True
                return True
        
        # Test initialization with default config
        plugin = TestPlugin()
        self.assertEqual(plugin.name, "test_plugin")
        self.assertEqual(plugin.config, {})
        self.assertFalse(plugin.initialized)
        
        # Test initialization with custom config
        config = {"param1": "value1", "param2": 42}
        plugin = TestPlugin(config)
        self.assertEqual(plugin.config, config)
        
    def test_initialize(self):
        """Test initialization of BasePlugin."""
        # Create a concrete implementation of BasePlugin for testing
        class TestPlugin(BasePlugin):
            name = "test_plugin"
            
            def initialize(self) -> bool:
                self.initialized = True
                return True
        
        # Test initialization
        plugin = TestPlugin()
        self.assertFalse(plugin.initialized)
        result = plugin.initialize()
        self.assertTrue(result)
        self.assertTrue(plugin.initialized)
        
    def test_shutdown(self):
        """Test shutdown of BasePlugin."""
        # Create a concrete implementation of BasePlugin for testing
        class TestPlugin(BasePlugin):
            name = "test_plugin"
            
            def initialize(self) -> bool:
                self.initialized = True
                return True
        
        # Test shutdown
        plugin = TestPlugin()
        plugin.initialize()
        self.assertTrue(plugin.initialized)
        result = plugin.shutdown()
        self.assertTrue(result)
        self.assertFalse(plugin.initialized)
        
    def test_validate_config(self):
        """Test config validation of BasePlugin."""
        # Create a concrete implementation of BasePlugin for testing
        class TestPlugin(BasePlugin):
            name = "test_plugin"
            
            def initialize(self) -> bool:
                return True
                
            def validate_config(self) -> bool:
                return "param1" in self.config and self.config["param1"] == "value1"
        
        # Test with valid config
        config = {"param1": "value1"}
        plugin = TestPlugin(config)
        self.assertTrue(plugin.validate_config())
        
        # Test with invalid config
        config = {"param1": "wrong_value"}
        plugin = TestPlugin(config)
        self.assertFalse(plugin.validate_config())
        
    def test_enable_disable(self):
        """Test enabling and disabling of BasePlugin."""
        # Create a concrete implementation of BasePlugin for testing
        class TestPlugin(BasePlugin):
            name = "test_plugin"
            
            def initialize(self) -> bool:
                return True
        
        # Test enable/disable
        plugin = TestPlugin()
        self.assertTrue(plugin.is_enabled)
        plugin.disable()
        self.assertFalse(plugin.is_enabled)
        plugin.enable()
        self.assertTrue(plugin.is_enabled)
        
    def test_get_status(self):
        """Test get_status of BasePlugin."""
        # Create a concrete implementation of BasePlugin for testing
        class TestPlugin(BasePlugin):
            name = "test_plugin"
            description = "Test plugin"
            version = "1.0.0"
            
            def initialize(self) -> bool:
                self.initialized = True
                return True
        
        # Test get_status
        plugin = TestPlugin()
        status = plugin.get_status()
        self.assertEqual(status["name"], "test_plugin")
        self.assertEqual(status["description"], "Test plugin")
        self.assertEqual(status["version"], "1.0.0")
        self.assertTrue(status["is_enabled"])
        self.assertFalse(status["initialized"])
        
        # Test get_status after initialization
        plugin.initialize()
        status = plugin.get_status()
        self.assertTrue(status["initialized"])


class TestPluginManager(unittest.TestCase):
    """Tests for the PluginManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for plugins
        self.plugins_dir = tempfile.mkdtemp()
        
        # Create a temporary config file
        self.config_file = os.path.join(self.plugins_dir, "config.json")
        with open(self.config_file, "w") as f:
            json.dump({
                "test_plugin": {
                    "param1": "value1",
                    "param2": 42
                }
            }, f)
        
        # Create a plugin manager
        self.plugin_manager = PluginManager(self.plugins_dir, self.config_file)
        
        # Create test plugin classes
        class TestPlugin(BasePlugin):
            name = "test_plugin"
            description = "Test plugin"
            version = "1.0.0"
            
            def initialize(self) -> bool:
                self.initialized = True
                return True
        
        class TestConnector(ConnectorPlugin):
            name = "test_connector"
            description = "Test connector"
            version = "1.0.0"
            
            def initialize(self) -> bool:
                self.initialized = True
                return True
                
            def connect(self) -> bool:
                return True
                
            def fetch_data(self, query, **kwargs) -> dict:
                return {"data": "test_data"}
                
            def disconnect(self) -> bool:
                return True
        
        class TestProcessor(ProcessorPlugin):
            name = "test_processor"
            description = "Test processor"
            version = "1.0.0"
            
            def initialize(self) -> bool:
                self.initialized = True
                return True
                
            def process(self, data, **kwargs) -> dict:
                return {"processed_data": data}
        
        class TestAnalyzer(AnalyzerPlugin):
            name = "test_analyzer"
            description = "Test analyzer"
            version = "1.0.0"
            
            def initialize(self) -> bool:
                self.initialized = True
                return True
                
            def analyze(self, data, **kwargs) -> dict:
                return {"analysis_results": data}
        
        # Store test plugin classes
        self.TestPlugin = TestPlugin
        self.TestConnector = TestConnector
        self.TestProcessor = TestProcessor
        self.TestAnalyzer = TestAnalyzer
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Remove temporary directory
        import shutil
        shutil.rmtree(self.plugins_dir)
    
    def test_init(self):
        """Test initialization of PluginManager."""
        self.assertEqual(self.plugin_manager.plugins_dir, self.plugins_dir)
        self.assertEqual(self.plugin_manager.config_file, self.config_file)
        self.assertEqual(self.plugin_manager.plugins, {})
        self.assertEqual(self.plugin_manager.plugin_classes, {})
        self.assertEqual(self.plugin_manager.plugin_modules, {})
        self.assertEqual(self.plugin_manager.connectors, {})
        self.assertEqual(self.plugin_manager.processors, {})
        self.assertEqual(self.plugin_manager.analyzers, {})
        self.assertEqual(self.plugin_manager.plugin_configs["test_plugin"]["param1"], "value1")
        self.assertEqual(self.plugin_manager.plugin_configs["test_plugin"]["param2"], 42)
    
    def test_register_connector(self):
        """Test registration of connector plugins."""
        self.plugin_manager.register_connector("test_connector", self.TestConnector)
        self.assertIn("test_connector", self.plugin_manager.connectors)
        self.assertIn("test_connector", self.plugin_manager.plugin_classes)
        self.assertEqual(self.plugin_manager.connectors["test_connector"], self.TestConnector)
        
        # Test registration of invalid connector
        with self.assertRaises(TypeError):
            self.plugin_manager.register_connector("invalid_connector", self.TestPlugin)
    
    def test_register_processor(self):
        """Test registration of processor plugins."""
        self.plugin_manager.register_processor("test_processor", self.TestProcessor)
        self.assertIn("test_processor", self.plugin_manager.processors)
        self.assertIn("test_processor", self.plugin_manager.plugin_classes)
        self.assertEqual(self.plugin_manager.processors["test_processor"], self.TestProcessor)
        
        # Test registration of invalid processor
        with self.assertRaises(TypeError):
            self.plugin_manager.register_processor("invalid_processor", self.TestPlugin)
    
    def test_register_analyzer(self):
        """Test registration of analyzer plugins."""
        self.plugin_manager.register_analyzer("test_analyzer", self.TestAnalyzer)
        self.assertIn("test_analyzer", self.plugin_manager.analyzers)
        self.assertIn("test_analyzer", self.plugin_manager.plugin_classes)
        self.assertEqual(self.plugin_manager.analyzers["test_analyzer"], self.TestAnalyzer)
        
        # Test registration of invalid analyzer
        with self.assertRaises(TypeError):
            self.plugin_manager.register_analyzer("invalid_analyzer", self.TestPlugin)
    
    def test_initialize_plugin(self):
        """Test initialization of plugins."""
        # Register a plugin
        self.plugin_manager.register_connector("test_connector", self.TestConnector)
        
        # Initialize the plugin
        result = self.plugin_manager.initialize_plugin("test_connector")
        self.assertTrue(result)
        self.assertIn("test_connector", self.plugin_manager.plugins)
        self.assertTrue(self.plugin_manager.plugins["test_connector"].initialized)
        
        # Initialize a non-existent plugin
        result = self.plugin_manager.initialize_plugin("non_existent_plugin")
        self.assertFalse(result)
        
        # Initialize an already initialized plugin
        result = self.plugin_manager.initialize_plugin("test_connector")
        self.assertTrue(result)
    
    def test_initialize_all_plugins(self):
        """Test initialization of all plugins."""
        # Register plugins
        self.plugin_manager.register_connector("test_connector", self.TestConnector)
        self.plugin_manager.register_processor("test_processor", self.TestProcessor)
        self.plugin_manager.register_analyzer("test_analyzer", self.TestAnalyzer)
        
        # Initialize all plugins
        results = self.plugin_manager.initialize_all_plugins()
        self.assertTrue(results["test_connector"])
        self.assertTrue(results["test_processor"])
        self.assertTrue(results["test_analyzer"])
        self.assertIn("test_connector", self.plugin_manager.plugins)
        self.assertIn("test_processor", self.plugin_manager.plugins)
        self.assertIn("test_analyzer", self.plugin_manager.plugins)
    
    def test_get_plugin(self):
        """Test getting a plugin."""
        # Register and initialize a plugin
        self.plugin_manager.register_connector("test_connector", self.TestConnector)
        self.plugin_manager.initialize_plugin("test_connector")
        
        # Get the plugin
        plugin = self.plugin_manager.get_plugin("test_connector")
        self.assertIsNotNone(plugin)
        self.assertIsInstance(plugin, self.TestConnector)
        
        # Get a non-existent plugin
        plugin = self.plugin_manager.get_plugin("non_existent_plugin")
        self.assertIsNone(plugin)
    
    def test_get_all_plugins(self):
        """Test getting all plugins."""
        # Register and initialize plugins
        self.plugin_manager.register_connector("test_connector", self.TestConnector)
        self.plugin_manager.register_processor("test_processor", self.TestProcessor)
        self.plugin_manager.initialize_plugin("test_connector")
        self.plugin_manager.initialize_plugin("test_processor")
        
        # Get all plugins
        plugins = self.plugin_manager.get_all_plugins()
        self.assertEqual(len(plugins), 2)
        self.assertIn("test_connector", plugins)
        self.assertIn("test_processor", plugins)
    
    def test_get_plugins_by_type(self):
        """Test getting plugins by type."""
        # Register and initialize plugins
        self.plugin_manager.register_connector("test_connector", self.TestConnector)
        self.plugin_manager.register_processor("test_processor", self.TestProcessor)
        self.plugin_manager.register_analyzer("test_analyzer", self.TestAnalyzer)
        self.plugin_manager.initialize_plugin("test_connector")
        self.plugin_manager.initialize_plugin("test_processor")
        self.plugin_manager.initialize_plugin("test_analyzer")
        
        # Get plugins by type
        connectors = self.plugin_manager.get_plugins_by_type("connectors")
        processors = self.plugin_manager.get_plugins_by_type("processors")
        analyzers = self.plugin_manager.get_plugins_by_type("analyzers")
        
        self.assertEqual(len(connectors), 1)
        self.assertEqual(len(processors), 1)
        self.assertEqual(len(analyzers), 1)
        self.assertIn("test_connector", connectors)
        self.assertIn("test_processor", processors)
        self.assertIn("test_analyzer", analyzers)
        
        # Get plugins by invalid type
        invalid_plugins = self.plugin_manager.get_plugins_by_type("invalid_type")
        self.assertEqual(len(invalid_plugins), 0)
    
    def test_shutdown_plugin(self):
        """Test shutting down a plugin."""
        # Register and initialize a plugin
        self.plugin_manager.register_connector("test_connector", self.TestConnector)
        self.plugin_manager.initialize_plugin("test_connector")
        
        # Shutdown the plugin
        result = self.plugin_manager.shutdown_plugin("test_connector")
        self.assertTrue(result)
        self.assertNotIn("test_connector", self.plugin_manager.plugins)
        
        # Shutdown a non-existent plugin
        result = self.plugin_manager.shutdown_plugin("non_existent_plugin")
        self.assertFalse(result)
    
    def test_shutdown_all_plugins(self):
        """Test shutting down all plugins."""
        # Register and initialize plugins
        self.plugin_manager.register_connector("test_connector", self.TestConnector)
        self.plugin_manager.register_processor("test_processor", self.TestProcessor)
        self.plugin_manager.initialize_plugin("test_connector")
        self.plugin_manager.initialize_plugin("test_processor")
        
        # Shutdown all plugins
        results = self.plugin_manager.shutdown_all_plugins()
        self.assertTrue(results["test_connector"])
        self.assertTrue(results["test_processor"])
        self.assertEqual(len(self.plugin_manager.plugins), 0)
    
    @patch("importlib.reload")
    def test_reload_plugin(self, mock_reload):
        """Test reloading a plugin."""
        # Register and initialize a plugin
        self.plugin_manager.register_connector("test_connector", self.TestConnector)
        self.plugin_manager.initialize_plugin("test_connector")
        
        # Mock the plugin module
        self.plugin_manager.plugin_modules["test_connector"] = MagicMock(__name__="test_connector")
        
        # Reload the plugin
        with patch.object(self.plugin_manager, "load_plugin", return_value=self.TestConnector):
            result = self.plugin_manager.reload_plugin("test_connector")
            self.assertTrue(result)
            mock_reload.assert_called_once()
        
        # Reload a non-existent plugin
        result = self.plugin_manager.reload_plugin("non_existent_plugin")
        self.assertFalse(result)


class TestEnhancedPluginFeatures(unittest.TestCase):
    """Tests for the enhanced plugin features."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for plugins
        self.plugins_dir = tempfile.mkdtemp()
        
        # Create a temporary config file
        self.config_file = os.path.join(self.plugins_dir, "config.json")
        with open(self.config_file, "w") as f:
            json.dump({
                "test_plugin": {
                    "param1": "value1",
                    "param2": 42
                }
            }, f)
        
        # Create a plugin manager
        self.plugin_manager = PluginManager(self.plugins_dir, self.config_file)
        
        # Create test plugin class
        class TestEnhancedPlugin(BasePlugin):
            name = "test_enhanced_plugin"
            description = "Test enhanced plugin"
            version = "1.0.0"
            
            def __init__(self, config=None):
                super().__init__(config)
                self.metadata = PluginMetadata(
                    name=self.name,
                    version=self.version,
                    description=self.description,
                    author="Test Author",
                    website="https://example.com",
                    license="MIT",
                    min_system_version="4.0.0",
                    max_system_version="5.0.0",
                    dependencies={},
                    security_level=PluginSecurityLevel.MEDIUM
                )
                self.file_resource = None
                self.event_received = False
            
            def initialize(self) -> bool:
                self.initialized = True
                self.state = PluginState.INITIALIZED
                
                # Create a resource
                self.file_resource = open(os.path.join(self.plugins_dir, "test.log"), "w")
                self._register_resource("file", self.file_resource)
                
                # Subscribe to events
                self._subscribe_to_event(EventType.SYSTEM_STARTUP, self._handle_system_startup)
                
                return True
            
            def _handle_system_startup(self, event: Event) -> None:
                self.event_received = True
            
            def process_data(self, data):
                return f"Processed: {data}"
        
        # Store test plugin class
        self.TestEnhancedPlugin = TestEnhancedPlugin
        
        # Configure plugin system components
        security_manager.set_security_enabled(True)
        compatibility_manager.set_system_version("4.0.0")
        isolation_manager.set_isolation_enabled(True)
        validation_manager.set_validation_enabled(True)
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Remove temporary directory
        import shutil
        shutil.rmtree(self.plugins_dir)
    
    def test_plugin_lifecycle(self):
        """Test plugin lifecycle management."""
        # Register lifecycle event handler
        events_received = []
        
        def lifecycle_hook(plugin):
            events_received.append(plugin.name)
        
        lifecycle_manager.register_hook(LifecycleEvent.INITIALIZE, lifecycle_hook)
        
        # Register the plugin
        self.plugin_manager.plugin_classes[self.TestEnhancedPlugin.name] = self.TestEnhancedPlugin
        
        # Initialize the plugin
        success = self.plugin_manager.initialize_plugin(self.TestEnhancedPlugin.name)
        self.assertTrue(success)
        
        # Check that lifecycle event was received
        self.assertIn(self.TestEnhancedPlugin.name, events_received)
        
        # Get the plugin
        plugin = self.plugin_manager.get_plugin(self.TestEnhancedPlugin.name)
        self.assertIsNotNone(plugin)
        
        # Check plugin state
        self.assertEqual(plugin.state, PluginState.INITIALIZED)
        
        # Enable the plugin
        self.plugin_manager.enable_plugin(self.TestEnhancedPlugin.name)
        self.assertEqual(plugin.state, PluginState.ACTIVE)
        
        # Disable the plugin
        self.plugin_manager.disable_plugin(self.TestEnhancedPlugin.name)
        self.assertEqual(plugin.state, PluginState.DISABLED)
        
        # Shutdown the plugin
        success = self.plugin_manager.shutdown_plugin(self.TestEnhancedPlugin.name)
        self.assertTrue(success)
        
        # Unregister lifecycle event handler
        lifecycle_manager.unregister_hook(LifecycleEvent.INITIALIZE, lifecycle_hook)
    
    def test_resource_management(self):
        """Test plugin resource management."""
        # Set resource limit
        resource_manager.set_resource_limit(
            self.TestEnhancedPlugin.name,
            ResourceLimit(
                max_memory=1024 * 1024 * 10,  # 10 MB
                max_cpu_percent=10.0,
                max_file_handles=5,
                max_threads=2
            )
        )
        
        # Register the plugin
        self.plugin_manager.plugin_classes[self.TestEnhancedPlugin.name] = self.TestEnhancedPlugin
        
        # Initialize the plugin
        success = self.plugin_manager.initialize_plugin(self.TestEnhancedPlugin.name)
        self.assertTrue(success)
        
        # Get the plugin
        plugin = self.plugin_manager.get_plugin(self.TestEnhancedPlugin.name)
        self.assertIsNotNone(plugin)
        
        # Check that resource was registered
        resources = resource_manager.get_registered_resources(self.TestEnhancedPlugin.name)
        self.assertIn("file", resources)
        self.assertEqual(len(resources["file"]), 1)
        
        # Check that resource limit was set
        limit = resource_manager.get_resource_limit(self.TestEnhancedPlugin.name)
        self.assertIsNotNone(limit)
        self.assertEqual(limit.max_cpu_percent, 10.0)
        
        # Shutdown the plugin
        success = self.plugin_manager.shutdown_plugin(self.TestEnhancedPlugin.name)
        self.assertTrue(success)
        
        # Check that resources were released
        resources = resource_manager.get_registered_resources(self.TestEnhancedPlugin.name)
        self.assertEqual(len(resources), 0)
    
    def test_error_isolation(self):
        """Test plugin error isolation."""
        # Create a plugin class with an error
        class ErrorPlugin(BasePlugin):
            name = "error_plugin"
            
            def initialize(self) -> bool:
                raise ValueError("Test error")
        
        # Register the plugin
        self.plugin_manager.plugin_classes[ErrorPlugin.name] = ErrorPlugin
        
        # Initialize the plugin with isolation
        success = self.plugin_manager.initialize_plugin(ErrorPlugin.name)
        self.assertFalse(success)
        
        # Test isolation decorator
        @isolation_manager.isolate("test_isolation")
        def test_function(value):
            if value == "error":
                raise ValueError("Test error")
            return f"Success: {value}"
        
        # Test successful execution
        result = test_function("test")
        self.assertEqual(result, "Success: test")
        
        # Test error handling
        with self.assertRaises(Exception):
            test_function("error")
    
    def test_event_integration(self):
        """Test plugin event integration."""
        # Register the plugin
        self.plugin_manager.plugin_classes[self.TestEnhancedPlugin.name] = self.TestEnhancedPlugin
        
        # Initialize the plugin
        success = self.plugin_manager.initialize_plugin(self.TestEnhancedPlugin.name)
        self.assertTrue(success)
        
        # Get the plugin
        plugin = self.plugin_manager.get_plugin(self.TestEnhancedPlugin.name)
        self.assertIsNotNone(plugin)
        
        # Publish an event
        event = Event(
            EventType.SYSTEM_STARTUP,
            {"test": "data"},
            "test"
        )
        from core.event_system import publish_sync
        publish_sync(event)
        
        # Check that the plugin received the event
        self.assertTrue(plugin.event_received)
        
        # Shutdown the plugin
        success = self.plugin_manager.shutdown_plugin(self.TestEnhancedPlugin.name)
        self.assertTrue(success)
    
    def test_validation(self):
        """Test plugin validation."""
        # Create an invalid plugin class
        class InvalidPlugin(BasePlugin):
            name = "invalid_plugin"
            
            # Missing required initialize method
            pass
        
        # Validate the plugin class
        is_valid, errors = validation_manager.validate_plugin_class(InvalidPlugin)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        
        # Create a valid plugin class
        class ValidPlugin(BasePlugin):
            name = "valid_plugin"
            version = "1.0.0"
            description = "Valid plugin"
            
            def initialize(self) -> bool:
                return True
            
            def shutdown(self) -> bool:
                return True
            
            def validate_config(self) -> bool:
                return True
        
        # Validate the plugin class
        is_valid, errors = validation_manager.validate_plugin_class(ValidPlugin)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
