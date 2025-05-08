"""
LiteLLM wrapper for Wiseflow.

This module provides a wrapper for the LiteLLM library.
"""

import os
import logging
import time
import asyncio
import functools
from typing import Dict, List, Any, Optional, Union, Callable
import json
from concurrent.futures import ThreadPoolExecutor

try:
    import litellm
    from litellm import completion
except ImportError:
    raise ImportError("LiteLLM is not installed. Please install it with 'pip install litellm'.")

logger = logging.getLogger(__name__)

# Create a dedicated thread pool for LLM calls
llm_thread_pool = ThreadPoolExecutor(
    max_workers=int(os.environ.get("LLM_MAX_WORKERS", "4")),
    thread_name_prefix="llm-worker"
)

# LRU Cache for LLM responses
class LRUCache:
    """Simple LRU cache implementation for LLM responses."""
    
    def __init__(self, capacity: int = 100):
        """Initialize the LRU cache."""
        self.capacity = capacity
        self.cache = {}
        self.usage_order = []
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        if key in self.cache:
            # Move key to the end (most recently used)
            self.usage_order.remove(key)
            self.usage_order.append(key)
            return self.cache[key]
        return None
    
    def put(self, key: str, value: Any) -> None:
        """Put a value in the cache."""
        if key in self.cache:
            # Update existing key
            self.cache[key] = value
            self.usage_order.remove(key)
            self.usage_order.append(key)
        else:
            # Add new key
            if len(self.cache) >= self.capacity:
                # Remove least recently used item
                oldest_key = self.usage_order.pop(0)
                del self.cache[oldest_key]
            self.cache[key] = value
            self.usage_order.append(key)

# Create a global LRU cache for LLM responses
llm_response_cache = LRUCache(capacity=int(os.environ.get("LLM_CACHE_SIZE", "1000")))

class LiteLLMWrapper:
    """Wrapper for the LiteLLM library."""
    
    def __init__(self, default_model: Optional[str] = None, cache_enabled: bool = True):
        """Initialize the LiteLLM wrapper."""
        self.default_model = default_model or os.environ.get("PRIMARY_MODEL", "")
        self.cache_enabled = cache_enabled
        self.cache = llm_response_cache if cache_enabled else None
        
        if not self.default_model:
            logger.warning("No default model specified for LiteLLM wrapper")
        
        # Configure litellm
        litellm.set_verbose = False
        
        # Set up request timeout
        self.request_timeout = int(os.environ.get("LLM_REQUEST_TIMEOUT", "60"))
        
        # Set up retry configuration
        self.max_retries = int(os.environ.get("LLM_MAX_RETRIES", "3"))
        self.retry_delay = int(os.environ.get("LLM_RETRY_DELAY", "2"))
    
    def _generate_cache_key(self, messages: List[Dict[str, str]], model: str, temperature: float, max_tokens: int) -> str:
        """Generate a cache key for the LLM request."""
        # Create a deterministic representation of the request
        key_parts = [
            model,
            str(temperature),
            str(max_tokens),
            json.dumps(messages, sort_keys=True)
        ]
        return ":".join(key_parts)
    
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
            
            # Check cache first if enabled
            if self.cache_enabled:
                cache_key = self._generate_cache_key(messages, model, temperature, max_tokens)
                cached_response = self.cache.get(cache_key)
                if cached_response:
                    logger.debug("Using cached LLM response")
                    return cached_response
            
            # Implement retry logic
            for attempt in range(self.max_retries):
                try:
                    response = completion(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        request_timeout=self.request_timeout
                    )
                    
                    result = response.choices[0].message.content
                    
                    # Cache the result if enabled
                    if self.cache_enabled:
                        self.cache.put(cache_key, result)
                    
                    return result
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        # Exponential backoff
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(f"LLM request failed (attempt {attempt+1}/{self.max_retries}): {str(e)}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        # Last attempt failed
                        logger.error(f"LLM request failed after {self.max_retries} attempts: {str(e)}")
                        raise
        except Exception as e:
            logger.error(f"Error generating text with LiteLLM: {e}")
            raise

def litellm_llm(messages: List[Dict[str, str]], model: str, temperature: float = 0.7, max_tokens: int = 1000, logger=None) -> str:
    """Generate text using LiteLLM."""
    try:
        # Check cache first
        cache_key = json.dumps({
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": messages
        }, sort_keys=True)
        
        cached_response = llm_response_cache.get(cache_key)
        if cached_response:
            if logger:
                logger.debug("Using cached LLM response")
            return cached_response
        
        # Implement retry logic
        max_retries = int(os.environ.get("LLM_MAX_RETRIES", "3"))
        retry_delay = int(os.environ.get("LLM_RETRY_DELAY", "2"))
        request_timeout = int(os.environ.get("LLM_REQUEST_TIMEOUT", "60"))
        
        for attempt in range(max_retries):
            try:
                response = completion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    request_timeout=request_timeout
                )
                
                result = response.choices[0].message.content
                
                # Cache the result
                llm_response_cache.put(cache_key, result)
                
                return result
            except Exception as e:
                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = retry_delay * (2 ** attempt)
                    if logger:
                        logger.warning(f"LLM request failed (attempt {attempt+1}/{max_retries}): {str(e)}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # Last attempt failed
                    if logger:
                        logger.error(f"LLM request failed after {max_retries} attempts: {str(e)}")
                    raise
    except Exception as e:
        if logger:
            logger.error(f"Error generating text with LiteLLM: {e}")
        raise

async def litellm_llm_async(messages: List[Dict[str, str]], model: str, temperature: float = 0.7, max_tokens: int = 1000, logger=None) -> str:
    """Generate text using LiteLLM asynchronously."""
    try:
        # Check cache first
        cache_key = json.dumps({
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": messages
        }, sort_keys=True)
        
        cached_response = llm_response_cache.get(cache_key)
        if cached_response:
            if logger:
                logger.debug("Using cached LLM response (async)")
            return cached_response
        
        # Run in a thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        
        # Implement retry logic
        max_retries = int(os.environ.get("LLM_MAX_RETRIES", "3"))
        retry_delay = int(os.environ.get("LLM_RETRY_DELAY", "2"))
        request_timeout = int(os.environ.get("LLM_REQUEST_TIMEOUT", "60"))
        
        for attempt in range(max_retries):
            try:
                # Use the dedicated thread pool for LLM calls
                response = await loop.run_in_executor(
                    llm_thread_pool, 
                    functools.partial(
                        completion,
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        request_timeout=request_timeout
                    )
                )
                
                result = response.choices[0].message.content
                
                # Cache the result
                llm_response_cache.put(cache_key, result)
                
                return result
            except Exception as e:
                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = retry_delay * (2 ** attempt)
                    if logger:
                        logger.warning(f"Async LLM request failed (attempt {attempt+1}/{max_retries}): {str(e)}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    # Last attempt failed
                    if logger:
                        logger.error(f"Async LLM request failed after {max_retries} attempts: {str(e)}")
                    raise
    except Exception as e:
        if logger:
            logger.error(f"Error generating text with LiteLLM async: {e}")
        raise
