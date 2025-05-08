"""
Plugin compatibility module for Wiseflow.

This module provides version compatibility utilities for the plugin system.
"""

import logging
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

class VersionCompatibilityManager:
    """
    Version compatibility manager for plugins.
    
    This class provides functionality to check version compatibility between
    plugins and the system.
    """
    
    def __init__(self, system_version: str = "4.0.0"):
        """
        Initialize the version compatibility manager.
        
        Args:
            system_version: Current system version
        """
        self.system_version = system_version
    
    def check_version_compatibility(
        self,
        plugin_version: str,
        min_system_version: Optional[str] = None,
        max_system_version: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Check if a plugin version is compatible with the system version.
        
        Args:
            plugin_version: Plugin version
            min_system_version: Minimum system version required
            max_system_version: Maximum system version supported
            
        Returns:
            Tuple of (is_compatible, reason)
        """
        try:
            from packaging import version
            
            # Check minimum system version
            if min_system_version:
                if version.parse(self.system_version) < version.parse(min_system_version):
                    return False, f"Plugin requires system version {min_system_version} or higher"
            
            # Check maximum system version
            if max_system_version:
                if version.parse(self.system_version) > version.parse(max_system_version):
                    return False, f"Plugin requires system version {max_system_version} or lower"
            
            return True, ""
        except ImportError:
            logger.warning("packaging module not available, skipping version compatibility check")
            return True, ""
        except Exception as e:
            logger.warning(f"Error checking version compatibility: {e}")
            return True, ""  # Default to compatible if check fails
    
    def check_dependency_compatibility(
        self,
        dependencies: Dict[str, str],
        available_plugins: Dict[str, str]
    ) -> Tuple[bool, List[str]]:
        """
        Check if plugin dependencies are compatible.
        
        Args:
            dependencies: Dictionary of plugin dependencies (name -> version requirement)
            available_plugins: Dictionary of available plugins (name -> version)
            
        Returns:
            Tuple of (is_compatible, missing_dependencies)
        """
        try:
            from packaging import version
            from packaging.requirements import Requirement
            
            missing_dependencies = []
            
            for dep_name, dep_req in dependencies.items():
                # Check if dependency is available
                if dep_name not in available_plugins:
                    missing_dependencies.append(f"{dep_name} (not found)")
                    continue
                
                # Check version compatibility
                available_version = available_plugins[dep_name]
                requirement = Requirement(f"{dep_name}{dep_req}")
                
                if version.parse(available_version) not in requirement.specifier:
                    missing_dependencies.append(f"{dep_name} (required: {dep_req}, available: {available_version})")
            
            return len(missing_dependencies) == 0, missing_dependencies
        except ImportError:
            logger.warning("packaging module not available, skipping dependency compatibility check")
            return True, []
        except Exception as e:
            logger.warning(f"Error checking dependency compatibility: {e}")
            return True, []  # Default to compatible if check fails
    
    def set_system_version(self, version: str) -> None:
        """
        Set the system version.
        
        Args:
            version: System version string
        """
        self.system_version = version
        logger.info(f"System version set to {version} for plugin compatibility checks")
    
    def get_system_version(self) -> str:
        """
        Get the system version.
        
        Returns:
            System version string
        """
        return self.system_version

# Global compatibility manager instance
compatibility_manager = VersionCompatibilityManager()

