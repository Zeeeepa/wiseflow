"""
Configuration module for LLM integration.

This module provides a centralized configuration system for LLM integration,
with support for environment variable overrides and default values.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Union, List

# Initialize logger
logger = logging.getLogger(__name__)

class LLMConfig:
    """
    Centralized configuration for LLM integration.
    
    This class provides a centralized configuration system for LLM integration,
    with support for environment variable overrides and default values.
    """
    
    # Default configuration values
    DEFAULT_CONFIG = {
        # Model settings
        "PRIMARY_MODEL": "gpt-3.5-turbo",
        "SECONDARY_MODEL": "gpt-3.5-turbo-16k",
        "DEFAULT_TEMPERATURE": 0.7,
        "DEFAULT_MAX_TOKENS": 1000,
        
        # API settings
        "LLM_API_BASE": "",
        "LLM_API_KEY": "",
        "LLM_CONCURRENT_NUMBER": 5,
        
        # Provider-specific API keys
        "ANTHROPIC_API_KEY": "",
        "AZURE_API_KEY": "",
        "AZURE_API_BASE": "",
        
        # Error handling settings
        "MAX_RETRIES": 3,
        "INITIAL_BACKOFF": 1.0,
        "BACKOFF_MULTIPLIER": 2.0,
        "MAX_BACKOFF": 60.0,
        
        # Caching settings
        "CACHE_ENABLED": True,
        "CACHE_DIR": "",
        "CACHE_TTL": 3600,
        "MEMORY_CACHE_SIZE": 1000,
        "DISK_CACHE_SIZE_MB": 100,
        
        # Logging settings
        "LOG_LEVEL": "INFO",
        "LOG_LLM_REQUESTS": False,
        "LOG_LLM_RESPONSES": False,
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the LLM configuration.
        
        Args:
            config_path: Optional path to a JSON configuration file
        """
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Load configuration from file if provided
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    file_config = json.load(f)
                    self.config.update(file_config)
                    logger.info(f"Loaded LLM configuration from {config_path}")
            except Exception as e:
                logger.error(f"Error loading configuration from {config_path}: {e}")
        
        # Override with environment variables
        self._load_from_env()
    
    def _load_from_env(self):
        """
        Load configuration from environment variables.
        
        Environment variables take precedence over configuration file values.
        """
        for key in self.config:
            env_value = os.environ.get(key)
            if env_value is not None:
                # Convert string values to appropriate types
                if isinstance(self.config[key], bool):
                    self.config[key] = env_value.lower() in ("true", "1", "yes", "y")
                elif isinstance(self.config[key], int):
                    try:
                        self.config[key] = int(env_value)
                    except ValueError:
                        logger.warning(f"Invalid integer value for {key}: {env_value}")
                elif isinstance(self.config[key], float):
                    try:
                        self.config[key] = float(env_value)
                    except ValueError:
                        logger.warning(f"Invalid float value for {key}: {env_value}")
                else:
                    self.config[key] = env_value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key is not found
            
        Returns:
            Configuration value
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value
    
    def update(self, config_dict: Dict[str, Any]) -> None:
        """
        Update multiple configuration values.
        
        Args:
            config_dict: Dictionary of configuration values
        """
        self.config.update(config_dict)
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.
        
        Returns:
            Dictionary of all configuration values
        """
        return self.config.copy()
    
    def save(self, config_path: str) -> bool:
        """
        Save the current configuration to a file.
        
        Args:
            config_path: Path to save the configuration file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(config_path, "w") as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved LLM configuration to {config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration to {config_path}: {e}")
            return False
    
    def get_model_config(self, model: str) -> Dict[str, Any]:
        """
        Get configuration for a specific model.
        
        Args:
            model: Model name
            
        Returns:
            Dictionary of model-specific configuration values
        """
        # Get model-specific configuration if available
        model_key = f"MODEL_{model.replace('-', '_').upper()}"
        model_config = self.config.get(model_key, {})
        
        # Add general model settings
        if model == self.get("PRIMARY_MODEL"):
            model_config["is_primary"] = True
        elif model == self.get("SECONDARY_MODEL"):
            model_config["is_secondary"] = True
        
        return model_config
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """
        Get configuration for a specific provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Dictionary of provider-specific configuration values
        """
        # Get provider-specific configuration if available
        provider_key = f"PROVIDER_{provider.upper()}"
        provider_config = self.config.get(provider_key, {})
        
        # Add provider-specific API keys
        if provider.lower() == "openai":
            provider_config["api_key"] = self.get("LLM_API_KEY")
            provider_config["api_base"] = self.get("LLM_API_BASE")
        elif provider.lower() == "anthropic":
            provider_config["api_key"] = self.get("ANTHROPIC_API_KEY")
        elif provider.lower() == "azure":
            provider_config["api_key"] = self.get("AZURE_API_KEY")
            provider_config["api_base"] = self.get("AZURE_API_BASE")
        
        return provider_config

# Create a singleton instance
llm_config = LLMConfig()

def get_config() -> LLMConfig:
    """
    Get the LLM configuration singleton instance.
    
    Returns:
        LLMConfig instance
    """
    return llm_config

def initialize_config(config_path: Optional[str] = None) -> LLMConfig:
    """
    Initialize the LLM configuration.
    
    Args:
        config_path: Optional path to a JSON configuration file
        
    Returns:
        LLMConfig instance
    """
    global llm_config
    llm_config = LLMConfig(config_path)
    return llm_config

