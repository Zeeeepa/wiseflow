# LLM Integration and Error Handling in WiseFlow

This document provides an overview of the LLM integration and error handling mechanisms in WiseFlow.

## Table of Contents

1. [Overview](#overview)
2. [LLM Wrappers](#llm-wrappers)
   - [LiteLLM Wrapper](#litellm-wrapper)
   - [OpenAI Wrapper](#openai-wrapper)
3. [Specialized Prompting](#specialized-prompting)
4. [Token Management](#token-management)
5. [Error Handling](#error-handling)
6. [Retry Logic](#retry-logic)
7. [API Key Management](#api-key-management)
8. [Best Practices](#best-practices)

## Overview

WiseFlow integrates with Large Language Models (LLMs) through a set of wrapper classes and specialized prompting strategies. The system is designed to handle various error scenarios, manage token limits, and provide fallback mechanisms for API failures.

## LLM Wrappers

### LiteLLM Wrapper

The `LiteLLMWrapper` class in `core/llms/litellm_wrapper.py` provides a unified interface to interact with various LLM providers through the LiteLLM library.

Key features:
- Robust error handling with categorized exceptions
- Retry logic for transient errors
- Token limit validation and management
- Fallback to alternative models
- Asynchronous processing support

Example usage:
```python
from core.llms.litellm_wrapper import LiteLLMWrapper

llm = LiteLLMWrapper(default_model="gpt-3.5-turbo")
response = llm.generate(
    prompt="Summarize this text: ...",
    temperature=0.7,
    max_tokens=500
)
```

### OpenAI Wrapper

The `openai_llm` function in `core/llms/openai_wrapper.py` provides a specialized interface for OpenAI models with enhanced error handling.

Key features:
- Comprehensive retry logic with exponential backoff
- Concurrency control through semaphores
- Token limit validation and management
- Fallback to alternative API keys and models
- Detailed error classification and handling

Example usage:
```python
from core.llms.openai_wrapper import openai_llm

response = await openai_llm(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Summarize this text: ..."}
    ],
    model="gpt-3.5-turbo",
    temperature=0.7,
    max_tokens=500
)
```

## Specialized Prompting

The `AdvancedPromptProcessor` class in `core/llms/advanced/specialized_prompting.py` provides specialized prompting strategies for different content types and tasks.

Key features:
- Content type-specific prompt templates
- Multi-step reasoning capabilities
- Token limit management for large content
- Chunking and combining results for large inputs
- Error handling and retry logic

Example usage:
```python
from core.llms.advanced.specialized_prompting import AdvancedPromptProcessor, CONTENT_TYPE_TEXT, TASK_EXTRACTION

processor = AdvancedPromptProcessor(default_model="gpt-3.5-turbo")
result = await processor.process(
    content="...",
    focus_point="Extract key information about AI trends",
    content_type=CONTENT_TYPE_TEXT,
    task=TASK_EXTRACTION
)
```

## Token Management

WiseFlow includes several utilities for token management:

1. **Token Counting**: The `get_token_count` function estimates the number of tokens in a text string.

2. **Content Chunking**: The `chunk_content` function splits large content into manageable chunks.

3. **Content Truncation**: The `truncate_content_to_fit` function intelligently truncates content to fit within token limits.

4. **Message Truncation**: The wrappers automatically truncate messages to fit within model context windows.

Example:
```python
from core.llms.advanced.prompt_utils import get_token_count, chunk_content

# Count tokens
token_count = get_token_count("Some text to analyze", model="gpt-3.5-turbo")

# Split content into chunks
chunks = chunk_content(large_content, max_chunk_tokens=4000, model="gpt-3.5-turbo")
```

## Error Handling

WiseFlow implements a hierarchical error handling strategy:

1. **Exception Categorization**:
   - Retryable exceptions (network issues, rate limits, server errors)
   - Non-retryable exceptions (authentication errors, invalid requests)
   - Unexpected exceptions

2. **Graceful Degradation**:
   - Fallback to alternative models
   - Fallback to alternative API keys
   - Returning partial results when possible

3. **Comprehensive Logging**:
   - Detailed error messages
   - Context information for debugging
   - Warning for potential issues

## Retry Logic

WiseFlow uses the `tenacity` library for implementing retry logic:

1. **Exponential Backoff**: Wait times increase exponentially between retries.

2. **Jitter**: Random variation in wait times to prevent thundering herd problems.

3. **Selective Retries**: Only retry for specific exception types.

4. **Maximum Attempts**: Limit the number of retry attempts.

Example:
```python
@retry(
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def some_function():
    # Function implementation
```

## API Key Management

WiseFlow manages API keys securely:

1. **Environment Variables**: API keys are loaded from environment variables.

2. **Fallback Keys**: Support for multiple fallback API keys.

3. **Validation**: API keys are validated before use.

4. **Secure Handling**: Keys are never logged or exposed in error messages.

## Best Practices

When working with the LLM integration in WiseFlow:

1. **Always handle exceptions**: Wrap LLM calls in try-except blocks.

2. **Check token limits**: Validate content size before sending to LLMs.

3. **Use appropriate timeouts**: Set reasonable timeouts for API calls.

4. **Implement fallbacks**: Have fallback strategies for when LLM calls fail.

5. **Monitor usage**: Keep track of API usage and errors.

6. **Test error scenarios**: Regularly test how the system handles various error conditions.

7. **Update models**: Keep the list of supported models and their token limits up to date.

