"""
LiteLLM wrapper for Wiseflow.

This module provides a wrapper for the LiteLLM library, enabling support for
multiple LLM providers with consistent error handling, caching, and fallback mechanisms.

## LiteLLM Wrapper Functions

This module provides several functions for interacting with LLMs through LiteLLM:

- `litellm_llm_raw`: For direct calls without error handling (internal use only)
  - Use this only when you need the raw response and will handle errors yourself
  - No retries, caching, or fallback mechanisms
  - Primarily used as a building block for other functions

- `litellm_llm`: For standard calls with error handling and caching
  - Recommended for most use cases
  - Includes automatic retries, error handling, and caching
  - Provides a consistent interface across different LLM providers

- `litellm_llm_with_fallback`: For calls that need automatic model fallback
  - Use when reliability is critical and you want automatic fallback to alternative models
  - Includes all features of `litellm_llm` plus automatic model switching if the primary model fails
  - Returns both the response and the model that was actually used

Each function accepts a standardized set of parameters for consistency:
- `messages`: List of message dictionaries (required)
- `model`: Model name to use (required)
- `temperature`: Controls randomness (default: 0.7)
- `max_tokens`: Maximum tokens to generate (default: 1000)
- `use_cache`: Whether to use caching (default: True)
- `logger`: Optional logger instance

For advanced use cases, additional parameters can be passed via **kwargs.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
import json
import asyncio
import time

from .error_handling import with_retries, LLMError
from .caching import cached_llm_call
from .token_management import token_counter, token_optimizer, token_usage_tracker
from .model_management import with_model_fallback, failover_manager

try:
    import litellm
    from litellm import completion
except ImportError:
    raise ImportError("LiteLLM is not installed. Please install it with 'pip install litellm'.")

logger = logging.getLogger(__name__)

class LiteLLMWrapper:
    """Wrapper for the LiteLLM library."""
    
    def __init__(self, default_model: Optional[str] = None):
        """Initialize the LiteLLM wrapper."""
        self.default_model = default_model or os.environ.get("PRIMARY_MODEL", "")
        if not self.default_model:
            logger.warning("No default model specified for LiteLLM wrapper")
        
        # Set up LiteLLM configuration
        self._configure_litellm()
    
    def _configure_litellm(self):
        """Configure LiteLLM with API keys and settings."""
        # Set up API keys from environment variables
        if os.environ.get("LLM_API_KEY"):
            litellm.api_key = os.environ.get("LLM_API_KEY")
        
        # Configure additional providers if needed
        if os.environ.get("ANTHROPIC_API_KEY"):
            litellm.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        
        if os.environ.get("AZURE_API_KEY"):
            litellm.azure_api_key = os.environ.get("AZURE_API_KEY")
            litellm.azure_api_base = os.environ.get("AZURE_API_BASE", "")
        
        # Set up caching if enabled
        litellm.cache = None  # We'll use our own caching system
        
        # Set up logging
        litellm.set_verbose = False  # We'll handle logging ourselves
    
    async def generate_async(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        use_cache: bool = True
    ) -> str:
        """Generate text using LiteLLM asynchronously."""
        model = model or self.default_model
        if not model:
            raise ValueError("No model specified for generation")
        
        messages = [
            {"role": "system", "content": "You are an expert information extractor."},
            {"role": "user", "content": prompt}
        ]
        
        return await litellm_llm(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            use_cache=use_cache,
            logger=logger
        )
    
    async def generate_with_fallback_async(
        self,
        prompt: str,
        primary_model: Optional[str] = None,
        task_type: str = "extraction",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        use_cache: bool = True
    ) -> Tuple[str, str]:
        """Generate text using LiteLLM with automatic model fallback."""
        primary_model = primary_model or self.default_model
        if not primary_model:
            raise ValueError("No model specified for generation")
        
        messages = [
            {"role": "system", "content": "You are an expert information extractor."},
            {"role": "user", "content": prompt}
        ]
        
        return await litellm_llm_with_fallback(
            messages=messages,
            primary_model=primary_model,
            task_type=task_type,
            temperature=temperature,
            max_tokens=max_tokens,
            use_cache=use_cache,
            logger=logger
        )
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Generate text using LiteLLM synchronously."""
        try:
            model = model or self.default_model
            if not model:
                raise ValueError("No model specified for generation")
            
            messages = [
                {"role": "system", "content": "You are an expert information extractor."},
                {"role": "user", "content": prompt}
            ]
            
            start_time = time.time()
            
            response = completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            # Track token usage
            if hasattr(response, 'usage'):
                token_usage_tracker.track_usage(
                    model=model,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    success=True
                )
            else:
                # Estimate token usage
                prompt_tokens = token_counter.count_message_tokens(messages, model)
                completion_tokens = token_counter.count_tokens(response.choices[0].message.content, model)
                token_usage_tracker.track_usage(
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    success=True
                )
            
            logger.debug(f"LiteLLM call completed in {duration_ms:.2f}ms")
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating text with LiteLLM: {e}")
            raise

async def litellm_llm_raw(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    logger=None,
    **kwargs
) -> str:
    """
    Make a raw asynchronous call to LiteLLM without error handling or retries.
    
    Args:
        messages: List of message dictionaries
        model: Model name
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        logger: Optional logger
        **kwargs: Additional parameters
        
    Returns:
        Generated text
        
    Raises:
        Exception: If the call fails
    """
    if logger:
        logger.debug(f'LiteLLM messages:\n {messages}')
        logger.debug(f'model: {model}')
        logger.debug(f'kwargs:\n {kwargs}')
    
    start_time = asyncio.get_event_loop().time()
    
    # Run in a thread to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None, 
        lambda: completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    )
    
    end_time = asyncio.get_event_loop().time()
    duration_ms = (end_time - start_time) * 1000
    
    if logger:
        logger.debug(f'LiteLLM call completed in {duration_ms:.2f}ms')
    
    # Track token usage
    if hasattr(response, 'usage'):
        token_usage_tracker.track_usage(
            model=model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            success=True
        )
    else:
        # Estimate token usage
        prompt_tokens = token_counter.count_message_tokens(messages, model)
        completion_tokens = token_counter.count_tokens(response.choices[0].message.content, model)
        token_usage_tracker.track_usage(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            success=True
        )
    
    return response.choices[0].message.content

async def litellm_llm(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    use_cache: bool = True,
    logger=None,
    **kwargs
) -> str:
    """
    Make an asynchronous call to LiteLLM with error handling, retries, and caching.
    
    Args:
        messages: List of message dictionaries
        model: Model name
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        use_cache: Whether to use the cache
        logger: Optional logger
        **kwargs: Additional parameters
        
    Returns:
        Generated text
        
    Raises:
        Exception: If all retries fail
    """
    # Use cached_llm_call to handle caching
    return await cached_llm_call(
        # Use with_retries to handle error handling and retries
        lambda msgs, mdl, **kw: with_retries(
            litellm_llm_raw,
            msgs, mdl, temperature=temperature, max_tokens=max_tokens, logger=logger, **kw
        ),
        messages, model, use_cache=use_cache, logger=logger, **kwargs
    )

async def litellm_llm_with_fallback(
    messages: List[Dict[str, str]],
    primary_model: str,
    task_type: str = "general",
    temperature: float = 0.7,
    max_tokens: int = 1000,
    use_cache: bool = True,
    logger=None,
    **kwargs
) -> Tuple[str, str]:
    """
    Make an asynchronous call to LiteLLM with automatic model fallback.
    
    Args:
        messages: List of message dictionaries
        primary_model: Primary model to use
        task_type: Type of task (used for model selection)
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        use_cache: Whether to use the cache
        logger: Optional logger
        **kwargs: Additional parameters
        
    Returns:
        Tuple of (response, model_used)
        
    Raises:
        Exception: If all models fail
    """
    # Count tokens for model selection
    token_count = token_counter.count_message_tokens(messages, primary_model)
    
    # Use with_model_fallback to handle model fallback
    return await with_model_fallback(
        # Use cached_llm_call to handle caching
        lambda msgs, mdl, **kw: cached_llm_call(
            # Use with_retries to handle error handling and retries
            lambda m, md, **k: with_retries(
                litellm_llm_raw,
                m, md, temperature=temperature, max_tokens=max_tokens, logger=logger, **k
            ),
            msgs, mdl, use_cache=use_cache, logger=logger, **kw
        ),
        messages, primary_model, failover_manager,
        task_type=task_type, token_count=token_count,
        logger=logger, **kwargs
    )
