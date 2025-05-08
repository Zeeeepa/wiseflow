"""
OpenAI wrapper for Wiseflow.

This module provides a wrapper for the OpenAI API.
"""

import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
import traceback

logger = logging.getLogger(__name__)

# Try to import OpenAI, but provide a fallback if it's not available
try:
    from openai import AsyncOpenAI as OpenAI
    from openai import RateLimitError, APIError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI is not installed. Some functionality will be limited.")
    # Define dummy exception classes for type checking
    class RateLimitError(Exception): pass
    class APIError(Exception): pass

# Initialize OpenAI client if available
if OPENAI_AVAILABLE:
    base_url = os.environ.get('LLM_API_BASE', "")
    token = os.environ.get('LLM_API_KEY', "")

    if not base_url and not token:
        logger.warning("LLM_API_BASE or LLM_API_KEY must be set for OpenAI integration")
        client = None
    elif base_url and not token:
        client = OpenAI(base_url=base_url, api_key="not_use")
    elif not base_url and token:
        client = OpenAI(api_key=token)
    else:
        client = OpenAI(api_key=token, base_url=base_url)
else:
    client = None

# Set maximum concurrency based on environment variable
concurrent_number = os.environ.get('LLM_CONCURRENT_NUMBER', 1)
try:
    concurrent_number = int(concurrent_number)
except ValueError:
    concurrent_number = 1

# Create a semaphore to limit concurrency
semaphore = asyncio.Semaphore(concurrent_number)

async def openai_llm(messages: List[Dict[str, Any]], model: str, logger=None, **kwargs):
    """
    Generate text using OpenAI API.
    
    Args:
        messages: List of message dictionaries to send to the API
        model: Model name to use for the API call
        logger: Optional logger for logging API calls and errors
        **kwargs: Additional arguments to pass to the API
        
    Returns:
        The content of the API response
        
    Raises:
        Exception: If all retries fail or OpenAI is not available
    """
    if not OPENAI_AVAILABLE:
        error_msg = "OpenAI is not installed. Please install it with 'pip install openai'."
        if logger:
            logger.error(error_msg)
        raise ImportError(error_msg)
    
    if client is None:
        error_msg = "OpenAI client is not initialized. Please set LLM_API_BASE or LLM_API_KEY."
        if logger:
            logger.error(error_msg)
        raise ValueError(error_msg)
    
    if logger:
        logger.debug(f'messages:\n {messages}')
        logger.debug(f'model: {model}')
    
    max_retries = 3
    retry_count = 0
    
    async with semaphore:
        while retry_count < max_retries:
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    **kwargs
                )
                
                if logger:
                    logger.debug(f'response: {response}')
                
                return response.choices[0].message.content
            
            except RateLimitError:
                retry_count += 1
                if logger:
                    logger.warning(f'Rate limit exceeded, retrying ({retry_count}/{max_retries})...')
                
                # Exponential backoff
                await asyncio.sleep(2 ** retry_count)
            
            except APIError as e:
                retry_count += 1
                if logger:
                    logger.warning(f'API error: {e}, retrying ({retry_count}/{max_retries})...')
                    logger.debug(f"Traceback: {traceback.format_exc()}")
                
                # Exponential backoff
                await asyncio.sleep(2 ** retry_count)
            
            except Exception as e:
                if logger:
                    logger.error(f'Error: {e}')
                    logger.debug(f"Traceback: {traceback.format_exc()}")
                raise
        
        # If we've exhausted all retries
        raise Exception(f"Failed to generate text after {max_retries} retries")
