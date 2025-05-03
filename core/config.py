#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Central configuration module for WiseFlow.

This module provides a centralized way to access all configuration settings
from environment variables, with proper defaults and validation.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Project directory
PROJECT_DIR = os.environ.get("PROJECT_DIR", "")
if PROJECT_DIR:
    os.makedirs(PROJECT_DIR, exist_ok=True)

# LLM Configuration
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_API_BASE = os.environ.get("LLM_API_BASE", "")
PRIMARY_MODEL = os.environ.get("PRIMARY_MODEL", "")
SECONDARY_MODEL = os.environ.get("SECONDARY_MODEL", PRIMARY_MODEL)
VL_MODEL = os.environ.get("VL_MODEL", PRIMARY_MODEL)
LLM_CONCURRENT_NUMBER = int(os.environ.get("LLM_CONCURRENT_NUMBER", "1"))

# PocketBase Configuration
PB_API_AUTH = os.environ.get("PB_API_AUTH", "")
PB_API_BASE = os.environ.get("PB_API_BASE", "http://127.0.0.1:8090")

# Search Engine Configuration
ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY", "")
EXA_API_KEY = os.environ.get("EXA_API_KEY", "")

# API Server Configuration
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "8000"))
API_RELOAD = os.environ.get("API_RELOAD", "false").lower() == "true"
WISEFLOW_API_KEY = os.environ.get("WISEFLOW_API_KEY", "dev-api-key")

# Task Configuration
MAX_CONCURRENT_TASKS = int(os.environ.get("MAX_CONCURRENT_TASKS", "4"))
AUTO_SHUTDOWN_ENABLED = os.environ.get("AUTO_SHUTDOWN_ENABLED", "false").lower() == "true"
AUTO_SHUTDOWN_IDLE_TIME = int(os.environ.get("AUTO_SHUTDOWN_IDLE_TIME", "3600"))  # Default: 1 hour
AUTO_SHUTDOWN_CHECK_INTERVAL = int(os.environ.get("AUTO_SHUTDOWN_CHECK_INTERVAL", "300"))  # Default: 5 minutes

# Feature Flags
ENABLE_MULTIMODAL = os.environ.get("ENABLE_MULTIMODAL", "false").lower() == "true"
VERBOSE = os.environ.get("VERBOSE", "false").lower() == "true"

# Validate critical configuration
if not PRIMARY_MODEL:
    raise ValueError("PRIMARY_MODEL not set, please set it in environment variables or edit core/.env")

if not PB_API_AUTH:
    raise ValueError("PB_API_AUTH not set, please set it in environment variables or edit core/.env")

def get_config() -> Dict[str, Any]:
    """
    Get the complete configuration as a dictionary.
    
    Returns:
        Dict[str, Any]: Dictionary containing all configuration values
    """
    return {
        "PROJECT_DIR": PROJECT_DIR,
        "LLM_API_KEY": LLM_API_KEY,
        "LLM_API_BASE": LLM_API_BASE,
        "PRIMARY_MODEL": PRIMARY_MODEL,
        "SECONDARY_MODEL": SECONDARY_MODEL,
        "VL_MODEL": VL_MODEL,
        "LLM_CONCURRENT_NUMBER": LLM_CONCURRENT_NUMBER,
        "PB_API_AUTH": PB_API_AUTH,
        "PB_API_BASE": PB_API_BASE,
        "ZHIPU_API_KEY": ZHIPU_API_KEY,
        "EXA_API_KEY": EXA_API_KEY,
        "API_HOST": API_HOST,
        "API_PORT": API_PORT,
        "API_RELOAD": API_RELOAD,
        "WISEFLOW_API_KEY": WISEFLOW_API_KEY,
        "MAX_CONCURRENT_TASKS": MAX_CONCURRENT_TASKS,
        "AUTO_SHUTDOWN_ENABLED": AUTO_SHUTDOWN_ENABLED,
        "AUTO_SHUTDOWN_IDLE_TIME": AUTO_SHUTDOWN_IDLE_TIME,
        "AUTO_SHUTDOWN_CHECK_INTERVAL": AUTO_SHUTDOWN_CHECK_INTERVAL,
        "ENABLE_MULTIMODAL": ENABLE_MULTIMODAL,
        "VERBOSE": VERBOSE
    }

