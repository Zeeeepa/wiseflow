"""
LiteLLM wrapper for Wiseflow.

This module provides a wrapper for the LiteLLM library, with support for
error handling, retries, caching, and streaming.
"""

import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union, Callable, Awaitable

try:
    import litellm
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

from .config import llm_config
from .error_handling import with_retries, LLMError, error_handler
from .caching import cached_llm_call
from .token_management import token_counter, token_optimizer, token_usage_tracker

# Initialize logger
logger = logging.getLogger(__name__)

# Get configuration values
config = llm_config.get_all()

# Set maximum concurrency based on configuration
concurrent_number = config.get("LLM_CONCURRENT_NUMBER", 5)
semaphore = asyncio.Semaphore(int(concurrent_number))

# Configure LiteLLM if available
if LITELLM_AVAILABLE:
    # Set API keys from configuration
    litellm.api_key = config.get("LLM_API_KEY", "")
    
    # Set provider-specific API keys
    if config.get("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = config.get("ANTHROPIC_API_KEY")
    
    if config.get("AZURE_API_KEY"):
        os.environ["AZURE_API_KEY"] = config.get("AZURE_API_KEY")
        os.environ["AZURE_API_BASE"] = config.get("AZURE_API_BASE", "")
    
    # Configure LiteLLM settings
    litellm.set_verbose = config.get("LOG_LLM_REQUESTS", False)
    
    # Set up fallback models if configured
    fallback_models = []
    if config.get("PRIMARY_MODEL") and config.get("SECONDARY_MODEL"):
        fallback_models = [
            {"model": config.get("PRIMARY_MODEL")},
            {"model": config.get("SECONDARY_MODEL")}
        ]
        litellm.model_fallbacks = fallback_models


async def litellm_llm_raw(
    messages: List[Dict[str, Any]],
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    top_p: float = 1.0,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
    stop: Optional[Union[str, List[str]]] = None,
    response_format: Optional[Dict[str, str]] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    seed: Optional[int] = None,
    user: Optional[str] = None,
    timeout: Optional[float] = None,
    logger: Optional[logging.Logger] = None,
    **kwargs
) -> Any:
    """
    Make a raw asynchronous call to the LiteLLM library without any error handling or retries.
    
    This function is a direct wrapper around the LiteLLM completion function.
    
    Args:
        messages: List of message dictionaries to send to the API
        model: Model name to use for the API call
        temperature: Temperature for generation (0.0 to 2.0)
        max_tokens: Maximum tokens to generate
        top_p: Top-p sampling parameter (0.0 to 1.0)
        frequency_penalty: Frequency penalty parameter (-2.0 to 2.0)
        presence_penalty: Presence penalty parameter (-2.0 to 2.0)
        stop: Optional stop sequences
        response_format: Optional response format (e.g., {"type": "json_object"})
        tools: Optional list of tools for function calling
        tool_choice: Optional tool choice for function calling
        seed: Optional seed for deterministic generation
        user: Optional user identifier
        timeout: Optional timeout in seconds
        logger: Optional logger for logging API calls and errors
        **kwargs: Additional keyword arguments to pass to the API
        
    Returns:
        The API response object
        
    Raises:
        Exception: If the API call fails or LiteLLM is not available
    """
    if not LITELLM_AVAILABLE:
        raise ImportError("LiteLLM is not installed. Please install it with 'pip install litellm'.")
    
    log = logger or logging.getLogger(__name__)
    
    if log.isEnabledFor(logging.DEBUG):
        log.debug(f'LiteLLM API call:')
        log.debug(f'  Model: {model}')
        log.debug(f'  Temperature: {temperature}')
        log.debug(f'  Max tokens: {max_tokens}')
        log.debug(f'  Messages: {json.dumps(messages, indent=2)}')
        if tools:
            log.debug(f'  Tools: {json.dumps(tools, indent=2)}')
        if tool_choice:
            log.debug(f'  Tool choice: {json.dumps(tool_choice, indent=2)}')
        if response_format:
            log.debug(f'  Response format: {json.dumps(response_format, indent=2)}')
    
    async with semaphore:  # Use semaphore to control concurrency
        start_time = asyncio.get_event_loop().time()
        
        # Prepare API call parameters
        api_params = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty
        }
        
        # Add optional parameters if provided
        if stop is not None:
            api_params["stop"] = stop
        if response_format is not None:
            api_params["response_format"] = response_format
        if tools is not None:
            api_params["tools"] = tools
        if tool_choice is not None:
            api_params["tool_choice"] = tool_choice
        if seed is not None:
            api_params["seed"] = seed
        if user is not None:
            api_params["user"] = user
        if timeout is not None:
            api_params["timeout"] = timeout
        
        # Add any additional kwargs
        api_params.update(kwargs)
        
        # Make the API call
        response = await completion(**api_params)
        
        end_time = asyncio.get_event_loop().time()
        duration_ms = (end_time - start_time) * 1000
        
        if log.isEnabledFor(logging.DEBUG):
            log.debug(f'LiteLLM API response:')
            log.debug(f'  Duration: {duration_ms:.2f}ms')
            if hasattr(response, 'usage'):
                log.debug(f'  Usage: {response.usage}')
            log.debug(f'  Response: {response}')
        
        # Track token usage
        if hasattr(response, 'usage'):
            token_usage_tracker.track_usage(
                model=model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                success=True
            )
        
        return response


async def litellm_llm_async(
    messages: List[Dict[str, Any]],
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    use_cache: bool = True,
    ttl: Optional[int] = None,
    logger: Optional[logging.Logger] = None,
    **kwargs
) -> str:
    """
    Make an asynchronous call to the LiteLLM library with error handling, retries, and caching.
    
    Args:
        messages: List of message dictionaries to send to the API
        model: Model name to use for the API call
        temperature: Temperature for generation (0.0 to 2.0)
        max_tokens: Maximum tokens to generate
        use_cache: Whether to use the cache
        ttl: Optional time-to-live override for this request
        logger: Optional logger for logging API calls and errors
        **kwargs: Additional keyword arguments to pass to the API
        
    Returns:
        The content of the API response
        
    Raises:
        LLMError: If the API call fails after retries
    """
    if not LITELLM_AVAILABLE:
        raise ImportError("LiteLLM is not installed. Please install it with 'pip install litellm'.")
    
    # Use cached_llm_call for caching
    async def llm_func(msgs, mdl, **kw):
        response = await with_retries(
            litellm_llm_raw,
            msgs,
            mdl,
            temperature=temperature,
            max_tokens=max_tokens,
            logger=logger,
            **kw
        )
        return response.choices[0].message.content
    
    return await cached_llm_call(
        llm_func,
        messages,
        model,
        use_cache=use_cache,
        ttl=ttl,
        temperature=temperature,
        max_tokens=max_tokens,
        logger=logger,
        **kwargs
    )


async def litellm_llm_streaming(
    messages: List[Dict[str, Any]],
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    logger: Optional[logging.Logger] = None,
    **kwargs
) -> AsyncGenerator[str, None]:
    """
    Make a streaming asynchronous call to the LiteLLM library.
    
    Args:
        messages: List of message dictionaries to send to the API
        model: Model name to use for the API call
        temperature: Temperature for generation (0.0 to 2.0)
        max_tokens: Maximum tokens to generate
        logger: Optional logger for logging API calls and errors
        **kwargs: Additional keyword arguments to pass to the API
        
    Yields:
        Chunks of the API response as they become available
        
    Raises:
        LLMError: If the API call fails
    """
    if not LITELLM_AVAILABLE:
        raise ImportError("LiteLLLM is not installed. Please install it with 'pip install litellm'.")
    
    log = logger or logging.getLogger(__name__)
    
    if log.isEnabledFor(logging.DEBUG):
        log.debug(f'LiteLLM streaming API call:')
        log.debug(f'  Model: {model}')
        log.debug(f'  Temperature: {temperature}')
        log.debug(f'  Max tokens: {max_tokens}')
        log.debug(f'  Messages: {json.dumps(messages, indent=2)}')
    
    # Prepare API call parameters
    api_params = {
        "messages": messages,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True
    }
    
    # Add any additional kwargs
    api_params.update(kwargs)
    
    try:
        # Make the API call with streaming
        start_time = asyncio.get_event_loop().time()
        
        response_stream = await completion(**api_params)
        
        full_response = ""
        async for chunk in response_stream:
            if hasattr(chunk, 'choices') and chunk.choices:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    yield content
        
        end_time = asyncio.get_event_loop().time()
        duration_ms = (end_time - start_time) * 1000
        
        if log.isEnabledFor(logging.DEBUG):
            log.debug(f'LiteLLM streaming API completed:')
            log.debug(f'  Duration: {duration_ms:.2f}ms')
            log.debug(f'  Full response length: {len(full_response)} characters')
        
        # Estimate token usage for tracking
        prompt_tokens = token_counter.count_message_tokens(messages, model)
        completion_tokens = token_counter.count_tokens(full_response, model)
        
        token_usage_tracker.track_usage(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            success=True
        )
        
    except Exception as e:
        # Handle errors
        error = error_handler.handle_error(e, provider="litellm")
        log.error(f"Error in LiteLLM streaming: {error}")
        raise error


def litellm_llm(
    messages: List[Dict[str, Any]],
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    use_cache: bool = True,
    **kwargs
) -> str:
    """
    Make a synchronous call to the LiteLLM library with error handling, retries, and caching.
    
    This is a convenience wrapper around litellm_llm_async for synchronous code.
    
    Args:
        messages: List of message dictionaries to send to the API
        model: Model name to use for the API call
        temperature: Temperature for generation (0.0 to 2.0)
        max_tokens: Maximum tokens to generate
        use_cache: Whether to use the cache
        **kwargs: Additional keyword arguments to pass to the API
        
    Returns:
        The content of the API response
        
    Raises:
        LLMError: If the API call fails after retries
    """
    if not LITELLM_AVAILABLE:
        raise ImportError("LiteLLM is not installed. Please install it with 'pip install litellm'.")
    
    # Create an event loop if there isn't one
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Run the async function
    return loop.run_until_complete(
        litellm_llm_async(
            messages,
            model,
            temperature=temperature,
            max_tokens=max_tokens,
            use_cache=use_cache,
            **kwargs
        )
    )


def is_available() -> bool:
    """
    Check if LiteLLM is available.
    
    Returns:
        True if LiteLLM is available, False otherwise
    """
    return LITELLM_AVAILABLE


def get_supported_models() -> List[str]:
    """
    Get a list of supported models.
    
    Returns:
        List of supported model names
    """
    if not LITELLM_AVAILABLE:
        return []
    
    try:
        return litellm.utils.get_supported_models()
    except Exception as e:
        logger.error(f"Error getting supported models: {e}")
        return []
