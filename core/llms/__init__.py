"""
LLM integration for WiseFlow.

This module provides a unified interface for interacting with Large Language Models (LLMs)
through various providers, with support for error handling, caching, token optimization,
and model fallback mechanisms.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union, Tuple

# Import configuration
from ..config import config

# Import core components
from .error_handling import (
    with_retries,
    LLMError,
    RateLimitError,
    AuthenticationError,
    InvalidRequestError,
    APIConnectionError,
    ServiceUnavailableError,
    ModelNotFoundError,
    ContextLengthExceededError,
    ContentFilterError
)

from .caching import (
    llm_cache,
    cached_llm_call
)

from .token_management import (
    token_counter,
    token_optimizer,
    token_usage_tracker
)

from .model_management import (
    model_capabilities,
    initialize_model_management,
    with_model_fallback
)

from .openai_wrapper import (
    openai_llm,
    openai_llm_with_fallback,
    openai_llm_streaming
)

from .litellm_wrapper import (
    LiteLLMWrapper,
    litellm_llm,
    litellm_llm_async,
    litellm_llm_with_fallback
)

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize model management with configuration
primary_model = config.get("PRIMARY_MODEL", "")
secondary_model = config.get("SECONDARY_MODEL", primary_model)

if not primary_model:
    logger.warning("PRIMARY_MODEL not set in configuration. LLM functionality may be limited.")

initialize_model_management(primary_model, secondary_model, logger)

# Initialize LiteLLM wrapper
litellm_wrapper = LiteLLMWrapper(default_model=primary_model)

class LLMManager:
    """
    Unified manager for LLM interactions.
    
    This class provides a unified interface for interacting with LLMs through
    various providers, with support for error handling, caching, token optimization,
    and model fallback mechanisms.
    """
    
    def __init__(self, default_model: Optional[str] = None):
        """
        Initialize the LLM manager.
        
        Args:
            default_model: Default model to use
        """
        self.default_model = default_model or primary_model
        self.logger = logger
    
    async def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        model: Optional[str] = None,
        provider: str = "auto",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        use_cache: bool = True,
        use_fallback: bool = True,
        task_type: str = "general",
        **kwargs
    ) -> Union[str, Tuple[str, str]]:
        """
        Generate text using an LLM.
        
        Args:
            prompt: Text prompt or list of message dictionaries
            model: Model to use (defaults to default_model)
            provider: Provider to use ("openai", "litellm", or "auto")
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            use_cache: Whether to use the cache
            use_fallback: Whether to use model fallback
            task_type: Type of task (used for model selection)
            **kwargs: Additional parameters
            
        Returns:
            Generated text, or tuple of (text, model_used) if use_fallback is True
            
        Raises:
            ValueError: If prompt or model is invalid
            LLMError: If the LLM call fails
        """
        model = model or self.default_model
        if not model:
            raise ValueError("No model specified for generation")
        
        # Convert string prompt to messages if needed
        messages = prompt if isinstance(prompt, list) else [
            {"role": "user", "content": prompt}
        ]
        
        # Determine provider
        if provider == "auto":
            if "gpt" in model.lower() or "openai" in model.lower():
                provider = "openai"
            else:
                provider = "litellm"
        
        # Generate with appropriate provider and fallback settings
        if use_fallback:
            if provider == "openai":
                return await openai_llm_with_fallback(
                    messages=messages,
                    primary_model=model,
                    task_type=task_type,
                    logger=self.logger,
                    use_cache=use_cache,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            else:
                return await litellm_llm_with_fallback(
                    messages=messages,
                    primary_model=model,
                    task_type=task_type,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    logger=self.logger,
                    use_cache=use_cache,
                    **kwargs
                )
        else:
            if provider == "openai":
                return await openai_llm(
                    messages=messages,
                    model=model,
                    logger=self.logger,
                    use_cache=use_cache,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            else:
                return await litellm_llm(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    logger=self.logger,
                    use_cache=use_cache,
                    **kwargs
                )
    
    async def generate_streaming(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        callback,
        model: Optional[str] = None,
        provider: str = "auto",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate text using an LLM with streaming.
        
        Args:
            prompt: Text prompt or list of message dictionaries
            callback: Function to call with each chunk of the response
            model: Model to use (defaults to default_model)
            provider: Provider to use ("openai", "litellm", or "auto")
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            Complete generated text
            
        Raises:
            ValueError: If prompt or model is invalid
            LLMError: If the LLM call fails
        """
        model = model or self.default_model
        if not model:
            raise ValueError("No model specified for generation")
        
        # Convert string prompt to messages if needed
        messages = prompt if isinstance(prompt, list) else [
            {"role": "user", "content": prompt}
        ]
        
        # Determine provider
        if provider == "auto":
            if "gpt" in model.lower() or "openai" in model.lower():
                provider = "openai"
            else:
                provider = "litellm"
        
        # Only OpenAI supports streaming for now
        if provider == "openai":
            return await openai_llm_streaming(
                messages=messages,
                model=model,
                callback=callback,
                logger=self.logger,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
        else:
            # Fall back to non-streaming for other providers
            self.logger.warning(f"Streaming not supported for provider {provider}. Using non-streaming API.")
            response = await litellm_llm(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                logger=self.logger,
                use_cache=False,  # Don't use cache for streaming
                **kwargs
            )
            
            # Simulate streaming by sending the entire response at once
            await callback(response)
            return response
    
    def get_token_count(self, text: Union[str, List[Dict[str, str]]], model: Optional[str] = None) -> int:
        """
        Count tokens in text or messages.
        
        Args:
            text: Text or list of message dictionaries
            model: Model to use for token counting
            
        Returns:
            Number of tokens
        """
        model = model or self.default_model
        
        if isinstance(text, list):
            return token_counter.count_message_tokens(text, model)
        else:
            return token_counter.count_tokens(text, model)
    
    def optimize_prompt(self, prompt: str, max_tokens: int, model: Optional[str] = None) -> str:
        """
        Optimize a prompt to fit within a token limit.
        
        Args:
            prompt: Prompt to optimize
            max_tokens: Maximum number of tokens
            model: Model to use for token counting
            
        Returns:
            Optimized prompt
        """
        model = model or self.default_model
        return token_optimizer.optimize_prompt(prompt, max_tokens, model)
    
    def optimize_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        model: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Optimize messages to fit within a token limit.
        
        Args:
            messages: Messages to optimize
            max_tokens: Maximum number of tokens
            model: Model to use for token counting
            
        Returns:
            Optimized messages
        """
        model = model or self.default_model
        return token_optimizer.optimize_messages(messages, max_tokens, model)
    
    def estimate_cost(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        model: Optional[str] = None,
        estimated_completion_tokens: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Estimate the cost of an LLM call.
        
        Args:
            prompt: Prompt text or list of message dictionaries
            model: Model to use
            estimated_completion_tokens: Optional estimated number of completion tokens
            
        Returns:
            Dictionary with estimated token counts and cost
        """
        model = model or self.default_model
        return token_usage_tracker.estimate_cost(model, prompt, estimated_completion_tokens)
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """
        Get a summary of token usage.
        
        Returns:
            Dictionary with usage summary
        """
        return token_usage_tracker.get_usage_summary()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return llm_cache.get_stats()
    
    async def invalidate_cache(self, key: Optional[str] = None) -> None:
        """
        Invalidate cache entries.
        
        Args:
            key: Specific cache key to invalidate, or None to invalidate all
        """
        await llm_cache.invalidate(key)

# Create a singleton instance
llm_manager = LLMManager(default_model=primary_model)

