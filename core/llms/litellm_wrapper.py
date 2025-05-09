"""
LiteLLM wrapper for Wiseflow.

This module provides a wrapper for the LiteLLM library.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union
import json
import asyncio
import time
import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import random

try:
    import litellm
    from litellm import completion
    from litellm.exceptions import (
        BadRequestError,
        AuthenticationError,
        RateLimitError,
        ServiceUnavailableError,
        APIError,
        APIConnectionError,
        APITimeoutError,
        InvalidRequestError
    )
except ImportError:
    raise ImportError("LiteLLM is not installed. Please install it with 'pip install litellm'.")

logger = logging.getLogger(__name__)

# Define retryable exceptions
RETRYABLE_EXCEPTIONS = (
    RateLimitError,
    ServiceUnavailableError,
    APIConnectionError,
    APITimeoutError
)

# Define non-retryable exceptions
NON_RETRYABLE_EXCEPTIONS = (
    BadRequestError,
    AuthenticationError,
    InvalidRequestError
)

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

def chunk_content(content: str, max_chunk_tokens: int = 4000, model: str = "gpt-3.5-turbo") -> List[str]:
    """
    Split content into chunks that fit within token limits.
    
    Args:
        content: The content to chunk
        max_chunk_tokens: Maximum tokens per chunk
        model: The model to use for token counting
        
    Returns:
        List[str]: List of content chunks
    """
    if not content:
        return []
        
    # If content is small enough, return as is
    if get_token_count(content, model) <= max_chunk_tokens:
        return [content]
    
    # Split by paragraphs first
    paragraphs = content.split("\n\n")
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If a single paragraph is too large, split it by sentences
        if get_token_count(paragraph, model) > max_chunk_tokens:
            sentences = paragraph.split(". ")
            for sentence in sentences:
                sentence_with_period = sentence + ". "
                if get_token_count(current_chunk + sentence_with_period, model) > max_chunk_tokens:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence_with_period
                else:
                    current_chunk += sentence_with_period
        else:
            if get_token_count(current_chunk + paragraph + "\n\n", model) > max_chunk_tokens:
                chunks.append(current_chunk)
                current_chunk = paragraph + "\n\n"
            else:
                current_chunk += paragraph + "\n\n"
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

class LiteLLMWrapper:
    """Wrapper for the LiteLLM library."""
    
    def __init__(self, default_model: Optional[str] = None, fallback_models: Optional[List[str]] = None):
        """
        Initialize the LiteLLM wrapper.
        
        Args:
            default_model: Default model to use for generation
            fallback_models: List of fallback models to try if the default model fails
        """
        self.default_model = default_model or os.environ.get("PRIMARY_MODEL", "")
        self.fallback_models = fallback_models or []
        
        # Add environment fallback models if available
        if not self.fallback_models and os.environ.get("FALLBACK_MODELS", ""):
            self.fallback_models = os.environ.get("FALLBACK_MODELS", "").split(",")
        
        if not self.default_model:
            logger.warning("No default model specified for LiteLLM wrapper")
    
    @retry(
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def generate(self, prompt: str, model: Optional[str] = None, temperature: float = 0.7, 
                max_tokens: int = 1000, system_message: Optional[str] = None) -> str:
        """
        Generate text using LiteLLM with retry logic and error handling.
        
        Args:
            prompt: The prompt to generate from
            model: The model to use (falls back to default_model)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            system_message: Optional system message
            
        Returns:
            str: The generated text
            
        Raises:
            Exception: If generation fails after retries or with non-retryable errors
        """
        try:
            model = model or self.default_model
            if not model:
                raise ValueError("No model specified for generation")
            
            # Prepare messages
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            else:
                messages.append({"role": "system", "content": "You are an expert information extractor."})
            
            messages.append({"role": "user", "content": prompt})
            
            # Check token count
            total_tokens = sum(get_token_count(msg["content"], model) for msg in messages)
            if total_tokens + max_tokens > 8192:  # Assuming 8192 is the model's context window
                logger.warning(f"Total tokens ({total_tokens} + {max_tokens}) exceeds model context window. Truncating prompt.")
                # Truncate the user prompt to fit within limits
                while total_tokens + max_tokens > 8192 and len(prompt) > 100:
                    prompt = prompt[:int(len(prompt) * 0.9)]  # Reduce by 10%
                    messages[-1]["content"] = prompt
                    total_tokens = sum(get_token_count(msg["content"], model) for msg in messages)
            
            # Attempt generation
            response = completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except RETRYABLE_EXCEPTIONS as e:
            logger.warning(f"Retryable error with model {model}: {e}. Retrying...")
            raise  # Let the retry decorator handle it
            
        except NON_RETRYABLE_EXCEPTIONS as e:
            logger.error(f"Non-retryable error with model {model}: {e}")
            
            # Try fallback models if available
            if self.fallback_models:
                for fallback_model in self.fallback_models:
                    try:
                        logger.info(f"Attempting fallback to model: {fallback_model}")
                        response = completion(
                            model=fallback_model,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                        logger.info(f"Fallback to {fallback_model} successful")
                        return response.choices[0].message.content
                    except Exception as fallback_error:
                        logger.warning(f"Fallback to {fallback_model} failed: {fallback_error}")
                        continue
            
            # If we get here, all fallbacks failed or none were available
            logger.error(f"All models failed for generation. Last error: {e}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error generating text with LiteLLM: {e}")
            raise

@retry(
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def litellm_llm(messages: List[Dict[str, str]], model: str, temperature: float = 0.7, 
               max_tokens: int = 1000, logger=None) -> str:
    """
    Generate text using LiteLLM with retry logic.
    
    Args:
        messages: List of message dictionaries
        model: Model to use for generation
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        logger: Optional logger
        
    Returns:
        str: The generated text
        
    Raises:
        Exception: If generation fails after retries
    """
    try:
        # Check token count
        total_tokens = sum(get_token_count(msg["content"], model) for msg in messages)
        if total_tokens + max_tokens > 8192:  # Assuming 8192 is the model's context window
            if logger:
                logger.warning(f"Total tokens ({total_tokens} + {max_tokens}) exceeds model context window. Truncating messages.")
            # Truncate the user messages to fit within limits
            while total_tokens + max_tokens > 8192 and len(messages) > 1:
                # Keep system message if present, truncate user messages
                if messages[0]["role"] == "system":
                    if len(messages) > 2:
                        messages.pop(1)  # Remove the oldest non-system message
                    else:
                        # Only system and one user message left, truncate the user message
                        user_msg = messages[-1]["content"]
                        messages[-1]["content"] = user_msg[:int(len(user_msg) * 0.8)]  # Reduce by 20%
                else:
                    messages.pop(0)  # Remove the oldest message
                
                total_tokens = sum(get_token_count(msg["content"], model) for msg in messages)
        
        response = completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
        
    except RETRYABLE_EXCEPTIONS as e:
        if logger:
            logger.warning(f"Retryable error with model {model}: {e}. Retrying...")
        raise  # Let the retry decorator handle it
        
    except Exception as e:
        if logger:
            logger.error(f"Error generating text with LiteLLM: {e}")
        raise

async def litellm_llm_async(messages: List[Dict[str, str]], model: str, temperature: float = 0.7, 
                          max_tokens: int = 1000, logger=None, max_retries: int = 3) -> str:
    """
    Generate text using LiteLLM asynchronously with retry logic.
    
    Args:
        messages: List of message dictionaries
        model: Model to use for generation
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        logger: Optional logger
        max_retries: Maximum number of retries
        
    Returns:
        str: The generated text
        
    Raises:
        Exception: If generation fails after retries
    """
    retries = 0
    last_exception = None
    
    while retries <= max_retries:
        try:
            # Check token count
            total_tokens = sum(get_token_count(msg["content"], model) for msg in messages)
            if total_tokens + max_tokens > 8192:  # Assuming 8192 is the model's context window
                if logger:
                    logger.warning(f"Total tokens ({total_tokens} + {max_tokens}) exceeds model context window. Truncating messages.")
                # Truncate the user messages to fit within limits
                while total_tokens + max_tokens > 8192 and len(messages) > 1:
                    # Keep system message if present, truncate user messages
                    if messages[0]["role"] == "system":
                        if len(messages) > 2:
                            messages.pop(1)  # Remove the oldest non-system message
                        else:
                            # Only system and one user message left, truncate the user message
                            user_msg = messages[-1]["content"]
                            messages[-1]["content"] = user_msg[:int(len(user_msg) * 0.8)]  # Reduce by 20%
                    else:
                        messages.pop(0)  # Remove the oldest message
                    
                    total_tokens = sum(get_token_count(msg["content"], model) for msg in messages)
            
            # Use asyncio.to_thread instead of run_in_executor for better async handling
            response = await asyncio.to_thread(
                completion,
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except RETRYABLE_EXCEPTIONS as e:
            last_exception = e
            retries += 1
            if logger:
                logger.warning(f"Retryable error with model {model}: {e}. Retry {retries}/{max_retries}")
            
            # Exponential backoff with jitter
            wait_time = min(2 ** retries + (0.1 * random.random()), 60)
            await asyncio.sleep(wait_time)
            
        except NON_RETRYABLE_EXCEPTIONS as e:
            if logger:
                logger.error(f"Non-retryable error with model {model}: {e}")
            raise
            
        except Exception as e:
            last_exception = e
            retries += 1
            if logger:
                logger.error(f"Error generating text with LiteLLM async: {e}. Retry {retries}/{max_retries}")
            
            # Shorter backoff for unknown errors
            await asyncio.sleep(1)
    
    # If we've exhausted retries
    error_msg = f"Maximum retries ({max_retries}) exceeded with model {model}. Last error: {last_exception}"
    if logger:
        logger.error(error_msg)
    raise Exception(error_msg)
