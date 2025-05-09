#!/usr/bin/env python3
"""
Backend module for WiseFlow.

This module provides backend functionality for WiseFlow, including integration with
various LLM providers like DashScope.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union

# Try to import DashScope, but provide a fallback if it's not available
try:
    import dashscope
    from dashscope import Generation
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    logging.getLogger(__name__).warning("DashScope is not installed. Some functionality will be limited.")

logger = logging.getLogger(__name__)

# Configure DashScope API key
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
if DASHSCOPE_AVAILABLE and DASHSCOPE_API_KEY:
    dashscope.api_key = DASHSCOPE_API_KEY
elif DASHSCOPE_AVAILABLE:
    logger.warning("DASHSCOPE_API_KEY not set. DashScope functionality will not work.")

def dashscope_llm(
    messages: List[Dict[str, str]], 
    model: str = "qwen1.5-72b-chat", 
    seed: int = None, 
    temperature: float = 0.7, 
    max_tokens: int = 1000,
    logger=None
) -> str:
    """
    Generate text using DashScope LLM.
    
    Args:
        messages: List of message dictionaries to send to the API
        model: Model name to use for the API call
        seed: Random seed for reproducibility
        temperature: Temperature for generation
        max_tokens: Maximum number of tokens to generate
        logger: Optional logger for logging API calls and errors
        
    Returns:
        The content of the API response
        
    Raises:
        Exception: If the API call fails
    """
    if not DASHSCOPE_AVAILABLE:
        error_msg = "DashScope is not installed. Please install it with 'pip install dashscope'."
        if logger:
            logger.error(error_msg)
        raise ImportError(error_msg)
    
    if not DASHSCOPE_API_KEY:
        error_msg = "DASHSCOPE_API_KEY not set. Cannot use dashscope_llm."
        if logger:
            logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        if logger:
            logger.debug(f"Calling DashScope with model: {model}, messages: {messages}")
        
        response = Generation.call(
            model=model,
            messages=messages,
            seed=seed,
            temperature=temperature,
            max_tokens=max_tokens,
            result_format='message',
        )
        
        if response.status_code == 200:
            if logger:
                logger.debug(f"DashScope response: {response}")
            return response.output.choices[0].message.content
        else:
            error_msg = f"DashScope API error: {response.status_code}, {response.message}"
            if logger:
                logger.error(error_msg)
            return ""
    except Exception as e:
        error_msg = f"Error calling DashScope API: {str(e)}"
        if logger:
            logger.error(error_msg)
        raise

