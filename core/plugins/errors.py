"""
Plugin error types for Wiseflow.

This module defines error types for the plugin system.
"""

from typing import Dict, Any, Optional


class PluginError(Exception):
    """Base class for all plugin errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        """
        Initialize plugin error.
        
        Args:
            message: Error message
            context: Error context information
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.cause = cause
    
    def __str__(self) -> str:
        """Get string representation."""
        if self.cause:
            return f"{self.message} (caused by: {type(self.cause).__name__}: {str(self.cause)})"
        return self.message


class PluginLoadError(PluginError):
    """Error loading a plugin."""
    
    def __init__(self, plugin_name: str, message: str, context: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        """
        Initialize plugin load error.
        
        Args:
            plugin_name: Name of the plugin
            message: Error message
            context: Error context information
            cause: Original exception that caused this error
        """
        super().__init__(f"Error loading plugin '{plugin_name}': {message}", context, cause)
        self.plugin_name = plugin_name


class PluginInitError(PluginError):
    """Error initializing a plugin."""
    
    def __init__(self, plugin_name: str, message: str, context: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        """
        Initialize plugin initialization error.
        
        Args:
            plugin_name: Name of the plugin
            message: Error message
            context: Error context information
            cause: Original exception that caused this error
        """
        super().__init__(f"Error initializing plugin '{plugin_name}': {message}", context, cause)
        self.plugin_name = plugin_name


class PluginValidationError(PluginError):
    """Error validating a plugin."""
    
    def __init__(self, plugin_name: str, validation_errors: list, context: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin validation error.
        
        Args:
            plugin_name: Name of the plugin
            validation_errors: List of validation error messages
            context: Error context information
        """
        message = f"Plugin '{plugin_name}' validation failed: {', '.join(validation_errors)}"
        super().__init__(message, context)
        self.plugin_name = plugin_name
        self.validation_errors = validation_errors


class PluginSecurityError(PluginError):
    """Security error in a plugin."""
    
    def __init__(self, plugin_name: str, security_issues: list, context: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin security error.
        
        Args:
            plugin_name: Name of the plugin
            security_issues: List of security issue descriptions
            context: Error context information
        """
        message = f"Plugin '{plugin_name}' has security issues: {', '.join(security_issues)}"
        super().__init__(message, context)
        self.plugin_name = plugin_name
        self.security_issues = security_issues


class PluginCompatibilityError(PluginError):
    """Compatibility error in a plugin."""
    
    def __init__(self, plugin_name: str, message: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin compatibility error.
        
        Args:
            plugin_name: Name of the plugin
            message: Error message
            context: Error context information
        """
        super().__init__(f"Plugin '{plugin_name}' compatibility error: {message}", context)
        self.plugin_name = plugin_name


class PluginDependencyError(PluginError):
    """Dependency error in a plugin."""
    
    def __init__(self, plugin_name: str, missing_dependencies: list, context: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin dependency error.
        
        Args:
            plugin_name: Name of the plugin
            missing_dependencies: List of missing dependencies
            context: Error context information
        """
        message = f"Plugin '{plugin_name}' has missing dependencies: {', '.join(missing_dependencies)}"
        super().__init__(message, context)
        self.plugin_name = plugin_name
        self.missing_dependencies = missing_dependencies


class PluginTimeoutError(PluginError):
    """Timeout error in a plugin operation."""
    
    def __init__(self, plugin_name: str, operation: str, timeout: float, context: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin timeout error.
        
        Args:
            plugin_name: Name of the plugin
            operation: Operation that timed out
            timeout: Timeout value in seconds
            context: Error context information
        """
        message = f"Plugin '{plugin_name}' operation '{operation}' timed out after {timeout} seconds"
        super().__init__(message, context)
        self.plugin_name = plugin_name
        self.operation = operation
        self.timeout = timeout


class PluginResourceError(PluginError):
    """Resource error in a plugin."""
    
    def __init__(self, plugin_name: str, resource_type: str, message: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin resource error.
        
        Args:
            plugin_name: Name of the plugin
            resource_type: Type of resource
            message: Error message
            context: Error context information
        """
        super().__init__(f"Plugin '{plugin_name}' resource error ({resource_type}): {message}", context)
        self.plugin_name = plugin_name
        self.resource_type = resource_type


class PluginPermissionError(PluginError):
    """Permission error in a plugin."""
    
    def __init__(self, plugin_name: str, permission: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin permission error.
        
        Args:
            plugin_name: Name of the plugin
            permission: Permission that was denied
            context: Error context information
        """
        message = f"Plugin '{plugin_name}' does not have permission: {permission}"
        super().__init__(message, context)
        self.plugin_name = plugin_name
        self.permission = permission

