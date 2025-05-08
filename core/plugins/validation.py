"""
Plugin validation module for Wiseflow.

This module provides utilities for validating plugins.
"""

import logging
import inspect
from typing import Dict, Any, Optional, List, Type, Tuple, Set

from core.plugins.base import BasePlugin, ConnectorPlugin, ProcessorPlugin, AnalyzerPlugin

logger = logging.getLogger(__name__)

class PluginValidationManager:
    """
    Plugin validation manager.
    
    This class provides functionality to validate plugins.
    """
    
    def __init__(self):
        """Initialize the plugin validation manager."""
        self.validation_enabled = True
        self.required_methods: Dict[Type, Set[str]] = {
            BasePlugin: {"initialize", "shutdown", "validate_config"},
            ConnectorPlugin: {"connect", "fetch_data", "disconnect"},
            ProcessorPlugin: {"process"},
            AnalyzerPlugin: {"analyze"}
        }
        self.required_attributes: Dict[Type, Set[str]] = {
            BasePlugin: {"name", "version", "description"},
            ConnectorPlugin: set(),
            ProcessorPlugin: set(),
            AnalyzerPlugin: set()
        }
    
    def set_validation_enabled(self, enabled: bool) -> None:
        """
        Enable or disable plugin validation.
        
        Args:
            enabled: Whether validation should be enabled
        """
        self.validation_enabled = enabled
        logger.info(f"Plugin validation {'enabled' if enabled else 'disabled'}")
    
    def validate_plugin_class(self, plugin_class: Type[BasePlugin]) -> Tuple[bool, List[str]]:
        """
        Validate a plugin class.
        
        Args:
            plugin_class: Plugin class to validate
            
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        if not self.validation_enabled:
            return True, []
        
        validation_errors = []
        
        # Determine the base class to validate against
        base_class = None
        if issubclass(plugin_class, ConnectorPlugin):
            base_class = ConnectorPlugin
        elif issubclass(plugin_class, ProcessorPlugin):
            base_class = ProcessorPlugin
        elif issubclass(plugin_class, AnalyzerPlugin):
            base_class = AnalyzerPlugin
        else:
            base_class = BasePlugin
        
        # Validate required methods
        self._validate_required_methods(plugin_class, base_class, validation_errors)
        
        # Validate required attributes
        self._validate_required_attributes(plugin_class, base_class, validation_errors)
        
        # Validate method signatures
        self._validate_method_signatures(plugin_class, base_class, validation_errors)
        
        return len(validation_errors) == 0, validation_errors
    
    def _validate_required_methods(
        self,
        plugin_class: Type[BasePlugin],
        base_class: Type[BasePlugin],
        validation_errors: List[str]
    ) -> None:
        """
        Validate that a plugin class has all required methods.
        
        Args:
            plugin_class: Plugin class to validate
            base_class: Base class to validate against
            validation_errors: List to add validation errors to
        """
        # Get required methods for this base class and all parent base classes
        required_methods = set()
        for cls in self.required_methods:
            if issubclass(base_class, cls):
                required_methods.update(self.required_methods[cls])
        
        # Check that all required methods are implemented
        for method_name in required_methods:
            if not hasattr(plugin_class, method_name):
                validation_errors.append(f"Missing required method: {method_name}")
                continue
            
            method = getattr(plugin_class, method_name)
            if not callable(method):
                validation_errors.append(f"Required method {method_name} is not callable")
    
    def _validate_required_attributes(
        self,
        plugin_class: Type[BasePlugin],
        base_class: Type[BasePlugin],
        validation_errors: List[str]
    ) -> None:
        """
        Validate that a plugin class has all required attributes.
        
        Args:
            plugin_class: Plugin class to validate
            base_class: Base class to validate against
            validation_errors: List to add validation errors to
        """
        # Get required attributes for this base class and all parent base classes
        required_attributes = set()
        for cls in self.required_attributes:
            if issubclass(base_class, cls):
                required_attributes.update(self.required_attributes[cls])
        
        # Check that all required attributes are present
        for attr_name in required_attributes:
            if not hasattr(plugin_class, attr_name):
                validation_errors.append(f"Missing required attribute: {attr_name}")
    
    def _validate_method_signatures(
        self,
        plugin_class: Type[BasePlugin],
        base_class: Type[BasePlugin],
        validation_errors: List[str]
    ) -> None:
        """
        Validate that plugin method signatures match the base class.
        
        Args:
            plugin_class: Plugin class to validate
            base_class: Base class to validate against
            validation_errors: List to add validation errors to
        """
        # Get methods to validate
        methods_to_validate = set()
        for cls in self.required_methods:
            if issubclass(base_class, cls):
                methods_to_validate.update(self.required_methods[cls])
        
        # Check method signatures
        for method_name in methods_to_validate:
            if not hasattr(plugin_class, method_name) or not hasattr(base_class, method_name):
                continue
            
            plugin_method = getattr(plugin_class, method_name)
            base_method = getattr(base_class, method_name)
            
            if not callable(plugin_method) or not callable(base_method):
                continue
            
            # Get method signatures
            plugin_sig = inspect.signature(plugin_method)
            base_sig = inspect.signature(base_method)
            
            # Check parameter count
            plugin_params = list(plugin_sig.parameters.values())
            base_params = list(base_sig.parameters.values())
            
            # Skip 'self' parameter
            if len(plugin_params) > 0 and plugin_params[0].name == 'self':
                plugin_params = plugin_params[1:]
            if len(base_params) > 0 and base_params[0].name == 'self':
                base_params = base_params[1:]
            
            # Check required parameters
            for i, base_param in enumerate(base_params):
                if base_param.default == inspect.Parameter.empty:
                    # This is a required parameter
                    if i >= len(plugin_params) or plugin_params[i].default != inspect.Parameter.empty:
                        validation_errors.append(
                            f"Method {method_name} is missing required parameter: {base_param.name}"
                        )
            
            # Check return type annotation
            if base_sig.return_annotation != inspect.Signature.empty:
                if plugin_sig.return_annotation == inspect.Signature.empty:
                    validation_errors.append(
                        f"Method {method_name} is missing return type annotation"
                    )
                elif plugin_sig.return_annotation != base_sig.return_annotation:
                    validation_errors.append(
                        f"Method {method_name} has incorrect return type annotation: "
                        f"expected {base_sig.return_annotation}, got {plugin_sig.return_annotation}"
                    )

# Global validation manager instance
validation_manager = PluginValidationManager()

