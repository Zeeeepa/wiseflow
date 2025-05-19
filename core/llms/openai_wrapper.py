import os
import logging
import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
from functools import wraps

from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError, APITimeoutError, BadRequestError
import tiktoken

from core.config import (
    LLM_API_BASE, 
    LLM_API_KEY, 
    LLM_CONCURRENT_NUMBER,
    ENABLE_MODEL_FALLBACK
)
from core.utils.error_handling import WiseflowError, ConnectionError, DataProcessingError
from core.utils.metrics import record_llm_metrics
from .caching import cached_llm_call
from .token_management import token_counter, token_optimizer, token_usage_tracker
from .model_management import with_model_fallback, failover_manager

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
if not LLM_API_BASE and not LLM_API_KEY:
    raise ValueError("LLM_API_BASE or LLM_API_KEY must be set")
elif LLM_API_BASE and not LLM_API_KEY:
    client = AsyncOpenAI(base_url=LLM_API_BASE, api_key="not_use")
elif not LLM_API_BASE and LLM_API_KEY:
    client = AsyncOpenAI(api_key=LLM_API_KEY)
else:
    client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_API_BASE)

# Set maximum concurrency based on configuration
semaphore = asyncio.Semaphore(LLM_CONCURRENT_NUMBER)

# Custom error classes
class LLMError(WiseflowError):
    """Base class for LLM-related errors."""
    pass

class ContextLengthExceededError(LLMError):
    """Error raised when the context length is exceeded."""
    pass

class ModelNotFoundError(LLMError):
    """Error raised when the model is not found."""
    pass

class ContentFilterError(LLMError):
    """Error raised when content is filtered."""
    pass

class TokenLimitError(LLMError):
    """Error raised when token limits are exceeded."""
    pass

# Error mapping
def map_openai_error(error: Exception) -> Exception:
    """
    Map OpenAI errors to our custom error classes.
    
    Args:
        error: Original OpenAI error
        
    Returns:
        Mapped error
    """
    error_message = str(error)
    
    if isinstance(error, RateLimitError):
        return LLMError("Rate limit exceeded", cause=error)
    elif isinstance(error, APIConnectionError):
        return ConnectionError("Failed to connect to OpenAI API", cause=error)
    elif isinstance(error, APITimeoutError):
        return ConnectionError("OpenAI API request timed out", cause=error)
    elif isinstance(error, BadRequestError):
        if "context_length_exceeded" in error_message or "maximum context length" in error_message:
            return ContextLengthExceededError("Maximum context length exceeded", cause=error)
        elif "content_filter" in error_message or "content policy" in error_message:
            return ContentFilterError("Content filtered by OpenAI", cause=error)
        else:
            return LLMError(f"Bad request: {error_message}", cause=error)
    elif isinstance(error, APIError):
        if "model not found" in error_message:
            return ModelNotFoundError(f"Model not found: {error_message}", cause=error)
        else:
            return LLMError(f"API error: {error_message}", cause=error)
    else:
        return LLMError(f"Unexpected error: {error_message}", cause=error)

# Retry decorator for LLM calls
def with_retries(
    func: Callable,
    max_retries: int = 3,
    initial_backoff: float = 1.0,
    backoff_multiplier: float = 2.0,
    max_backoff: float = 60.0,
    jitter: bool = True,
    retryable_errors: Optional[List[type]] = None
):
    """
    Decorator for retrying LLM calls with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        initial_backoff: Initial backoff time in seconds
        backoff_multiplier: Multiplier for backoff time after each retry
        max_backoff: Maximum backoff time in seconds
        jitter: Whether to add jitter to backoff times
        retryable_errors: List of error types that should trigger a retry
        
    Returns:
        Decorated function
    """
    if retryable_errors is None:
        retryable_errors = [
            RateLimitError,
            APIConnectionError,
            APITimeoutError,
            APIError
        ]
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        import random
        
        backoff = initial_backoff
        last_exception = None
        
        for retry in range(max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                # Check if this exception is retryable
                if not any(isinstance(e, error_type) for error_type in retryable_errors):
                    # Map the error to our custom error classes
                    mapped_error = map_openai_error(e)
                    raise mapped_error
                
                # If we've exhausted our retries, map and raise the error
                if retry >= max_retries:
                    mapped_error = map_openai_error(last_exception)
                    logger.warning(f"Maximum retries ({max_retries}) reached. Last error: {mapped_error}")
                    raise mapped_error
                
                # Calculate backoff time with optional jitter
                if jitter:
                    # Add random jitter between 0-100% of the backoff time
                    jitter_amount = backoff * random.random()
                    sleep_time = min(backoff + jitter_amount, max_backoff)
                else:
                    sleep_time = min(backoff, max_backoff)
                
                logger.info(f"Retry {retry+1}/{max_retries} after error: {str(e)}. Waiting {sleep_time:.2f}s")
                
                # Wait before retrying
                await asyncio.sleep(sleep_time)
                
                # Increase backoff for next retry
                backoff = min(backoff * backoff_multiplier, max_backoff)
    
    return wrapper

async def openai_llm_raw(
    messages: List[Dict[str, Any]], 
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
    Make a raw asynchronous call to the OpenAI API without any error handling or retries.
    
    This function is used internally by the higher-level functions that add error handling,
    retries, caching, and other features.
    
    Args:
        messages: List of message dictionaries to send to the API
        model: Model name to use for the API call
        temperature: Temperature for generation (0.0 to 2.0)
        max_tokens: Maximum tokens to generate
        top_p: Top-p sampling parameter
        frequency_penalty: Frequency penalty parameter
        presence_penalty: Presence penalty parameter
        stop: Stop sequences
        timeout: Request timeout in seconds
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
        start_time = time.time()
        
        # Prepare request parameters
        request_params = {
            "messages": messages,
            "model": model,
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
            request_params["timeout"] = timeout
            
        # Add any additional kwargs
        request_params.update(kwargs)
        
        # Make the API call
        response = await client.chat.completions.create(**request_params)
        
        end_time = time.time()
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
            
            # Record metrics
            record_llm_metrics(
                model=model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                duration_ms=duration_ms,
                success=True
            )
        
        return response.choices[0].message.content


async def openai_llm(
    messages: List[Dict[str, Any]], 
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
    Make an asynchronous call to the OpenAI API with error handling, retries, and caching.
    
    This function makes an asynchronous call to the OpenAI API, handling rate
    limiting, error handling, retries, and caching. It uses a semaphore to limit the
    number of concurrent API calls.
    
    Args:
        messages: List of message dictionaries to send to the API
        model: Model name to use for the API call
        temperature: Temperature for generation (0.0 to 2.0)
        max_tokens: Maximum tokens to generate
        top_p: Top-p sampling parameter
        frequency_penalty: Frequency penalty parameter
        presence_penalty: Presence penalty parameter
        stop: Stop sequences
        timeout: Request timeout in seconds
        use_cache: Whether to use the cache
        logger: Optional logger for logging API calls and errors
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
    Make an asynchronous call to the OpenAI API with automatic model fallback.
    
    This function makes an asynchronous call to the OpenAI API, with automatic
    fallback to alternative models if the primary model fails.
    
    Args:
        messages: List of message dictionaries to send to the API
        primary_model: Primary model to use
        task_type: Type of task (used for model selection)
        temperature: Temperature for generation (0.0 to 2.0)
        max_tokens: Maximum tokens to generate
        top_p: Top-p sampling parameter
        frequency_penalty: Frequency penalty parameter
        presence_penalty: Presence penalty parameter
        stop: Stop sequences
        timeout: Request timeout in seconds
        use_cache: Whether to use the cache
        logger: Optional logger for logging API calls and errors
        **kwargs: Additional keyword arguments to pass to the API
        
    Returns:
        Tuple of (response, model_used)
        
    Raises:
        Exception: If all models fail
    """
    # Skip fallback if disabled
    if not ENABLE_MODEL_FALLBACK:
        response = await openai_llm(
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
    Make an asynchronous streaming call to the OpenAI API.
    
    This function makes an asynchronous streaming call to the OpenAI API,
    calling the provided callback function with each chunk of the response.
    
    Args:
        messages: List of message dictionaries to send to the API
        model: Model name to use for the API call
        callback: Function to call with each chunk of the response
        temperature: Temperature for generation (0.0 to 2.0)
        max_tokens: Maximum tokens to generate
        top_p: Top-p sampling parameter
        frequency_penalty: Frequency penalty parameter
        presence_penalty: Presence penalty parameter
        stop: Stop sequences
        timeout: Request timeout in seconds
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
        start_time = time.time()
        
        # Prepare request parameters
        request_params = {
            "messages": messages,
            "model": model,
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
            request_params["timeout"] = timeout
            
        # Add any additional kwargs
        request_params.update(kwargs)
        
        try:
            # Make the API call
            response = await client.chat.completions.create(**request_params)
            
            full_content = ""
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    content_chunk = chunk.choices[0].delta.content
                    full_content += content_chunk
                    await callback(content_chunk)
            
            end_time = time.time()
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
                logger.error(f"Error in streaming LLM call after {duration_ms:.2f}ms: {e}")
            
            # Track token usage for the failed call
            prompt_tokens = token_counter.count_message_tokens(messages, model)
            
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
            mapped_error = map_openai_error(e)
            raise mapped_error


async def openai_embeddings(
    texts: Union[str, List[str]],
    model: str = "text-embedding-ada-002",
    dimensions: Optional[int] = None,
    timeout: Optional[float] = None,
    logger: Optional[logging.Logger] = None
) -> List[List[float]]:
    """
    Generate embeddings for text using the OpenAI API.
    
    Args:
        texts: Text or list of texts to generate embeddings for
        model: Model to use for embeddings
        dimensions: Optional number of dimensions for the embeddings
        timeout: Request timeout in seconds
        logger: Optional logger for logging API calls and errors
        
    Returns:
        List of embeddings
    """
    if logger:
        logger.debug(f'Generating embeddings for {len(texts) if isinstance(texts, list) else 1} texts')
        logger.debug(f'model: {model}')
    
    async with semaphore:  # Use semaphore to control concurrency
        start_time = time.time()
        
        # Prepare request parameters
        request_params = {
            "model": model,
            "input": texts,
        }
        
        # Add optional parameters if provided
        if dimensions is not None:
            request_params["dimensions"] = dimensions
        if timeout is not None:
            request_params["timeout"] = timeout
        
        try:
            # Make the API call
            response = await client.embeddings.create(**request_params)
            
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            if logger:
                logger.debug(f'Embeddings generated in {duration_ms:.2f}ms')
            
            # Track token usage
            if hasattr(response, 'usage'):
                token_usage_tracker.track_usage(
                    model=model,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=0,
                    success=True
                )
                
                # Record metrics
                record_llm_metrics(
                    model=model,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=0,
                    duration_ms=duration_ms,
                    success=True
                )
            
            # Extract embeddings
            embeddings = [item.embedding for item in response.data]
            
            return embeddings
        except Exception as e:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            if logger:
                logger.error(f"Error generating embeddings after {duration_ms:.2f}ms: {e}")
            
            # Estimate token usage
            if isinstance(texts, list):
                prompt_tokens = sum(token_counter.count_tokens(text, model) for text in texts)
            else:
                prompt_tokens = token_counter.count_tokens(texts, model)
            
            # Track token usage for the failed call
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
            mapped_error = map_openai_error(e)
            raise mapped_error
