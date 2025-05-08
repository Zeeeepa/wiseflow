import os
import asyncio
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI as OpenAI
from openai import RateLimitError, APIError

from core.utils.logging_config import logger, with_context, log_execution
from core.utils.error_handling import (
    handle_exceptions, WiseflowError, ConnectionError, 
    RateLimitError as WiseflowRateLimitError
)

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


@log_execution(log_args=True, log_result=False, level="DEBUG")
@handle_exceptions(
    error_types=[RateLimitError, APIError, Exception],
    default_return="",
    log_error=True,
    retry_count=3,
    retry_delay=30,
    retry_backoff=2.0,
    retry_condition=lambda e: isinstance(e, (RateLimitError, APIError)) and 
                             (not hasattr(e, 'status_code') or 
                              getattr(e, 'status_code', 0) not in [400, 401])
)
async def openai_llm(messages: List[Dict[str, Any]], model: str, logger=None, **kwargs) -> str:
    """
    Make an asynchronous call to the OpenAI API.
    
    This function makes an asynchronous call to the OpenAI API, handling rate
    limiting, error handling, and retries. It uses a semaphore to limit the
    number of concurrent API calls.
    
    Args:
        messages: List of message dictionaries to send to the API
        model: Model name to use for the API call
        logger: Optional logger for logging API calls and errors
        **kwargs: Additional keyword arguments to pass to the API
        
    Returns:
        The content of the API response
        
    Raises:
        WiseflowRateLimitError: If rate limit is exceeded
        ConnectionError: If API connection fails
        Exception: If other errors occur
    """
    log_context = {
        "model": model,
        "message_count": len(messages),
        "kwargs": str(kwargs)
    }
    
    if logger:
        logger.debug(f'messages:\n {messages}', **log_context)
        logger.debug(f'model: {model}')
        logger.debug(f'kwargs:\n {kwargs}')

    async with semaphore:  # Use semaphore to control concurrency
        response = await client.chat.completions.create(
            messages=messages,
            model=model,
            **kwargs
        )
        
        if logger:
            logger.debug(f'choices:\n {response.choices}')
            logger.debug(f'usage:\n {response.usage}')
        
        with_context(**log_context).debug(f"OpenAI API call successful")
        return response.choices[0].message.content
