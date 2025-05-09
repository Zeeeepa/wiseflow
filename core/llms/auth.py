"""
Authentication module for LLM API integrations.

This module provides a unified way to handle authentication for different LLM providers.
It centralizes API key management, validation, and error handling.
"""

import os
import logging
from typing import Dict, Optional, Any, Tuple
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Exception raised for authentication errors."""
    pass

class LLMAuthManager:
    """Manager for LLM API authentication."""
    
    def __init__(self):
        """Initialize the authentication manager."""
        self.api_keys = {}
        self.api_bases = {}
        self.load_from_env()
    
    def load_from_env(self) -> None:
        """Load API keys and base URLs from environment variables."""
        # OpenAI
        self.api_keys["openai"] = os.environ.get("OPENAI_API_KEY", os.environ.get("LLM_API_KEY", ""))
        self.api_bases["openai"] = os.environ.get("OPENAI_API_BASE", os.environ.get("LLM_API_BASE", ""))
        
        # Anthropic
        self.api_keys["anthropic"] = os.environ.get("ANTHROPIC_API_KEY", "")
        self.api_bases["anthropic"] = os.environ.get("ANTHROPIC_API_BASE", "")
        
        # Azure OpenAI
        self.api_keys["azure"] = os.environ.get("AZURE_OPENAI_API_KEY", "")
        self.api_bases["azure"] = os.environ.get("AZURE_OPENAI_API_BASE", "")
        
        # LiteLLM
        self.api_keys["litellm"] = os.environ.get("LITELLM_API_KEY", "")
        
        # Cohere
        self.api_keys["cohere"] = os.environ.get("COHERE_API_KEY", "")
        
        # AI21
        self.api_keys["ai21"] = os.environ.get("AI21_API_KEY", "")
        
        # Log configured providers (without showing the actual keys)
        configured_providers = [provider for provider, key in self.api_keys.items() if key]
        if configured_providers:
            logger.info(f"Configured API keys for: {', '.join(configured_providers)}")
        else:
            logger.warning("No API keys configured for any provider")
    
    def get_api_key(self, provider: str) -> str:
        """
        Get the API key for a specific provider.
        
        Args:
            provider: Provider name (e.g., 'openai', 'anthropic')
            
        Returns:
            API key for the provider
            
        Raises:
            AuthenticationError: If no API key is configured for the provider
        """
        api_key = self.api_keys.get(provider, "")
        if not api_key:
            raise AuthenticationError(f"No API key configured for {provider}")
        return api_key
    
    def get_api_base(self, provider: str) -> str:
        """
        Get the API base URL for a specific provider.
        
        Args:
            provider: Provider name (e.g., 'openai', 'anthropic')
            
        Returns:
            API base URL for the provider, or empty string if not configured
        """
        return self.api_bases.get(provider, "")
    
    def get_auth_config(self, provider: str) -> Dict[str, str]:
        """
        Get the authentication configuration for a specific provider.
        
        Args:
            provider: Provider name (e.g., 'openai', 'anthropic')
            
        Returns:
            Dictionary with 'api_key' and 'api_base' (if configured)
            
        Raises:
            AuthenticationError: If no API key is configured for the provider
        """
        api_key = self.get_api_key(provider)
        api_base = self.get_api_base(provider)
        
        config = {"api_key": api_key}
        if api_base:
            config["api_base"] = api_base
        
        return config
    
    def validate_auth(self, provider: str) -> Tuple[bool, str]:
        """
        Validate authentication for a specific provider.
        
        Args:
            provider: Provider name (e.g., 'openai', 'anthropic')
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            api_key = self.get_api_key(provider)
            if not api_key:
                return False, f"No API key configured for {provider}"
            
            # Basic validation - just check if the key exists and has a reasonable length
            if len(api_key) < 8:
                return False, f"API key for {provider} is too short"
            
            return True, ""
        except AuthenticationError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error validating {provider} authentication: {str(e)}"
    
    def get_fallback_provider(self, primary_provider: str) -> Optional[str]:
        """
        Get a fallback provider if the primary provider is not available.
        
        Args:
            primary_provider: Primary provider name
            
        Returns:
            Fallback provider name, or None if no fallback is available
        """
        # Priority order for fallbacks
        fallback_order = {
            "openai": ["azure", "litellm", "anthropic", "cohere", "ai21"],
            "azure": ["openai", "litellm", "anthropic", "cohere", "ai21"],
            "anthropic": ["openai", "azure", "litellm", "cohere", "ai21"],
            "litellm": ["openai", "azure", "anthropic", "cohere", "ai21"],
            "cohere": ["openai", "azure", "anthropic", "litellm", "ai21"],
            "ai21": ["openai", "azure", "anthropic", "litellm", "cohere"]
        }
        
        # Get fallback options for the primary provider
        fallback_options = fallback_order.get(primary_provider, [])
        
        # Find the first fallback option with a configured API key
        for provider in fallback_options:
            if self.api_keys.get(provider, ""):
                return provider
        
        return None

# Create a singleton instance
auth_manager = LLMAuthManager()

def get_auth_manager() -> LLMAuthManager:
    """
    Get the authentication manager instance.
    
    Returns:
        Authentication manager instance
    """
    return auth_manager

