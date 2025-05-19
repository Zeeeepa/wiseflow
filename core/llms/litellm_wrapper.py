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
import time
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
import json
import asyncio

from core.config import (
    LLM_API_KEY,
    ANTHROPIC_API_KEY,
    AZURE_API_KEY,
    ENABLE_MODEL_FALLBACK
)
from core.utils.error_handling import WiseflowError, ConnectionError, DataProcessingError
from core.utils.metrics import record_llm_metrics
from .openai_wrapper import (
    LLMError,
    ContextLengthExceededError,
    ModelNotFoundError,
    ContentFilterError,
    TokenLimitError,
    map_openai_error,
    with_retries
)
from .caching import cached_llm_call
from .token_management import token_counter, token_optimizer, token_usage_tracker
from .model_management import with_model_fallback, failover_manager

try:
    import litellm
    from litellm import completion, acompletion
except ImportError:
    raise ImportError("LiteLLM is not installed. Please install it with 'pip install litellm'.")

# Configure logging
logger = logging.getLogger(__name__)

# Configure LiteLLM
def configure_litellm():
    """Configure LiteLLM with API keys and settings."""
    # Set up API keys from environment variables
    if LLM_API_KEY:
        litellm.api_key = LLM_API_KEY
    
    # Configure additional providers if needed
    if ANTHROPIC_API_KEY:
        litellm.anthropic_api_key = ANTHROPIC_API_KEY
    
    if AZURE_API_KEY:
        litellm.azure_api_key = AZURE_API_KEY
        litellm.azure_api_base = os.environ.get("AZURE_API_BASE", "")
    
    # Set up logging
    litellm.set_verbose = False  # We'll handle logging ourselves
    
    # Set up custom exception mapping
    litellm.add_function_to_map_errors(map_litellm_error)

# Map LiteLLM errors to our custom error classes
def map_litellm_error(error: Exception) -> Exception:
    """
    Map LiteLLM errors to our custom error classes.
    
    Args:
        error: Original LiteLLM error
        
    Returns:
        Mapped error
    """
    error_message = str(error)
    
    # Check for specific error types
    if "rate limit" in error_message.lower():
        return LLMError("Rate limit exceeded", cause=error)
    elif "connection" in error_message.lower() or "timeout" in error_message.lower():
        return ConnectionError("Failed to connect to LLM provider", cause=error)
    elif "context length" in error_message.lower() or "maximum context" in error_message.lower():
        return ContextLengthExceededError("Maximum context length exceeded", cause=error)
    elif "content filter" in error_message.lower() or "content policy" in error_message.lower():
        return ContentFilterError("Content filtered by provider", cause=error)
    elif "model not found" in error_message.lower():
        return ModelNotFoundError(f"Model not found: {error_message}", cause=error)
    elif "token limit" in error_message.lower():
        return TokenLimitError("Token limit exceeded", cause=error)
    else:
        return LLMError(f"LLM error: {error_message}", cause=error)

# Initialize LiteLLM
configure_litellm()

class LiteLLMWrapper:
    """Wrapper for the LiteLLM library."""
    
    def __init__(self, default_model: Optional[str] = None):
        """Initialize the LiteLLM wrapper."""
        self.default_model = default_model or os.environ.get("PRIMARY_MODEL", "")
        if not self.default_model:
            logger.warning("No default model specified for LiteLLM wrapper")
    
    async def generate_async(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        use_cache: bool = True,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: Optional[Union[str, List[str]]] = None,
        timeout: Optional[float] = None
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
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            timeout=timeout,
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
        use_cache: bool = True,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: Optional[Union[str, List[str]]] = None,
        timeout: Optional[float] = None
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
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            timeout=timeout,
            use_cache=use_cache,
            logger=logger
        )
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: Optional[Union[str, List[str]]] = None,
        timeout: Optional[float] = None
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
            
            # Prepare request parameters
            request_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "frequency_penalty": frequency_penalty,
                "presence_penalty": presence_penalty,
            }
            
            # Add optional parameters if provided
            if max_tokens is not None:
                request_params["max_tokens"] = max_tokens
            if stop is not None:
                request_params["stop"] = stop
            if timeout is not None:
                request_params["request_timeout"] = timeout
            
            response = completion(**request_params)
            
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
                
                # Record metrics
                record_llm_metrics(
                    model=model,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    duration_ms=duration_ms,
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
                
                # Record metrics
                record_llm_metrics(
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    duration_ms=duration_ms,
                    success=True
                )
            
            logger.debug(f"LiteLLM call completed in {duration_ms:.2f}ms")
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating text with LiteLLM: {e}")
            
            # Estimate token usage for the failed call
            prompt_tokens = token_counter.count_message_tokens(messages, model)
            
            # Track token usage
            token_usage_tracker.track_usage(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=0,
                success=False
            )
            
            # Record metrics
            record_llm_metrics(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=0,
                duration_ms=time.time() - start_time,
                success=False
            )
            
            # Map the error to our custom error classes
            mapped_error = map_litellm_error(e)
            raise mapped_error

async def litellm_llm_raw(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    top_p: float = 1.0,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
    stop: Optional[Union[str, List[str]]] = None,
    timeout: Optional[float] = None,
    logger: Optional[logging.Logger] = None,
    **kwargs
) -> str:
    """
    Make a raw asynchronous call to LiteLLM without error handling or retries.
    
    Args:
        messages: List of message dictionaries
        model: Model name
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        top_p: Top-p sampling parameter
        frequency_penalty: Frequency penalty parameter
        presence_penalty: Presence penalty parameter
        stop: Stop sequences
        timeout: Request timeout in seconds
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
    
    start_time = time.time()
    
    # Prepare request parameters
    request_params = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty,
    }
    
    # Add optional parameters if provided
    if max_tokens is not None:
        request_params["max_tokens"] = max_tokens
    if stop is not None:
        request_params["stop"] = stop
    if timeout is not None:
        request_params["request_timeout"] = timeout
        
    # Add any additional kwargs
    request_params.update(kwargs)
    
    # Make the API call
    response = await acompletion(**request_params)
    
    end_time = time.time()
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
        
        # Record metrics
        record_llm_metrics(
            model=model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            duration_ms=duration_ms,
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
        
        # Record metrics
        record_llm_metrics(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration_ms=duration_ms,
            success=True
        )
    
    return response.choices[0].message.content

async def litellm_llm(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    top_p: float = 1.0,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
    stop: Optional[Union[str, List[str]]] = None,
    timeout: Optional[float] = None,
    use_cache: bool = True,
    logger: Optional[logging.Logger] = None,
    **kwargs
) -> str:
    """
    Make an asynchronous call to LiteLLM with error handling, retries, and caching.
    
    Args:
        messages: List of message dictionaries
        model: Model name
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        top_p: Top-p sampling parameter
        frequency_penalty: Frequency penalty parameter
        presence_penalty: Presence penalty parameter
        stop: Stop sequences
        timeout: Request timeout in seconds
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
        lambda msgs, mdl, **kw: with_retries(litellm_llm_raw)(
            msgs, mdl, 
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            timeout=timeout,
            logger=logger,
            **kw
        ),
        messages, model, use_cache=use_cache, logger=logger, **kwargs
    )

async def litellm_llm_with_fallback(
    messages: List[Dict[str, str]],
    primary_model: str,
    task_type: str = "general",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    top_p: float = 1.0,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
    stop: Optional[Union[str, List[str]]] = None,
    timeout: Optional[float] = None,
    use_cache: bool = True,
    logger: Optional[logging.Logger] = None,
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
        top_p: Top-p sampling parameter
        frequency_penalty: Frequency penalty parameter
        presence_penalty: Presence penalty parameter
        stop: Stop sequences
        timeout: Request timeout in seconds
        use_cache: Whether to use the cache
        logger: Optional logger
        **kwargs: Additional parameters
        
    Returns:
        Tuple of (response, model_used)
        
    Raises:
        Exception: If all models fail
    """
    # Skip fallback if disabled
    if not ENABLE_MODEL_FALLBACK:
        response = await litellm_llm(
            messages, primary_model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            timeout=timeout,
            use_cache=use_cache,
            logger=logger,
            **kwargs
        )
        return response, primary_model
    
    # Count tokens for model selection
    token_count = token_counter.count_message_tokens(messages, primary_model)
    
    # Use with_model_fallback to handle model fallback
    return await with_model_fallback(
        # Use cached_llm_call to handle caching
        lambda msgs, mdl, **kw: cached_llm_call(
            # Use with_retries to handle error handling and retries
            lambda m, md, **k: with_retries(litellm_llm_raw)(
                m, md, 
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stop=stop,
                timeout=timeout,
                logger=logger,
                **k
            ),
            msgs, mdl, use_cache=use_cache, logger=logger, **kw
        ),
        messages, primary_model, failover_manager,
        task_type=task_type, token_count=token_count,
        logger=logger, **kwargs
    )

async def litellm_streaming(
    messages: List[Dict[str, str]],
    model: str,
    callback: Callable[[str], Any],
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    top_p: float = 1.0,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
    stop: Optional[Union[str, List[str]]] = None,
    timeout: Optional[float] = None,
    logger: Optional[logging.Logger] = None,
    **kwargs
) -> str:
    """
    Make an asynchronous streaming call to LiteLLM.
    
    Args:
        messages: List of message dictionaries
        model: Model name
        callback: Function to call with each chunk of the response
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        top_p: Top-p sampling parameter
        frequency_penalty: Frequency penalty parameter
        presence_penalty: Presence penalty parameter
        stop: Stop sequences
        timeout: Request timeout in seconds
        logger: Optional logger
        **kwargs: Additional parameters
        
    Returns:
        Complete generated text
        
    Raises:
        Exception: If the call fails
    """
    if logger:
        logger.debug(f'LiteLLM streaming messages:\n {messages}')
        logger.debug(f'model: {model}')
        logger.debug(f'kwargs:\n {kwargs}')
    
    start_time = time.time()
    
    # Prepare request parameters
    request_params = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty,
        "stream": True,
    }
    
    # Add optional parameters if provided
    if max_tokens is not None:
        request_params["max_tokens"] = max_tokens
    if stop is not None:
        request_params["stop"] = stop
    if timeout is not None:
        request_params["request_timeout"] = timeout
        
    # Add any additional kwargs
    request_params.update(kwargs)
    
    try:
        # Make the API call
        response = await acompletion(**request_params)
        
        full_content = ""
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                content_chunk = chunk.choices[0].delta.content
                full_content += content_chunk
                await callback(content_chunk)
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        if logger:
            logger.debug(f'LiteLLM streaming completed in {duration_ms:.2f}ms')
        
        # Estimate token usage
        prompt_tokens = token_counter.count_message_tokens(messages, model)
        completion_tokens = token_counter.count_tokens(full_content, model)
        
        # Track token usage
        token_usage_tracker.track_usage(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            success=True
        )
        
        # Record metrics
        record_llm_metrics(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration_ms=duration_ms,
            success=True
        )
        
        return full_content
    except Exception as e:
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        if logger:
            logger.error(f"Error in LiteLLM streaming call after {duration_ms:.2f}ms: {e}")
        
        # Estimate token usage for the failed call
        prompt_tokens = token_counter.count_message_tokens(messages, model)
        
        # Track token usage
        token_usage_tracker.track_usage(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            success=False
        )
        
        # Record metrics
        record_llm_metrics(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            duration_ms=duration_ms,
            success=False
        )
        
        # Map the error to our custom error classes
        mapped_error = map_litellm_error(e)
        raise mapped_error
