#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Central configuration module for WiseFlow.

This module provides a centralized way to access all configuration settings
from environment variables, with proper defaults and validation.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
if env_path.exists():
# Add to imports
from cryptography.fernet import Fernet
from base64 import b64encode

class Config:
    SENSITIVE_KEYS = {
        'LLM_API_KEY', 'PB_API_AUTH', 'ZHIPU_API_KEY',
        'EXA_API_KEY', 'WISEFLOW_API_KEY'
    }
    
    def __init__(self):
        self._config = {}
        self._encrypted_values = {}
        self._cipher = Fernet(Fernet.generate_key())
    
    def _encrypt_value(self, value: str) -> bytes:
        return self._cipher.encrypt(value.encode())
        
    def _decrypt_value(self, encrypted: bytes) -> str:
        return self._cipher.decrypt(encrypted).decode()
        
    def set(self, key: str, value: Any) -> None:
        if key in self.SENSITIVE_KEYS:
            self._encrypted_values[key] = self._encrypt_value(str(value))
        else:
            self._config[key] = value
            
    def get(self, key: str, default: Any = None) -> Any:
        if key in self.SENSITIVE_KEYS:
            encrypted = self._encrypted_values.get(key)
            return self._decrypt_value(encrypted) if encrypted else default
        return self._config.get(key, default)
        # Project settings
        "PROJECT_DIR": "work_dir",
        "VERBOSE": False,
        
        # LLM settings
        "LLM_API_BASE": "",
        "LLM_API_KEY": "",
        "PRIMARY_MODEL": "",
        "SECONDARY_MODEL": "",
        "VL_MODEL": "",
        "LLM_CONCURRENT_NUMBER": 1,
        
        # PocketBase settings
        "PB_API_BASE": "http://127.0.0.1:8090",
        "PB_API_AUTH": "",
        
        # Search settings
        "ZHIPU_API_KEY": "",
        "EXA_API_KEY": "",
        
        # Crawler settings
        "CRAWLER_TIMEOUT": 60,
        "CRAWLER_MAX_DEPTH": 3,
        "CRAWLER_MAX_PAGES": 100,
        "MAX_CONCURRENT_REQUESTS": 5,
        
        # Task settings
        "MAX_CONCURRENT_TASKS": 4,
        "AUTO_SHUTDOWN_ENABLED": False,
        "AUTO_SHUTDOWN_IDLE_TIME": 3600,
        "AUTO_SHUTDOWN_CHECK_INTERVAL": 300,
        
        # Feature flags
        "ENABLE_MULTIMODAL": False,
        "ENABLE_KNOWLEDGE_GRAPH": False,
        "ENABLE_INSIGHTS": True,
        "ENABLE_REFERENCES": True,
        "ENABLE_EVENT_SYSTEM": True
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the configuration.
        
        Args:
            config_file: Optional path to a JSON configuration file
        """
        self._config = self.DEFAULT_CONFIG.copy()
        
        # Load configuration from file if provided
        if config_file:
            self._load_from_file(config_file)
        
        # Override with environment variables
        self._load_from_env()
        
        # Validate configuration
        self._validate()
        
        # Create project directory if needed
        self._setup_project_dir()
        
        # Log configuration (excluding sensitive values)
        self._log_config()
    
    def _load_from_file(self, config_file: str) -> None:
        """
        Load configuration from a JSON file.
        
        Args:
            config_file: Path to the JSON configuration file
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                self._config.update(file_config)
                logger.info(f"Loaded configuration from {config_file}")
        except Exception as e:
            logger.error(f"Error loading configuration from {config_file}: {e}")
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        for key in self._config.keys():
            env_value = os.environ.get(key)
            if env_value is not None:
                # Convert string values to appropriate types
                if isinstance(self._config[key], bool):
                    self._config[key] = env_value.lower() in ('true', 'yes', '1', 'y')
                elif isinstance(self._config[key], int):
                    try:
                        self._config[key] = int(env_value)
                    except ValueError:
                        logger.warning(f"Invalid integer value for {key}: {env_value}")
                elif isinstance(self._config[key], float):
                    try:
                        self._config[key] = float(env_value)
                    except ValueError:
                        logger.warning(f"Invalid float value for {key}: {env_value}")
                else:
                    self._config[key] = env_value
    
    def _validate(self) -> None:
        """Validate the configuration and set derived values."""
        # Check required values
        if not self._config["PRIMARY_MODEL"]:
            logger.warning("PRIMARY_MODEL not set, this may cause issues with LLM functionality")
        
        if not self._config["PB_API_AUTH"]:
            logger.warning("PB_API_AUTH not set, this may cause issues with database access")
        
        # Set SECONDARY_MODEL to PRIMARY_MODEL if not specified
        if not self._config["SECONDARY_MODEL"]:
            self._config["SECONDARY_MODEL"] = self._config["PRIMARY_MODEL"]
            
        # Set VL_MODEL to PRIMARY_MODEL if not specified
        if not self._config["VL_MODEL"]:
            self._config["VL_MODEL"] = self._config["PRIMARY_MODEL"]
    
    def _setup_project_dir(self) -> None:
        """Create project directory if it doesn't exist."""
        if self._config["PROJECT_DIR"]:
            os.makedirs(self._config["PROJECT_DIR"], exist_ok=True)
    
    def _log_config(self) -> None:
        """Log the configuration (excluding sensitive values)."""
        if self._config.get("VERBOSE", False):
            # Create a copy with sensitive values masked
            safe_config = self._config.copy()
            for key in ["LLM_API_KEY", "PB_API_AUTH", "ZHIPU_API_KEY", "EXA_API_KEY"]:
                if safe_config.get(key):
                    safe_config[key] = "********"
            
            logger.info(f"Configuration: {json.dumps(safe_config, indent=2)}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key is not found
            
        Returns:
            Configuration value
        """
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config[key] = value
    
    def as_dict(self) -> Dict[str, Any]:
        """
        Get the configuration as a dictionary.
        
        Returns:
            Configuration dictionary
        """
        return self._config.copy()
    
    def save_to_file(self, filepath: str) -> bool:
        """
        Save the configuration to a JSON file.
        
        Args:
            filepath: Path to save the configuration to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2)
            logger.info(f"Configuration saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration to {filepath}: {e}")
            return False

def validate_config():
    """Validate all critical configuration settings."""
    if not config.get("PRIMARY_MODEL"):
        raise ValueError("PRIMARY_MODEL not set")
    if not config.get("PB_API_AUTH"):
        raise ValueError("PB_API_AUTH not set")
    if not config.get("API_PORT") or not (1024 <= config.get("API_PORT", 8000) <= 65535):
        logger.warning("Invalid API_PORT value, using default 8000")
    if not config.get("API_HOST"):
        logger.warning("API_HOST not set, using default 0.0.0.0")

def get_int_config(key: str, default: int) -> int:
    """
    Get an integer configuration value with validation.
    
    Args:
        key: Configuration key
        default: Default value if key is not found or invalid
        
    Returns:
        Integer configuration value
    """
    try:
        value = config.get(key)
        if value is None:
            return default
        return int(value)
    except (ValueError, TypeError):
        logger.warning(f"Invalid integer value for {key}, using default {default}")
        return default

def get_bool_config(key: str, default: bool) -> bool:
    """
    Get a boolean configuration value with validation.
    
    Args:
        key: Configuration key
        default: Default value if key is not found or invalid
        
    Returns:
        Boolean configuration value
    """
    value = config.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', 'yes', '1', 'y')
    return bool(value)

# Create a singleton instance for easy access
config = Config()

# Export commonly used configuration values
PROJECT_DIR = config.get("PROJECT_DIR", "work_dir")
VERBOSE = get_bool_config("VERBOSE", False)
LLM_API_KEY = config.get("LLM_API_KEY", "")
LLM_API_BASE = config.get("LLM_API_BASE", "")
PRIMARY_MODEL = config.get("PRIMARY_MODEL", "")
SECONDARY_MODEL = config.get("SECONDARY_MODEL", PRIMARY_MODEL)
VL_MODEL = config.get("VL_MODEL", PRIMARY_MODEL)
LLM_CONCURRENT_NUMBER = get_int_config("LLM_CONCURRENT_NUMBER", 1)
PB_API_AUTH = config.get("PB_API_AUTH", "")
PB_API_BASE = config.get("PB_API_BASE", "http://127.0.0.1:8090")
ZHIPU_API_KEY = config.get("ZHIPU_API_KEY", "")
EXA_API_KEY = config.get("EXA_API_KEY", "")
API_HOST = config.get("API_HOST", "0.0.0.0")
API_PORT = get_int_config("API_PORT", 8000)
API_RELOAD = get_bool_config("API_RELOAD", False)
WISEFLOW_API_KEY = config.get("WISEFLOW_API_KEY", "dev-api-key")
MAX_CONCURRENT_TASKS = get_int_config("MAX_CONCURRENT_TASKS", 4)
AUTO_SHUTDOWN_ENABLED = get_bool_config("AUTO_SHUTDOWN_ENABLED", False)
AUTO_SHUTDOWN_IDLE_TIME = get_int_config("AUTO_SHUTDOWN_IDLE_TIME", 3600)
AUTO_SHUTDOWN_CHECK_INTERVAL = get_int_config("AUTO_SHUTDOWN_CHECK_INTERVAL", 300)
ENABLE_MULTIMODAL = get_bool_config("ENABLE_MULTIMODAL", False)
ENABLE_KNOWLEDGE_GRAPH = get_bool_config("ENABLE_KNOWLEDGE_GRAPH", False)
ENABLE_INSIGHTS = get_bool_config("ENABLE_INSIGHTS", True)
ENABLE_REFERENCES = get_bool_config("ENABLE_REFERENCES", True)
ENABLE_EVENT_SYSTEM = get_bool_config("ENABLE_EVENT_SYSTEM", True)

