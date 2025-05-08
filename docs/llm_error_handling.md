# LLM Integration and Error Handling

This document describes the error handling and reliability improvements for LLM integration in the WiseFlow project.

## Overview

The LLM integration has been enhanced with the following features:

1. **Comprehensive Error Handling**
   - Custom exception types for different error categories
   - Detailed error logging with context information
   - Proper error propagation to calling code

2. **Retry Mechanism**
   - Exponential backoff with jitter for transient errors
   - Configurable retry parameters (max retries, base delay, max delay)
   - Skip retries for non-transient errors (e.g., content policy violations)

3. **Timeout Handling**
   - Configurable timeout parameters for all LLM calls
   - Proper timeout handling in both synchronous and asynchronous contexts
   - Timeout exceptions with detailed information

4. **Rate Limit Handling**
   - Token bucket algorithm for rate limiting
   - Configurable rate limit parameters
   - Special handling for provider rate limit errors

5. **Standardized Error Propagation**
   - Custom exception hierarchy for different error types
   - Consistent error propagation to calling code
   - Context information in exceptions for better debugging

## Exception Hierarchy

The following custom exception types have been defined:

- `LLMException` - Base exception for all LLM-related errors
  - `NetworkException` - Network-related errors (connection issues, timeouts, etc.)
  - `AuthenticationException` - Authentication errors (invalid API key, etc.)
  - `RateLimitException` - Rate limit errors
  - `TimeoutException` - Timeout errors
  - `ContentFilterException` - Content filter errors (content policy violations, etc.)
  - `ContextLengthException` - Context length errors (input too long, etc.)
  - `InvalidRequestException` - Invalid request errors (malformed input, etc.)
  - `ServiceUnavailableException` - Service unavailability errors (server down, etc.)
  - `QuotaExceededException` - Quota exceeded errors (usage limits, etc.)
  - `UnknownException` - Unknown or unexpected errors

## Configuration

The following environment variables can be used to configure the LLM integration:

- `PRIMARY_MODEL` - Default model to use for generation
- `LLM_TIMEOUT` - Timeout for LLM calls in seconds (default: 60.0)
- `LLM_MAX_RETRIES` - Maximum number of retries for transient errors (default: 3)
- `LLM_BASE_DELAY` - Base delay between retries in seconds (default: 1.0)
- `LLM_MAX_DELAY` - Maximum delay between retries in seconds (default: 60.0)
- `LLM_TOKENS_PER_SECOND` - Rate limit tokens per second (default: 10.0)
- `LLM_MAX_TOKENS_BUCKET` - Maximum tokens in the rate limit bucket (default: 100)

## Usage Examples

### Basic Usage

```python
from core.llms.litellm_wrapper import litellm_llm

# Simple synchronous call
try:
    response = litellm_llm(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"}
        ],
        model="gpt-3.5-turbo"
    )
    print(response)
except Exception as e:
    print(f"Error: {e}")
```

### Asynchronous Usage

```python
import asyncio
from core.llms.litellm_wrapper import litellm_llm_async

async def generate_text():
    try:
        response = await litellm_llm_async(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, world!"}
            ],
            model="gpt-3.5-turbo",
            timeout=30.0,  # Custom timeout
            max_retries=2  # Custom retry count
        )
        return response
    except Exception as e:
        print(f"Error: {e}")
        return None

# Run the async function
asyncio.run(generate_text())
```

### Error Handling

```python
from core.llms.litellm_wrapper import litellm_llm
from core.llms.exceptions import (
    LLMException, NetworkException, AuthenticationException, RateLimitException,
    TimeoutException, ContentFilterException, ContextLengthException,
    InvalidRequestException, ServiceUnavailableException, QuotaExceededException,
    UnknownException
)

try:
    response = litellm_llm(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"}
        ],
        model="gpt-3.5-turbo"
    )
    print(response)
except NetworkException as e:
    print(f"Network error: {e}")
    # Retry or handle network errors
except RateLimitException as e:
    print(f"Rate limit exceeded: {e}")
    # Wait and retry later
except TimeoutException as e:
    print(f"Request timed out: {e}")
    # Handle timeout
except ContentFilterException as e:
    print(f"Content filter triggered: {e}")
    # Handle content policy violation
except ContextLengthException as e:
    print(f"Context length exceeded: {e}")
    # Truncate input or split into chunks
except LLMException as e:
    print(f"LLM error: {e}")
    # Handle other LLM-related errors
except Exception as e:
    print(f"Unexpected error: {e}")
    # Handle unexpected errors
```

### Using the LiteLLMWrapper Class

```python
from core.llms.litellm_wrapper import LiteLLMWrapper

# Create a wrapper instance with custom configuration
wrapper = LiteLLMWrapper(
    default_model="gpt-3.5-turbo",
    timeout=30.0,
    max_retries=2,
    base_delay=1.0,
    max_delay=30.0
)

# Generate text
try:
    response = wrapper.generate(
        prompt="Hello, world!",
        temperature=0.7,
        max_tokens=100
    )
    print(response)
except Exception as e:
    print(f"Error: {e}")
```

## Testing

The LLM error handling functionality can be tested using the provided test suite:

```bash
python -m unittest test.test_llm_error_handling
```

The test suite includes tests for:
- Successful text generation
- Retry mechanism for network errors
- Rate limit error handling
- Context length error handling
- Timeout error handling
- Rate limiter functionality
- Exception mapping
- Transient error detection

