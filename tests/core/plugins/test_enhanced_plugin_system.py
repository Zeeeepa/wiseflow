"""
Tests for the enhanced plugin system.
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
from core.plugins.security import security_manager, SecurityViolation
from core.plugins.compatibility import compatibility_manager
from core.plugins.lifecycle import lifecycle_manager, LifecycleEvent
from core.plugins.resources import resource_manager, ResourceLimit, ResourceUsage
from core.plugins.isolation import isolation_manager
from core.plugins.validation import validation_manager
from core.plugins.dependency import dependency_resolver
from core.plugins.errors import (
    PluginError,
    PluginLoadError,
    PluginInitError,
    PluginValidationError,
    PluginSecurityError,
    PluginCompatibilityError,
    PluginDependencyError,
    PluginTimeoutError,
    PluginResourceError,
    PluginPermissionError
)
from core.event_system import EventType, Event


class TestEnhancedPluginSystem(unittest.TestCase):
    """Tests for the enhanced plugin system."""
    
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
            
            def initialize(self) -> bool:
                self.initialized = True
                return True
        
        class DependentPlugin(BasePlugin):
            name = "dependent_plugin"
            description = "Dependent plugin"
            version = "1.0.0"
            
            def __init__(self, config=None):
                super().__init__(config)
                self.metadata = PluginMetadata(
                    name=self.name,
                    version=self.version,
                    description=self.description,
                    dependencies={"test_plugin": ">=1.0.0"}
                )
            
            def initialize(self) -> bool:
                self.initialized = True
                return True
        
        class CircularPlugin1(BasePlugin):
            name = "circular_plugin1"
            description = "Circular plugin 1"
            version = "1.0.0"
            
            def __init__(self, config=None):
                super().__init__(config)
                self.metadata = PluginMetadata(
                    name=self.name,
                    version=self.version,
                    description=self.description,
                    dependencies={"circular_plugin2": ">=1.0.0"}
                )
            
            def initialize(self) -> bool:
                self.initialized = True
                return True
        
        class CircularPlugin2(BasePlugin):
            name = "circular_plugin2"
            description = "Circular plugin 2"
            version = "1.0.0"
            
            def __init__(self, config=None):
                super().__init__(config)
                self.metadata = PluginMetadata(
                    name=self.name,
                    version=self.version,
                    description=self.description,
                    dependencies={"circular_plugin1": ">=1.0.0"}
                )
            
            def initialize(self) -> bool:
                self.initialized = True
                return True
        
        # Store test plugin classes
        self.TestPlugin = TestPlugin
        self.DependentPlugin = DependentPlugin
        self.CircularPlugin1 = CircularPlugin1
        self.CircularPlugin2 = CircularPlugin2
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Remove temporary directory
        import shutil
        shutil.rmtree(self.plugins_dir)
    
    def test_dependency_resolution(self):
        """Test dependency resolution."""
        # Create plugin metadata
        plugins = {
            "plugin1": {
                "dependencies": {}
            },
            "plugin2": {
                "dependencies": {"plugin1": ">=1.0.0"}
            },
            "plugin3": {
                "dependencies": {"plugin2": ">=1.0.0"}
            },
            "plugin4": {
                "dependencies": {"plugin1": ">=1.0.0", "plugin3": ">=1.0.0"}
            }
        }
        
        # Resolve dependencies
        order = dependency_resolver.resolve_dependencies(plugins)
        
        # Check order
        self.assertEqual(len(order), 4)
        self.assertIn("plugin1", order)
        self.assertIn("plugin2", order)
        self.assertIn("plugin3", order)
        self.assertIn("plugin4", order)
        
        # Check that dependencies come before dependents
        self.assertLess(order.index("plugin1"), order.index("plugin2"))
        self.assertLess(order.index("plugin2"), order.index("plugin3"))
        self.assertLess(order.index("plugin1"), order.index("plugin4"))
        self.assertLess(order.index("plugin3"), order.index("plugin4"))
    
    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        # Create plugin metadata
        plugins = {
            "circular1": {
                "dependencies": {"circular2": ">=1.0.0"}
            },
            "circular2": {
                "dependencies": {"circular3": ">=1.0.0"}
            },
            "circular3": {
                "dependencies": {"circular1": ">=1.0.0"}
            }
        }
        
        # Resolve dependencies
        with self.assertRaises(PluginDependencyError):
            dependency_resolver.resolve_dependencies(plugins)
    
    def test_enhanced_security_checks(self):
        """Test enhanced security checks."""
        # Test secure code
        secure_code = """
def hello():
    return "Hello, world!"
"""
        is_secure, violations = security_manager.check_code_security(secure_code)
        self.assertTrue(is_secure)
        self.assertEqual(len(violations), 0)
        
        # Test insecure code
        insecure_code = """
import subprocess

def execute_command(cmd):
    return subprocess.check_output(cmd, shell=True)
"""
        is_secure, violations = security_manager.check_code_security(insecure_code)
        self.assertFalse(is_secure)
        self.assertGreater(len(violations), 0)
        
        # Test dangerous functions
        dangerous_code = """
def execute_code(code):
    return eval(code)
"""
        is_secure, violations = security_manager.check_code_security(dangerous_code)
        self.assertFalse(is_secure)
        self.assertGreater(len(violations), 0)
    
    def test_permission_system(self):
        """Test permission system."""
        # Set permissions
        security_manager.set_plugin_permissions("test_plugin", {"file_read", "network"})
        
        # Check permissions
        self.assertTrue(security_manager.check_permission("test_plugin", "file_read"))
        self.assertTrue(security_manager.check_permission("test_plugin", "network"))
        self.assertFalse(security_manager.check_permission("test_plugin", "file_write"))
        self.assertFalse(security_manager.check_permission("test_plugin", "process"))
        
        # Get permissions
        permissions = security_manager.get_plugin_permissions("test_plugin")
        self.assertEqual(permissions, {"file_read", "network"})
        
        # Get available permissions
        available_permissions = security_manager.get_available_permissions()
        self.assertIn("file_read", available_permissions)
        self.assertIn("network", available_permissions)
    
    def test_resource_monitoring(self):
        """Test resource monitoring."""
        # Create a plugin instance
        plugin = self.TestPlugin()
        
        # Set resource limit
        resource_manager.set_resource_limit(
            plugin.name,
            ResourceLimit(
                max_memory=1024 * 1024 * 10,  # 10 MB
                max_cpu_percent=10.0,
                max_file_handles=5,
                max_threads=2
            )
        )
        
        # Get resource limit
        limit = resource_manager.get_resource_limit(plugin.name)
        self.assertIsNotNone(limit)
        self.assertEqual(limit.max_memory, 1024 * 1024 * 10)
        self.assertEqual(limit.max_cpu_percent, 10.0)
        self.assertEqual(limit.max_file_handles, 5)
        self.assertEqual(limit.max_threads, 2)
        
        # Register resources
        file_resource = open(os.path.join(self.plugins_dir, "test.log"), "w")
        resource_manager.register_resource(plugin.name, "file", file_resource)
        
        thread_resource = threading.Thread(target=lambda: time.sleep(0.1))
        resource_manager.register_resource(plugin.name, "thread", thread_resource)
        
        # Get registered resources
        resources = resource_manager.get_registered_resources(plugin.name)
        self.assertIn("file", resources)
        self.assertIn("thread", resources)
        self.assertEqual(len(resources["file"]), 1)
        self.assertEqual(len(resources["thread"]), 1)
        
        # Update resource usage
        resource_manager._update_resource_usage()
        
        # Get resource usage
        usage = resource_manager.get_resource_usage(plugin.name)
        self.assertIsNotNone(usage)
        
        # Release resources
        resource_manager.release_resources(plugin.name)
        
        # Check that resources were released
        resources = resource_manager.get_registered_resources(plugin.name)
        self.assertEqual(len(resources), 0)
        
        # Close file
        file_resource.close()
    
    def test_error_types(self):
        """Test error types."""
        # Test PluginError
        error = PluginError("Test error", {"key": "value"}, ValueError("Inner error"))
        self.assertEqual(str(error), "Test error (caused by: ValueError: Inner error)")
        
        # Test PluginLoadError
        error = PluginLoadError("test_plugin", "Failed to load", {"file": "test.py"})
        self.assertEqual(str(error), "Error loading plugin 'test_plugin': Failed to load")
        self.assertEqual(error.plugin_name, "test_plugin")
        
        # Test PluginInitError
        error = PluginInitError("test_plugin", "Failed to initialize")
        self.assertEqual(str(error), "Error initializing plugin 'test_plugin': Failed to initialize")
        self.assertEqual(error.plugin_name, "test_plugin")
        
        # Test PluginValidationError
        error = PluginValidationError("test_plugin", ["Missing method", "Invalid signature"])
        self.assertEqual(str(error), "Plugin 'test_plugin' validation failed: Missing method, Invalid signature")
        self.assertEqual(error.plugin_name, "test_plugin")
        self.assertEqual(error.validation_errors, ["Missing method", "Invalid signature"])
        
        # Test PluginSecurityError
        error = PluginSecurityError("test_plugin", ["Restricted import", "Dangerous function"])
        self.assertEqual(str(error), "Plugin 'test_plugin' has security issues: Restricted import, Dangerous function")
        self.assertEqual(error.plugin_name, "test_plugin")
        self.assertEqual(error.security_issues, ["Restricted import", "Dangerous function"])
        
        # Test PluginCompatibilityError
        error = PluginCompatibilityError("test_plugin", "Incompatible with system version")
        self.assertEqual(str(error), "Plugin 'test_plugin' compatibility error: Incompatible with system version")
        self.assertEqual(error.plugin_name, "test_plugin")
        
        # Test PluginDependencyError
        error = PluginDependencyError("test_plugin", ["missing_plugin", "another_plugin"])
        self.assertEqual(str(error), "Plugin 'test_plugin' has missing dependencies: missing_plugin, another_plugin")
        self.assertEqual(error.plugin_name, "test_plugin")
        self.assertEqual(error.missing_dependencies, ["missing_plugin", "another_plugin"])
        
        # Test PluginTimeoutError
        error = PluginTimeoutError("test_plugin", "initialize", 30.0)
        self.assertEqual(str(error), "Plugin 'test_plugin' operation 'initialize' timed out after 30.0 seconds")
        self.assertEqual(error.plugin_name, "test_plugin")
        self.assertEqual(error.operation, "initialize")
        self.assertEqual(error.timeout, 30.0)
        
        # Test PluginResourceError
        error = PluginResourceError("test_plugin", "memory", "Exceeded limit")
        self.assertEqual(str(error), "Plugin 'test_plugin' resource error (memory): Exceeded limit")
        self.assertEqual(error.plugin_name, "test_plugin")
        self.assertEqual(error.resource_type, "memory")
        
        # Test PluginPermissionError
        error = PluginPermissionError("test_plugin", "file_write")
        self.assertEqual(str(error), "Plugin 'test_plugin' does not have permission: file_write")
        self.assertEqual(error.plugin_name, "test_plugin")
        self.assertEqual(error.permission, "file_write")


if __name__ == "__main__":
    unittest.main()

