"""
Unit tests for the plugin system.
"""

import os
import json
import pytest
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from core.plugins.base import (
    BasePlugin,
    ConnectorPlugin,
    ProcessorPlugin,
    AnalyzerPlugin,
    PluginManager
)


@pytest.mark.unit
class TestBasePlugin:
    """Test the BasePlugin class."""
    
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
        assert plugin.name == "test_plugin"
        assert plugin.config == {}
        assert plugin.initialized is False
        
        # Test initialization with custom config
        config = {"param1": "value1", "param2": 42}
        plugin = TestPlugin(config)
        assert plugin.config == config
    
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
        assert plugin.initialized is False
        result = plugin.initialize()
        assert result is True
        assert plugin.initialized is True
    
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
        assert plugin.initialized is True
        result = plugin.shutdown()
        assert result is True
        assert plugin.initialized is False
    
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
        assert plugin.validate_config() is True
        
        # Test with invalid config
        config = {"param1": "wrong_value"}
        plugin = TestPlugin(config)
        assert plugin.validate_config() is False
    
    def test_enable_disable(self):
        """Test enabling and disabling of BasePlugin."""
        # Create a concrete implementation of BasePlugin for testing
        class TestPlugin(BasePlugin):
            name = "test_plugin"
            
            def initialize(self) -> bool:
                return True
        
        # Test enable/disable
        plugin = TestPlugin()
        assert plugin.is_enabled is True
        plugin.disable()
        assert plugin.is_enabled is False
        plugin.enable()
        assert plugin.is_enabled is True
    
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
        assert status["name"] == "test_plugin"
        assert status["description"] == "Test plugin"
        assert status["version"] == "1.0.0"
        assert status["is_enabled"] is True
        assert status["initialized"] is False
        
        # Test get_status after initialization
        plugin.initialize()
        status = plugin.get_status()
        assert status["initialized"] is True


@pytest.mark.unit
class TestPluginManager:
    """Test the PluginManager class."""
    
    def setup_method(self):
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
    
    def teardown_method(self):
        """Tear down test fixtures."""
        # Remove temporary directory
        shutil.rmtree(self.plugins_dir)
    
    def test_init(self):
        """Test initialization of PluginManager."""
        assert self.plugin_manager.plugins_dir == self.plugins_dir
        assert self.plugin_manager.config_file == self.config_file
        assert self.plugin_manager.plugins == {}
        assert self.plugin_manager.plugin_classes == {}
        assert self.plugin_manager.plugin_modules == {}
        assert self.plugin_manager.connectors == {}
        assert self.plugin_manager.processors == {}
        assert self.plugin_manager.analyzers == {}
        assert self.plugin_manager.plugin_configs["test_plugin"]["param1"] == "value1"
        assert self.plugin_manager.plugin_configs["test_plugin"]["param2"] == 42
    
    def test_register_connector(self):
        """Test registration of connector plugins."""
        self.plugin_manager.register_connector("test_connector", self.TestConnector)
        assert "test_connector" in self.plugin_manager.connectors
        assert "test_connector" in self.plugin_manager.plugin_classes
        assert self.plugin_manager.connectors["test_connector"] == self.TestConnector
        
        # Test registration of invalid connector
        with pytest.raises(TypeError):
            self.plugin_manager.register_connector("invalid_connector", self.TestPlugin)
    
    def test_register_processor(self):
        """Test registration of processor plugins."""
        self.plugin_manager.register_processor("test_processor", self.TestProcessor)
        assert "test_processor" in self.plugin_manager.processors
        assert "test_processor" in self.plugin_manager.plugin_classes
        assert self.plugin_manager.processors["test_processor"] == self.TestProcessor
        
        # Test registration of invalid processor
        with pytest.raises(TypeError):
            self.plugin_manager.register_processor("invalid_processor", self.TestPlugin)
    
    def test_register_analyzer(self):
        """Test registration of analyzer plugins."""
        self.plugin_manager.register_analyzer("test_analyzer", self.TestAnalyzer)
        assert "test_analyzer" in self.plugin_manager.analyzers
        assert "test_analyzer" in self.plugin_manager.plugin_classes
        assert self.plugin_manager.analyzers["test_analyzer"] == self.TestAnalyzer
        
        # Test registration of invalid analyzer
        with pytest.raises(TypeError):
            self.plugin_manager.register_analyzer("invalid_analyzer", self.TestPlugin)
    
    def test_load_plugin(self):
        """Test loading plugins."""
        # Register a plugin class
        self.plugin_manager.plugin_classes["test_plugin"] = self.TestPlugin
        
        # Load the plugin
        plugin = self.plugin_manager.load_plugin("test_plugin")
        assert plugin is not None
        assert plugin.name == "test_plugin"
        assert plugin.config["param1"] == "value1"
        assert plugin.config["param2"] == 42
        assert "test_plugin" in self.plugin_manager.plugins
        assert self.plugin_manager.plugins["test_plugin"] == plugin
    
    def test_load_connector(self):
        """Test loading connector plugins."""
        # Register a connector class
        self.plugin_manager.register_connector("test_connector", self.TestConnector)
        
        # Load the connector
        connector = self.plugin_manager.load_connector("test_connector")
        assert connector is not None
        assert connector.name == "test_connector"
        assert "test_connector" in self.plugin_manager.plugins
        assert self.plugin_manager.plugins["test_connector"] == connector
    
    def test_load_processor(self):
        """Test loading processor plugins."""
        # Register a processor class
        self.plugin_manager.register_processor("test_processor", self.TestProcessor)
        
        # Load the processor
        processor = self.plugin_manager.load_processor("test_processor")
        assert processor is not None
        assert processor.name == "test_processor"
        assert "test_processor" in self.plugin_manager.plugins
        assert self.plugin_manager.plugins["test_processor"] == processor
    
    def test_load_analyzer(self):
        """Test loading analyzer plugins."""
        # Register an analyzer class
        self.plugin_manager.register_analyzer("test_analyzer", self.TestAnalyzer)
        
        # Load the analyzer
        analyzer = self.plugin_manager.load_analyzer("test_analyzer")
        assert analyzer is not None
        assert analyzer.name == "test_analyzer"
        assert "test_analyzer" in self.plugin_manager.plugins
        assert self.plugin_manager.plugins["test_analyzer"] == analyzer
    
    def test_get_plugin(self):
        """Test getting plugins."""
        # Register and load a plugin
        self.plugin_manager.plugin_classes["test_plugin"] = self.TestPlugin
        self.plugin_manager.load_plugin("test_plugin")
        
        # Get the plugin
        plugin = self.plugin_manager.get_plugin("test_plugin")
        assert plugin is not None
        assert plugin.name == "test_plugin"
        
        # Test getting a non-existent plugin
        with pytest.raises(KeyError):
            self.plugin_manager.get_plugin("non_existent_plugin")
    
    def test_get_connector(self):
        """Test getting connector plugins."""
        # Register and load a connector
        self.plugin_manager.register_connector("test_connector", self.TestConnector)
        self.plugin_manager.load_connector("test_connector")
        
        # Get the connector
        connector = self.plugin_manager.get_connector("test_connector")
        assert connector is not None
        assert connector.name == "test_connector"
        
        # Test getting a non-existent connector
        with pytest.raises(KeyError):
            self.plugin_manager.get_connector("non_existent_connector")
    
    def test_get_processor(self):
        """Test getting processor plugins."""
        # Register and load a processor
        self.plugin_manager.register_processor("test_processor", self.TestProcessor)
        self.plugin_manager.load_processor("test_processor")
        
        # Get the processor
        processor = self.plugin_manager.get_processor("test_processor")
        assert processor is not None
        assert processor.name == "test_processor"
        
        # Test getting a non-existent processor
        with pytest.raises(KeyError):
            self.plugin_manager.get_processor("non_existent_processor")
    
    def test_get_analyzer(self):
        """Test getting analyzer plugins."""
        # Register and load an analyzer
        self.plugin_manager.register_analyzer("test_analyzer", self.TestAnalyzer)
        self.plugin_manager.load_analyzer("test_analyzer")
        
        # Get the analyzer
        analyzer = self.plugin_manager.get_analyzer("test_analyzer")
        assert analyzer is not None
        assert analyzer.name == "test_analyzer"
        
        # Test getting a non-existent analyzer
        with pytest.raises(KeyError):
            self.plugin_manager.get_analyzer("non_existent_analyzer")
    
    def test_shutdown_plugin(self):
        """Test shutting down plugins."""
        # Register and load a plugin
        self.plugin_manager.plugin_classes["test_plugin"] = self.TestPlugin
        plugin = self.plugin_manager.load_plugin("test_plugin")
        plugin.initialize()
        assert plugin.initialized is True
        
        # Shutdown the plugin
        self.plugin_manager.shutdown_plugin("test_plugin")
        assert plugin.initialized is False
    
    def test_shutdown_all(self):
        """Test shutting down all plugins."""
        # Register and load multiple plugins
        self.plugin_manager.plugin_classes["test_plugin"] = self.TestPlugin
        self.plugin_manager.register_connector("test_connector", self.TestConnector)
        self.plugin_manager.register_processor("test_processor", self.TestProcessor)
        self.plugin_manager.register_analyzer("test_analyzer", self.TestAnalyzer)
        
        plugin = self.plugin_manager.load_plugin("test_plugin")
        connector = self.plugin_manager.load_connector("test_connector")
        processor = self.plugin_manager.load_processor("test_processor")
        analyzer = self.plugin_manager.load_analyzer("test_analyzer")
        
        plugin.initialize()
        connector.initialize()
        processor.initialize()
        analyzer.initialize()
        
        assert plugin.initialized is True
        assert connector.initialized is True
        assert processor.initialized is True
        assert analyzer.initialized is True
        
        # Shutdown all plugins
        self.plugin_manager.shutdown_all()
        
        assert plugin.initialized is False
        assert connector.initialized is False
        assert processor.initialized is False
        assert analyzer.initialized is False
    
    def test_reload_plugin(self):
        """Test reloading plugins."""
        # Register and load a plugin
        self.plugin_manager.plugin_classes["test_plugin"] = self.TestPlugin
        plugin = self.plugin_manager.load_plugin("test_plugin")
        plugin.initialize()
        assert plugin.initialized is True
        
        # Reload the plugin
        new_plugin = self.plugin_manager.reload_plugin("test_plugin")
        assert new_plugin is not None
        assert new_plugin.name == "test_plugin"
        assert new_plugin.initialized is True
        assert new_plugin is not plugin  # Should be a new instance
    
    def test_reload_config(self):
        """Test reloading plugin configurations."""
        # Register and load a plugin
        self.plugin_manager.plugin_classes["test_plugin"] = self.TestPlugin
        plugin = self.plugin_manager.load_plugin("test_plugin")
        assert plugin.config["param1"] == "value1"
        assert plugin.config["param2"] == 42
        
        # Update the config file
        with open(self.config_file, "w") as f:
            json.dump({
                "test_plugin": {
                    "param1": "new_value",
                    "param2": 100
                }
            }, f)
        
        # Reload the config
        self.plugin_manager.reload_config()
        assert self.plugin_manager.plugin_configs["test_plugin"]["param1"] == "new_value"
        assert self.plugin_manager.plugin_configs["test_plugin"]["param2"] == 100
        
        # Reload the plugin to apply the new config
        plugin = self.plugin_manager.reload_plugin("test_plugin")
        assert plugin.config["param1"] == "new_value"
        assert plugin.config["param2"] == 100

