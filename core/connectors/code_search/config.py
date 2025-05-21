"""
Configuration manager for the Code Search Connector.

This module provides a centralized configuration management for the Code Search Connector,
allowing for easy configuration via environment variables or configuration files.
"""

import os
from typing import Dict, Any, Optional, List, Union
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ServiceConfig:
    """Configuration for a specific code search service."""
    
    # API configuration
    api_key: str = ""
    api_url: str = ""
    
    # Rate limiting
    rate_limit: int = 60  # requests per minute
    rate_limit_pause: int = 60  # seconds to pause when rate limited
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: int = 5  # base delay in seconds
    
    # Cache configuration
    cache_enabled: bool = True
    cache_ttl: int = 3600  # seconds
    
    # Additional service-specific settings
    additional_settings: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CodeSearchConfig:
    """Configuration for the Code Search Connector."""
    
    # Default service to use
    default_service: str = "github"
    
    # Concurrency settings
    concurrency: int = 5
    
    # Cache settings
    cache_enabled: bool = True
    cache_dir: str = ""
    memory_cache_size: int = 100  # number of items
    disk_cache_size: int = 1000  # number of items
    
    # Service-specific configurations
    services: Dict[str, ServiceConfig] = field(default_factory=dict)
    
    # Logging
    log_level: str = "INFO"
    
    def __post_init__(self):
        """Initialize default service configurations if not provided."""
        # Ensure we have configurations for all supported services
        for service in ["github", "gitlab", "bitbucket", "sourcegraph", "searchcode"]:
            if service not in self.services:
                self.services[service] = ServiceConfig()
                
                # Set service-specific defaults
                if service == "github":
                    self.services[service].api_url = "https://api.github.com"
                elif service == "gitlab":
                    self.services[service].api_url = "https://gitlab.com/api/v4"
                elif service == "bitbucket":
                    self.services[service].api_url = "https://api.bitbucket.org/2.0"
                elif service == "sourcegraph":
                    self.services[service].api_url = "https://sourcegraph.com/.api"
                elif service == "searchcode":
                    self.services[service].api_url = "https://searchcode.com/api"

class ConfigManager:
    """Manager for Code Search Connector configuration."""
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_dict: Optional configuration dictionary to override defaults
        """
        self.config = self._load_config(config_dict)
    
    def _load_config(self, config_dict: Optional[Dict[str, Any]] = None) -> CodeSearchConfig:
        """
        Load configuration from environment variables and/or config dictionary.
        
        Args:
            config_dict: Optional configuration dictionary to override defaults
            
        Returns:
            CodeSearchConfig: Configuration object
        """
        # Start with default configuration
        config = CodeSearchConfig()
        
        # Override with environment variables
        self._load_from_env(config)
        
        # Override with provided config dictionary
        if config_dict:
            self._load_from_dict(config, config_dict)
        
        # Validate configuration
        self._validate_config(config)
        
        return config
    
    def _load_from_env(self, config: CodeSearchConfig) -> None:
        """
        Load configuration from environment variables.
        
        Args:
            config: Configuration object to update
        """
        # General settings
        config.default_service = os.environ.get("CODE_SEARCH_DEFAULT_SERVICE", config.default_service)
        config.concurrency = int(os.environ.get("CODE_SEARCH_CONCURRENCY", config.concurrency))
        config.cache_enabled = os.environ.get("CODE_SEARCH_CACHE_ENABLED", str(config.cache_enabled)).lower() == "true"
        config.cache_dir = os.environ.get("CODE_SEARCH_CACHE_DIR", config.cache_dir)
        config.memory_cache_size = int(os.environ.get("CODE_SEARCH_MEMORY_CACHE_SIZE", config.memory_cache_size))
        config.disk_cache_size = int(os.environ.get("CODE_SEARCH_DISK_CACHE_SIZE", config.disk_cache_size))
        config.log_level = os.environ.get("CODE_SEARCH_LOG_LEVEL", config.log_level)
        
        # Service-specific settings
        for service in config.services:
            service_config = config.services[service]
            
            # API configuration
            service_config.api_key = os.environ.get(f"{service.upper()}_TOKEN", service_config.api_key)
            service_config.api_url = os.environ.get(f"{service.upper()}_API_URL", service_config.api_url)
            
            # Rate limiting
            service_config.rate_limit = int(os.environ.get(f"{service.upper()}_RATE_LIMIT", service_config.rate_limit))
            service_config.rate_limit_pause = int(os.environ.get(f"{service.upper()}_RATE_LIMIT_PAUSE", service_config.rate_limit_pause))
            
            # Retry configuration
            service_config.max_retries = int(os.environ.get(f"{service.upper()}_MAX_RETRIES", service_config.max_retries))
            service_config.retry_delay = int(os.environ.get(f"{service.upper()}_RETRY_DELAY", service_config.retry_delay))
            
            # Cache configuration
            service_config.cache_enabled = os.environ.get(f"{service.upper()}_CACHE_ENABLED", str(service_config.cache_enabled)).lower() == "true"
            service_config.cache_ttl = int(os.environ.get(f"{service.upper()}_CACHE_TTL", service_config.cache_ttl))
    
    def _load_from_dict(self, config: CodeSearchConfig, config_dict: Dict[str, Any]) -> None:
        """
        Load configuration from a dictionary.
        
        Args:
            config: Configuration object to update
            config_dict: Configuration dictionary
        """
        # General settings
        if "default_service" in config_dict:
            config.default_service = config_dict["default_service"]
        if "concurrency" in config_dict:
            config.concurrency = config_dict["concurrency"]
        if "cache_enabled" in config_dict:
            config.cache_enabled = config_dict["cache_enabled"]
        if "cache_dir" in config_dict:
            config.cache_dir = config_dict["cache_dir"]
        if "memory_cache_size" in config_dict:
            config.memory_cache_size = config_dict["memory_cache_size"]
        if "disk_cache_size" in config_dict:
            config.disk_cache_size = config_dict["disk_cache_size"]
        if "log_level" in config_dict:
            config.log_level = config_dict["log_level"]
        
        # Service-specific settings
        if "services" in config_dict:
            for service, service_dict in config_dict["services"].items():
                if service not in config.services:
                    config.services[service] = ServiceConfig()
                
                service_config = config.services[service]
                
                # Update service configuration from dictionary
                if "api_key" in service_dict:
                    service_config.api_key = service_dict["api_key"]
                if "api_url" in service_dict:
                    service_config.api_url = service_dict["api_url"]
                if "rate_limit" in service_dict:
                    service_config.rate_limit = service_dict["rate_limit"]
                if "rate_limit_pause" in service_dict:
                    service_config.rate_limit_pause = service_dict["rate_limit_pause"]
                if "max_retries" in service_dict:
                    service_config.max_retries = service_dict["max_retries"]
                if "retry_delay" in service_dict:
                    service_config.retry_delay = service_dict["retry_delay"]
                if "cache_enabled" in service_dict:
                    service_config.cache_enabled = service_dict["cache_enabled"]
                if "cache_ttl" in service_dict:
                    service_config.cache_ttl = service_dict["cache_ttl"]
                if "additional_settings" in service_dict:
                    service_config.additional_settings.update(service_dict["additional_settings"])
    
    def _validate_config(self, config: CodeSearchConfig) -> None:
        """
        Validate the configuration.
        
        Args:
            config: Configuration object to validate
        """
        # Validate default service
        if config.default_service not in config.services:
            logger.warning(f"Default service '{config.default_service}' not found in configured services. Using 'github' as default.")
            config.default_service = "github"
        
        # Validate concurrency
        if config.concurrency < 1:
            logger.warning(f"Invalid concurrency value: {config.concurrency}. Setting to 1.")
            config.concurrency = 1
        
        # Validate cache settings
        if config.cache_enabled and not config.cache_dir:
            # Use a default cache directory if not specified
            config.cache_dir = os.path.join(os.path.expanduser("~"), ".wiseflow", "cache", "code_search")
            logger.info(f"No cache directory specified. Using default: {config.cache_dir}")
        
        # Validate service configurations
        for service, service_config in config.services.items():
            # Validate rate limit
            if service_config.rate_limit < 1:
                logger.warning(f"Invalid rate limit for {service}: {service_config.rate_limit}. Setting to 60.")
                service_config.rate_limit = 60
            
            # Validate retry settings
            if service_config.max_retries < 0:
                logger.warning(f"Invalid max retries for {service}: {service_config.max_retries}. Setting to 3.")
                service_config.max_retries = 3
            
            if service_config.retry_delay < 1:
                logger.warning(f"Invalid retry delay for {service}: {service_config.retry_delay}. Setting to 5.")
                service_config.retry_delay = 5
            
            # Validate cache TTL
            if service_config.cache_ttl < 0:
                logger.warning(f"Invalid cache TTL for {service}: {service_config.cache_ttl}. Setting to 3600.")
                service_config.cache_ttl = 3600
    
    def get_config(self) -> CodeSearchConfig:
        """
        Get the configuration.
        
        Returns:
            CodeSearchConfig: Configuration object
        """
        return self.config
    
    def get_service_config(self, service: str) -> ServiceConfig:
        """
        Get configuration for a specific service.
        
        Args:
            service: Service name
            
        Returns:
            ServiceConfig: Service configuration
        """
        if service not in self.config.services:
            logger.warning(f"Service '{service}' not found in configured services. Using default service '{self.config.default_service}'.")
            service = self.config.default_service
        
        return self.config.services[service]
    
    def update_config(self, config_dict: Dict[str, Any]) -> None:
        """
        Update the configuration.
        
        Args:
            config_dict: Configuration dictionary
        """
        self._load_from_dict(self.config, config_dict)
        self._validate_config(self.config)
"""

