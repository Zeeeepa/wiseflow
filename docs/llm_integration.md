# LLM Integration Guide

This guide explains how to configure and use the LLM integration in Wiseflow.

## Configuration

The LLM integration can be configured using environment variables or a configuration file.

### Environment Variables

- `LLM_PROVIDER`: The LLM provider to use. Supported values are `openai`, `litellm`, `anthropic`, `azure`, and `fallback`. Default: `litellm`.
- `PRIMARY_MODEL`: The primary LLM model to use. This is the default model for all LLM operations.
- `SECONDARY_MODEL`: The secondary LLM model to use. This is used as a fallback if the primary model is unavailable.
- `LLM_API_KEY`: The API key for the LLM provider.
- `LLM_API_BASE`: The API base URL for the LLM provider.

### Provider-Specific Configuration

#### OpenAI

- `OPENAI_API_KEY`: The API key for OpenAI.
- `OPENAI_API_BASE`: The API base URL for OpenAI. Default: `https://api.openai.com/v1`.

#### Anthropic

- `ANTHROPIC_API_KEY`: The API key for Anthropic.
- `ANTHROPIC_API_BASE`: The API base URL for Anthropic. Default: `https://api.anthropic.com`.

#### Azure

- `AZURE_API_KEY`: The API key for Azure OpenAI.
- `AZURE_API_BASE`: The API base URL for Azure OpenAI.
- `AZURE_API_VERSION`: The API version for Azure OpenAI. Default: `2023-05-15`.

## Usage

### Basic Usage

```python
from core.llms import generate

async def example():
    response = await generate(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"}
        ],
        model="gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=1000
    )
    
    print(response["text"])
```

### Advanced Usage

```python
from core.llms import LLMInterface

async def example():
    # Create a custom LLM interface
    llm = LLMInterface(
        provider="openai",
        model="gpt-4",
        api_key="your-api-key",
        api_base="https://api.openai.com/v1",
        max_retries=5,
        timeout=120.0,
        max_concurrent_requests=10
    )
    
    response = await llm.generate(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    
    print(response["text"])
    print(response["metadata"])
```

## Error Handling

The LLM integration provides robust error handling. If an error occurs, the response will include an `error` field with the error message and an `error_type` field with the type of error.

```python
response = await generate(...)

if "error" in response:
    print(f"Error: {response['error']} ({response['error_type']})")
else:
    print(response["text"])
```

## Metadata

The response includes metadata about the LLM operation, including the provider, model, temperature, max tokens, usage statistics, latency, and timestamp.

```python
response = await generate(...)

print(response["metadata"])
```

## Fallback Mechanism

The LLM integration includes a fallback mechanism that can be used when the primary LLM provider is unavailable. To use the fallback mechanism, set the `LLM_PROVIDER` environment variable to `fallback`.

## Supported Providers

The LLM integration supports the following providers:

- **OpenAI**: The OpenAI API, including GPT-3.5 and GPT-4 models.
- **LiteLLM**: A library that provides a unified interface for multiple LLM providers.
- **Anthropic**: The Anthropic API, including Claude models.
- **Azure**: The Azure OpenAI API, which provides access to OpenAI models through Azure.

## Concurrency Control

The LLM integration includes concurrency control to limit the number of concurrent API calls. This helps prevent rate limiting and ensures that the application remains responsive even under heavy load.

To configure the maximum number of concurrent requests, set the `max_concurrent_requests` parameter when creating an `LLMInterface` instance, or set the `LLM_CONCURRENT_NUMBER` environment variable.

## Retries and Exponential Backoff

The LLM integration includes automatic retries with exponential backoff for failed API calls. This helps handle temporary issues with the LLM provider, such as rate limiting or network errors.

To configure the maximum number of retries, set the `max_retries` parameter when creating an `LLMInterface` instance.

## Logging

The LLM integration includes comprehensive logging to help diagnose issues. All API calls, errors, and retries are logged using the Python logging system.

To enable debug logging, set the `WISEFLOW_LOG_LEVEL` environment variable to `DEBUG`.

## Best Practices

- Always handle errors gracefully by checking for the `error` field in the response.
- Use the metadata to track usage and performance.
- Configure appropriate timeouts and concurrency limits based on your application's needs.
- Use the fallback mechanism to ensure that your application remains functional even when the primary LLM provider is unavailable.
- Monitor your API usage to avoid exceeding rate limits or incurring unexpected costs.

