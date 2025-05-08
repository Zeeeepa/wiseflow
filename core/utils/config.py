"""
Configuration utility for WiseFlow.

This module provides functions for loading and accessing configuration settings
from environment variables and configuration files.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "project_dir": os.environ.get("PROJECT_DIR", ""),
    "primary_model": os.environ.get("PRIMARY_MODEL", "gpt-3.5-turbo"),
    "log_level": os.environ.get("LOG_LEVEL", "INFO"),
    "cache_enabled": os.environ.get("CACHE_ENABLED", "true").lower() == "true",
    "max_connections": int(os.environ.get("MAX_CONNECTIONS", "10")),
    "memory_threshold_percent": float(os.environ.get("MEMORY_THRESHOLD_PERCENT", "85.0")),
    "memory_warning_percent": float(os.environ.get("MEMORY_WARNING_PERCENT", "75.0")),
    "retry_count": int(os.environ.get("RETRY_COUNT", "3")),
    "retry_delay": int(os.environ.get("RETRY_DELAY", "5")),
}

# Global configuration
_config = None

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from a file and/or environment variables.
    
    Args:
        config_path: Path to the configuration file (optional)
        
    Returns:
        Dictionary containing configuration settings
    """
    global _config
    
    # Start with default configuration
    config = DEFAULT_CONFIG.copy()
    
    # Load configuration from file if provided
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                config.update(file_config)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration from {config_path}: {e}")
    
    # Override with environment variables
    for key in config:
        env_var = key.upper()
        if env_var in os.environ:
            # Convert environment variable to appropriate type
            env_value = os.environ[env_var]
            if isinstance(config[key], bool):
                config[key] = env_value.lower() == "true"
            elif isinstance(config[key], int):
                try:
                    config[key] = int(env_value)
                except ValueError:
                    logger.warning(f"Invalid integer value for {env_var}: {env_value}")
            elif isinstance(config[key], float):
                try:
                    config[key] = float(env_value)
                except ValueError:
                    logger.warning(f"Invalid float value for {env_var}: {env_value}")
            else:
                config[key] = env_value
    
    # Store configuration globally
    _config = config
    
    return config

def get_config() -> Dict[str, Any]:
    """
    Get the current configuration.
    
    Returns:
        Dictionary containing configuration settings
    """
    global _config
    
    # Load configuration if not already loaded
    if _config is None:
        config_path = os.environ.get("CONFIG_PATH")
        _config = load_config(config_path)
    
    return _config

def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get a specific configuration value.
    
    Args:
        key: Configuration key
        default: Default value to return if key is not found
        
    Returns:
        Configuration value
    """
    config = get_config()
    return config.get(key, default)

