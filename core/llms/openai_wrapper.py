"""
OpenAI API wrapper for Wiseflow.

This module provides a wrapper for the OpenAI API, with support for
error handling, retries, caching, and streaming.
"""

import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union, Callable, Awaitable

from openai import AsyncOpenAI as OpenAI
from openai import RateLimitError, APIError

from .config import llm_config
from .error_handling import with_retries, LLMError, error_handler
from .caching import cached_llm_call
from .token_management import token_counter, token_optimizer, token_usage_tracker
from .model_management import with_model_fallback, failover_manager

# Get configuration values
config = llm_config.get_all()

# Initialize OpenAI client
base_url = config.get("LLM_API_BASE", "")
token = config.get("LLM_API_KEY", "")

if not base_url and not token:
    raise ValueError("LLM_API_BASE or LLM_API_KEY must be set")
elif base_url and not token:
    client = OpenAI(base_url=base_url, api_key="not_use")
elif not base_url and token:
    client = OpenAI(api_key=token)
else:
    client = OpenAI(api_key=token, base_url=base_url)

# Set maximum concurrency based on configuration
concurrent_number = config.get("LLM_CONCURRENT_NUMBER", 5)
semaphore = asyncio.Semaphore(int(concurrent_number))

# Initialize logger
logger = logging.getLogger(__name__)

async def openai_llm_raw(
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
    Make a raw asynchronous call to the OpenAI API without any error handling or retries.
    
    This function is used internally by the higher-level functions that add error handling,
    retries, caching, and other features.
    
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
        Exception: If the API call fails
    """
    log = logger or logging.getLogger(__name__)
    
    if log.isEnabledFor(logging.DEBUG):
        log.debug(f'OpenAI API call:')
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
        response = await client.chat.completions.create(**api_params)
        
        end_time = asyncio.get_event_loop().time()
        duration_ms = (end_time - start_time) * 1000
        
        if log.isEnabledFor(logging.DEBUG):
            log.debug(f'OpenAI API response:')
            log.debug(f'  Duration: {duration_ms:.2f}ms')
            log.debug(f'  Usage: {response.usage}')
            log.debug(f'  Choices: {response.choices}')
        
        # Track token usage
        if hasattr(response, 'usage'):
            token_usage_tracker.track_usage(
                model=model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                success=True
            )
        
        return response

async def openai_llm(
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
    Make an asynchronous call to the OpenAI API with error handling, retries, and caching.
    
    This function makes an asynchronous call to the OpenAI API, handling rate
    limiting, error handling, retries, and caching. It uses a semaphore to limit the
    number of concurrent API calls.
    
    Args:
        messages: List of message dictionaries to send to the API
        model: Model name to use for the API call
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        use_cache: Whether to use the cache
        ttl: Optional time-to-live for cache entry
        logger: Optional logger for logging API calls and errors
        **kwargs: Additional keyword arguments to pass to the API
        
    Returns:
        The content of the API response
        
    Raises:
        Exception: If all retries fail
    """
    # Use cached_llm_call to handle caching
    response = await cached_llm_call(
        # Use with_retries to handle error handling and retries
        lambda msgs, mdl, **kw: with_retries(
            openai_llm_raw,
            msgs, mdl, temperature=temperature, max_tokens=max_tokens, logger=logger, **kw
        ),
        messages, model, use_cache=use_cache, ttl=ttl, logger=logger, **kwargs
    )
    
    # Extract content from response
    if isinstance(response, str):
        return response
    
    # If response is an API response object, extract content
    if hasattr(response, 'choices') and response.choices:
        # Check for tool calls
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            # Return tool calls as JSON string
            tool_calls = response.choices[0].message.tool_calls
            return json.dumps([{
                "id": tool_call.id,
                "type": tool_call.type,
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments
                }
            } for tool_call in tool_calls])
        
        # Return content
        return response.choices[0].message.content or ""
    
    # If we get here, something unexpected happened
    if logger:
        logger.warning(f"Unexpected response format: {response}")
    
    # Try to convert to string
    return str(response)

async def openai_llm_with_fallback(
    messages: List[Dict[str, Any]],
    primary_model: str,
    task_type: str = "general",
    temperature: float = 0.7,
    max_tokens: int = 1000,
    logger: Optional[logging.Logger] = None,
    use_cache: bool = True,
    ttl: Optional[int] = None,
    **kwargs
) -> Tuple[str, str]:
    """
    Make an asynchronous call to the OpenAI API with automatic model fallback.
    
    This function makes an asynchronous call to the OpenAI API, with automatic
    fallback to alternative models if the primary model fails.
    
    Args:
        messages: List of message dictionaries to send to the API
        primary_model: Primary model to use
        task_type: Type of task (used for model selection)
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        logger: Optional logger for logging API calls and errors
        use_cache: Whether to use the cache
        ttl: Optional time-to-live for cache entry
        **kwargs: Additional keyword arguments to pass to the API
        
    Returns:
        Tuple of (response, model_used)
        
    Raises:
        Exception: If all models fail
    """
    # Count tokens for model selection
    token_count = token_counter.count_message_tokens(messages, primary_model)
    
    # Determine required features
    required_features = []
    if kwargs.get("tools") or kwargs.get("tool_choice"):
        required_features.append("functions")
    if kwargs.get("response_format", {}).get("type") == "json_object":
        required_features.append("json_mode")
    
    # Check for vision requests
    has_vision_content = False
    for message in messages:
        if isinstance(message.get("content"), list):
            for content_item in message["content"]:
                if content_item.get("type") == "image":
                    has_vision_content = True
                    break
    
    if has_vision_content:
        required_features.append("vision")
    
    # Use with_model_fallback to handle model fallback
    return await with_model_fallback(
        # Use cached_llm_call to handle caching
        lambda msgs, mdl, **kw: cached_llm_call(
            # Use with_retries to handle error handling and retries
            lambda m, md, **k: with_retries(
                openai_llm_raw,
                m, md, temperature=temperature, max_tokens=max_tokens, logger=logger, **k
            ),
            msgs, mdl, use_cache=use_cache, ttl=ttl, logger=logger, **kw
        ),
        messages, primary_model, failover_manager,
        task_type=task_type, token_count=token_count,
        required_features=required_features,
        logger=logger, **kwargs
    )

async def openai_llm_streaming(
    messages: List[Dict[str, Any]],
    model: str,
    callback: Callable[[str], Awaitable[None]],
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
) -> str:
    """
    Make an asynchronous streaming call to the OpenAI API.
    
    This function makes an asynchronous streaming call to the OpenAI API,
    calling the provided callback function with each chunk of the response.
    
    Args:
        messages: List of message dictionaries to send to the API
        model: Model name to use for the API call
        callback: Async function to call with each chunk of the response
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        top_p: Top-p sampling parameter
        frequency_penalty: Frequency penalty parameter
        presence_penalty: Presence penalty parameter
        stop: Optional stop sequences
        response_format: Optional response format
        tools: Optional list of tools for function calling
        tool_choice: Optional tool choice for function calling
        seed: Optional seed for deterministic generation
        user: Optional user identifier
        timeout: Optional timeout in seconds
        logger: Optional logger for logging API calls and errors
        **kwargs: Additional keyword arguments to pass to the API
        
    Returns:
        The complete content of the API response
        
    Raises:
        Exception: If the API call fails
    """
    log = logger or logging.getLogger(__name__)
    
    if log.isEnabledFor(logging.DEBUG):
        log.debug(f'OpenAI API streaming call:')
        log.debug(f'  Model: {model}')
        log.debug(f'  Temperature: {temperature}')
        log.debug(f'  Max tokens: {max_tokens}')
        log.debug(f'  Messages: {json.dumps(messages, indent=2)}')
    
    async with semaphore:  # Use semaphore to control concurrency
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Prepare API call parameters
            api_params = {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "frequency_penalty": frequency_penalty,
                "presence_penalty": presence_penalty,
                "stream": True
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
            response = await client.chat.completions.create(**api_params)
            
            full_content = ""
            tool_calls_by_id = {}
            
            async for chunk in response:
                if not chunk.choices:
                    continue
                
                delta = chunk.choices[0].delta
                
                # Handle content chunks
                if delta.content:
                    content_chunk = delta.content
                    full_content += content_chunk
                    await callback(content_chunk)
                
                # Handle tool call chunks
                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        # Initialize tool call if it's new
                        if tool_call.index not in tool_calls_by_id:
                            tool_calls_by_id[tool_call.index] = {
                                "id": tool_call.id or "",
                                "type": tool_call.type or "function",
                                "function": {
                                    "name": "",
                                    "arguments": ""
                                }
                            }
                        
                        # Update tool call with new data
                        if tool_call.id:
                            tool_calls_by_id[tool_call.index]["id"] = tool_call.id
                        
                        if tool_call.type:
                            tool_calls_by_id[tool_call.index]["type"] = tool_call.type
                        
                        if tool_call.function:
                            if tool_call.function.name:
                                tool_calls_by_id[tool_call.index]["function"]["name"] = tool_call.function.name
                            
                            if tool_call.function.arguments:
                                tool_calls_by_id[tool_call.index]["function"]["arguments"] += tool_call.function.arguments
            
            end_time = asyncio.get_event_loop().time()
            duration_ms = (end_time - start_time) * 1000
            
            if log.isEnabledFor(logging.DEBUG):
                log.debug(f'OpenAI API streaming completed:')
                log.debug(f'  Duration: {duration_ms:.2f}ms')
            
            # If we have tool calls, return them as JSON
            if tool_calls_by_id:
                tool_calls_json = json.dumps(list(tool_calls_by_id.values()))
                return tool_calls_json
            
            # Estimate token usage since streaming doesn't provide usage info
            prompt_tokens = token_counter.count_message_tokens(messages, model)
            completion_tokens = token_counter.count_tokens(full_content, model)
            
            # Track token usage
            token_usage_tracker.track_usage(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                success=True
            )
            
            return full_content
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            duration_ms = (end_time - start_time) * 1000
            
            if log:
                log.error(f"Error in streaming LLM call after {duration_ms:.2f}ms: {e}")
            
            # Handle error
            error = error_handler.handle_error(e, "openai")
            
            # Track token usage for the failed call
            prompt_tokens = token_counter.count_message_tokens(messages, model)
            
            token_usage_tracker.track_usage(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=0,
                success=False
            )
            
            raise error

async def openai_llm_streaming_with_fallback(
    messages: List[Dict[str, Any]],
    primary_model: str,
    callback: Callable[[str], Awaitable[None]],
    task_type: str = "general",
    temperature: float = 0.7,
    max_tokens: int = 1000,
    logger: Optional[logging.Logger] = None,
    **kwargs
) -> Tuple[str, str]:
    """
    Make an asynchronous streaming call to the OpenAI API with automatic model fallback.
    
    This function makes an asynchronous streaming call to the OpenAI API, with automatic
    fallback to alternative models if the primary model fails.
    
    Args:
        messages: List of message dictionaries to send to the API
        primary_model: Primary model to use
        callback: Async function to call with each chunk of the response
        task_type: Type of task (used for model selection)
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        logger: Optional logger for logging API calls and errors
        **kwargs: Additional keyword arguments to pass to the API
        
    Returns:
        Tuple of (complete_response, model_used)
        
    Raises:
        Exception: If all models fail
    """
    # Count tokens for model selection
    token_count = token_counter.count_message_tokens(messages, primary_model)
    
    # Determine required features
    required_features = []
    if kwargs.get("tools") or kwargs.get("tool_choice"):
        required_features.append("functions")
    if kwargs.get("response_format", {}).get("type") == "json_object":
        required_features.append("json_mode")
    
    # Check for vision requests
    has_vision_content = False
    for message in messages:
        if isinstance(message.get("content"), list):
            for content_item in message["content"]:
                if content_item.get("type") == "image":
                    has_vision_content = True
                    break
    
    if has_vision_content:
        required_features.append("vision")
    
    # Get the model to use (primary or fallback)
    model = failover_manager.get_fallback_model(
        primary_model,
        task_type,
        token_count,
        required_features
    )
    
    try:
        # Call the streaming function
        response = await openai_llm_streaming(
            messages=messages,
            model=model,
            callback=callback,
            temperature=temperature,
            max_tokens=max_tokens,
            logger=logger,
            **kwargs
        )
        
        # Mark the model as successful
        failover_manager.mark_model_success(model)
        
        return response, model
    except Exception as e:
        # Mark the model as failed
        failover_manager.mark_model_failure(model, e)
        
        if logger:
            logger.warning(f"Model {model} failed in streaming mode: {e}. Trying fallback model.")
        
        # Get a fallback model
        fallback_model = failover_manager.get_fallback_model(
            model,  # Now this is the "primary" that failed
            task_type,
            token_count,
            required_features
        )
        
        if fallback_model != model:
            try:
                # Call the streaming function with the fallback model
                response = await openai_llm_streaming(
                    messages=messages,
                    model=fallback_model,
                    callback=callback,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    logger=logger,
                    **kwargs
                )
                
                # Mark the fallback model as successful
                failover_manager.mark_model_success(fallback_model)
                
                if logger:
                    logger.info(f"Fallback to {fallback_model} succeeded in streaming mode.")
                
                return response, fallback_model
            except Exception as e2:
                # Mark the fallback model as failed
                failover_manager.mark_model_failure(fallback_model, e2)
                
                if logger:
                    logger.error(f"Fallback model {fallback_model} also failed in streaming mode: {e2}")
        
        # If we get here, all fallbacks failed
        raise e
