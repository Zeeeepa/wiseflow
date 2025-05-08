#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM wrappers for Wiseflow.

This module provides wrappers for various LLM providers, making it easy to
switch between different providers and models.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union

# Configure logging
logger = logging.getLogger(__name__)

# Import wrappers
try:
    from .openai_wrapper import openai_llm
except ImportError as e:
    logger.warning(f"Failed to import OpenAI wrapper: {e}")
    openai_llm = None

try:
    from .litellm_wrapper import LiteLLMWrapper, litellm_llm, litellm_llm_async
except ImportError as e:
    logger.warning(f"Failed to import LiteLLM wrapper: {e}")
    LiteLLMWrapper = None
    litellm_llm = None
    litellm_llm_async = None

# Export wrappers
__all__ = [
    'openai_llm',
    'LiteLLMWrapper',
    'litellm_llm',
    'litellm_llm_async',
    'get_llm_wrapper'
]

def get_llm_wrapper(provider: str = None):
    """
    Get an LLM wrapper based on the provider.
    
    Args:
        provider: LLM provider name (e.g., 'openai', 'litellm')
        
    Returns:
        LLM wrapper instance
    """
    if not provider:
        # Try to determine provider from environment variables
        if os.environ.get('LLM_PROVIDER'):
            provider = os.environ.get('LLM_PROVIDER')
        elif os.environ.get('OPENAI_API_KEY'):
            provider = 'openai'
        elif os.environ.get('LITELLM_API_KEY'):
            provider = 'litellm'
        else:
            provider = 'litellm'  # Default to LiteLLM
    
    provider = provider.lower()
    
    if provider == 'openai':
        if openai_llm:
            return openai_llm
        else:
            logger.error("OpenAI wrapper is not available")
            raise ImportError("OpenAI wrapper is not available")
    elif provider == 'litellm':
        if LiteLLMWrapper:
            return LiteLLMWrapper()
        else:
            logger.error("LiteLLM wrapper is not available")
            raise ImportError("LiteLLM wrapper is not available")
    else:
        logger.error(f"Unknown LLM provider: {provider}")
        raise ValueError(f"Unknown LLM provider: {provider}")

