"""
Configuration module for Wiseflow.

This module provides a centralized configuration system for the Wiseflow application.
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
    load_dotenv(env_path)
else:
    logger.warning(f".env file not found at {env_path}")

class Config:
    """
    Configuration class for Wiseflow.
    
    This class provides a centralized configuration system for the Wiseflow application,
    combining environment variables, configuration files, and default values.
    """
    
    # Default configuration values
    DEFAULT_CONFIG = {
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
        
        # Crawler settings
        "CRAWLER_TIMEOUT": 60,
        "CRAWLER_MAX_DEPTH": 3,
        "CRAWLER_MAX_PAGES": 100,
        
        # Task settings
        "MAX_CONCURRENT_TASKS": 4,
        "AUTO_SHUTDOWN_ENABLED": False,
        "AUTO_SHUTDOWN_IDLE_TIME": 3600,
        "AUTO_SHUTDOWN_CHECK_INTERVAL": 300,
        
        # Feature flags
        "ENABLE_MULTIMODAL": False,
        "ENABLE_KNOWLEDGE_GRAPH": False,
        "ENABLE_INSIGHTS": True,
        "ENABLE_REFERENCES": True
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
        """Validate the configuration."""
        # Check required values
        if not self._config["PRIMARY_MODEL"]:
            logger.warning("PRIMARY_MODEL not set, this may cause issues with LLM functionality")
        
        if not self._config["PB_API_AUTH"]:
            logger.warning("PB_API_AUTH not set, this may cause issues with database access")
        
        # Create project directory if it doesn't exist
        if self._config["PROJECT_DIR"]:
            os.makedirs(self._config["PROJECT_DIR"], exist_ok=True)
    
    def _log_config(self) -> None:
        """Log the configuration (excluding sensitive values)."""
        if self._config.get("VERBOSE", False):
            # Create a copy with sensitive values masked
            safe_config = self._config.copy()
            for key in ["LLM_API_KEY", "PB_API_AUTH", "ZHIPU_API_KEY"]:
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

# Create a singleton instance for easy access
config = Config()

