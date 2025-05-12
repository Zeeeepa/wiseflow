"""
Configuration management module for crawl4ai.

This module provides a centralized configuration system for the crawl4ai package,
with support for environment variables, configuration files, and sensible defaults.
"""

import os
import json
from typing import Any, Dict, Optional, Union, List
import logging

from .errors import ConfigurationError

logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG = {
    # Browser configuration
    "browser": {
        "type": "chromium",
        "headless": True,
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/116.0.0.0 Safari/537.36",
        "viewport_width": 1080,
        "viewport_height": 600,
        "ignore_https_errors": True,
        "javascript_enabled": True,
    },
    
    # Crawler configuration
    "crawler": {
        "max_depth": 1,
        "max_pages": 10,
        "timeout": 60000,  # 60 seconds in milliseconds
        "retry_attempts": 3,
        "retry_delay": 5,  # seconds
        "memory_threshold_percent": 85.0,
        "memory_warning_percent": 75.0,
        "memory_check_interval": 10.0,  # seconds
        "cooldown_period": 300,  # 5 minutes in seconds
        "concurrency": 5,
    },
    
    # Cache configuration
    "cache": {
        "enabled": True,
        "ttl": 86400,  # 24 hours in seconds
        "max_size": 1000,  # Maximum number of items in cache
        "cleanup_interval": 3600,  # 1 hour in seconds
    },
    
    # Content processing configuration
    "content": {
        "word_count_threshold": 200,
        "image_description_min_word_threshold": 5,
        "image_score_threshold": 0.5,
        "screenshot_height_threshold": 10000,
    },
    
    # Logging configuration
    "logging": {
        "level": "INFO",
        "console": True,
        "file": True,
        "file_path": "",  # Will be set dynamically
    },
}

class ConfigManager:
    """
    Configuration manager for crawl4ai.
    
    This class provides methods for loading, accessing, and updating configuration
    values from various sources, including environment variables and configuration files.
    """
    
    def __init__(self, config_path: Optional[str] = None, base_directory: str = ""):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to a JSON configuration file.
            base_directory: Base directory for relative paths.
        """
        self.base_directory = base_directory
        self.config = DEFAULT_CONFIG.copy()
        
        # Set dynamic file path for logs
        if base_directory:
            self.config["logging"]["file_path"] = os.path.join(
                base_directory, ".crawl4ai", "crawler.log"
            )
        
        # Load configuration from file if provided
        if config_path:
            self.load_from_file(config_path)
        
        # Override with environment variables
        self.load_from_env()
    
    def load_from_file(self, config_path: str) -> None:
        """
        Load configuration from a JSON file.
        
        Args:
            config_path: Path to a JSON configuration file.
            
        Raises:
            ConfigurationError: If the file cannot be read or parsed.
        """
        try:
            with open(config_path, "r") as f:
                file_config = json.load(f)
                self._update_nested_dict(self.config, file_config)
            logger.info(f"Loaded configuration from {config_path}")
        except (IOError, json.JSONDecodeError) as e:
            raise ConfigurationError(
                f"Failed to load configuration from {config_path}", 
                original_error=e
            )
    
    def load_from_env(self) -> None:
        """
        Load configuration from environment variables.
        
        Environment variables should be prefixed with CRAWL4AI_ and use double underscores
        to indicate nesting. For example, CRAWL4AI_BROWSER__TYPE would override config["browser"]["type"].
        """
        prefix = "CRAWL4AI_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and split by double underscore
                config_key = key[len(prefix):].lower()
                parts = config_key.split("__")
                
                # Convert value to appropriate type
                if value.lower() in ("true", "false"):
                    value = value.lower() == "true"
                elif value.isdigit():
                    value = int(value)
                elif value.replace(".", "", 1).isdigit() and value.count(".") == 1:
                    value = float(value)
                
                # Update config
                current = self.config
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        current[part] = value
                    else:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
    
    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            *keys: Nested keys to access the configuration value.
            default: Default value to return if the key is not found.
            
        Returns:
            The configuration value, or the default if not found.
        """
        current = self.config
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        return current
    
    def set(self, value: Any, *keys: str) -> None:
        """
        Set a configuration value.
        
        Args:
            value: The value to set.
            *keys: Nested keys to access the configuration value.
            
        Raises:
            ConfigurationError: If the keys are invalid.
        """
        if not keys:
            raise ConfigurationError("No keys provided")
        
        current = self.config
        for i, key in enumerate(keys):
            if i == len(keys) - 1:
                current[key] = value
            else:
                if key not in current:
                    current[key] = {}
                elif not isinstance(current[key], dict):
                    current[key] = {}
                current = current[key]
    
    def _update_nested_dict(self, target: Dict, source: Dict) -> None:
        """
        Update a nested dictionary with values from another dictionary.
        
        Args:
            target: The dictionary to update.
            source: The dictionary to update from.
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._update_nested_dict(target[key], value)
            else:
                target[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the configuration to a dictionary.
        
        Returns:
            A dictionary representation of the configuration.
        """
        return self.config.copy()
    
    def get_browser_config(self) -> Dict[str, Any]:
        """
        Get the browser configuration.
        
        Returns:
            A dictionary containing browser configuration.
        """
        return self.get("browser", default={})
    
    def get_crawler_config(self) -> Dict[str, Any]:
        """
        Get the crawler configuration.
        
        Returns:
            A dictionary containing crawler configuration.
        """
        return self.get("crawler", default={})
    
    def get_cache_config(self) -> Dict[str, Any]:
        """
        Get the cache configuration.
        
        Returns:
            A dictionary containing cache configuration.
        """
        return self.get("cache", default={})
    
    def get_content_config(self) -> Dict[str, Any]:
        """
        Get the content processing configuration.
        
        Returns:
            A dictionary containing content processing configuration.
        """
        return self.get("content", default={})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Get the logging configuration.
        
        Returns:
            A dictionary containing logging configuration.
        """
        return self.get("logging", default={})

