"""
Configuration module for WiseFlow.

This module provides functions for loading, validating, and accessing configuration settings.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

# Default configuration values
DEFAULT_CONFIG = {
    "api": {
        "host": "0.0.0.0",
        "port": 8000,
        "reload": False,
        "api_key": "dev-api-key"
    },
    "llm": {
        "primary_model": "gpt-3.5-turbo",
        "secondary_model": "gpt-3.5-turbo",
        "default_temperature": 0.7,
        "default_max_tokens": 1000
    },
    "resources": {
        "max_concurrent_tasks": 4,
        "cpu_threshold": 80.0,
        "memory_threshold": 80.0,
        "disk_threshold": 90.0,
        "resource_check_interval": 10.0,
        "min_workers": 2,
        "adjust_interval": 30.0
    },
    "auto_shutdown": {
        "enabled": False,
        "idle_time": 3600,
        "check_interval": 300
    },
    "features": {
        "enable_multimodal": False,
        "enable_cross_source_analysis": True,
        "enable_knowledge_graph": True,
        "enable_reference_support": True
    },
    "paths": {
        "project_dir": "",
        "plugins_dir": "core/plugins",
        "config_file": "core/plugins/config.json"
    }
}

class Config:
    """Configuration manager for WiseFlow."""
    
    _instance = None
    
    def __new__(cls):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the configuration manager."""
        if self._initialized:
            return
            
        self.logger = logging.getLogger("wiseflow.config")
        self.config = DEFAULT_CONFIG.copy()
        self._initialized = True
    
    def load_from_env(self):
        """Load configuration from environment variables."""
        # API settings
        self.config["api"]["host"] = os.environ.get("API_HOST", self.config["api"]["host"])
        self.config["api"]["port"] = int(os.environ.get("API_PORT", self.config["api"]["port"]))
        self.config["api"]["reload"] = os.environ.get("API_RELOAD", "false").lower() == "true"
        self.config["api"]["api_key"] = os.environ.get("WISEFLOW_API_KEY", self.config["api"]["api_key"])
        
        # LLM settings
        self.config["llm"]["primary_model"] = os.environ.get("PRIMARY_MODEL", self.config["llm"]["primary_model"])
        self.config["llm"]["secondary_model"] = os.environ.get("SECONDARY_MODEL", self.config["llm"]["primary_model"])
        
        # Resource settings
        self.config["resources"]["max_concurrent_tasks"] = int(os.environ.get(
            "MAX_CONCURRENT_TASKS", self.config["resources"]["max_concurrent_tasks"]
        ))
        
        # Auto-shutdown settings
        self.config["auto_shutdown"]["enabled"] = os.environ.get(
            "AUTO_SHUTDOWN_ENABLED", "false"
        ).lower() == "true"
        self.config["auto_shutdown"]["idle_time"] = int(os.environ.get(
            "AUTO_SHUTDOWN_IDLE_TIME", self.config["auto_shutdown"]["idle_time"]
        ))
        self.config["auto_shutdown"]["check_interval"] = int(os.environ.get(
            "AUTO_SHUTDOWN_CHECK_INTERVAL", self.config["auto_shutdown"]["check_interval"]
        ))
        
        # Feature flags
        self.config["features"]["enable_multimodal"] = os.environ.get(
            "ENABLE_MULTIMODAL", "false"
        ).lower() == "true"
        
        # Paths
        self.config["paths"]["project_dir"] = os.environ.get("PROJECT_DIR", self.config["paths"]["project_dir"])
        
        self.logger.info("Configuration loaded from environment variables")
        return self.config
    
    def load_from_file(self, config_file: str):
        """Load configuration from a JSON file."""
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                
            # Merge with default config
            self._merge_configs(self.config, file_config)
            
            self.logger.info(f"Configuration loaded from file: {config_file}")
            return self.config
        except Exception as e:
            self.logger.error(f"Failed to load configuration from file {config_file}: {e}")
            return self.config
    
    def _merge_configs(self, target: Dict[str, Any], source: Dict[str, Any]):
        """Recursively merge source config into target config."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_configs(target[key], value)
            else:
                target[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """Set a configuration value by key."""
        keys = key.split('.')
        config = self.config
        
        for i, k in enumerate(keys[:-1]):
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save_to_file(self, config_file: str) -> bool:
        """Save the current configuration to a file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(config_file)), exist_ok=True)
            
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
                
            self.logger.info(f"Configuration saved to file: {config_file}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save configuration to file {config_file}: {e}")
            return False
    
    def validate(self) -> List[str]:
        """Validate the configuration and return a list of validation errors."""
        errors = []
        
        # Validate API settings
        try:
            port = int(self.config["api"]["port"])
            if port < 1 or port > 65535:
                errors.append(f"Invalid API port: {port}")
        except (ValueError, KeyError):
            errors.append("Invalid API port configuration")
        
        # Validate resource settings
        try:
            max_tasks = int(self.config["resources"]["max_concurrent_tasks"])
            if max_tasks < 1:
                errors.append(f"Invalid max_concurrent_tasks: {max_tasks}")
        except (ValueError, KeyError):
            errors.append("Invalid max_concurrent_tasks configuration")
        
        # Validate LLM settings
        if not self.config["llm"]["primary_model"]:
            errors.append("PRIMARY_MODEL not set")
        
        return errors

# Create a singleton instance
config_manager = Config()

def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from environment variables and optionally from a file."""
    # Load from environment variables
    config_manager.load_from_env()
    
    # Load from file if provided
    if config_file and os.path.exists(config_file):
        config_manager.load_from_file(config_file)
    
    # Validate configuration
    errors = config_manager.validate()
    if errors:
        logger = logging.getLogger("wiseflow.config")
        for error in errors:
            logger.error(f"Configuration error: {error}")
    
    return config_manager.config

def get_config() -> Dict[str, Any]:
    """Get the current configuration."""
    return config_manager.config

def get(key: str, default: Any = None) -> Any:
    """Get a configuration value by key."""
    return config_manager.get(key, default)

def set(key: str, value: Any):
    """Set a configuration value by key."""
    config_manager.set(key, value)

