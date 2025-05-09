"""
Plugin security module for Wiseflow.

This module provides security utilities for the plugin system.
"""

import os
import sys
import inspect
import importlib
import hashlib
import logging
import ast
import re
from typing import Dict, Any, Optional, Tuple, List, Set, Union

logger = logging.getLogger(__name__)

class SecurityViolation:
    """Security violation information."""
    
    def __init__(self, violation_type: str, description: str, severity: str = "medium"):
        """
        Initialize security violation.
        
        Args:
            violation_type: Type of violation
            description: Description of the violation
            severity: Severity level (low, medium, high, critical)
        """
        self.violation_type = violation_type
        self.description = description
        self.severity = severity
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return {
            "violation_type": self.violation_type,
            "description": self.description,
            "severity": self.severity
        }

class PluginSecurityManager:
    """
    Security manager for plugins.
    
    This class provides functionality to validate and secure plugins.
    """
    
    def __init__(self):
        """Initialize the plugin security manager."""
        # Default allowed modules
        self.allowed_modules = set([
            "os", "sys", "time", "datetime", "json", "logging", 
            "math", "random", "re", "collections", "itertools",
            "functools", "typing", "enum", "abc", "copy", "uuid"
        ])
        
        # Default restricted modules
        self.restricted_modules = set([
            "subprocess", "socket", "shutil", "pickle", "marshal",
            "multiprocessing", "ctypes", "importlib"
        ])
        
        # Dangerous function patterns
        self.dangerous_functions = [
            r"eval\s*\(",
            r"exec\s*\(",
            r"__import__\s*\(",
            r"globals\(\)",
            r"locals\(\)",
            r"getattr\s*\(.+?,\s*['\"]__",
            r"setattr\s*\(.+?,\s*['\"]__"
        ]
        
        # Plugin file hashes
        self.file_hashes: Dict[str, str] = {}
        
        # Security enabled flag
        self.security_enabled = True
        
        # Permission system
        self.plugin_permissions: Dict[str, Set[str]] = {}
        self.available_permissions = {
            "file_read": "Read files",
            "file_write": "Write files",
            "network": "Access network",
            "process": "Create processes",
            "system": "Access system information",
            "database": "Access database"
        }
    
    def calculate_file_hash(self, file_path: str) -> Optional[str]:
        """
        Calculate a hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hash string or None if file not found
        """
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            return file_hash
        except Exception as e:
            logger.warning(f"Error calculating file hash for {file_path}: {e}")
            return None
    
    def verify_file_hash(self, file_path: str, expected_hash: Optional[str] = None) -> bool:
        """
        Verify a file hash.
        
        Args:
            file_path: Path to the file
            expected_hash: Expected hash value
            
        Returns:
            True if hash matches or no expected hash, False otherwise
        """
        if not self.security_enabled:
            return True
        
        if not expected_hash:
            # If no expected hash, use stored hash
            expected_hash = self.file_hashes.get(file_path)
            
            # If no stored hash, calculate and store it
            if not expected_hash:
                expected_hash = self.calculate_file_hash(file_path)
                if expected_hash:
                    self.file_hashes[file_path] = expected_hash
                return True
        
        # Calculate current hash
        current_hash = self.calculate_file_hash(file_path)
        
        # Compare hashes
        if current_hash and expected_hash:
            return current_hash == expected_hash
        
        return True
    
    def check_module_imports(self, module: Any) -> Tuple[bool, str]:
        """
        Check module imports for security issues.
        
        Args:
            module: Module to check
            
        Returns:
            Tuple of (is_secure, reason)
        """
        if not self.security_enabled:
            return True, ""
        
        try:
            # Check imported modules
            for name, obj in inspect.getmembers(module):
                if inspect.ismodule(obj):
                    module_name = obj.__name__.split('.')[0]
                    if module_name in self.restricted_modules:
                        return False, f"Module imports restricted module: {module_name}"
            
            return True, ""
        except Exception as e:
            logger.warning(f"Error checking module imports: {e}")
            return False, f"Import check error: {str(e)}"
    
    def check_dangerous_attributes(self, module: Any) -> Tuple[bool, str]:
        """
        Check for dangerous attributes in a module.
        
        Args:
            module: Module to check
            
        Returns:
            Tuple of (is_secure, reason)
        """
        if not self.security_enabled:
            return True, ""
        
        try:
            # Check for potentially dangerous attributes
            for name, obj in inspect.getmembers(module):
                if name.startswith('__') and name.endswith('__') and name not in ['__name__', '__doc__', '__file__']:
                    if callable(obj):
                        return False, f"Module contains potentially dangerous dunder method: {name}"
            
            return True, ""
        except Exception as e:
            logger.warning(f"Error checking dangerous attributes: {e}")
            return False, f"Attribute check error: {str(e)}"
    
    def check_plugin_security(self, module: Any) -> Tuple[bool, str]:
        """
        Check plugin security.
        
        Args:
            module: Plugin module
            
        Returns:
            Tuple of (is_secure, reason)
        """
        if not self.security_enabled:
            return True, ""
        
        # Check module imports
        is_secure, reason = self.check_module_imports(module)
        if not is_secure:
            return False, reason
        
        # Check dangerous attributes
        is_secure, reason = self.check_dangerous_attributes(module)
        if not is_secure:
            return False, reason
        
        return True, ""
    
    def check_code_security(self, source_code: str) -> Tuple[bool, List[SecurityViolation]]:
        """
        Check source code for security issues.
        
        Args:
            source_code: Source code to check
            
        Returns:
            Tuple of (is_secure, violations)
        """
        if not self.security_enabled:
            return True, []
        
        violations = []
        
        try:
            # Parse the source code
            tree = ast.parse(source_code)
            
            # Check for dangerous imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        module_name = name.name.split('.')[0]
                        if module_name in self.restricted_modules:
                            violations.append(SecurityViolation(
                                "restricted_import",
                                f"Importing restricted module: {module_name}",
                                "high"
                            ))
                
                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module.split('.')[0] if node.module else ""
                    if module_name in self.restricted_modules:
                        violations.append(SecurityViolation(
                            "restricted_import",
                            f"Importing from restricted module: {module_name}",
                            "high"
                        ))
                
                # Check for dangerous function calls
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name in ["eval", "exec", "__import__"]:
                            violations.append(SecurityViolation(
                                "dangerous_function",
                                f"Using dangerous function: {func_name}",
                                "critical"
                            ))
            
            # Check for dangerous patterns using regex
            for pattern in self.dangerous_functions:
                matches = re.findall(pattern, source_code)
                if matches:
                    violations.append(SecurityViolation(
                        "dangerous_pattern",
                        f"Dangerous code pattern detected: {pattern}",
                        "high"
                    ))
            
            return len(violations) == 0, violations
        
        except Exception as e:
            logger.warning(f"Error checking code security: {e}")
            violations.append(SecurityViolation(
                "security_check_error",
                f"Error checking code security: {str(e)}",
                "medium"
            ))
            return False, violations
    
    def set_security_enabled(self, enabled: bool) -> None:
        """
        Enable or disable security checks.
        
        Args:
            enabled: Whether security checks should be enabled
        """
        self.security_enabled = enabled
        logger.info(f"Plugin security checks {'enabled' if enabled else 'disabled'}")
    
    def add_allowed_module(self, module_name: str) -> None:
        """
        Add a module to the allowed modules list.
        
        Args:
            module_name: Name of the module to allow
        """
        self.allowed_modules.add(module_name)
        if module_name in self.restricted_modules:
            self.restricted_modules.remove(module_name)
    
    def add_restricted_module(self, module_name: str) -> None:
        """
        Add a module to the restricted modules list.
        
        Args:
            module_name: Name of the module to restrict
        """
        self.restricted_modules.add(module_name)
        if module_name in self.allowed_modules:
            self.allowed_modules.remove(module_name)
    
    def get_allowed_modules(self) -> Set[str]:
        """
        Get the set of allowed modules.
        
        Returns:
            Set of allowed module names
        """
        return self.allowed_modules.copy()
    
    def get_restricted_modules(self) -> Set[str]:
        """
        Get the set of restricted modules.
        
        Returns:
            Set of restricted module names
        """
        return self.restricted_modules.copy()
    
    def set_plugin_permissions(self, plugin_name: str, permissions: Set[str]) -> None:
        """
        Set permissions for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            permissions: Set of permission names
        """
        # Validate permissions
        invalid_permissions = permissions - set(self.available_permissions.keys())
        if invalid_permissions:
            logger.warning(f"Invalid permissions for plugin {plugin_name}: {invalid_permissions}")
            permissions = permissions - invalid_permissions
        
        self.plugin_permissions[plugin_name] = permissions
        logger.info(f"Set permissions for plugin {plugin_name}: {permissions}")
    
    def check_permission(self, plugin_name: str, permission: str) -> bool:
        """
        Check if a plugin has a specific permission.
        
        Args:
            plugin_name: Name of the plugin
            permission: Permission to check
            
        Returns:
            True if the plugin has the permission, False otherwise
        """
        if not self.security_enabled:
            return True
        
        if plugin_name not in self.plugin_permissions:
            return False
        
        return permission in self.plugin_permissions[plugin_name]
    
    def get_plugin_permissions(self, plugin_name: str) -> Set[str]:
        """
        Get permissions for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Set of permission names
        """
        return self.plugin_permissions.get(plugin_name, set())
    
    def get_available_permissions(self) -> Dict[str, str]:
        """
        Get available permissions.
        
        Returns:
            Dictionary mapping permission names to descriptions
        """
        return self.available_permissions.copy()

# Global security manager instance
security_manager = PluginSecurityManager()
