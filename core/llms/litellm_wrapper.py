"""
LiteLLM wrapper for Wiseflow.

This module provides a wrapper for the LiteLLM library with enhanced error handling,
retry mechanism, timeout handling, and rate limiting.
"""

import os
import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime

try:
    import litellm
    from litellm import completion
    from litellm.exceptions import (
        BadRequestError, AuthenticationError, RateLimitError,
        ServiceUnavailableError, APIError, APITimeoutError, APIConnectionError,
        InvalidRequestError, ContextWindowExceededError
    )
except ImportError:
    raise ImportError("LiteLLM is not installed. Please install it with 'pip install litellm'.")

from .exceptions import (
    LLMException, NetworkException, AuthenticationException, RateLimitException,
    TimeoutException, ContentFilterException, ContextLengthException,
    InvalidRequestException, ServiceUnavailableException, QuotaExceededException,
    UnknownException
)
from .utils import with_retry, with_timeout, RateLimiter, map_exception, is_transient_error

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_TIMEOUT = 60.0  # seconds
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 60.0  # seconds
DEFAULT_TOKENS_PER_SECOND = 10.0
DEFAULT_MAX_TOKENS_BUCKET = 100

# Global rate limiter
rate_limiter = RateLimiter(
    tokens_per_second=float(os.environ.get("LLM_TOKENS_PER_SECOND", DEFAULT_TOKENS_PER_SECOND)),
    max_tokens=int(os.environ.get("LLM_MAX_TOKENS_BUCKET", DEFAULT_MAX_TOKENS_BUCKET))
)


def map_litellm_exception(exception: Exception) -> LLMException:
    """
    Map a LiteLLM-specific exception to a custom LLM exception.
    
    Args:
        exception: The original exception
        
    Returns:
        LLMException: The mapped exception
    """
    error_msg = str(exception)
    error_type = type(exception).__name__
    details = {"original_exception": error_type, "provider": "litellm"}
    
    if isinstance(exception, AuthenticationError):
        return AuthenticationException("Authentication error with LLM provider", details)
    
    elif isinstance(exception, RateLimitError):
        retry_after = getattr(exception, "retry_after", None)
        return RateLimitException("Rate limit exceeded", details, retry_after)
    
    elif isinstance(exception, APITimeoutError):
        return TimeoutException("Request timed out", details)
    
    elif isinstance(exception, APIConnectionError):
        return NetworkException("Network error connecting to LLM provider", details)
    
    elif isinstance(exception, ContextWindowExceededError):
        return ContextLengthException("Context length exceeded", details)
    
    elif isinstance(exception, InvalidRequestError):
        return InvalidRequestException("Invalid request parameters", details)
    
    elif isinstance(exception, BadRequestError):
        # Check if it's a content filter issue
        if "content filter" in error_msg.lower() or "policy" in error_msg.lower():
            return ContentFilterException("Content filter triggered", details)
        return InvalidRequestException("Bad request", details)
    
    elif isinstance(exception, ServiceUnavailableError):
        return ServiceUnavailableException("LLM service unavailable", details)
    
    elif isinstance(exception, APIError):
        # Check for specific API error types
        if "quota" in error_msg.lower() or "billing" in error_msg.lower():
            return QuotaExceededException("Quota exceeded", details)
        return ServiceUnavailableException("API error from LLM provider", details)
    
    # Fall back to generic mapping for unknown exceptions
    return map_exception(exception)


class LiteLLMWrapper:
    """Wrapper for the LiteLLM library with enhanced error handling and reliability."""
    
    def __init__(
        self,
        default_model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        base_delay: Optional[float] = None,
        max_delay: Optional[float] = None
    ):
        """
        Initialize the LiteLLM wrapper.
        
        Args:
            default_model: Default model to use for generation
            timeout: Timeout for LLM calls in seconds
            max_retries: Maximum number of retries for transient errors
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
        """
        self.default_model = default_model or os.environ.get("PRIMARY_MODEL", "")
        if not self.default_model:
            logger.warning("No default model specified for LiteLLM wrapper")
        
        # Configure retry and timeout settings
        self.timeout = timeout or float(os.environ.get("LLM_TIMEOUT", DEFAULT_TIMEOUT))
        self.max_retries = max_retries or int(os.environ.get("LLM_MAX_RETRIES", DEFAULT_MAX_RETRIES))
        self.base_delay = base_delay or float(os.environ.get("LLM_BASE_DELAY", DEFAULT_BASE_DELAY))
        self.max_delay = max_delay or float(os.environ.get("LLM_MAX_DELAY", DEFAULT_MAX_DELAY))
    
    async def _generate_with_retry(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> Any:
        """
        Generate text using LiteLLM with retry logic.
        
        Args:
            messages: List of message dictionaries
            model: Model to use for generation
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments to pass to LiteLLM
            
        Returns:
            The LiteLLM response
            
        Raises:
            LLMException: If generation fails after retries
        """
        # Apply rate limiting
        await rate_limiter.wait()
        
        async def _generate():
            try:
                # Add timeout to the kwargs if not already present
                if "request_timeout" not in kwargs:
                    kwargs["request_timeout"] = self.timeout
                
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
                return response
            except Exception as e:
                # Map the exception to a custom LLM exception
                raise map_litellm_exception(e)
        
        # Execute with retry logic
        return await with_retry(
            _generate,
            max_retries=self.max_retries,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            logger=logger
        )
    
    async def generate_async(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate text using LiteLLM asynchronously.
        
        Args:
            prompt: The prompt for generation
            model: Model to use for generation
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments to pass to LiteLLM
            
        Returns:
            str: The generated text
            
        Raises:
            LLMException: If generation fails
        """
        model = model or self.default_model
        if not model:
            raise InvalidRequestException("No model specified for generation")
        
        messages = [
            {"role": "system", "content": "You are an expert information extractor."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self._generate_with_retry(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return response.choices[0].message.content
        except LLMException as e:
            logger.error(f"Error generating text with LiteLLM: {e}")
            raise
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate text using LiteLLM synchronously.
        
        Args:
            prompt: The prompt for generation
            model: Model to use for generation
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments to pass to LiteLLM
            
        Returns:
            str: The generated text
            
        Raises:
            LLMException: If generation fails
        """
        try:
            # Run the async method in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.generate_async(
                    prompt=prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            )
            loop.close()
            return result
        except Exception as e:
            if not isinstance(e, LLMException):
                e = map_litellm_exception(e)
            logger.error(f"Error generating text with LiteLLM: {e}")
            raise


async def litellm_llm_async(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
    logger: Optional[logging.Logger] = None,
    **kwargs
) -> str:
    """
    Generate text using LiteLLM asynchronously with enhanced error handling.
    
    Args:
        messages: List of message dictionaries
        model: Model to use for generation
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        timeout: Timeout for the request in seconds
        max_retries: Maximum number of retries for transient errors
        logger: Logger for logging errors
        **kwargs: Additional arguments to pass to LiteLLM
        
    Returns:
        str: The generated text
        
    Raises:
        LLMException: If generation fails
    """
    logger = logger or logging.getLogger(__name__)
    timeout = timeout or float(os.environ.get("LLM_TIMEOUT", DEFAULT_TIMEOUT))
    max_retries = max_retries or int(os.environ.get("LLM_MAX_RETRIES", DEFAULT_MAX_RETRIES))
    
    # Apply rate limiting
    await rate_limiter.wait()
    
    # Add request timeout to kwargs if not present
    if "request_timeout" not in kwargs:
        kwargs["request_timeout"] = timeout
    
    async def _generate():
        try:
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
            
            return response.choices[0].message.content
        except Exception as e:
            # Map the exception to a custom LLM exception
            raise map_litellm_exception(e)
    
    try:
        # Execute with retry logic and timeout
        return await with_retry(
            _generate,
            max_retries=max_retries,
            logger=logger
        )
    except LLMException as e:
        logger.error(f"Error generating text with LiteLLM async: {e}")
        raise


def litellm_llm(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
    logger: Optional[logging.Logger] = None,
    **kwargs
) -> str:
    """
    Generate text using LiteLLM synchronously with enhanced error handling.
    
    Args:
        messages: List of message dictionaries
        model: Model to use for generation
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        timeout: Timeout for the request in seconds
        max_retries: Maximum number of retries for transient errors
        logger: Logger for logging errors
        **kwargs: Additional arguments to pass to LiteLLM
        
    Returns:
        str: The generated text
        
    Raises:
        LLMException: If generation fails
    """
    try:
        # Run the async method in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            litellm_llm_async(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                max_retries=max_retries,
                logger=logger,
                **kwargs
            )
        )
        loop.close()
        return result
    except Exception as e:
        if not isinstance(e, LLMException):
            e = map_litellm_exception(e)
        if logger:
            logger.error(f"Error generating text with LiteLLM: {e}")
        raise
