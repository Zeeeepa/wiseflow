#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Environment variable utilities for WiseFlow.

This module provides utilities for working with environment variables,
including loading from .env files, validating environment variables,
and converting environment variables to appropriate types.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union, TypeVar, Type, cast
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

logger = logging.getLogger(__name__)

T = TypeVar('T')

def load_env_files(env_files: Optional[List[str]] = None) -> None:
    """
    Load environment variables from .env files.
    
    This function loads environment variables from the specified .env files,
    or from the default .env file in the project root if no files are specified.
    
    Args:
        env_files: Optional list of .env file paths to load
    """
    if env_files:
        for env_file in env_files:
            if os.path.exists(env_file):
                logger.info(f"Loading environment variables from {env_file}")
                load_dotenv(env_file)
            else:
                logger.warning(f"Environment file not found: {env_file}")
    else:
        # Try to find .env file in project root
        env_path = find_dotenv(usecwd=True)
        if env_path:
            logger.info(f"Loading environment variables from {env_path}")
            load_dotenv(env_path)
        else:
            logger.info("No .env file found")

def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get an environment variable.
    
    This function gets an environment variable, returning the default value
    if the variable is not set.
    
    Args:
        key: Environment variable name
        default: Default value if variable is not set
        
    Returns:
        Environment variable value, or default if not set
    """
    return os.environ.get(key, default)

def get_env_int(key: str, default: Optional[int] = None) -> Optional[int]:
    """
    Get an integer environment variable.
    
    This function gets an integer environment variable, returning the default value
    if the variable is not set or is not a valid integer.
    
    Args:
        key: Environment variable name
        default: Default value if variable is not set or invalid
        
    Returns:
        Integer environment variable value, or default if not set or invalid
    """
    value = os.environ.get(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid integer value for environment variable {key}: {value}")
        return default

def get_env_float(key: str, default: Optional[float] = None) -> Optional[float]:
    """
    Get a float environment variable.
    
    This function gets a float environment variable, returning the default value
    if the variable is not set or is not a valid float.
    
    Args:
        key: Environment variable name
        default: Default value if variable is not set or invalid
        
    Returns:
        Float environment variable value, or default if not set or invalid
    """
    value = os.environ.get(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning(f"Invalid float value for environment variable {key}: {value}")
        return default

def get_env_bool(key: str, default: Optional[bool] = None) -> Optional[bool]:
    """
    Get a boolean environment variable.
    
    This function gets a boolean environment variable, returning the default value
    if the variable is not set. The variable is considered True if it is set to
    'true', 'yes', '1', 'y', or 'on' (case-insensitive).
    
    Args:
        key: Environment variable name
        default: Default value if variable is not set
        
    Returns:
        Boolean environment variable value, or default if not set
    """
    value = os.environ.get(key)
    if value is None:
        return default
    return value.lower() in ('true', 'yes', '1', 'y', 'on')

def get_env_list(key: str, default: Optional[List[str]] = None, separator: str = ',') -> Optional[List[str]]:
    """
    Get a list environment variable.
    
    This function gets a list environment variable, returning the default value
    if the variable is not set. The variable is split by the specified separator.
    
    Args:
        key: Environment variable name
        default: Default value if variable is not set
        separator: Separator to split the variable by
        
    Returns:
        List environment variable value, or default if not set
    """
    value = os.environ.get(key)
    if value is None:
        return default
    return [item.strip() for item in value.split(separator) if item.strip()]

def get_env_dict(key: str, default: Optional[Dict[str, str]] = None, item_separator: str = ',', key_value_separator: str = '=') -> Optional[Dict[str, str]]:
    """
    Get a dictionary environment variable.
    
    This function gets a dictionary environment variable, returning the default value
    if the variable is not set. The variable is split by the specified item separator
    and key-value separator.
    
    Args:
        key: Environment variable name
        default: Default value if variable is not set
        item_separator: Separator to split items by
        key_value_separator: Separator to split keys and values by
        
    Returns:
        Dictionary environment variable value, or default if not set
    """
    value = os.environ.get(key)
    if value is None:
        return default
    
    result = {}
    for item in value.split(item_separator):
        if not item.strip():
            continue
        try:
            k, v = item.split(key_value_separator, 1)
            result[k.strip()] = v.strip()
        except ValueError:
            logger.warning(f"Invalid key-value pair in environment variable {key}: {item}")
    
    return result

def get_env_path(key: str, default: Optional[str] = None, create: bool = False) -> Optional[str]:
    """
    Get a path environment variable.
    
    This function gets a path environment variable, returning the default value
    if the variable is not set. If create is True, the directory will be created
    if it doesn't exist.
    
    Args:
        key: Environment variable name
        default: Default value if variable is not set
        create: Whether to create the directory if it doesn't exist
        
    Returns:
        Path environment variable value, or default if not set
    """
    path = os.environ.get(key, default)
    if path is None:
        return None
    
    # Expand user directory if path starts with ~
    if path.startswith("~"):
        path = os.path.expanduser(path)
    
    # Create directory if it doesn't exist
    if create and path:
        os.makedirs(path, exist_ok=True)
    
    return path

def set_env(key: str, value: str) -> None:
    """
    Set an environment variable.
    
    This function sets an environment variable to the specified value.
    
    Args:
        key: Environment variable name
        value: Environment variable value
    """
    os.environ[key] = value

def get_env_enum(key: str, enum_class: Type[T], default: Optional[T] = None) -> Optional[T]:
    """
    Get an enum environment variable.
    
    This function gets an enum environment variable, returning the default value
    if the variable is not set or is not a valid enum value.
    
    Args:
        key: Environment variable name
        enum_class: Enum class to convert to
        default: Default value if variable is not set or invalid
        
    Returns:
        Enum environment variable value, or default if not set or invalid
    """
    value = os.environ.get(key)
    if value is None:
        return default
    
    try:
        return cast(T, enum_class[value.upper()])
    except (KeyError, ValueError):
        try:
            return cast(T, enum_class(value))
        except (KeyError, ValueError):
            logger.warning(f"Invalid enum value for environment variable {key}: {value}")
            return default

