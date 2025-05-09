#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Configuration Service.

This module provides a centralized configuration service for accessing and
managing application configuration.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union, Set
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class ConfigurationValidationError(Exception):
    """Exception raised for configuration validation errors."""
    pass

class ConfigurationService:
    """
    Configuration service for WiseFlow.
    
    This class provides a centralized way to access and manage application
    configuration from various sources, including environment variables,
    configuration files, and default values.
    """
    
    # Set of keys that contain sensitive values
    SENSITIVE_KEYS: Set[str] = {
        'LLM_API_KEY', 'PB_API_AUTH', 'ZHIPU_API_KEY',
        'EXA_API_KEY', 'WISEFLOW_API_KEY'
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
        Initialize the configuration service.
        
        Args:
            config_file: Optional path to a configuration file
        """
        self._config: Dict[str, Any] = self.DEFAULT_CONFIG.copy()
        self._schema: Dict[str, Dict[str, Any]] = {}
        self._env_prefix: str = ""
        
        # Load configuration from file if provided
        if config_file:
            self._load_from_file(config_file)
        
        # Load configuration from environment variables
        self._load_from_env()
        
        # Validate configuration
        self._validate()
        
        # Set up project directory
        self._setup_project_dir()
        
        # Log configuration if verbose
        self._log_config()
        
        logger.info("Configuration service initialized")
    
    def _load_from_file(self, config_file: str) -> None:
        """
        Load configuration from a file.
        
        Args:
            config_file: Path to the configuration file
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                self._config.update(file_config)
                logger.info(f"Loaded configuration from {config_file}")
        except Exception as e:
            logger.error(f"Error loading configuration from {config_file}: {e}")
    
    def _load_from_env(self) -> None:
        """
        Load configuration from environment variables.
        
        Environment variables take precedence over configuration files and defaults.
        """
        # Load .env file if it exists
        env_path = Path('.env')
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Loaded environment variables from {env_path}")
        
        # Update configuration from environment variables
        for key in self._config.keys():
            env_key = f"{self._env_prefix}{key}" if self._env_prefix else key
            env_value = os.environ.get(env_key)
            
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
        """
        Validate the configuration and set derived values.
        
        Raises:
            ConfigurationValidationError: If validation fails
        """
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
        
        # Validate LOG_LEVEL
        valid_log_levels = ['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']
        if self._config["LOG_LEVEL"] not in valid_log_levels:
            logger.warning(f"Invalid LOG_LEVEL: {self._config['LOG_LEVEL']}, using INFO")
            self._config["LOG_LEVEL"] = "INFO"
        
        # Validate numeric values
        try:
            self._validate_numeric("LLM_CONCURRENT_NUMBER", min_value=1)
            self._validate_numeric("MAX_CONCURRENT_TASKS", min_value=1)
            self._validate_numeric("CRAWLER_TIMEOUT", min_value=0)
            self._validate_numeric("CRAWLER_MAX_DEPTH", min_value=1)
            self._validate_numeric("CRAWLER_MAX_PAGES", min_value=1)
            self._validate_numeric("MAX_CONCURRENT_REQUESTS", min_value=1)
            self._validate_numeric("AUTO_SHUTDOWN_IDLE_TIME", min_value=0)
            self._validate_numeric("AUTO_SHUTDOWN_CHECK_INTERVAL", min_value=0)
        except ConfigurationValidationError as e:
            logger.warning(f"Configuration validation error: {e}")
    
    def _validate_numeric(self, key: str, min_value: Optional[float] = None, max_value: Optional[float] = None) -> None:
        """
        Validate a numeric configuration value.
        
        Args:
            key: Configuration key
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Raises:
            ConfigurationValidationError: If validation fails
        """
        value = self._config.get(key)
        
        if value is None:
            return
        
        try:
            if isinstance(value, str):
                if '.' in value:
                    value = float(value)
                else:
                    value = int(value)
                self._config[key] = value
            
            if min_value is not None and value < min_value:
                raise ConfigurationValidationError(f"{key} must be at least {min_value}")
            
            if max_value is not None and value > max_value:
                raise ConfigurationValidationError(f"{key} must be at most {max_value}")
                
        except ValueError:
            raise ConfigurationValidationError(f"{key} must be a number")
    
    def _setup_project_dir(self) -> None:
        """
        Create project directory if it doesn't exist.
        """
        if self._config["PROJECT_DIR"]:
            os.makedirs(self._config["PROJECT_DIR"], exist_ok=True)
            
            # Create logs directory if LOG_DIR is not specified
            if not self._config["LOG_DIR"]:
                log_dir = os.path.join(self._config["PROJECT_DIR"], "logs")
                self._config["LOG_DIR"] = log_dir
                os.makedirs(log_dir, exist_ok=True)
    
    def _log_config(self) -> None:
        """
        Log the configuration (excluding sensitive values).
        """
        if self._config.get("VERBOSE", False):
            # Create a copy with sensitive values masked
            safe_config = self._config.copy()
            for key in self.SENSITIVE_KEYS:
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
            Configuration value, or default if key is not found
        """
        return self._config.get(key, default)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """
        Get an integer configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key is not found or invalid
            
        Returns:
            Integer configuration value, or default if key is not found or invalid
        """
        try:
            value = self.get(key)
            if value is None:
                return default
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Invalid integer value for {key}, using default {default}")
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        Get a float configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key is not found or invalid
            
        Returns:
            Float configuration value, or default if key is not found or invalid
        """
        try:
            value = self.get(key)
            if value is None:
                return default
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Invalid float value for {key}, using default {default}")
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Get a boolean configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key is not found or invalid
            
        Returns:
            Boolean configuration value, or default if key is not found or invalid
        """
        value = self.get(key)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'y')
        return bool(value)
    
    def get_list(self, key: str, default: Optional[List[Any]] = None) -> List[Any]:
        """
        Get a list configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key is not found
            
        Returns:
            List configuration value, or default if key is not found
        """
        value = self.get(key)
        if value is None:
            return default or []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value.split(',')
        return [value]
    
    def get_dict(self, key: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get a dictionary configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key is not found
            
        Returns:
            Dictionary configuration value, or default if key is not found
        """
        value = self.get(key)
        if value is None:
            return default or {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.warning(f"Invalid dictionary value for {key}")
                return default or {}
        return default or {}
    
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
        Save the configuration to a file.
        
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
    
    def set_schema(self, schema: Dict[str, Dict[str, Any]]) -> None:
        """
        Set the configuration schema.
        
        Args:
            schema: Configuration schema
        """
        self._schema = schema
    
    def validate_schema(self) -> List[str]:
        """
        Validate the configuration against the schema.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        for key, schema in self._schema.items():
            if key not in self._config and schema.get('required', False):
                errors.append(f"Required configuration key '{key}' is missing")
                continue
                
            if key not in self._config:
                continue
                
            value = self._config[key]
            value_type = schema.get('type')
            
            if value_type and not self._check_type(value, value_type):
                errors.append(f"Configuration key '{key}' has invalid type, expected {value_type}")
                
            if 'min' in schema and value < schema['min']:
                errors.append(f"Configuration key '{key}' is less than minimum value {schema['min']}")
                
            if 'max' in schema and value > schema['max']:
                errors.append(f"Configuration key '{key}' is greater than maximum value {schema['max']}")
                
            if 'enum' in schema and value not in schema['enum']:
                errors.append(f"Configuration key '{key}' has invalid value, expected one of {schema['enum']}")
                
            if 'pattern' in schema and isinstance(value, str):
                import re
                if not re.match(schema['pattern'], value):
                    errors.append(f"Configuration key '{key}' does not match pattern {schema['pattern']}")
        
        return errors
    
    def _check_type(self, value: Any, expected_type: Union[str, List[str]]) -> bool:
        """
        Check if a value has the expected type.
        
        Args:
            value: Value to check
            expected_type: Expected type or list of types
            
        Returns:
            True if the value has the expected type, False otherwise
        """
        if isinstance(expected_type, list):
            return any(self._check_type(value, t) for t in expected_type)
            
        if expected_type == 'string':
            return isinstance(value, str)
        elif expected_type == 'number':
            return isinstance(value, (int, float))
        elif expected_type == 'integer':
            return isinstance(value, int)
        elif expected_type == 'boolean':
            return isinstance(value, bool)
        elif expected_type == 'array':
            return isinstance(value, list)
        elif expected_type == 'object':
            return isinstance(value, dict)
        elif expected_type == 'null':
            return value is None
        else:
            return False

# Create a singleton instance
configuration_service = ConfigurationService()

def get_configuration_service() -> ConfigurationService:
    """
    Get the global configuration service instance.
    
    Returns:
        The global configuration service instance
    """
    return configuration_service

