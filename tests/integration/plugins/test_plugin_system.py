"""
Integration tests for the plugin system.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

from core.plugins.base import Plugin, PluginInterface
from core.plugins.loader import PluginLoader
from core.plugins.lifecycle import PluginLifecycleManager
from core.plugins.validation import validate_plugin
from core.plugins.compatibility import check_compatibility
from core.plugins.isolation import create_plugin_sandbox


@pytest.mark.integration
@pytest.mark.plugins
class TestPluginSystem:
    """Integration tests for the plugin system."""
    
    @pytest.fixture
    def sample_plugin_class(self):
        """Create a sample plugin class for testing."""
        class SamplePlugin(Plugin):
            """A sample plugin for testing."""
            
            def __init__(self):
                super().__init__(
                    name="sample_plugin",
                    version="1.0.0",
                    description="A sample plugin for testing",
                    author="Test Author",
                    dependencies={"core": ">=0.1.0"},
                )
            
            def initialize(self):
                """Initialize the plugin."""
                return True
            
            def execute(self, *args, **kwargs):
                """Execute the plugin."""
                return {"status": "success", "args": args, "kwargs": kwargs}
            
            def cleanup(self):
                """Clean up the plugin."""
                return True
        
        return SamplePlugin
    
    @pytest.fixture
    def sample_plugin_instance(self, sample_plugin_class):
        """Create a sample plugin instance for testing."""
        return sample_plugin_class()
    
    def test_plugin_creation(self, sample_plugin_instance):
        """Test creating a plugin."""
        # Check the plugin attributes
        assert sample_plugin_instance.name == "sample_plugin"
        assert sample_plugin_instance.version == "1.0.0"
        assert sample_plugin_instance.description == "A sample plugin for testing"
        assert sample_plugin_instance.author == "Test Author"
        assert sample_plugin_instance.dependencies == {"core": ">=0.1.0"}
    
    def test_plugin_validation(self, sample_plugin_instance):
        """Test validating a plugin."""
        # Validate the plugin
        validation_result = validate_plugin(sample_plugin_instance)
        
        # Check the validation result
        assert validation_result["is_valid"] is True
        assert len(validation_result["errors"]) == 0
        
        # Create an invalid plugin
        invalid_plugin = MagicMock()
        invalid_plugin.name = None
        invalid_plugin.version = "1.0.0"
        invalid_plugin.description = "An invalid plugin"
        invalid_plugin.author = "Test Author"
        invalid_plugin.dependencies = {"core": ">=0.1.0"}
        
        # Validate the invalid plugin
        validation_result = validate_plugin(invalid_plugin)
        
        # Check the validation result
        assert validation_result["is_valid"] is False
        assert len(validation_result["errors"]) > 0
        assert any("name" in error for error in validation_result["errors"])
    
    def test_plugin_compatibility(self, sample_plugin_instance):
        """Test checking plugin compatibility."""
        # Check compatibility with a compatible system version
        compatibility_result = check_compatibility(
            sample_plugin_instance,
            {"core": "0.1.0"}
        )
        
        # Check the compatibility result
        assert compatibility_result["is_compatible"] is True
        assert len(compatibility_result["incompatibilities"]) == 0
        
        # Check compatibility with an incompatible system version
        compatibility_result = check_compatibility(
            sample_plugin_instance,
            {"core": "0.0.9"}
        )
        
        # Check the compatibility result
        assert compatibility_result["is_compatible"] is False
        assert len(compatibility_result["incompatibilities"]) > 0
        assert any("core" in incompatibility for incompatibility in compatibility_result["incompatibilities"])
    
    @patch("core.plugins.isolation.create_plugin_sandbox")
    def test_plugin_isolation(self, mock_create_sandbox, sample_plugin_instance):
        """Test plugin isolation."""
        # Mock the sandbox creation
        mock_sandbox = MagicMock()
        mock_create_sandbox.return_value = mock_sandbox
        
        # Create a sandbox for the plugin
        sandbox = create_plugin_sandbox(sample_plugin_instance)
        
        # Check that the sandbox was created
        assert sandbox is mock_sandbox
        mock_create_sandbox.assert_called_once_with(sample_plugin_instance)
    
    @patch("core.plugins.loader.PluginLoader._load_plugin_from_path")
    def test_plugin_loading(self, mock_load_plugin, sample_plugin_class):
        """Test loading plugins."""
        # Mock the plugin loading
        mock_load_plugin.return_value = sample_plugin_class
        
        # Create a plugin loader
        loader = PluginLoader()
        
        # Load a plugin
        plugin = loader.load_plugin("sample_plugin")
        
        # Check that the plugin was loaded
        assert plugin.__class__ == sample_plugin_class
        mock_load_plugin.assert_called_once_with("sample_plugin")
    
    @patch("core.plugins.loader.PluginLoader._discover_plugins")
    @patch("core.plugins.loader.PluginLoader._load_plugin_from_path")
    def test_plugin_discovery(self, mock_load_plugin, mock_discover_plugins, sample_plugin_class):
        """Test discovering plugins."""
        # Mock the plugin discovery
        mock_discover_plugins.return_value = ["sample_plugin"]
        mock_load_plugin.return_value = sample_plugin_class
        
        # Create a plugin loader
        loader = PluginLoader()
        
        # Discover plugins
        plugins = loader.discover_plugins()
        
        # Check that the plugins were discovered
        assert len(plugins) == 1
        assert plugins[0].__class__ == sample_plugin_class
        mock_discover_plugins.assert_called_once()
        mock_load_plugin.assert_called_once_with("sample_plugin")
    
    def test_plugin_lifecycle(self, sample_plugin_instance):
        """Test the plugin lifecycle."""
        # Create a plugin lifecycle manager
        lifecycle_manager = PluginLifecycleManager()
        
        # Register the plugin
        lifecycle_manager.register_plugin(sample_plugin_instance)
        
        # Check that the plugin was registered
        assert sample_plugin_instance.name in lifecycle_manager.plugins
        
        # Initialize the plugin
        success = lifecycle_manager.initialize_plugin(sample_plugin_instance.name)
        
        # Check that the plugin was initialized
        assert success is True
        
        # Execute the plugin
        result = lifecycle_manager.execute_plugin(
            sample_plugin_instance.name,
            "arg1", "arg2",
            kwarg1="value1", kwarg2="value2"
        )
        
        # Check the execution result
        assert result["status"] == "success"
        assert result["args"] == ("arg1", "arg2")
        assert result["kwargs"] == {"kwarg1": "value1", "kwarg2": "value2"}
        
        # Clean up the plugin
        success = lifecycle_manager.cleanup_plugin(sample_plugin_instance.name)
        
        # Check that the plugin was cleaned up
        assert success is True
        
        # Unregister the plugin
        lifecycle_manager.unregister_plugin(sample_plugin_instance.name)
        
        # Check that the plugin was unregistered
        assert sample_plugin_instance.name not in lifecycle_manager.plugins
    
    def test_plugin_interface(self):
        """Test the plugin interface."""
        # Create a class that implements the plugin interface
        class TestPlugin(PluginInterface):
            def initialize(self):
                return True
            
            def execute(self, *args, **kwargs):
                return {"status": "success"}
            
            def cleanup(self):
                return True
        
        # Create an instance of the class
        plugin = TestPlugin()
        
        # Check that the interface methods are implemented
        assert plugin.initialize() is True
        assert plugin.execute()["status"] == "success"
        assert plugin.cleanup() is True
    
    def test_plugin_interface_not_implemented(self):
        """Test a class that doesn't implement the plugin interface."""
        # Create a class that doesn't implement the plugin interface
        class IncompletePlugin(PluginInterface):
            def initialize(self):
                return True
            
            # Missing execute method
            
            def cleanup(self):
                return True
        
        # Create an instance of the class
        plugin = IncompletePlugin()
        
        # Check that the missing method raises NotImplementedError
        with pytest.raises(NotImplementedError):
            plugin.execute()
    
    @patch("core.plugins.loader.PluginLoader._load_plugin_from_path")
    def test_plugin_dependencies(self, mock_load_plugin, sample_plugin_class):
        """Test plugin dependencies."""
        # Create a plugin with dependencies
        class PluginWithDependencies(sample_plugin_class):
            def __init__(self):
                super().__init__()
                self.dependencies = {
                    "core": ">=0.1.0",
                    "sample_plugin": "==1.0.0",
                }
        
        # Mock the plugin loading
        mock_load_plugin.side_effect = [sample_plugin_class, PluginWithDependencies]
        
        # Create a plugin loader
        loader = PluginLoader()
        
        # Load the plugins
        plugin1 = loader.load_plugin("sample_plugin")
        plugin2 = loader.load_plugin("plugin_with_dependencies")
        
        # Check the plugin dependencies
        assert plugin1.dependencies == {"core": ">=0.1.0"}
        assert plugin2.dependencies == {
            "core": ">=0.1.0",
            "sample_plugin": "==1.0.0",
        }
        
        # Check compatibility with both plugins loaded
        system_versions = {"core": "0.1.0"}
        plugin_versions = {"sample_plugin": "1.0.0"}
        
        compatibility_result = check_compatibility(
            plugin2,
            system_versions,
            plugin_versions
        )
        
        # Check the compatibility result
        assert compatibility_result["is_compatible"] is True
        assert len(compatibility_result["incompatibilities"]) == 0
        
        # Check compatibility with incompatible plugin version
        plugin_versions = {"sample_plugin": "2.0.0"}
        
        compatibility_result = check_compatibility(
            plugin2,
            system_versions,
            plugin_versions
        )
        
        # Check the compatibility result
        assert compatibility_result["is_compatible"] is False
        assert len(compatibility_result["incompatibilities"]) > 0
        assert any("sample_plugin" in incompatibility for incompatibility in compatibility_result["incompatibilities"])

