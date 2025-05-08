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
import base64
from typing import Dict, Any, Optional, List, Union, Type, TypeVar, cast
from pathlib import Path
from dotenv import load_dotenv

# Configure basic logging until our full logging system is initialized
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    logger.info(f"Loading environment variables from {env_path}")
    load_dotenv(env_path)
else:
    logger.warning(f"No .env file found at {env_path}")
    # Try loading from core/.env as a fallback
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        logger.info(f"Loading environment variables from {env_path}")
        load_dotenv(env_path)

# Import cryptography for sensitive value encryption
try:
    from cryptography.fernet import Fernet
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    logger.warning("cryptography package not available, sensitive values will not be encrypted")
    CRYPTOGRAPHY_AVAILABLE = False

# Type variable for configuration values
T = TypeVar('T')

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
    # Skip validation for None values (they'll use defaults)
    if value is None:
        return None
        
    # Memory thresholds
    if key in ['MEMORY_THRESHOLD_PERCENT', 'MEMORY_WARNING_PERCENT']:
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
               'CRAWLER_MAX_DEPTH', 'CRAWLER_MAX_PAGES']:
        try:
            int_value = int(value)
            if int_value < 0:
                raise ConfigValidationError(f"{key} must be non-negative")
            return int_value
        except ValueError:
            raise ConfigValidationError(f"{key} must be an integer")
    
    # Port validation
    if key == 'API_PORT':
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
               'STRUCTURED_LOGGING', 'LOG_TO_FILE', 'LOG_TO_CONSOLE',
               'ENABLE_EVENT_SYSTEM', 'API_RELOAD']:
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
    
    # URL validation for API bases
    if key in ['LLM_API_BASE', 'PB_API_BASE']:
        if not isinstance(value, str):
            raise ConfigValidationError(f"{key} must be a string")
        # Basic URL validation
        if value and not (value.startswith('http://') or value.startswith('https://')):
            raise ConfigValidationError(f"{key} must be a valid URL starting with http:// or https://")
        return value
    
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
        REQUIRED_KEYS: Set of keys that must be provided for the application to function
    """
    
    # Keys that contain sensitive values (e.g., API keys)
    SENSITIVE_KEYS = {
        'LLM_API_KEY', 'PB_API_AUTH', 'ZHIPU_API_KEY',
        'EXA_API_KEY', 'WISEFLOW_API_KEY'
    }
    
    # Keys that are required for the application to function
    REQUIRED_KEYS = {
        'PRIMARY_MODEL', 'PB_API_AUTH'
    }
    
    # Default configuration values
    DEFAULT_CONFIG = {
        # Project settings
        "PROJECT_DIR": "work_dir",
        "VERBOSE": False,
        
        # LLM settings
        "LLM_API_BASE": "https://api.openai.com/v1",
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
        
        # API settings
        "API_HOST": "0.0.0.0",
        "API_PORT": 8000,
        "API_RELOAD": False,
        "WISEFLOW_API_KEY": "dev-api-key",
        
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
        
        # Logging settings
        "LOG_LEVEL": "INFO",
        "LOG_TO_FILE": True,
        "LOG_TO_CONSOLE": True,
        "LOG_DIR": "",  # Default will be PROJECT_DIR/logs
        "STRUCTURED_LOGGING": False,
        "LOG_ROTATION": "50 MB",
        "LOG_RETENTION": "10 days",
        
        # Memory management
        "MEMORY_THRESHOLD_PERCENT": 80.0,
        "MEMORY_WARNING_PERCENT": 70.0,
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
        # Initialize configuration with default values
        self._config = self.DEFAULT_CONFIG.copy()
        self._encrypted_values = {}
        
        # Initialize encryption
        self._setup_encryption()
        
        # Load configuration from file if provided
        if config_file:
            self._load_from_file(config_file)
        
        # Override with environment variables
        self._load_from_env()
        
        # Validate configuration and set derived values
        self._validate()
        
        # Create project directory if it doesn't exist
        self._setup_project_dir()
        
        # Log configuration if verbose
        self._log_config()
    
    def _setup_encryption(self) -> None:
        """
        Set up encryption for sensitive values.
        
        This method sets up encryption for sensitive values using Fernet.
        It tries to load an encryption key from the environment, or generates
        a new one if none is provided.
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            return
            
        # Try to get encryption key from environment
        env_key = os.environ.get('WISEFLOW_ENCRYPTION_KEY')
        
        if env_key:
            try:
                # Ensure the key is properly padded for base64 decoding
                padding = 4 - (len(env_key) % 4)
                if padding < 4:
                    env_key += '=' * padding
                
                # Try to decode and use the key
                key = base64.urlsafe_b64decode(env_key)
                if len(key) != 32:  # Fernet keys must be 32 bytes
                    raise ValueError("Invalid key length")
                
                self._cipher = Fernet(env_key)
                logger.info("Using encryption key from environment")
            except Exception as e:
                logger.warning(f"Invalid encryption key from environment: {e}")
                self._generate_new_key()
        else:
            self._generate_new_key()
    
    def _generate_new_key(self) -> None:
        """
        Generate a new encryption key.
        
        This method generates a new encryption key for sensitive values.
        Note that this means encrypted values cannot be decrypted after restart
        unless the key is persisted.
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            return
            
        key = Fernet.generate_key()
        self._cipher = Fernet(key)
        
        # Log the key so it can be saved if needed
        logger.warning(
            "Generated new encryption key. To persist encrypted values, set "
            "WISEFLOW_ENCRYPTION_KEY environment variable to: "
            f"{key.decode()}"
        )
    
    def _encrypt_value(self, value: str) -> bytes:
        """
        Encrypt a sensitive value.
        
        Args:
            value: Value to encrypt
            
        Returns:
            Encrypted value as bytes
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            # If encryption is not available, store as is but warn
            logger.warning("Storing sensitive value without encryption")
            return value.encode()
            
        return self._cipher.encrypt(value.encode())
        
    def _decrypt_value(self, encrypted: bytes) -> str:
        """
        Decrypt a sensitive value.
        
        Args:
            encrypted: Encrypted value as bytes
            
        Returns:
            Decrypted value as string
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            # If encryption is not available, return as is
            return encrypted.decode()
            
        try:
            return self._cipher.decrypt(encrypted).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt value: {e}")
            return ""
    
    def _load_from_file(self, config_file: str) -> None:
        """
        Load configuration from a JSON file.
        
        Args:
            config_file: Path to the JSON configuration file
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                
                # Validate and convert values
                for key, value in file_config.items():
                    try:
                        validated_value = validate_config_value(key, value)
                        self._config[key] = validated_value
                    except ConfigValidationError as e:
                        logger.warning(f"Invalid configuration value in file: {e}")
                
                logger.info(f"Loaded configuration from {config_file}")
        except Exception as e:
            logger.error(f"Error loading configuration from {config_file}: {e}")
    
    def _load_from_env(self) -> None:
        """
        Load configuration from environment variables.
        
        This method loads configuration from environment variables and updates
        the current configuration with the values from the environment.
        """
        # Process all keys in DEFAULT_CONFIG
        for key in self.DEFAULT_CONFIG.keys():
            env_value = os.environ.get(key)
            if env_value is not None:
                try:
                    # Validate and convert the value
                    validated_value = validate_config_value(key, env_value)
                    
                    # Store sensitive values encrypted
                    if key in self.SENSITIVE_KEYS and validated_value:
                        self._encrypted_values[key] = self._encrypt_value(str(validated_value))
                    else:
                        self._config[key] = validated_value
                        
                except ConfigValidationError as e:
                    logger.warning(f"Invalid environment variable: {e}")
    
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
        if not self._config["SECONDARY_MODEL"]:
            self._config["SECONDARY_MODEL"] = self._config["PRIMARY_MODEL"]
            
        # Set VL_MODEL to PRIMARY_MODEL if not specified
        if not self._config["VL_MODEL"]:
            self._config["VL_MODEL"] = self._config["PRIMARY_MODEL"]
        
        # Set LOG_DIR to PROJECT_DIR/logs if not specified
        if not self._config["LOG_DIR"]:
            self._config["LOG_DIR"] = os.path.join(self._config["PROJECT_DIR"], "logs")
        
        # Validate LOG_LEVEL
        valid_log_levels = ['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']
        if self._config["LOG_LEVEL"] not in valid_log_levels:
            logger.warning(f"Invalid LOG_LEVEL: {self._config['LOG_LEVEL']}, using INFO")
            self._config["LOG_LEVEL"] = "INFO"
    
    def _setup_project_dir(self) -> None:
        """
        Create project directory if it doesn't exist.
        
        This method creates the project directory if it doesn't exist, based
        on the PROJECT_DIR configuration value.
        """
        if self._config["PROJECT_DIR"]:
            os.makedirs(self._config["PROJECT_DIR"], exist_ok=True)
            logger.debug(f"Ensured project directory exists: {self._config['PROJECT_DIR']}")
    
    def _log_config(self) -> None:
        """
        Log the configuration (excluding sensitive values).
        
        This method logs the configuration, excluding sensitive values, if
        verbose logging is enabled.
        """
        if self._config.get("VERBOSE", False):
            # Create a copy with sensitive values masked
            safe_config = self._config.copy()
            for key in self.SENSITIVE_KEYS:
                if self.get(key):
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
        # Check for sensitive keys
        if key in self.SENSITIVE_KEYS:
            encrypted = self._encrypted_values.get(key)
            if encrypted:
                return self._decrypt_value(encrypted)
            return self._config.get(key, default)
        
        # Return regular configuration value
        return self._config.get(key, default)
    
    def get_typed(self, key: str, default: T, expected_type: Type[T] = None) -> T:
        """
        Get a configuration value with type checking.
        
        This method returns the configuration value for the given key, or the
        default value if the key is not found or the value is not of the expected type.
        
        Args:
            key: Configuration key
            default: Default value if key is not found or invalid
            expected_type: Expected type of the value (inferred from default if not provided)
            
        Returns:
            Configuration value, or default if key is not found or invalid
        """
        value = self.get(key)
        
        if value is None:
            return default
            
        # Determine expected type from default if not provided
        if expected_type is None:
            if default is None:
                # Can't infer type from None
                return value
            expected_type = type(default)
        
        # Check if value is of expected type
        if not isinstance(value, expected_type):
            try:
                # Try to convert value to expected type
                if expected_type is bool and isinstance(value, str):
                    if value.lower() in ('true', 'yes', '1', 'y', 'on'):
                        return cast(T, True)
                    if value.lower() in ('false', 'no', '0', 'n', 'off'):
                        return cast(T, False)
                
                # Try standard conversion
                converted_value = expected_type(value)
                return cast(T, converted_value)
            except (ValueError, TypeError):
                logger.warning(
                    f"Configuration value for {key} is not of expected type {expected_type.__name__}, "
                    f"using default: {default}"
                )
                return default
        
        return cast(T, value)
    
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
            
            if key in self.SENSITIVE_KEYS and validated_value:
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
            # Get configuration as dictionary
            config_dict = self.as_dict()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2)
            logger.info(f"Configuration saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration to {filepath}: {e}")
            return False
    
    def validate_all(self, raise_on_error: bool = False) -> List[str]:
        """
        Validate all configuration values.
        
        This method validates all configuration values and returns a list of
        validation errors.
        
        Args:
            raise_on_error: Whether to raise an exception on validation error
            
        Returns:
            List of validation errors
            
        Raises:
            ConfigValidationError: If raise_on_error is True and validation fails
        """
        errors = []
        
        # Check required values
        for key in self.REQUIRED_KEYS:
            if not self.get(key):
                errors.append(f"Required configuration value missing: {key}")
        
        # Validate all values
        for key, value in self._config.items():
            try:
                validate_config_value(key, value)
            except ConfigValidationError as e:
                errors.append(str(e))
        
        # Raise exception if requested
        if errors and raise_on_error:
            raise ConfigValidationError("\n".join(errors))
        
        return errors

# Create a singleton instance for easy access
config = Config()

# Helper functions for type-safe configuration access
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
    return config.get_typed(key, default, int)

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
    return config.get_typed(key, default, float)

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
    return config.get_typed(key, default, bool)

def get_str_config(key: str, default: str = "") -> str:
    """
    Get a string configuration value with validation.
    
    This function gets a string configuration value with validation, returning
    the default value if the key is not found or the value is invalid.
    
    Args:
        key: Configuration key
        default: Default value if key is not found or invalid
        
    Returns:
        String configuration value, or default if key is not found or invalid
    """
    return config.get_typed(key, default, str)

def validate_config(raise_on_error: bool = True) -> List[str]:
    """
    Validate all critical configuration settings.
    
    This function validates all critical configuration settings and returns
    a list of validation errors.
    
    Args:
        raise_on_error: Whether to raise an exception on validation error
        
    Returns:
        List of validation errors
        
    Raises:
        ConfigValidationError: If raise_on_error is True and validation fails
    """
    return config.validate_all(raise_on_error)

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

# Logging configuration
LOG_LEVEL = config.get("LOG_LEVEL", "INFO")
LOG_TO_FILE = get_bool_config("LOG_TO_FILE", True)
LOG_TO_CONSOLE = get_bool_config("LOG_TO_CONSOLE", True)
LOG_DIR = config.get("LOG_DIR", os.path.join(PROJECT_DIR, "logs"))
STRUCTURED_LOGGING = get_bool_config("STRUCTURED_LOGGING", False)
LOG_ROTATION = config.get("LOG_ROTATION", "50 MB")
LOG_RETENTION = config.get("LOG_RETENTION", "10 days")

# Memory management
MEMORY_THRESHOLD_PERCENT = get_float_config("MEMORY_THRESHOLD_PERCENT", 80.0)
MEMORY_WARNING_PERCENT = get_float_config("MEMORY_WARNING_PERCENT", 70.0)

