# LLM Integration and API Wrapper Documentation

This document provides information about the LLM integration and API wrapper components in the Wiseflow project.

## Overview

Wiseflow integrates with various LLM providers through wrapper modules that handle API calls, error handling, and retries. The main components are:

1. **OpenAI Wrapper** - Provides integration with OpenAI's API
2. **LiteLLM Wrapper** - Provides integration with multiple LLM providers through LiteLLM
3. **Advanced LLM Processing** - Provides specialized prompting strategies for different content types and tasks

## Configuration

### Environment Variables

The following environment variables are used for LLM integration:

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_API_BASE` | Base URL for the LLM API (optional) | None |
| `LLM_API_KEY` | API key for the LLM provider | Required |
| `LLM_CONCURRENT_NUMBER` | Maximum number of concurrent LLM API calls | 1 |
| `PRIMARY_MODEL` | Default model to use for LLM calls | "gpt-3.5-turbo" |
| `DEFAULT_TEMPERATURE` | Default temperature for LLM generation | 0.7 |
| `DEFAULT_MAX_TOKENS` | Default maximum tokens for LLM generation | 1000 |
| `WISEFLOW_API_KEY` | API key for the Wiseflow API | "dev-api-key" |

### Dependencies

The LLM integration requires the following dependencies:

- `openai>=1.0.0,<2.0.0` - For OpenAI API integration
- `litellm>=1.0.0,<2.0.0` - For multi-provider LLM integration

Install these dependencies with:

```bash
pip install -r requirements-base.txt
pip install -r requirements-optional.txt
```

## Usage

### Basic Usage

```python
from core.llms.openai_wrapper import openai_llm
from core.llms.litellm_wrapper import litellm_llm, litellm_llm_async

# Using OpenAI wrapper
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello, how are you?"}
]
response = await openai_llm(messages, "gpt-3.5-turbo")

# Using LiteLLM wrapper
response = await litellm_llm_async(messages, "gpt-3.5-turbo")
```

### Advanced Usage

```python
from core.llms.advanced.specialized_prompting import SpecializedPromptProcessor
from core.llms.advanced import CONTENT_TYPE_TEXT, TASK_EXTRACTION

# Initialize the processor
processor = SpecializedPromptProcessor()

# Process content
result = await processor.process(
    content="Sample content to process",
    focus_point="What is the main topic?",
    explanation="Extract the main topic from the content",
    content_type=CONTENT_TYPE_TEXT,
    task=TASK_EXTRACTION
)

# Multi-step reasoning
result = await processor.multi_step_reasoning(
    content="Sample content to analyze",
    focus_point="What are the key arguments?",
    explanation="Analyze the arguments in the content"
)

# Batch processing
items = [
    {"content": "Content 1", "content_type": CONTENT_TYPE_TEXT},
    {"content": "Content 2", "content_type": CONTENT_TYPE_TEXT}
]
results = await processor.batch_process(
    items=items,
    focus_point="Extract key information",
    explanation="Extract important information from each item"
)
```

## API Endpoints

The Wiseflow API provides the following endpoints for LLM integration:

- `POST /api/v1/process` - Process content using specialized prompting strategies
- `POST /api/v1/batch` - Process multiple content items concurrently
- `POST /api/v1/integration/extract` - Extract information from content
- `POST /api/v1/integration/analyze` - Analyze content using multi-step reasoning
- `POST /api/v1/integration/contextual` - Process content with contextual understanding

## Error Handling

The LLM integration components include robust error handling with:

1. **Rate Limiting** - Handles rate limit errors with exponential backoff
2. **Connection Errors** - Retries on connection errors
3. **API Errors** - Handles various API errors appropriately
4. **Client Errors** - Provides clear error messages for client errors

## Recent Updates

The following updates have been made to the LLM integration components:

1. Updated OpenAI wrapper to use the latest API client (v1.0+)
2. Enhanced error handling in both OpenAI and LiteLLM wrappers
3. Improved async implementation in LiteLLM wrapper
4. Consolidated duplicate code in specialized prompting modules
5. Fixed potential issues with background tasks in the API server
6. Added proper exports in module __init__ files
7. Added comprehensive documentation

## Troubleshooting

If you encounter issues with the LLM integration, check the following:

1. Ensure that the required environment variables are set correctly
2. Verify that the dependencies are installed with the correct versions
3. Check the logs for specific error messages
4. Ensure that the API keys are valid and have the necessary permissions

