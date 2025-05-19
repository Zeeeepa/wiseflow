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
import yaml
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dotenv import load_dotenv

# Configure basic logging until our full logging system is initialized
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

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
    if key in ['LLM_CONCURRENT_NUMBER', 'MAX_CONCURRENT_TASKS', 'MAX_CONCURRENT_REQUESTS']:
        try:
            int_value = int(value)
            if int_value < 1:
                raise ConfigValidationError(f"{key} must be at least 1")
            return int_value
        except ValueError:
            raise ConfigValidationError(f"{key} must be an integer")
    
    # Timeout settings
    if key in ['CRAWLER_TIMEOUT', 'AUTO_SHUTDOWN_IDLE_TIME', 'AUTO_SHUTDOWN_CHECK_INTERVAL', 
               'API_TIMEOUT', 'REDIS_TIMEOUT', 'CACHE_TTL']:
        try:
            int_value = int(value)
            if int_value < 0:
                raise ConfigValidationError(f"{key} must be non-negative")
            return int_value
        except ValueError:
            raise ConfigValidationError(f"{key} must be an integer")
    
    # Boolean settings
    if key in ['VERBOSE', 'AUTO_SHUTDOWN_ENABLED', 'ENABLE_MULTIMODAL', 
               'ENABLE_KNOWLEDGE_GRAPH', 'ENABLE_INSIGHTS', 'ENABLE_REFERENCES',
               'STRUCTURED_LOGGING', 'LOG_TO_FILE', 'LOG_TO_CONSOLE', 
               'ENABLE_CACHING', 'ENABLE_RATE_LIMITING', 'ENABLE_METRICS',
               'ENABLE_TRACING', 'ENABLE_SECURITY', 'ENABLE_COMPRESSION']:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value.lower() in ['true', 'yes', '1', 'on']:
                return True
            if value.lower() in ['false', 'no', '0', 'off']:
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
    """
    
    SENSITIVE_KEYS = {
        'LLM_API_KEY', 'PB_API_AUTH', 'ZHIPU_API_KEY',
        'EXA_API_KEY', 'WISEFLOW_API_KEY', 'ANTHROPIC_API_KEY',
        'AZURE_API_KEY', 'REDIS_PASSWORD', 'JWT_SECRET_KEY'
    }
    
    def __init__(self):
        """Initialize the configuration manager with empty configuration."""
        self._config = {}
        self._encrypted_values = {}
        self._cipher_key = os.environ.get('CIPHER_KEY', Fernet.generate_key())
        self._cipher = Fernet(self._cipher_key)
    
    def _encrypt_value(self, value: str) -> bytes:
        """
        Encrypt a sensitive value.
        
        Args:
            value: Value to encrypt
            
        Returns:
            Encrypted value as bytes
        """
        return self._cipher.encrypt(value.encode())
        
    def _decrypt_value(self, encrypted: bytes) -> str:
        """
        Decrypt a sensitive value.
        
        Args:
            encrypted: Encrypted value as bytes
            
        Returns:
            Decrypted value as string
        """
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
            
            if key in self.SENSITIVE_KEYS:
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

    # Default configuration values
    DEFAULT_CONFIG = {
        # Project settings
        "PROJECT_DIR": "work_dir",
        "VERBOSE": False,
        "VERSION": "2.0.0",
        
        # LLM settings
        "LLM_API_BASE": "",
        "LLM_API_KEY": "",
        "PRIMARY_MODEL": "",
        "SECONDARY_MODEL": "",
        "VL_MODEL": "",
        "LLM_CONCURRENT_NUMBER": 3,
        "ENABLE_MODEL_FALLBACK": True,
        
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
        "MAX_CONCURRENT_REQUESTS": 10,
        
        # Task settings
        "MAX_CONCURRENT_TASKS": 8,
        "AUTO_SHUTDOWN_ENABLED": False,
        "AUTO_SHUTDOWN_IDLE_TIME": 3600,
        "AUTO_SHUTDOWN_CHECK_INTERVAL": 300,
        
        # Feature flags
        "ENABLE_MULTIMODAL": True,
        "ENABLE_KNOWLEDGE_GRAPH": True,
        "ENABLE_INSIGHTS": True,
        "ENABLE_REFERENCES": True,
        "ENABLE_EVENT_SYSTEM": True,
        "ENABLE_CACHING": True,
        "ENABLE_RATE_LIMITING": True,
        "ENABLE_METRICS": True,
        "ENABLE_TRACING": False,
        "ENABLE_SECURITY": True,
        "ENABLE_COMPRESSION": True,
        
        # Caching settings
        "CACHE_TTL": 3600,
        "CACHE_MAX_SIZE_MB": 100,
        "CACHE_MEMORY_ITEMS": 1000,
        
        # Redis settings
        "REDIS_HOST": "localhost",
        "REDIS_PORT": 6379,
        "REDIS_DB": 0,
        "REDIS_PASSWORD": "",
        "REDIS_TIMEOUT": 5,
        
        # API settings
        "API_HOST": "0.0.0.0",
        "API_PORT": 8000,
        "API_RELOAD": False,
        "API_TIMEOUT": 30,
        "API_WORKERS": 4,
        "WISEFLOW_API_KEY": "dev-api-key",
        
        # Security settings
        "JWT_SECRET_KEY": "",
        "JWT_ALGORITHM": "HS256",
        "JWT_EXPIRATION_MINUTES": 60,
        
        # Logging settings
        "LOG_LEVEL": "INFO",
        "LOG_TO_FILE": True,
        "LOG_TO_CONSOLE": True,
        "LOG_DIR": "",  # Default will be PROJECT_DIR/logs
        "STRUCTURED_LOGGING": True,
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
            config_file: Optional path to a configuration file
        """
        self._config = self.DEFAULT_CONFIG.copy()
        self._encrypted_values = {}
        self._cipher_key = os.environ.get('CIPHER_KEY', Fernet.generate_key())
        self._cipher = Fernet(self._cipher_key)
        
        # Load configuration from file if provided
        if config_file:
            self._load_from_file(config_file)
        
        # Override with environment variables
        self._load_from_env()
        
        # Validate and set derived values
        self._validate()
        
        # Create project directory if it doesn't exist
        self._setup_project_dir()
        
        # Log configuration if verbose
        self._log_config()
    
    def _load_from_file(self, config_file: str) -> None:
        """
        Load configuration from a file.
        
        This method loads configuration from a file, supporting both JSON and YAML formats.
        
        Args:
            config_file: Path to the configuration file
        """
        try:
            file_extension = Path(config_file).suffix.lower()
            
            if file_extension == '.json':
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
            elif file_extension in ['.yaml', '.yml']:
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f)
            else:
                logger.warning(f"Unsupported configuration file format: {file_extension}")
                return
                
            self._config.update(file_config)
            logger.info(f"Loaded configuration from {config_file}")
        except Exception as e:
            logger.error(f"Error loading configuration from {config_file}: {e}")
    
    def _load_from_env(self) -> None:
        """
        Load configuration from environment variables.
        
        This method loads configuration from environment variables and updates
        the current configuration with the values from the environment.
        """
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
                    
                # Encrypt sensitive values
                if key in self.SENSITIVE_KEYS:
                    self._encrypted_values[key] = self._encrypt_value(str(self._config[key]))
                    # Remove from plain config
                    del self._config[key]
    
    def _validate(self) -> None:
        """
        Validate the configuration and set derived values.
        
        This method validates the configuration and sets derived values based
        on other configuration values.
        """
        # Check required values
        if not self.get("PRIMARY_MODEL"):
            logger.warning("PRIMARY_MODEL not set, this may cause issues with LLM functionality")
        
        if not self.get("PB_API_AUTH"):
            logger.warning("PB_API_AUTH not set, this may cause issues with database access")
        
        # Set SECONDARY_MODEL to PRIMARY_MODEL if not specified
        if not self.get("SECONDARY_MODEL"):
            self.set("SECONDARY_MODEL", self.get("PRIMARY_MODEL"))
            
        # Set VL_MODEL to PRIMARY_MODEL if not specified
        if not self.get("VL_MODEL"):
            self.set("VL_MODEL", self.get("PRIMARY_MODEL"))
        
        # Validate LOG_LEVEL
        valid_log_levels = ['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']
        if self.get("LOG_LEVEL") not in valid_log_levels:
            logger.warning(f"Invalid LOG_LEVEL: {self.get('LOG_LEVEL')}, using INFO")
            self.set("LOG_LEVEL", "INFO")
            
        # Generate JWT_SECRET_KEY if not set
        if not self.get("JWT_SECRET_KEY"):
            import secrets
            jwt_secret = secrets.token_hex(32)
            self.set("JWT_SECRET_KEY", jwt_secret)
            logger.info("Generated new JWT_SECRET_KEY")
    
    def _setup_project_dir(self) -> None:
        """
        Create project directory if it doesn't exist.
        
        This method creates the project directory if it doesn't exist, based
        on the PROJECT_DIR configuration value.
        """
        if self.get("PROJECT_DIR"):
            os.makedirs(self.get("PROJECT_DIR"), exist_ok=True)
    
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
                if key in safe_config:
                    safe_config[key] = "********"
            
            logger.info(f"Configuration: {json.dumps(safe_config, indent=2)}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        This method returns the configuration value for the given key, or the
        default value if the key is not found.
        
        Args:
            key: Configuration key
            default: Default value if key is not found
            
        Returns:
            Configuration value, or default if key is not found
        """
        if key in self.SENSITIVE_KEYS:
            encrypted = self._encrypted_values.get(key)
            if encrypted:
                try:
                    return self._decrypt_value(encrypted)
                except Exception as e:
                    logger.error(f"Error decrypting value for {key}: {e}")
                    return default
            return default
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        This method sets the configuration value for the given key.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        try:
            validated_value = validate_config_value(key, value)
            
            if key in self.SENSITIVE_KEYS:
                self._encrypted_values[key] = self._encrypt_value(str(validated_value))
            else:
                self._config[key] = validated_value
        except ConfigValidationError as e:
            logger.warning(f"Configuration validation error: {e}")
            raise
    
    def as_dict(self) -> Dict[str, Any]:
        """
        Get the configuration as a dictionary.
        
        This method returns a copy of the configuration as a dictionary.
        
        Returns:
            Configuration dictionary
        """
        # Create a copy of the configuration
        config_dict = self._config.copy()
        
        # Add decrypted sensitive values
        for key in self.SENSITIVE_KEYS:
            if key in self._encrypted_values:
                try:
                    config_dict[key] = self._decrypt_value(self._encrypted_values[key])
                except Exception as e:
                    logger.error(f"Error decrypting value for {key}: {e}")
                    config_dict[key] = None
        
        return config_dict
    
    def save_to_file(self, filepath: str, format: str = 'json') -> bool:
        """
        Save the configuration to a file.
        
        This method saves the configuration to a file in the specified format.
        
        Args:
            filepath: Path to save the configuration to
            format: Format to save the configuration in ('json' or 'yaml')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create a copy of the configuration with decrypted sensitive values
            config_dict = self.as_dict()
            
            # Create parent directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            
            if format.lower() == 'json':
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(config_dict, f, indent=2)
            elif format.lower() in ['yaml', 'yml']:
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.dump(config_dict, f, default_flow_style=False)
            else:
                logger.error(f"Unsupported format: {format}")
                return False
                
            logger.info(f"Configuration saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration to {filepath}: {e}")
            return False
            
    def export_env_file(self, filepath: str) -> bool:
        """
        Export the configuration to a .env file.
        
        This method exports the configuration to a .env file for easy environment variable setup.
        
        Args:
            filepath: Path to save the .env file to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create a copy of the configuration with decrypted sensitive values
            config_dict = self.as_dict()
            
            # Create parent directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                for key, value in sorted(config_dict.items()):
                    if value is None:
                        continue
                        
                    if isinstance(value, bool):
                        value = 'true' if value else 'false'
                    
                    f.write(f"{key}={value}\n")
                
            logger.info(f"Environment variables exported to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error exporting environment variables to {filepath}: {e}")
            return False

def validate_config():
    """
    Validate all critical configuration settings.
    
    This function validates all critical configuration settings and raises
    a ValueError if any required settings are missing or invalid.
    
    Raises:
        ValueError: If any required settings are missing or invalid
    """
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
        return value.lower() in ('true', 'yes', '1', 'y')
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

# Create a singleton instance for easy access
config = Config()

# Export commonly used configuration values
PROJECT_DIR = config.get("PROJECT_DIR", "work_dir")
VERBOSE = get_bool_config("VERBOSE", False)
VERSION = config.get("VERSION", "2.0.0")

# LLM configuration
LLM_API_KEY = config.get("LLM_API_KEY", "")
LLM_API_BASE = config.get("LLM_API_BASE", "")
PRIMARY_MODEL = config.get("PRIMARY_MODEL", "")
SECONDARY_MODEL = config.get("SECONDARY_MODEL", PRIMARY_MODEL)
VL_MODEL = config.get("VL_MODEL", PRIMARY_MODEL)
LLM_CONCURRENT_NUMBER = get_int_config("LLM_CONCURRENT_NUMBER", 3)
ENABLE_MODEL_FALLBACK = get_bool_config("ENABLE_MODEL_FALLBACK", True)

# PocketBase configuration
PB_API_AUTH = config.get("PB_API_AUTH", "")
PB_API_BASE = config.get("PB_API_BASE", "http://127.0.0.1:8090")

# Search API configuration
ZHIPU_API_KEY = config.get("ZHIPU_API_KEY", "")
EXA_API_KEY = config.get("EXA_API_KEY", "")

# API configuration
API_HOST = config.get("API_HOST", "0.0.0.0")
API_PORT = get_int_config("API_PORT", 8000)
API_RELOAD = get_bool_config("API_RELOAD", False)
API_TIMEOUT = get_int_config("API_TIMEOUT", 30)
API_WORKERS = get_int_config("API_WORKERS", 4)
WISEFLOW_API_KEY = config.get("WISEFLOW_API_KEY", "dev-api-key")

# Task configuration
MAX_CONCURRENT_TASKS = get_int_config("MAX_CONCURRENT_TASKS", 8)
AUTO_SHUTDOWN_ENABLED = get_bool_config("AUTO_SHUTDOWN_ENABLED", False)
AUTO_SHUTDOWN_IDLE_TIME = get_int_config("AUTO_SHUTDOWN_IDLE_TIME", 3600)
AUTO_SHUTDOWN_CHECK_INTERVAL = get_int_config("AUTO_SHUTDOWN_CHECK_INTERVAL", 300)

# Feature flags
ENABLE_MULTIMODAL = get_bool_config("ENABLE_MULTIMODAL", True)
ENABLE_KNOWLEDGE_GRAPH = get_bool_config("ENABLE_KNOWLEDGE_GRAPH", True)
ENABLE_INSIGHTS = get_bool_config("ENABLE_INSIGHTS", True)
ENABLE_REFERENCES = get_bool_config("ENABLE_REFERENCES", True)
ENABLE_EVENT_SYSTEM = get_bool_config("ENABLE_EVENT_SYSTEM", True)
ENABLE_CACHING = get_bool_config("ENABLE_CACHING", True)
ENABLE_RATE_LIMITING = get_bool_config("ENABLE_RATE_LIMITING", True)
ENABLE_METRICS = get_bool_config("ENABLE_METRICS", True)
ENABLE_TRACING = get_bool_config("ENABLE_TRACING", False)
ENABLE_SECURITY = get_bool_config("ENABLE_SECURITY", True)
ENABLE_COMPRESSION = get_bool_config("ENABLE_COMPRESSION", True)

# Caching configuration
CACHE_TTL = get_int_config("CACHE_TTL", 3600)
CACHE_MAX_SIZE_MB = get_int_config("CACHE_MAX_SIZE_MB", 100)
CACHE_MEMORY_ITEMS = get_int_config("CACHE_MEMORY_ITEMS", 1000)

# Redis configuration
REDIS_HOST = config.get("REDIS_HOST", "localhost")
REDIS_PORT = get_int_config("REDIS_PORT", 6379)
REDIS_DB = get_int_config("REDIS_DB", 0)
REDIS_PASSWORD = config.get("REDIS_PASSWORD", "")
REDIS_TIMEOUT = get_int_config("REDIS_TIMEOUT", 5)

# Security configuration
JWT_SECRET_KEY = config.get("JWT_SECRET_KEY", "")
JWT_ALGORITHM = config.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES = get_int_config("JWT_EXPIRATION_MINUTES", 60)

# Logging configuration
LOG_LEVEL = config.get("LOG_LEVEL", "INFO")
LOG_TO_FILE = get_bool_config("LOG_TO_FILE", True)
LOG_TO_CONSOLE = get_bool_config("LOG_TO_CONSOLE", True)
LOG_DIR = config.get("LOG_DIR", os.path.join(PROJECT_DIR, "logs"))
STRUCTURED_LOGGING = get_bool_config("STRUCTURED_LOGGING", True)
LOG_ROTATION = config.get("LOG_ROTATION", "50 MB")
LOG_RETENTION = config.get("LOG_RETENTION", "10 days")
