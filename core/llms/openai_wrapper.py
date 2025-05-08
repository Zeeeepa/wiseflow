import os
from openai import AsyncOpenAI as OpenAI
from openai import RateLimitError, APIError
import asyncio
from typing import List, Dict, Any, Optional

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
        Exception: If all retries fail
    """
    if logger:
        logger.debug(f'messages:\n {messages}')
        logger.debug(f'model: {model}')
        logger.debug(f'kwargs:\n {kwargs}')

    async with semaphore:  # Use semaphore to control concurrency
        # Maximum number of retries
        max_retries = 3
        # Initial wait time (seconds)
        wait_time = 30
        
        for retry in range(max_retries):
            try:
                response = await client.chat.completions.create(
                    messages=messages,
                    model=model,
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
            except APIError as e:
                if hasattr(e, 'status_code'):
                    if e.status_code in [400, 401]:
                        # Client errors don't need to be retried
                        error_msg = f"Client error: {e.status_code}. Detail: {str(e)}"
                        if logger:
                            logger.error(error_msg)
                        else:
                            print(error_msg)
                        return ''
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
            except Exception as e:
                # Other exceptions need to be retried
                error_msg = f"Unexpected error: {str(e)}. Retry {retry+1}/{max_retries}."
                if logger:
                    logger.error(error_msg)
                else:
                    print(error_msg)

            if retry < max_retries - 1:
                # Exponential backoff strategy
                await asyncio.sleep(wait_time)
                # Double the wait time for the next retry
                wait_time *= 2

    # If all retries fail
    error_msg = "Maximum retries reached, still unable to get a valid response."
    if logger:
        logger.error(error_msg)
    else:
        print(error_msg)
    return ''
