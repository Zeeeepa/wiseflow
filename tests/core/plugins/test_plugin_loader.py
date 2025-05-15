"""
Tests for the plugin loader.
"""

import pytest
from unittest.mock import patch, MagicMock

from core.plugins.loader import PluginLoader
from core.plugins.base import PluginBase

class TestPluginBase:
    """Test the plugin base class."""
    
    def test_plugin_base_initialization(self):
        """Test initializing the plugin base class."""
        plugin = PluginBase(name="test-plugin", version="1.0.0")
        assert plugin.name == "test-plugin"
        assert plugin.version == "1.0.0"
        assert plugin.enabled is True
    
    def test_plugin_base_disable(self):
        """Test disabling a plugin."""
        plugin = PluginBase(name="test-plugin", version="1.0.0")
        plugin.disable()
        assert plugin.enabled is False
    
    def test_plugin_base_enable(self):
        """Test enabling a plugin."""
        plugin = PluginBase(name="test-plugin", version="1.0.0")
        plugin.disable()
        assert plugin.enabled is False
        plugin.enable()
        assert plugin.enabled is True
    
    def test_plugin_base_get_info(self):
        """Test getting plugin info."""
        plugin = PluginBase(name="test-plugin", version="1.0.0")
        info = plugin.get_info()
        assert info["name"] == "test-plugin"
        assert info["version"] == "1.0.0"
        assert info["enabled"] is True

class TestPluginLoader:
    """Test the plugin loader."""
    
    @pytest.fixture
    def plugin_loader(self):
        """Create a plugin loader for testing."""
        return PluginLoader()
    
    def test_plugin_loader_initialization(self, plugin_loader):
        """Test initializing the plugin loader."""
        assert plugin_loader.plugins == {}
    
    def test_register_plugin(self, plugin_loader):
        """Test registering a plugin."""
        plugin = PluginBase(name="test-plugin", version="1.0.0")
        plugin_loader.register_plugin(plugin)
        assert "test-plugin" in plugin_loader.plugins
        assert plugin_loader.plugins["test-plugin"] == plugin
    
    def test_register_duplicate_plugin(self, plugin_loader):
        """Test registering a duplicate plugin."""
        plugin1 = PluginBase(name="test-plugin", version="1.0.0")
        plugin2 = PluginBase(name="test-plugin", version="2.0.0")
        plugin_loader.register_plugin(plugin1)
        with pytest.raises(ValueError) as excinfo:
            plugin_loader.register_plugin(plugin2)
        assert "Plugin with name 'test-plugin' already registered" in str(excinfo.value)
    
    def test_get_plugin(self, plugin_loader):
        """Test getting a plugin."""
        plugin = PluginBase(name="test-plugin", version="1.0.0")
        plugin_loader.register_plugin(plugin)
        retrieved_plugin = plugin_loader.get_plugin("test-plugin")
        assert retrieved_plugin == plugin
    
    def test_get_nonexistent_plugin(self, plugin_loader):
        """Test getting a nonexistent plugin."""
        with pytest.raises(KeyError) as excinfo:
            plugin_loader.get_plugin("nonexistent-plugin")
        assert "Plugin 'nonexistent-plugin' not found" in str(excinfo.value)
    
    def test_get_all_plugins(self, plugin_loader):
        """Test getting all plugins."""
        plugin1 = PluginBase(name="test-plugin-1", version="1.0.0")
        plugin2 = PluginBase(name="test-plugin-2", version="1.0.0")
        plugin_loader.register_plugin(plugin1)
        plugin_loader.register_plugin(plugin2)
        plugins = plugin_loader.get_all_plugins()
        assert len(plugins) == 2
        assert "test-plugin-1" in plugins
        assert "test-plugin-2" in plugins
        assert plugins["test-plugin-1"] == plugin1
        assert plugins["test-plugin-2"] == plugin2
    
    def test_disable_plugin(self, plugin_loader):
        """Test disabling a plugin."""
        plugin = PluginBase(name="test-plugin", version="1.0.0")
        plugin_loader.register_plugin(plugin)
        plugin_loader.disable_plugin("test-plugin")
        assert plugin.enabled is False
    
    def test_disable_nonexistent_plugin(self, plugin_loader):
        """Test disabling a nonexistent plugin."""
        with pytest.raises(KeyError) as excinfo:
            plugin_loader.disable_plugin("nonexistent-plugin")
        assert "Plugin 'nonexistent-plugin' not found" in str(excinfo.value)
    
    def test_enable_plugin(self, plugin_loader):
        """Test enabling a plugin."""
        plugin = PluginBase(name="test-plugin", version="1.0.0")
        plugin.disable()
        plugin_loader.register_plugin(plugin)
        plugin_loader.enable_plugin("test-plugin")
        assert plugin.enabled is True
    
    def test_enable_nonexistent_plugin(self, plugin_loader):
        """Test enabling a nonexistent plugin."""
        with pytest.raises(KeyError) as excinfo:
            plugin_loader.enable_plugin("nonexistent-plugin")
        assert "Plugin 'nonexistent-plugin' not found" in str(excinfo.value)
    
    def test_get_enabled_plugins(self, plugin_loader):
        """Test getting enabled plugins."""
        plugin1 = PluginBase(name="test-plugin-1", version="1.0.0")
        plugin2 = PluginBase(name="test-plugin-2", version="1.0.0")
        plugin2.disable()
        plugin_loader.register_plugin(plugin1)
        plugin_loader.register_plugin(plugin2)
        enabled_plugins = plugin_loader.get_enabled_plugins()
        assert len(enabled_plugins) == 1
        assert "test-plugin-1" in enabled_plugins
        assert "test-plugin-2" not in enabled_plugins
        assert enabled_plugins["test-plugin-1"] == plugin1
    
    def test_get_disabled_plugins(self, plugin_loader):
        """Test getting disabled plugins."""
        plugin1 = PluginBase(name="test-plugin-1", version="1.0.0")
        plugin2 = PluginBase(name="test-plugin-2", version="1.0.0")
        plugin2.disable()
        plugin_loader.register_plugin(plugin1)
        plugin_loader.register_plugin(plugin2)
        disabled_plugins = plugin_loader.get_disabled_plugins()
        assert len(disabled_plugins) == 1
        assert "test-plugin-1" not in disabled_plugins
        assert "test-plugin-2" in disabled_plugins
        assert disabled_plugins["test-plugin-2"] == plugin2

