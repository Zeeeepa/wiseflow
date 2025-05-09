"""
Configuration validator for LLM integrations.

This module provides functionality to validate LLM configuration settings
and ensure that all required settings are properly configured.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
import json

from core.llms.auth import get_auth_manager, AuthenticationError

logger = logging.getLogger(__name__)
auth_manager = get_auth_manager()

class ConfigValidationError(Exception):
    """Exception raised for configuration validation errors."""
    pass

def validate_llm_config() -> Tuple[bool, List[str]]:
    """
    Validate LLM configuration settings.
    
    This function validates all LLM configuration settings and returns a list
    of validation errors if any are found.
    
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check if at least one provider is configured
    providers = ["openai", "anthropic", "azure", "litellm", "cohere", "ai21"]
    configured_providers = []
    
    for provider in providers:
        is_valid, error = auth_manager.validate_auth(provider)
        if is_valid:
            configured_providers.append(provider)
    
    if not configured_providers:
        errors.append("No LLM providers are configured. At least one provider must be configured.")
    else:
        logger.info(f"Configured providers: {', '.join(configured_providers)}")
    
    # Check if PRIMARY_MODEL is set
    primary_model = os.environ.get("PRIMARY_MODEL", "")
    if not primary_model:
        errors.append("PRIMARY_MODEL environment variable is not set.")
    
    # Check if LLM_CONCURRENT_NUMBER is valid
    try:
        concurrent_number = int(os.environ.get("LLM_CONCURRENT_NUMBER", "1"))
        if concurrent_number < 1:
            errors.append("LLM_CONCURRENT_NUMBER must be at least 1.")
    except ValueError:
        errors.append("LLM_CONCURRENT_NUMBER must be an integer.")
    
    # Check if API base URL is valid if provided
    api_base = os.environ.get("LLM_API_BASE", "")
    if api_base and not (api_base.startswith("http://") or api_base.startswith("https://")):
        errors.append("LLM_API_BASE must be a valid URL starting with http:// or https://.")
    
    return len(errors) == 0, errors

def validate_webhook_config() -> Tuple[bool, List[str]]:
    """
    Validate webhook configuration settings.
    
    This function validates all webhook configuration settings and returns a list
    of validation errors if any are found.
    
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check if WEBHOOK_SECRET_KEY is set
    webhook_secret = os.environ.get("WEBHOOK_SECRET_KEY", "")
    if not webhook_secret or webhook_secret == "wiseflow-webhook-secret":
        errors.append("WEBHOOK_SECRET_KEY is not set or is using the default value.")
    
    return len(errors) == 0, errors

def validate_api_server_config() -> Tuple[bool, List[str]]:
    """
    Validate API server configuration settings.
    
    This function validates all API server configuration settings and returns a list
    of validation errors if any are found.
    
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check if WISEFLOW_API_KEY is set
    api_key = os.environ.get("WISEFLOW_API_KEY", "")
    if not api_key or api_key == "dev-api-key":
        errors.append("WISEFLOW_API_KEY is not set or is using the default value.")
    
    # Check if API_PORT is valid
    try:
        api_port = int(os.environ.get("API_PORT", "8000"))
        if not (1024 <= api_port <= 65535):
            errors.append("API_PORT must be between 1024 and 65535.")
    except ValueError:
        errors.append("API_PORT must be an integer.")
    
    return len(errors) == 0, errors

def validate_all_config() -> Tuple[bool, Dict[str, List[str]]]:
    """
    Validate all configuration settings.
    
    This function validates all configuration settings and returns a dictionary
    of validation errors by category if any are found.
    
    Returns:
        Tuple of (is_valid, error_messages_by_category)
    """
    all_errors = {}
    
    # Validate LLM configuration
    llm_valid, llm_errors = validate_llm_config()
    if not llm_valid:
        all_errors["llm"] = llm_errors
    
    # Validate webhook configuration
    webhook_valid, webhook_errors = validate_webhook_config()
    if not webhook_valid:
        all_errors["webhook"] = webhook_errors
    
    # Validate API server configuration
    api_valid, api_errors = validate_api_server_config()
    if not api_valid:
        all_errors["api"] = api_errors
    
    return len(all_errors) == 0, all_errors

def print_validation_results(is_valid: bool, errors_by_category: Dict[str, List[str]]) -> None:
    """
    Print validation results.
    
    This function prints validation results in a user-friendly format.
    
    Args:
        is_valid: Whether all configuration is valid
        errors_by_category: Dictionary of validation errors by category
    """
    if is_valid:
        logger.info("All configuration settings are valid.")
        return
    
    logger.error("Configuration validation failed:")
    
    for category, errors in errors_by_category.items():
        logger.error(f"  {category.upper()} configuration errors:")
        for error in errors:
            logger.error(f"    - {error}")
    
    logger.error("Please fix these configuration errors before continuing.")

def validate_and_print() -> bool:
    """
    Validate all configuration settings and print results.
    
    This function validates all configuration settings, prints the results,
    and returns whether all configuration is valid.
    
    Returns:
        Whether all configuration is valid
    """
    is_valid, errors_by_category = validate_all_config()
    print_validation_results(is_valid, errors_by_category)
    return is_valid

