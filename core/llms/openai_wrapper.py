import os
import random
import tiktoken
from typing import List, Dict, Any, Optional, Union, Tuple
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from openai import AsyncOpenAI as OpenAI
from openai.types.chat import ChatCompletionMessage
from openai import (
    RateLimitError, 
    APIError, 
    APIConnectionError, 
    APITimeoutError, 
    AuthenticationError, 
    BadRequestError, 
    InternalServerError
)

# Setup logging
import logging
logger = logging.getLogger(__name__)

# Define retryable exceptions
RETRYABLE_EXCEPTIONS = (
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
    InternalServerError
)

# Define non-retryable exceptions
NON_RETRYABLE_EXCEPTIONS = (
    BadRequestError,
    AuthenticationError
)

# Load API configuration from environment variables
base_url = os.environ.get('LLM_API_BASE', "")
token = os.environ.get('LLM_API_KEY', "")
fallback_api_keys = os.environ.get('LLM_FALLBACK_API_KEYS', "").split(",") if os.environ.get('LLM_FALLBACK_API_KEYS') else []
fallback_models = os.environ.get('FALLBACK_MODELS', "").split(",") if os.environ.get('FALLBACK_MODELS') else []

# Validate API configuration
if not base_url and not token:
    raise ValueError("LLM_API_BASE or LLM_API_KEY must be set")
elif base_url and not token:
    client = OpenAI(base_url=base_url, api_key="not_use")
elif not base_url and token:
    client = OpenAI(api_key=token)
else:
    client = OpenAI(api_key=token, base_url=base_url)

# Set maximum concurrency based on environment variable
concurrent_number = int(os.environ.get('LLM_CONCURRENT_NUMBER', 1))
semaphore = asyncio.Semaphore(concurrent_number)

def get_token_count(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Count the number of tokens in a text string.
    
    Args:
        text: The text to count tokens for
        model: The model to use for token counting
        
    Returns:
        int: The number of tokens
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"Error counting tokens: {e}. Using approximate count.")
        # Fallback to approximate count (1 token ≈ 4 chars for English text)
        return len(text) // 4

def get_model_token_limit(model: str) -> int:
    """
    Get the token limit for a specific model.
    
    Args:
        model: The model name
        
    Returns:
        int: The token limit
    """
    # Define token limits for known models
    token_limits = {
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-16k": 16384,
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-turbo": 128000,
        "claude-instant-1": 100000,
        "claude-2": 100000,
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000
    }
    
    # Return the token limit for the model, or a default value
    return token_limits.get(model, 4096)

def truncate_messages_to_fit_context(
    messages: List[Dict[str, Any]], 
    model: str, 
    max_tokens: int
) -> List[Dict[str, Any]]:
    """
    Truncate messages to fit within the model's context window.
    
    Args:
        messages: List of message dictionaries
        model: The model name
        max_tokens: Maximum tokens for completion
        
    Returns:
        List[Dict[str, Any]]: Truncated messages
    """
    model_token_limit = get_model_token_limit(model)
    
    # Calculate current token count
    total_tokens = sum(get_token_count(msg["content"], model) for msg in messages)
    
    # Check if we need to truncate
    if total_tokens + max_tokens <= model_token_limit:
        return messages
    
    # Make a copy to avoid modifying the original
    messages_copy = messages.copy()
    
    # Keep truncating until we fit
    while total_tokens + max_tokens > model_token_limit and len(messages_copy) > 1:
        # Preserve system message if present
        if messages_copy[0]["role"] == "system" and len(messages_copy) > 2:
            # Remove the second message (oldest non-system message)
            messages_copy.pop(1)
        else:
            # Remove the oldest message
            messages_copy.pop(0)
        
        # Recalculate token count
        total_tokens = sum(get_token_count(msg["content"], model) for msg in messages_copy)
    
    # If we still don't fit, truncate the last user message
    if total_tokens + max_tokens > model_token_limit and messages_copy:
        last_msg = messages_copy[-1]
        if last_msg["role"] == "user":
            content = last_msg["content"]
            # Keep truncating until it fits or gets too small
            while total_tokens + max_tokens > model_token_limit and len(content) > 100:
                content = content[:int(len(content) * 0.8)]  # Reduce by 20%
                last_msg["content"] = content
                total_tokens = sum(get_token_count(msg["content"], model) for msg in messages_copy)
    
    return messages_copy

async def create_fallback_client(api_key: str = None) -> Optional[OpenAI]:
    """
    Create a fallback OpenAI client with a different API key.
    
    Args:
        api_key: API key to use
        
    Returns:
        Optional[OpenAI]: New client or None if creation fails
    """
    try:
        if not api_key:
            return None
            
        if base_url:
            return OpenAI(api_key=api_key, base_url=base_url)
        else:
            return OpenAI(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to create fallback client: {e}")
        return None

async def openai_llm(
    messages: List[Dict[str, Any]], 
    model: str, 
    logger=None, 
    temperature: float = 0.7,
    max_tokens: int = 1000,
    fallback_to_alternative_models: bool = True,
    **kwargs
) -> str:
    """
    Make an asynchronous call to the OpenAI API with enhanced error handling.
    
    This function makes an asynchronous call to the OpenAI API, handling rate
    limiting, error handling, and retries. It uses a semaphore to limit the
    number of concurrent API calls and supports fallback to alternative models.
    
    Args:
        messages: List of message dictionaries to send to the API
        model: Model name to use for the API call
        logger: Optional logger for logging API calls and errors
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        fallback_to_alternative_models: Whether to try alternative models on failure
        **kwargs: Additional keyword arguments to pass to the API
        
    Returns:
        The content of the API response
        
    Raises:
        Exception: If all retries and fallbacks fail
    """
    if logger:
        logger.debug(f'messages:\n {messages}')
        logger.debug(f'model: {model}')
        logger.debug(f'kwargs:\n {kwargs}')

    # Truncate messages to fit context window
    truncated_messages = truncate_messages_to_fit_context(messages, model, max_tokens)
    if truncated_messages != messages and logger:
        logger.warning(f"Messages were truncated to fit context window. Original count: {len(messages)}, New count: {len(truncated_messages)}")
    
    messages = truncated_messages

    async with semaphore:  # Use semaphore to control concurrency
        # Maximum number of retries
        max_retries = 3
        # Initial wait time (seconds)
        wait_time = 2
        
        # Try with primary client
        for retry in range(max_retries):
            try:
                response = await client.chat.completions.create(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                if logger:
                    logger.debug(f'choices:\n {response.choices}')
                    logger.debug(f'usage:\n {response.usage}')
                return response.choices[0].message.content
                
            except RateLimitError as e:
                # Rate limit error needs to be retried
                error_msg = f"Rate limit error: {str(e)}. Retry {retry+1}/{max_retries}."
                if logger:
                    logger.warning(error_msg)
                else:
                    print(error_msg)
                
                # Exponential backoff with jitter
                jittered_wait = wait_time + (random.random() * 0.5 * wait_time)
                await asyncio.sleep(jittered_wait)
                wait_time *= 2  # Double the wait time for the next retry
                
            except APIError as e:
                if hasattr(e, 'status_code'):
                    if e.status_code in [400, 401]:
                        # Client errors don't need to be retried
                        error_msg = f"Client error: {e.status_code}. Detail: {str(e)}"
                        if logger:
                            logger.error(error_msg)
                        else:
                            print(error_msg)
                        break  # Exit the retry loop to try fallbacks
                    else:
                        # Other API errors need to be retried
                        error_msg = f"API error: {e.status_code}. Retry {retry+1}/{max_retries}."
                        if logger:
                            logger.warning(error_msg)
                        else:
                            print(error_msg)
                else:
                    # Unknown API errors need to be retried
                    error_msg = f"Unknown API error: {str(e)}. Retry {retry+1}/{max_retries}."
                    if logger:
                        logger.warning(error_msg)
                    else:
                        print(error_msg)
                
                # Exponential backoff with jitter
                jittered_wait = wait_time + (random.random() * 0.5 * wait_time)
                await asyncio.sleep(jittered_wait)
                wait_time *= 2  # Double the wait time for the next retry
                
            except Exception as e:
                # Other exceptions need to be retried
                error_msg = f"Unexpected error: {str(e)}. Retry {retry+1}/{max_retries}."
                if logger:
                    logger.error(error_msg)
                else:
                    print(error_msg)
                
                # Exponential backoff with jitter
                jittered_wait = wait_time + (random.random() * 0.5 * wait_time)
                await asyncio.sleep(jittered_wait)
                wait_time *= 2  # Double the wait time for the next retry
        
        # If we get here, all retries with the primary client failed
        
        # Try fallback API keys
        for fallback_key in fallback_api_keys:
            try:
                fallback_client = await create_fallback_client(fallback_key)
                if not fallback_client:
                    continue
                    
                if logger:
                    logger.info(f"Trying fallback API key")
                
                response = await fallback_client.chat.completions.create(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                if logger:
                    logger.info(f"Fallback API key successful")
                    logger.debug(f'choices:\n {response.choices}')
                    logger.debug(f'usage:\n {response.usage}')
                
                return response.choices[0].message.content
                
            except Exception as e:
                if logger:
                    logger.warning(f"Fallback API key failed: {str(e)}")
        
        # Try fallback models if enabled
        if fallback_to_alternative_models and fallback_models:
            for fallback_model in fallback_models:
                try:
                    if logger:
                        logger.info(f"Trying fallback model: {fallback_model}")
                    
                    # Truncate messages for the fallback model
                    fallback_messages = truncate_messages_to_fit_context(messages, fallback_model, max_tokens)
                    
                    response = await client.chat.completions.create(
                        messages=fallback_messages,
                        model=fallback_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs
                    )
                    
                    if logger:
                        logger.info(f"Fallback model {fallback_model} successful")
                        logger.debug(f'choices:\n {response.choices}')
                        logger.debug(f'usage:\n {response.usage}')
                    
                    return response.choices[0].message.content
                    
                except Exception as e:
                    if logger:
                        logger.warning(f"Fallback model {fallback_model} failed: {str(e)}")

    # If all retries and fallbacks fail
    error_msg = "Maximum retries reached and all fallbacks failed. Unable to get a valid response."
    if logger:
        logger.error(error_msg)
    else:
        print(error_msg)
    
    # Raise an exception instead of returning empty string
    # This allows callers to implement their own fallback logic
    raise Exception(error_msg)
