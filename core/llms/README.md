# WiseFlow LLM Integration

This directory contains the LLM (Large Language Model) integration for the WiseFlow project. The implementation provides a unified interface for interacting with various LLM providers, with support for error handling, caching, token optimization, and model fallback mechanisms.

## Overview

The LLM integration is designed to be:

- **Reliable**: With robust error handling and automatic retries
- **Efficient**: With caching and token optimization to reduce costs
- **Flexible**: Supporting multiple providers through direct OpenAI integration and LiteLLM
- **Resilient**: With automatic model fallback mechanisms

## Components

### Core Components

- **LLMManager** (`__init__.py`): Unified interface for LLM interactions
- **OpenAI Wrapper** (`openai_wrapper.py`): Integration with OpenAI's API
- **LiteLLM Wrapper** (`litellm_wrapper.py`): Integration with multiple providers via LiteLLM

### Support Modules

- **Error Handling** (`error_handling.py`): Standardized error handling and retry logic
- **Caching** (`caching.py`): Caching system to avoid redundant API calls
- **Token Management** (`token_management.py`): Token counting, optimization, and usage tracking
- **Model Management** (`model_management.py`): Model capabilities, selection, and fallback mechanisms

### Advanced Features

- **Specialized Prompting** (`advanced/specialized_prompting.py`): Advanced prompting strategies for different content types
- **Multi-step Reasoning** (`advanced/specialized_prompting.py`): Support for multi-step reasoning and chain-of-thought

## Usage

### Basic Usage

```python
from core.llms import llm_manager

# Generate text with default settings
response = await llm_manager.generate(
    prompt="Summarize the benefits of renewable energy.",
    max_tokens=500
)

# Generate text with specific model and settings
response = await llm_manager.generate(
    prompt="Explain quantum computing in simple terms.",
    model="gpt-4",
    temperature=0.7,
    max_tokens=1000,
    use_cache=True
)

# Generate text with model fallback
response, model_used = await llm_manager.generate(
    prompt="Describe the process of photosynthesis.",
    use_fallback=True,
    task_type="explanation"
)
```

### Using Messages Format

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"}
]

response = await llm_manager.generate(
    prompt=messages,
    model="gpt-3.5-turbo"
)
```

### Streaming Responses

```python
async def handle_chunk(chunk):
    print(chunk, end="", flush=True)

full_response = await llm_manager.generate_streaming(
    prompt="Write a short story about a robot learning to paint.",
    callback=handle_chunk,
    model="gpt-4"
)
```

### Token Management

```python
# Count tokens
token_count = llm_manager.get_token_count(
    text="This is a sample text to count tokens in.",
    model="gpt-3.5-turbo"
)

# Optimize a prompt to fit within token limits
optimized_prompt = llm_manager.optimize_prompt(
    prompt=long_prompt,
    max_tokens=2000,
    model="gpt-3.5-turbo"
)

# Estimate cost
cost_estimate = llm_manager.estimate_cost(
    prompt=messages,
    model="gpt-4"
)

# Get usage summary
usage_summary = llm_manager.get_usage_summary()
```

### Cache Management

```python
# Get cache statistics
cache_stats = llm_manager.get_cache_stats()

# Invalidate specific cache entry
await llm_manager.invalidate_cache(key="specific_key")

# Invalidate entire cache
await llm_manager.invalidate_cache()
```

## Configuration

The LLM integration is configured through environment variables and the central configuration system in `core/config.py`:

- `PRIMARY_MODEL`: Default model to use
- `SECONDARY_MODEL`: Fallback model if the primary model fails
- `LLM_API_KEY`: API key for OpenAI
- `LLM_API_BASE`: Base URL for OpenAI API (optional)
- `LLM_CONCURRENT_NUMBER`: Maximum number of concurrent API calls

Additional provider-specific API keys can be set for use with LiteLLM.

## Error Handling

The LLM integration provides standardized error handling with automatic retries for transient errors:

- `RateLimitError`: When hitting rate limits
- `AuthenticationError`: For authentication issues
- `InvalidRequestError`: For invalid requests
- `APIConnectionError`: For API connection issues
- `ServiceUnavailableError`: When the service is unavailable
- `ModelNotFoundError`: When the requested model is not found
- `ContextLengthExceededError`: When the context length is exceeded
- `ContentFilterError`: When content is filtered by the provider

## Model Fallback

The LLM integration supports automatic fallback to alternative models when the primary model fails:

1. If the primary model fails, it tries the secondary model
2. If the secondary model also fails, it tries other available models
3. Models are selected based on task requirements and token counts

## Advanced Usage

### Specialized Prompting

```python
from core.llms.advanced.specialized_prompting import ContentTypePromptStrategy

prompt_strategy = ContentTypePromptStrategy()

result = await prompt_strategy.process(
    content=document_text,
    focus_point="Climate change impacts",
    explanation="Focus on economic impacts",
    content_type="academic",
    task="extraction",
    model="gpt-4"
)
```

### Multi-step Reasoning

```python
from core.llms.advanced import AdvancedLLMProcessor

processor = AdvancedLLMProcessor()

result = await processor.multi_step_reasoning(
    content=complex_text,
    focus_point="Ethical implications of AI",
    explanation="Consider both short-term and long-term impacts",
    content_type="text/plain",
    model="gpt-4"
)
```

## Best Practices

1. **Use Caching**: Enable caching for repetitive or similar queries to reduce costs and improve response times.
2. **Optimize Tokens**: Use token optimization for long prompts to stay within model context limits.
3. **Handle Errors**: Wrap LLM calls in try-except blocks to handle potential errors gracefully.
4. **Monitor Usage**: Regularly check usage statistics to optimize costs and performance.
5. **Use Fallback**: Enable model fallback for critical applications to ensure reliability.
6. **Specialized Prompting**: Use specialized prompting strategies for different content types to improve results.
7. **Streaming**: Use streaming for long responses to improve user experience.

