"""
Custom exceptions for the plugin system.

This module defines custom exception classes for the plugin system.
"""

class PluginError(Exception):
    """Base class for all plugin-related exceptions."""
    pass


class PluginInitializationError(PluginError):
    """Exception raised when a plugin fails to initialize."""
    
    def __init__(self, plugin_name: str, message: str = None):
        self.plugin_name = plugin_name
        self.message = message or f"Failed to initialize plugin: {plugin_name}"
        super().__init__(self.message)


class PluginValidationError(PluginError):
    """Exception raised when a plugin fails validation."""
    
    def __init__(self, plugin_name: str, message: str = None):
        self.plugin_name = plugin_name
        self.message = message or f"Plugin validation failed: {plugin_name}"
        super().__init__(self.message)


class PluginInterfaceError(PluginError):
    """Exception raised when a plugin has an inconsistent interface."""
    
    def __init__(self, plugin_name: str, missing_methods: list = None, message: str = None):
        self.plugin_name = plugin_name
        self.missing_methods = missing_methods or []
        
        if message:
            self.message = message
        elif missing_methods:
            self.message = f"Plugin {plugin_name} is missing required methods: {', '.join(missing_methods)}"
        else:
            self.message = f"Plugin {plugin_name} has an inconsistent interface"
            
        super().__init__(self.message)


class PluginLoadError(PluginError):
    """Exception raised when a plugin fails to load."""
    
    def __init__(self, plugin_name: str, message: str = None, cause: Exception = None):
        self.plugin_name = plugin_name
        self.cause = cause
        
        if message:
            self.message = message
        elif cause:
            self.message = f"Failed to load plugin {plugin_name}: {str(cause)}"
        else:
            self.message = f"Failed to load plugin: {plugin_name}"
            
        super().__init__(self.message)


class PluginDependencyError(PluginError):
    """Exception raised when a plugin has missing dependencies."""
    
    def __init__(self, plugin_name: str, missing_dependencies: list = None, message: str = None):
        self.plugin_name = plugin_name
        self.missing_dependencies = missing_dependencies or []
        
        if message:
            self.message = message
        elif missing_dependencies:
            self.message = f"Plugin {plugin_name} has missing dependencies: {', '.join(missing_dependencies)}"
        else:
            self.message = f"Plugin {plugin_name} has missing dependencies"
            
        super().__init__(self.message)


class PluginResourceError(PluginError):
    """Exception raised when a plugin has resource management issues."""
    
    def __init__(self, plugin_name: str, resource_name: str = None, message: str = None):
        self.plugin_name = plugin_name
        self.resource_name = resource_name
        
        if message:
            self.message = message
        elif resource_name:
            self.message = f"Resource error in plugin {plugin_name}: {resource_name}"
        else:
            self.message = f"Resource error in plugin: {plugin_name}"
            
        super().__init__(self.message)

