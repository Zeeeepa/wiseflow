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
from functools import wraps

try:
    import litellm
    from litellm import completion
    from litellm.exceptions import (
        AuthenticationError, 
        BadRequestError, 
        RateLimitError, 
        ServiceUnavailableError,
        APIError
    )
except ImportError:
    raise ImportError("LiteLLM is not installed. Please install it with 'pip install litellm'.")

from core.llms.auth import get_auth_manager, AuthenticationError as AuthError
from core.llms.fallback import with_circuit_breaker

logger = logging.getLogger(__name__)
auth_manager = get_auth_manager()

# Set maximum concurrency based on environment variable
concurrent_number = os.environ.get('LLM_CONCURRENT_NUMBER', 1)
semaphore = asyncio.Semaphore(int(concurrent_number))

class LiteLLMWrapper:
    """Wrapper for the LiteLLM library."""
    
    def __init__(self, default_model: Optional[str] = None):
        """Initialize the LiteLLM wrapper."""
        self.default_model = default_model or os.environ.get("PRIMARY_MODEL", "")
        if not self.default_model:
            logger.warning("No default model specified for LiteLLM wrapper")
        
        # Configure API keys from environment variables
        self._configure_api_keys()
    
    def _configure_api_keys(self):
        """Configure API keys for different providers."""
        # Check for LiteLLM-specific environment variables
        litellm_api_key = os.environ.get("LITELLM_API_KEY", "")
        if litellm_api_key:
            litellm.api_key = litellm_api_key
            logger.info("Configured LiteLLM API key")
        
        # Configure providers using auth manager
        for provider in ["openai", "anthropic", "cohere", "ai21"]:
            try:
                auth_config = auth_manager.get_auth_config(provider)
                if "api_key" in auth_config:
                    # Set environment variables for LiteLLM to use
                    os.environ[f"{provider.upper()}_API_KEY"] = auth_config["api_key"]
                    if "api_base" in auth_config and auth_config["api_base"]:
                        os.environ[f"{provider.upper()}_API_BASE"] = auth_config["api_base"]
                    logger.info(f"Configured {provider} API key for LiteLLM")
            except AuthError:
                # Skip if no API key is configured for this provider
                pass
    
    def generate(self, prompt: str, model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """Generate text using LiteLLM."""
        try:
            model = model or self.default_model
            if not model:
                raise ValueError("No model specified for generation")
            
            messages = [
                {"role": "system", "content": "You are an expert information extractor."},
                {"role": "user", "content": prompt}
            ]
            
            # Maximum number of retries
            max_retries = 3
            # Initial wait time (seconds)
            wait_time = 5
            
            for retry in range(max_retries):
                try:
                    response = completion(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    
                    return response.choices[0].message.content
                except RateLimitError as e:
                    # Rate limit error needs to be retried
                    error_msg = f"Rate limit error: {str(e)}. Retry {retry+1}/{max_retries}."
                    logger.warning(error_msg)
                except AuthenticationError as e:
                    # Authentication errors don't need to be retried
                    error_msg = f"Authentication error: {str(e)}"
                    logger.error(error_msg)
                    
                    # Try to use fallback provider if available
                    provider = model.split("/")[0] if "/" in model else "openai"
                    fallback_provider = auth_manager.get_fallback_provider(provider)
                    if fallback_provider:
                        logger.info(f"Attempting to use fallback provider: {fallback_provider}")
                        # This would need to be implemented to actually use the fallback
                    
                    raise
                except BadRequestError as e:
                    # Bad request errors don't need to be retried
                    error_msg = f"Bad request error: {str(e)}"
                    logger.error(error_msg)
                    raise
                except ServiceUnavailableError as e:
                    # Service unavailable errors need to be retried
                    error_msg = f"Service unavailable: {str(e)}. Retry {retry+1}/{max_retries}."
                    logger.warning(error_msg)
                except APIError as e:
                    # Other API errors need to be retried
                    error_msg = f"API error: {str(e)}. Retry {retry+1}/{max_retries}."
                    logger.warning(error_msg)
                except Exception as e:
                    # Other exceptions need to be retried
                    error_msg = f"Unexpected error: {str(e)}. Retry {retry+1}/{max_retries}."
                    logger.error(error_msg)
                
                if retry < max_retries - 1:
                    # Exponential backoff strategy
                    time.sleep(wait_time)
                    # Double the wait time for the next retry
                    wait_time *= 2
            
            # If all retries fail
            error_msg = "Maximum retries reached, still unable to get a valid response."
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Error generating text with LiteLLM: {e}")
            raise

def litellm_llm(messages: List[Dict[str, str]], model: str, temperature: float = 0.7, max_tokens: int = 1000, logger=None) -> str:
    """Generate text using LiteLLM."""
    # Maximum number of retries
    max_retries = 3
    # Initial wait time (seconds)
    wait_time = 5
    
    for retry in range(max_retries):
        try:
            response = completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
        except RateLimitError as e:
            # Rate limit error needs to be retried
            error_msg = f"Rate limit error: {str(e)}. Retry {retry+1}/{max_retries}."
            if logger:
                logger.warning(error_msg)
            else:
                print(error_msg)
        except AuthenticationError as e:
            # Authentication errors don't need to be retried
            error_msg = f"Authentication error: {str(e)}"
            if logger:
                logger.error(error_msg)
            else:
                print(error_msg)
            
            # Try to use fallback provider if available
            provider = model.split("/")[0] if "/" in model else "openai"
            fallback_provider = auth_manager.get_fallback_provider(provider)
            if fallback_provider and logger:
                logger.info(f"Attempting to use fallback provider: {fallback_provider}")
            elif fallback_provider:
                print(f"Attempting to use fallback provider: {fallback_provider}")
            
            raise
        except BadRequestError as e:
            # Bad request errors don't need to be retried
            error_msg = f"Bad request error: {str(e)}"
            if logger:
                logger.error(error_msg)
            else:
                print(error_msg)
            raise
        except ServiceUnavailableError as e:
            # Service unavailable errors need to be retried
            error_msg = f"Service unavailable: {str(e)}. Retry {retry+1}/{max_retries}."
            if logger:
                logger.warning(error_msg)
            else:
                print(error_msg)
        except APIError as e:
            # Other API errors need to be retried
            error_msg = f"API error: {str(e)}. Retry {retry+1}/{max_retries}."
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
            time.sleep(wait_time)
            # Double the wait time for the next retry
            wait_time *= 2
    
    # If all retries fail
    error_msg = "Maximum retries reached, still unable to get a valid response."
    if logger:
        logger.error(error_msg)
    else:
        print(error_msg)
    return ''

@with_circuit_breaker("litellm")
async def litellm_llm_async(messages: List[Dict[str, str]], model: str, temperature: float = 0.7, max_tokens: int = 1000, logger=None) -> str:
    """Generate text using LiteLLM asynchronously."""
    async with semaphore:  # Use semaphore to control concurrency
        # Maximum number of retries
        max_retries = 3
        # Initial wait time (seconds)
        wait_time = 5
        
        for retry in range(max_retries):
            try:
                # Run in a thread to avoid blocking the event loop
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, 
                    lambda: completion(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                )
                
                return response.choices[0].message.content
            except RateLimitError as e:
                # Rate limit error needs to be retried
                error_msg = f"Rate limit error: {str(e)}. Retry {retry+1}/{max_retries}."
                if logger:
                    logger.warning(error_msg)
                else:
                    print(error_msg)
            except AuthenticationError as e:
                # Authentication errors don't need to be retried
                error_msg = f"Authentication error: {str(e)}"
                if logger:
                    logger.error(error_msg)
                else:
                    print(error_msg)
                
                # Try to use fallback provider if available
                provider = model.split("/")[0] if "/" in model else "openai"
                fallback_provider = auth_manager.get_fallback_provider(provider)
                if fallback_provider and logger:
                    logger.info(f"Attempting to use fallback provider: {fallback_provider}")
                elif fallback_provider:
                    print(f"Attempting to use fallback provider: {fallback_provider}")
                
                raise
            except BadRequestError as e:
                # Bad request errors don't need to be retried
                error_msg = f"Bad request error: {str(e)}"
                if logger:
                    logger.error(error_msg)
                else:
                    print(error_msg)
                raise
            except ServiceUnavailableError as e:
                # Service unavailable errors need to be retried
                error_msg = f"Service unavailable: {str(e)}. Retry {retry+1}/{max_retries}."
                if logger:
                    logger.warning(error_msg)
                else:
                    print(error_msg)
            except APIError as e:
                # Other API errors need to be retried
                error_msg = f"API error: {str(e)}. Retry {retry+1}/{max_retries}."
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
