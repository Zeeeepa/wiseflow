#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Central configuration module for WiseFlow.

This module provides a centralized way to access all configuration settings
from environment variables, with proper defaults and validation. It handles
loading configuration from environment variables or a configuration file,
validating configuration values, and providing access to configuration
settings throughout the application.

The configuration system supports:
- Loading from environment variables
- Loading from a JSON configuration file
- Validation of configuration values
- Encryption of sensitive values
- Default values for missing settings
- Derived values based on other settings

Key configuration categories include:
- LLM settings (API keys, models, etc.)
- System settings (directories, logging, etc.)
- Feature flags (enabling/disabling features)
- API settings (host, port, etc.)
- Database settings (PocketBase connection)

Example usage:
    from core.config import config
    
    # Get a configuration value
    api_key = config.get("LLM_API_KEY")
    
    # Get a configuration value with a default
    verbose = config.get("VERBOSE", False)
    
    # Set a configuration value
    config.set("MAX_CONCURRENT_TASKS", 4)
"""

import os
import json
import logging
import traceback
from typing import Dict, Any, Optional, List, Union, Set, Type
from pathlib import Path
from dotenv import load_dotenv

# Configure basic logging until our full logging system is initialized
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file if it exists
env_path = Path('.env')
if env_path.exists():
    logger.info(f"Loading environment variables from {env_path}")
    load_dotenv(env_path)
else:
    # Also check for .env in the parent directory (project root)
    parent_env_path = Path(__file__).parent.parent / '.env'
    if parent_env_path.exists():
        logger.info(f"Loading environment variables from {parent_env_path}")
        load_dotenv(parent_env_path)
    else:
        logger.warning("No .env file found. Using environment variables or defaults.")

# Add to imports
from cryptography.fernet import Fernet
from base64 import b64encode, b64decode

class ConfigValidationError(Exception):
    """
    Exception raised for configuration validation errors.
    
    This exception is raised when a configuration value fails validation,
    such as when a numeric value is out of range or a required value is missing.
    """
    pass

class ConfigurationError(Exception):
    """
    Exception raised for general configuration errors.
    
    This exception is raised when there is an error loading, parsing, or
    accessing configuration values.
    """
    pass

def validate_config_value(key: str, value: Any) -> Any:
    """
    Validate configuration values based on their keys.
    
    This function validates configuration values based on their keys and
    converts them to the appropriate type if necessary. It raises a
    ConfigValidationError if validation fails.
    
    Args:
        key: Configuration key to validate
        value: Configuration value to validate
        
    Returns:
        Validated value (possibly converted to appropriate type)
        
    Raises:
        ConfigValidationError: If validation fails
    """
    # Skip validation for None values (they'll be replaced with defaults)
    if value is None:
        return None
        
    # Memory thresholds
    if key in ['memory_threshold_percent', 'memory_warning_percent']:
        try:
            float_value = float(value)
            if not (0 <= float_value <= 100):
                raise ConfigValidationError(f"{key} must be between 0 and 100")
            return float_value
        except ValueError:
            raise ConfigValidationError(f"{key} must be a number")
    
    # Concurrency settings
    if key in ['LLM_CONCURRENT_NUMBER', 'MAX_CONCURRENT_TASKS']:
        try:
            int_value = int(value)
            if int_value < 1:
                raise ConfigValidationError(f"{key} must be at least 1")
            return int_value
        except ValueError:
            raise ConfigValidationError(f"{key} must be an integer")
    
    # Timeout settings
    if key in ['CRAWLER_TIMEOUT', 'AUTO_SHUTDOWN_IDLE_TIME', 'AUTO_SHUTDOWN_CHECK_INTERVAL']:
        try:
            int_value = int(value)
            if int_value < 0:
                raise ConfigValidationError(f"{key} must be non-negative")
            return int_value
        except ValueError:
            raise ConfigValidationError(f"{key} must be an integer")
    
    # Port settings
    if key in ['API_PORT', 'PB_PORT']:
        try:
            int_value = int(value)
            if not (1024 <= int_value <= 65535):
                raise ConfigValidationError(f"{key} must be between 1024 and 65535")
            return int_value
        except ValueError:
            raise ConfigValidationError(f"{key} must be an integer")
    
    # Boolean settings
    if key in ['VERBOSE', 'AUTO_SHUTDOWN_ENABLED', 'ENABLE_MULTIMODAL', 
               'ENABLE_KNOWLEDGE_GRAPH', 'ENABLE_INSIGHTS', 'ENABLE_REFERENCES',
               'STRUCTURED_LOGGING', 'LOG_TO_FILE', 'LOG_TO_CONSOLE', 'API_RELOAD']:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value.lower() in ['true', 'yes', '1', 'on', 'y']:
                return True
            if value.lower() in ['false', 'no', '0', 'off', 'n']:
                return False
        raise ConfigValidationError(f"{key} must be a boolean value")
    
    # Log level validation
    if key == 'LOG_LEVEL':
        if isinstance(value, str):
            valid_levels = ['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']
            if value.upper() in valid_levels:
                return value.upper()
            raise ConfigValidationError(f"{key} must be one of {valid_levels}")
    
    # Return the value as is for other keys
    return value

class Config:
    """
    Configuration manager for WiseFlow.
    
    This class manages configuration settings for WiseFlow, including loading
    from environment variables or a configuration file, validating configuration
    values, and providing access to configuration settings throughout the
    application.
    
    Attributes:
        SENSITIVE_KEYS: Set of keys that contain sensitive values (e.g., API keys)
        DEFAULT_CONFIG: Dictionary of default configuration values
        REQUIRED_KEYS: Set of keys that must be provided (no default values)
    """
    
    SENSITIVE_KEYS: Set[str] = {
        'LLM_API_KEY', 'PB_API_AUTH', 'ZHIPU_API_KEY',
        'EXA_API_KEY', 'WISEFLOW_API_KEY'
    }
    
    # Keys that must be provided (no default values)
    REQUIRED_KEYS: Set[str] = {
        'PRIMARY_MODEL',
        'PB_API_AUTH'
    }
    
    # Default configuration values
    DEFAULT_CONFIG: Dict[str, Any] = {
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
        "ENABLE_EVENT_SYSTEM": True,
        
        # API settings
        "API_HOST": "0.0.0.0",
        "API_PORT": 8000,
        "API_RELOAD": False,
        "WISEFLOW_API_KEY": "dev-api-key",
        
        # Logging settings
        "LOG_LEVEL": "INFO",
        "LOG_TO_FILE": True,
        "LOG_TO_CONSOLE": True,
        "LOG_DIR": "",  # Default will be PROJECT_DIR/logs
        "STRUCTURED_LOGGING": False,
        "LOG_ROTATION": "50 MB",
        "LOG_RETENTION": "10 days"
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the configuration.
        
        This method initializes the configuration with default values, then
        loads configuration from a file if provided, and finally overrides
        with environment variables.
        
        Args:
            config_file: Optional path to a JSON configuration file
        """
        self._config = self.DEFAULT_CONFIG.copy()
        self._encrypted_values = {}
        
        # Generate a key for encryption (this will be regenerated on each restart)
        # In a production environment, this key should be persisted securely
        self._cipher_key = Fernet.generate_key()
        self._cipher = Fernet(self._cipher_key)
        
        # Load configuration from file if provided
        if config_file:
            self._load_from_file(config_file)
        
        # Load configuration from environment variables
        self._load_from_env()
        
        # Validate the configuration
        try:
            self._validate()
        except ConfigValidationError as e:
            logger.error(f"Configuration validation error: {e}")
            # Don't raise here, as this would prevent the application from starting
            # The validate_config() function can be called later to enforce validation
        
        # Set up project directory
        self._setup_project_dir()
        
        # Log the configuration
        self._log_config()
    
    def _encrypt_value(self, value: str) -> bytes:
        """
        Encrypt a sensitive value.
        
        Args:
            value: Value to encrypt
            
        Returns:
            Encrypted value as bytes
        """
        if not value:
            return b""
        return self._cipher.encrypt(value.encode())
        
    def _decrypt_value(self, encrypted: bytes) -> str:
        """
        Decrypt a sensitive value.
        
        Args:
            encrypted: Encrypted value as bytes
            
        Returns:
            Decrypted value as string
        """
        if not encrypted:
            return ""
        return self._cipher.decrypt(encrypted).decode()
        
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value with validation.
        
        This method validates the configuration value and encrypts it if it's
        a sensitive value.
        
        Args:
            key: Configuration key
            value: Configuration value
            
        Raises:
            ConfigValidationError: If validation fails
        """
        try:
            validated_value = validate_config_value(key, value)
            
            if key in self.SENSITIVE_KEYS and validated_value is not None:
                self._encrypted_values[key] = self._encrypt_value(str(validated_value))
            else:
                self._config[key] = validated_value
                
        except ConfigValidationError as e:
            logger.warning(f"Configuration validation error: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        This method returns the configuration value for the given key, or the
        default value if the key is not found. If the key is a sensitive key,
        the value is decrypted before being returned.
        
        Args:
            key: Configuration key
            default: Default value if key is not found
            
        Returns:
            Configuration value, or default if key is not found
        """
        if key in self.SENSITIVE_KEYS:
            encrypted = self._encrypted_values.get(key)
            return self._decrypt_value(encrypted) if encrypted else default
        return self._config.get(key, default)
    
    def _load_from_file(self, config_file: str) -> None:
        """
        Load configuration from a JSON file.
        
        This method loads configuration from a JSON file and updates the
        current configuration with the values from the file.
        
        Args:
            config_file: Path to the JSON configuration file
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                
                # Validate and set each value
                for key, value in file_config.items():
                    try:
                        self.set(key, value)
                    except ConfigValidationError as e:
                        logger.warning(f"Invalid configuration value in file: {e}")
                
                logger.info(f"Loaded configuration from {config_file}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing configuration file {config_file}: {e}")
        except Exception as e:
            logger.error(f"Error loading configuration from {config_file}: {e}")
    
    def _load_from_env(self) -> None:
        """
        Load configuration from environment variables.
        
        This method loads configuration from environment variables and updates
        the current configuration with the values from the environment.
        """
        # First, check for all keys in DEFAULT_CONFIG
        for key in self.DEFAULT_CONFIG.keys():
            env_value = os.environ.get(key)
            if env_value is not None:
                try:
                    self.set(key, env_value)
                except ConfigValidationError as e:
                    logger.warning(f"Invalid environment variable value: {e}")
        
        # Then check for any additional environment variables that might be used
        # but aren't in DEFAULT_CONFIG
        additional_env_vars = [
            # Add any additional environment variables that might be used
            # but aren't in DEFAULT_CONFIG
        ]
        
        for key in additional_env_vars:
            env_value = os.environ.get(key)
            if env_value is not None:
                try:
                    self.set(key, env_value)
                except ConfigValidationError as e:
                    logger.warning(f"Invalid environment variable value: {e}")
    
    def _validate(self) -> None:
        """
        Validate the configuration and set derived values.
        
        This method validates the configuration and sets derived values based
        on other configuration values.
        """
        # Check required values
        missing_required = [key for key in self.REQUIRED_KEYS if not self.get(key)]
        if missing_required:
            logger.warning(f"Missing required configuration values: {', '.join(missing_required)}")
        
        # Set SECONDARY_MODEL to PRIMARY_MODEL if not specified
        if not self.get("SECONDARY_MODEL"):
            primary_model = self.get("PRIMARY_MODEL", "")
            if primary_model:
                self.set("SECONDARY_MODEL", primary_model)
            
        # Set VL_MODEL to PRIMARY_MODEL if not specified
        if not self.get("VL_MODEL"):
            primary_model = self.get("PRIMARY_MODEL", "")
            if primary_model:
                self.set("VL_MODEL", primary_model)
        
        # Validate LOG_LEVEL
        valid_log_levels = ['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']
        log_level = self.get("LOG_LEVEL", "INFO")
        if log_level not in valid_log_levels:
            logger.warning(f"Invalid LOG_LEVEL: {log_level}, using INFO")
            self.set("LOG_LEVEL", "INFO")
        
        # Set LOG_DIR if not specified
        if not self.get("LOG_DIR"):
            project_dir = self.get("PROJECT_DIR", "work_dir")
            self.set("LOG_DIR", os.path.join(project_dir, "logs"))
    
    def _setup_project_dir(self) -> None:
        """
        Create project directory if it doesn't exist.
        
        This method creates the project directory if it doesn't exist, based
        on the PROJECT_DIR configuration value.
        """
        project_dir = self.get("PROJECT_DIR")
        if project_dir:
            try:
                os.makedirs(project_dir, exist_ok=True)
                logger.info(f"Project directory created/verified: {project_dir}")
            except Exception as e:
                logger.error(f"Error creating project directory {project_dir}: {e}")
    
    def _log_config(self) -> None:
        """
        Log the configuration (excluding sensitive values).
        
        This method logs the configuration, excluding sensitive values, if
        verbose logging is enabled.
        """
        if self.get("VERBOSE", False):
            # Create a copy with sensitive values masked
            safe_config = self.as_dict()
            for key in self.SENSITIVE_KEYS:
                if safe_config.get(key):
                    safe_config[key] = "********"
            
            logger.info(f"Configuration: {json.dumps(safe_config, indent=2)}")
    
    def as_dict(self) -> Dict[str, Any]:
        """
        Get the configuration as a dictionary.
        
        This method returns a copy of the configuration as a dictionary,
        including decrypted sensitive values.
        
        Returns:
            Configuration dictionary
        """
        # Start with a copy of the regular config
        config_dict = self._config.copy()
        
        # Add decrypted sensitive values
        for key in self.SENSITIVE_KEYS:
            encrypted = self._encrypted_values.get(key)
            if encrypted:
                config_dict[key] = self._decrypt_value(encrypted)
        
        return config_dict
    
    def save_to_file(self, filepath: str) -> bool:
        """
        Save the configuration to a JSON file.
        
        This method saves the configuration to a JSON file.
        
        Args:
            filepath: Path to save the configuration to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get a copy of the configuration with decrypted sensitive values
            config_dict = self.as_dict()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2)
            logger.info(f"Configuration saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration to {filepath}: {e}")
            return False

def validate_config() -> None:
    """
    Validate all critical configuration settings.
    
    This function validates all critical configuration settings and raises
    a ConfigurationError if any required settings are missing or invalid.
    
    Raises:
        ConfigurationError: If any required settings are missing or invalid
    """
    missing_required = []
    
    # Check required values
    for key in config.REQUIRED_KEYS:
        if not config.get(key):
            missing_required.append(key)
    
    if missing_required:
        error_msg = f"Missing required configuration values: {', '.join(missing_required)}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)
    
    # Validate API_PORT
    api_port = config.get("API_PORT", 8000)
    if not (1024 <= api_port <= 65535):
        logger.warning(f"Invalid API_PORT value: {api_port}, using default 8000")
        config.set("API_PORT", 8000)
    
    # Validate API_HOST
    if not config.get("API_HOST"):
        logger.warning("API_HOST not set, using default 0.0.0.0")
        config.set("API_HOST", "0.0.0.0")
    
    # Validate LLM_CONCURRENT_NUMBER
    llm_concurrent = config.get("LLM_CONCURRENT_NUMBER", 1)
    if not isinstance(llm_concurrent, int) or llm_concurrent < 1:
        logger.warning(f"Invalid LLM_CONCURRENT_NUMBER value: {llm_concurrent}, using default 1")
        config.set("LLM_CONCURRENT_NUMBER", 1)
    
    # Validate MAX_CONCURRENT_TASKS
    max_tasks = config.get("MAX_CONCURRENT_TASKS", 4)
    if not isinstance(max_tasks, int) or max_tasks < 1:
        logger.warning(f"Invalid MAX_CONCURRENT_TASKS value: {max_tasks}, using default 4")
        config.set("MAX_CONCURRENT_TASKS", 4)
    
    logger.info("Configuration validation completed successfully")

def get_int_config(key: str, default: int) -> int:
    """
    Get an integer configuration value with validation.
    
    This function gets an integer configuration value with validation, returning
    the default value if the key is not found or the value is invalid.
    
    Args:
        key: Configuration key
        default: Default value if key is not found or invalid
        
    Returns:
        Integer configuration value, or default if key is not found or invalid
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
    
    This function gets a boolean configuration value with validation, returning
    the default value if the key is not found or the value is invalid.
    
    Args:
        key: Configuration key
        default: Default value if key is not found or invalid
        
    Returns:
        Boolean configuration value, or default if key is not found or invalid
    """
    value = config.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', 'yes', '1', 'y', 'on')
    return bool(value)

def get_float_config(key: str, default: float) -> float:
    """
    Get a float configuration value with validation.
    
    This function gets a float configuration value with validation, returning
    the default value if the key is not found or the value is invalid.
    
    Args:
        key: Configuration key
        default: Default value if key is not found or invalid
        
    Returns:
        Float configuration value, or default if key is not found or invalid
    """
    try:
        value = config.get(key)
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        logger.warning(f"Invalid float value for {key}, using default {default}")
        return default

def get_str_config(key: str, default: str = "") -> str:
    """
    Get a string configuration value.
    
    This function gets a string configuration value, returning the default
    value if the key is not found.
    
    Args:
        key: Configuration key
        default: Default value if key is not found
        
    Returns:
        String configuration value, or default if key is not found
    """
    value = config.get(key)
    if value is None:
        return default
    return str(value)

# Create a singleton instance for easy access
config = Config()

# Export commonly used configuration values
PROJECT_DIR = get_str_config("PROJECT_DIR", "work_dir")
VERBOSE = get_bool_config("VERBOSE", False)
LLM_API_KEY = get_str_config("LLM_API_KEY")
LLM_API_BASE = get_str_config("LLM_API_BASE")
PRIMARY_MODEL = get_str_config("PRIMARY_MODEL")
SECONDARY_MODEL = get_str_config("SECONDARY_MODEL", PRIMARY_MODEL)
VL_MODEL = get_str_config("VL_MODEL", PRIMARY_MODEL)
LLM_CONCURRENT_NUMBER = get_int_config("LLM_CONCURRENT_NUMBER", 1)
PB_API_AUTH = get_str_config("PB_API_AUTH")
PB_API_BASE = get_str_config("PB_API_BASE", "http://127.0.0.1:8090")
ZHIPU_API_KEY = get_str_config("ZHIPU_API_KEY")
EXA_API_KEY = get_str_config("EXA_API_KEY")
API_HOST = get_str_config("API_HOST", "0.0.0.0")
API_PORT = get_int_config("API_PORT", 8000)
API_RELOAD = get_bool_config("API_RELOAD", False)
WISEFLOW_API_KEY = get_str_config("WISEFLOW_API_KEY", "dev-api-key")
MAX_CONCURRENT_TASKS = get_int_config("MAX_CONCURRENT_TASKS", 4)
AUTO_SHUTDOWN_ENABLED = get_bool_config("AUTO_SHUTDOWN_ENABLED", False)
AUTO_SHUTDOWN_IDLE_TIME = get_int_config("AUTO_SHUTDOWN_IDLE_TIME", 3600)
AUTO_SHUTDOWN_CHECK_INTERVAL = get_int_config("AUTO_SHUTDOWN_CHECK_INTERVAL", 300)
ENABLE_MULTIMODAL = get_bool_config("ENABLE_MULTIMODAL", False)
ENABLE_KNOWLEDGE_GRAPH = get_bool_config("ENABLE_KNOWLEDGE_GRAPH", False)
ENABLE_INSIGHTS = get_bool_config("ENABLE_INSIGHTS", True)
ENABLE_REFERENCES = get_bool_config("ENABLE_REFERENCES", True)
ENABLE_EVENT_SYSTEM = get_bool_config("ENABLE_EVENT_SYSTEM", True)

# Logging configuration
LOG_LEVEL = get_str_config("LOG_LEVEL", "INFO")
LOG_TO_FILE = get_bool_config("LOG_TO_FILE", True)
LOG_TO_CONSOLE = get_bool_config("LOG_TO_CONSOLE", True)
LOG_DIR = get_str_config("LOG_DIR", os.path.join(PROJECT_DIR, "logs"))
STRUCTURED_LOGGING = get_bool_config("STRUCTURED_LOGGING", False)
LOG_ROTATION = get_str_config("LOG_ROTATION", "50 MB")
LOG_RETENTION = get_str_config("LOG_RETENTION", "10 days")
