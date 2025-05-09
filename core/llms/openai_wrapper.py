import os
from openai import AsyncOpenAI as OpenAI
from openai import RateLimitError, APIError
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union

from .error_handling import with_retries, LLMError
from .caching import cached_llm_call
from .token_management import token_counter, token_optimizer, token_usage_tracker
from .model_management import with_model_fallback, failover_manager

base_url = os.environ.get('LLM_API_BASE', "")
token = os.environ.get('LLM_API_KEY', "")

if not base_url and not token:
    raise ValueError("LLM_API_BASE or LLM_API_KEY must be set")
elif base_url and not token:
    client = OpenAI(base_url=base_url, api_key="not_use")
elif not base_url and token:
    client = OpenAI(api_key=token)
else:
    client = OpenAI(api_key=token, base_url=base_url)

# Set maximum concurrency based on environment variable
concurrent_number = os.environ.get('LLM_CONCURRENT_NUMBER', 1)
semaphore = asyncio.Semaphore(int(concurrent_number))


async def openai_llm_raw(messages: List[Dict[str, Any]], model: str, logger=None, **kwargs) -> str:
    """
    Make a raw asynchronous call to the OpenAI API without any error handling or retries.
    
    This function is used internally by the higher-level functions that add error handling,
    retries, caching, and other features.
    
    Args:
        messages: List of message dictionaries to send to the API
        model: Model name to use for the API call
        logger: Optional logger for logging API calls and errors
        **kwargs: Additional keyword arguments to pass to the API
        
    Returns:
        The content of the API response
        
    Raises:
        Exception: If the API call fails
    """
    if logger:
        logger.debug(f'messages:\n {messages}')
        logger.debug(f'model: {model}')
        logger.debug(f'kwargs:\n {kwargs}')

    async with semaphore:  # Use semaphore to control concurrency
        start_time = asyncio.get_event_loop().time()
        
        response = await client.chat.completions.create(
            messages=messages,
            model=model,
            **kwargs
        )
        
        end_time = asyncio.get_event_loop().time()
        duration_ms = (end_time - start_time) * 1000
        
        if logger:
            logger.debug(f'choices:\n {response.choices}')
            logger.debug(f'usage:\n {response.usage}')
            logger.debug(f'duration: {duration_ms:.2f}ms')
        
        # Track token usage
        if hasattr(response, 'usage'):
            token_usage_tracker.track_usage(
                model=model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                success=True
            )
        
        return response.choices[0].message.content


async def openai_llm(messages: List[Dict[str, Any]], model: str, logger=None, use_cache: bool = True, **kwargs) -> str:
    """
    Make an asynchronous call to the OpenAI API with error handling, retries, and caching.
    
    This function makes an asynchronous call to the OpenAI API, handling rate
    limiting, error handling, retries, and caching. It uses a semaphore to limit the
    number of concurrent API calls.
    
    Args:
        messages: List of message dictionaries to send to the API
        model: Model name to use for the API call
        logger: Optional logger for logging API calls and errors
        use_cache: Whether to use the cache
        **kwargs: Additional keyword arguments to pass to the API
        
    Returns:
        The content of the API response
        
    Raises:
        Exception: If all retries fail
    """
    # Use cached_llm_call to handle caching
    return await cached_llm_call(
        # Use with_retries to handle error handling and retries
        lambda msgs, mdl, **kw: with_retries(
            openai_llm_raw,
            msgs, mdl, logger=logger, **kw
        ),
        messages, model, use_cache=use_cache, logger=logger, **kwargs
    )


async def openai_llm_with_fallback(
    messages: List[Dict[str, Any]],
    primary_model: str,
    task_type: str = "general",
    logger=None,
    use_cache: bool = True,
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
        logger: Optional logger for logging API calls and errors
        use_cache: Whether to use the cache
        **kwargs: Additional keyword arguments to pass to the API
        
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
                openai_llm_raw,
                m, md, logger=logger, **k
            ),
            msgs, mdl, use_cache=use_cache, logger=logger, **kw
        ),
        messages, primary_model, failover_manager,
        task_type=task_type, token_count=token_count,
        logger=logger, **kwargs
    )


async def openai_llm_streaming(
    messages: List[Dict[str, Any]],
    model: str,
    callback,
    logger=None,
    **kwargs
) -> str:
    """
    Make an asynchronous streaming call to the OpenAI API.
    
    This function makes an asynchronous streaming call to the OpenAI API,
    calling the provided callback function with each chunk of the response.
    
    Args:
        messages: List of message dictionaries to send to the API
        model: Model name to use for the API call
        callback: Function to call with each chunk of the response
        logger: Optional logger for logging API calls and errors
        **kwargs: Additional keyword arguments to pass to the API
        
    Returns:
        The complete content of the API response
        
    Raises:
        Exception: If the API call fails
    """
    if logger:
        logger.debug(f'Streaming messages:\n {messages}')
        logger.debug(f'model: {model}')
        logger.debug(f'kwargs:\n {kwargs}')
    
    async with semaphore:  # Use semaphore to control concurrency
        start_time = asyncio.get_event_loop().time()
        
        try:
            response = await client.chat.completions.create(
                messages=messages,
                model=model,
                stream=True,
                **kwargs
            )
            
            full_content = ""
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    content_chunk = chunk.choices[0].delta.content
                    full_content += content_chunk
                    await callback(content_chunk)
            
            end_time = asyncio.get_event_loop().time()
            duration_ms = (end_time - start_time) * 1000
            
            if logger:
                logger.debug(f'Streaming completed in {duration_ms:.2f}ms')
            
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
            
            if logger:
                logger.error(f"Error in streaming LLM call after {duration_ms:.2f}ms: {e}")
            
            # Track token usage for the failed call
            prompt_tokens = token_counter.count_message_tokens(messages, model)
            
            token_usage_tracker.track_usage(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=0,
                success=False
            )
            
            raise
