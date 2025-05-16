"""
LLM Integration Module for Wiseflow.

This module provides a comprehensive integration with various LLM providers,
with support for error handling, retries, caching, token management, and more.
"""

# Import configuration
from .config import (
    llm_config,
    get_config,
    initialize_config
)

# Import error handling
from .error_handling import (
    LLMError,
    RateLimitError,
    AuthenticationError,
    InvalidRequestError,
    APIConnectionError,
    ServiceUnavailableError,
    ModelNotFoundError,
    ContextLengthExceededError,
    ContentFilterError,
    QuotaExceededError,
    TimeoutError,
    ServerOverloadedError,
    UnknownLLMError,
    with_retries,
    is_retryable_error,
    get_error_context,
    error_handler
)

# Import caching
from .caching import (
    llm_cache,
    cached_llm_call
)

# Import token management
from .token_management import (
    token_counter,
    token_optimizer,
    token_usage_tracker
)

# Import model management
from .model_management import (
    ModelCapabilities,
    model_capabilities,
    with_model_fallback,
    failover_manager
)

# Import OpenAI wrapper
from .openai_wrapper import (
    openai_llm,
    openai_llm_streaming
)

# Import LiteLLM wrapper
from .litellm_wrapper import (
    litellm_llm,
    litellm_llm_async,
    litellm_llm_streaming,
    is_available as litellm_is_available,
    get_supported_models as litellm_get_supported_models
)

# Import specialized prompting
from .advanced.specialized_prompting import (
    PromptTemplate,
    PromptLibrary,
    prompt_library,
    specialized_prompt,
    process_with_specialized_prompt,
    multi_step_reasoning,
    CONTENT_TYPE_TEXT,
    CONTENT_TYPE_HTML,
    CONTENT_TYPE_MARKDOWN,
    CONTENT_TYPE_CODE,
    CONTENT_TYPE_ACADEMIC,
    CONTENT_TYPE_VIDEO,
    CONTENT_TYPE_SOCIAL,
    TASK_EXTRACTION,
    TASK_SUMMARIZATION,
    TASK_ANALYSIS,
    TASK_REASONING,
    TASK_COMPARISON
)

# Convenience functions
async def generate_text(
    prompt: str,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    use_cache: bool = True,
    **kwargs
) -> str:
    """
    Generate text from a prompt using the configured LLM provider.
    
    Args:
        prompt: The prompt to generate text from
        model: Model to use (defaults to configured primary model)
        temperature: Temperature for generation (0.0 to 2.0)
        max_tokens: Maximum tokens to generate
        use_cache: Whether to use the cache
        **kwargs: Additional keyword arguments to pass to the LLM function
        
    Returns:
        Generated text
    """
    # Use the configured primary model if not specified
    if model is None:
        model = llm_config.get("PRIMARY_MODEL", "gpt-3.5-turbo")
    
    # Create a message from the prompt
    messages = [{"role": "user", "content": prompt}]
    
    # Use LiteLLM if available, otherwise fall back to OpenAI
    if litellm_is_available():
        return await litellm_llm_async(
            messages,
            model,
            temperature=temperature,
            max_tokens=max_tokens,
            use_cache=use_cache,
            **kwargs
        )
    else:
        return await openai_llm(
            messages,
            model,
            temperature=temperature,
            max_tokens=max_tokens,
            use_cache=use_cache,
            **kwargs
        )

async def chat_completion(
    messages: list,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    use_cache: bool = True,
    **kwargs
) -> str:
    """
    Generate a chat completion from a list of messages.
    
    Args:
        messages: List of message dictionaries
        model: Model to use (defaults to configured primary model)
        temperature: Temperature for generation (0.0 to 2.0)
        max_tokens: Maximum tokens to generate
        use_cache: Whether to use the cache
        **kwargs: Additional keyword arguments to pass to the LLM function
        
    Returns:
        Generated completion
    """
    # Use the configured primary model if not specified
    if model is None:
        model = llm_config.get("PRIMARY_MODEL", "gpt-3.5-turbo")
    
    # Use LiteLLM if available, otherwise fall back to OpenAI
    if litellm_is_available():
        return await litellm_llm_async(
            messages,
            model,
            temperature=temperature,
            max_tokens=max_tokens,
            use_cache=use_cache,
            **kwargs
        )
    else:
        return await openai_llm(
            messages,
            model,
            temperature=temperature,
            max_tokens=max_tokens,
            use_cache=use_cache,
            **kwargs
        )

# Version
__version__ = "1.0.0"
