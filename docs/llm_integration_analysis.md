# WiseFlow LLM Integration Analysis and Optimization

## Overview

This document provides a comprehensive analysis of the Large Language Model (LLM) integration in the WiseFlow project, identifying current implementation patterns, potential issues, and recommendations for optimization.

## Current Implementation Analysis

### LLM Wrapper Architecture

The WiseFlow project implements LLM integration through two primary wrapper modules:

1. **OpenAI Wrapper** (`core/llms/openai_wrapper.py`):
   - Provides direct integration with OpenAI's API
   - Implements asynchronous API calls with error handling and retries
   - Uses a semaphore to control concurrent API calls
   - Handles rate limiting and API errors

2. **LiteLLM Wrapper** (`core/llms/litellm_wrapper.py`):
   - Provides a wrapper around the LiteLLM library for multi-provider support
   - Implements both synchronous and asynchronous methods
   - Lacks the robust error handling and retry logic found in the OpenAI wrapper

3. **Advanced Prompting** (`core/llms/advanced/specialized_prompting.py`):
   - Implements specialized prompting strategies for different content types
   - Provides multi-step reasoning and chain-of-thought capabilities
   - Uses template-based prompt generation

### Configuration Management

LLM configuration is managed through the central configuration system in `core/config.py`:

- API keys and base URLs are loaded from environment variables
- Default models are specified with fallback mechanisms
- Concurrency limits are configurable

### Usage Patterns

LLMs are used throughout the codebase for various purposes:

1. **Information Extraction** (`core/general_process.py`):
   - Extracts relevant information from content based on focus points
   - Processes different content types (text, HTML, academic papers, code)

2. **Insight Generation** (`core/run_task.py`):
   - Generates insights from collected information
   - Uses multi-step reasoning for complex analysis

3. **Knowledge Graph Enhancement** (`core/knowledge/graph.py`):
   - Infers relationships between entities
   - Enriches knowledge graphs with LLM-generated insights

## Identified Issues and Optimization Opportunities

### 1. Inconsistent Error Handling

**Issue**: The OpenAI wrapper has robust error handling with retries, but the LiteLLM wrapper has minimal error handling.

**Impact**: This inconsistency can lead to different behavior depending on which wrapper is used, potentially causing unexpected failures when using LiteLLM.

### 2. Limited Caching Strategy

**Issue**: The current implementation lacks a comprehensive caching strategy for LLM responses.

**Impact**: Without proper caching, the system may make redundant API calls for similar or identical prompts, increasing costs and latency.

### 3. Inefficient Token Usage

**Issue**: Prompts are not optimized for token efficiency, and there's no mechanism to track or limit token usage.

**Impact**: This can lead to excessive token consumption, higher costs, and potential truncation of responses.

### 4. Lack of Model Fallback Mechanism

**Issue**: While there's a configuration for primary and secondary models, there's no automatic fallback mechanism if the primary model fails.

**Impact**: If the primary model is unavailable or returns an error, the system may fail instead of gracefully falling back to the secondary model.

### 5. Inadequate Batching of Requests

**Issue**: The system processes items sequentially in many cases, even when batching would be more efficient.

**Impact**: This leads to higher latency and less efficient use of API rate limits.

### 6. Prompt Template Duplication

**Issue**: There's duplication in prompt templates between `specialized_prompting.py` and the `__init__.py` in the advanced directory.

**Impact**: This makes maintenance more difficult and can lead to inconsistencies if one template is updated but not the other.

### 7. Limited Monitoring and Logging

**Issue**: There's limited monitoring and logging of LLM usage, costs, and performance.

**Impact**: Without proper monitoring, it's difficult to identify optimization opportunities or track costs.

### 8. Lack of Streaming Support

**Issue**: The current implementation doesn't support streaming responses from LLMs.

**Impact**: For long responses, this means users must wait for the entire response before seeing any results.

## Optimization Recommendations

### 1. Unified Error Handling and Retry Logic

Implement a consistent error handling and retry mechanism across all LLM wrappers:

```python
# Example implementation for unified error handling
async def handle_llm_errors(func, *args, max_retries=3, **kwargs):
    wait_time = 1
    for retry in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except RateLimitError as e:
            logger.warning(f"Rate limit error: {e}. Retry {retry+1}/{max_retries}")
        except APIError as e:
            if hasattr(e, 'status_code') and e.status_code in [400, 401]:
                logger.error(f"Client error: {e.status_code}. Detail: {e}")
                return None
            logger.warning(f"API error: {e}. Retry {retry+1}/{max_retries}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}. Retry {retry+1}/{max_retries}")
        
        if retry < max_retries - 1:
            await asyncio.sleep(wait_time)
            wait_time *= 2
    
    logger.error("Maximum retries reached, still unable to get a valid response.")
    return None
```

### 2. Implement a Comprehensive Caching System

Add a caching layer to avoid redundant LLM calls:

```python
# Example implementation for LLM response caching
class LLMCache:
    def __init__(self, cache_dir=None, ttl=3600):
        self.cache_dir = cache_dir or os.path.join(os.environ.get("PROJECT_DIR", ""), "llm_cache")
        self.ttl = ttl
        os.makedirs(self.cache_dir, exist_ok=True)
        self.memory_cache = {}
    
    def _get_cache_key(self, messages, model, **kwargs):
        # Create a deterministic cache key from the request parameters
        key_dict = {
            "messages": messages,
            "model": model,
            **{k: v for k, v in kwargs.items() if k not in ["stream", "logger"]}
        }
        return hashlib.md5(json.dumps(key_dict, sort_keys=True).encode()).hexdigest()
    
    def get(self, messages, model, **kwargs):
        key = self._get_cache_key(messages, model, **kwargs)
        
        # Check memory cache first
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                return entry["response"]
            else:
                del self.memory_cache[key]
        
        # Check disk cache
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    entry = json.load(f)
                if time.time() - entry["timestamp"] < self.ttl:
                    # Refresh memory cache
                    self.memory_cache[key] = entry
                    return entry["response"]
                else:
                    os.remove(cache_file)
            except Exception as e:
                logger.error(f"Error reading cache file: {e}")
        
        return None
    
    def set(self, messages, model, response, **kwargs):
        key = self._get_cache_key(messages, model, **kwargs)
        entry = {
            "timestamp": time.time(),
            "response": response
        }
        
        # Update memory cache
        self.memory_cache[key] = entry
        
        # Update disk cache
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        try:
            with open(cache_file, "w") as f:
                json.dump(entry, f)
        except Exception as e:
            logger.error(f"Error writing cache file: {e}")
```

### 3. Optimize Token Usage

Implement token counting and optimization:

```python
# Example implementation for token counting and optimization
def count_tokens(text, model="gpt-3.5-turbo"):
    """Count the number of tokens in a text string."""
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except ImportError:
        # Fallback to approximate counting if tiktoken is not available
        return len(text.split()) * 1.3  # Rough approximation

def optimize_prompt(prompt, max_tokens=4000, model="gpt-3.5-turbo"):
    """Optimize a prompt to fit within token limits."""
    current_tokens = count_tokens(prompt, model)
    
    if current_tokens <= max_tokens:
        return prompt
    
    # Simple truncation strategy - more sophisticated strategies could be implemented
    ratio = max_tokens / current_tokens
    words = prompt.split()
    truncated_words = words[:int(len(words) * ratio * 0.9)]  # 10% safety margin
    return " ".join(truncated_words)
```

### 4. Implement Model Fallback Mechanism

Add automatic fallback to secondary models:

```python
# Example implementation for model fallback
async def llm_with_fallback(messages, primary_model, secondary_model, **kwargs):
    try:
        return await openai_llm(messages, primary_model, **kwargs)
    except Exception as e:
        logger.warning(f"Primary model {primary_model} failed: {e}. Falling back to {secondary_model}")
        try:
            return await openai_llm(messages, secondary_model, **kwargs)
        except Exception as e2:
            logger.error(f"Secondary model {secondary_model} also failed: {e2}")
            raise
```

### 5. Implement Efficient Request Batching

Optimize the batch processing functionality:

```python
# Example implementation for efficient batching
async def batch_process_optimized(items, process_func, max_concurrency=5, chunk_size=None):
    """Process items in optimized batches with controlled concurrency."""
    if chunk_size:
        # Process in chunks for more efficient API usage
        results = []
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i+chunk_size]
            # Process each chunk with controlled concurrency
            semaphore = asyncio.Semaphore(max_concurrency)
            
            async def process_with_semaphore(item):
                async with semaphore:
                    return await process_func(item)
            
            chunk_tasks = [process_with_semaphore(item) for item in chunk]
            chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)
            results.extend(chunk_results)
        return results
    else:
        # Process all items with controlled concurrency
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def process_with_semaphore(item):
            async with semaphore:
                return await process_func(item)
        
        tasks = [process_with_semaphore(item) for item in items]
        return await asyncio.gather(*tasks, return_exceptions=True)
```

### 6. Consolidate Prompt Templates

Refactor the prompt templates to eliminate duplication:

```python
# Example implementation for consolidated prompt templates
# Create a single source of truth for prompt templates in a dedicated module
from typing import Dict, Any

class PromptLibrary:
    """Central repository for all prompt templates."""
    
    @staticmethod
    def get_template(template_name: str) -> Dict[str, Any]:
        """Get a prompt template by name."""
        templates = {
            "general_extraction": {
                "template": (
                    "You are an expert information extraction system. "
                    "Your task is to extract relevant information from the provided content "
                    "based on the focus point: {focus_point}.\n\n"
                    "Additional context: {explanation}\n\n"
                    "Content:\n{content}\n\n"
                    "Extract the most relevant information related to the focus point. "
                    "Format your response as a JSON object with the following structure:\n"
                    "```json\n"
                    "{\n"
                    "  \"relevance\": \"high|medium|low\",\n"
                    "  \"extracted_info\": [\n"
                    "    {\n"
                    "      \"content\": \"extracted information\",\n"
                    "      \"relevance_score\": 0.0-1.0,\n"
                    "      \"reasoning\": \"why this information is relevant\"\n"
                    "    }\n"
                    "  ],\n"
                    "  \"summary\": \"brief summary of the extracted information\"\n"
                    "}\n"
                    "```\n"
                ),
                "input_variables": ["focus_point", "explanation", "content"]
            },
            # Add other templates here
        }
        
        if template_name not in templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        return templates[template_name]
```

### 7. Implement Comprehensive Monitoring and Logging

Add detailed monitoring and logging for LLM usage:

```python
# Example implementation for LLM usage monitoring
class LLMMonitor:
    def __init__(self):
        self.usage_log = []
        self.cost_per_1k_tokens = {
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-4": {"input": 0.03, "output": 0.06},
            # Add other models as needed
        }
    
    async def log_usage(self, model, prompt_tokens, completion_tokens, duration_ms, success):
        """Log usage of LLM API."""
        timestamp = datetime.now().isoformat()
        
        # Calculate estimated cost
        cost = 0
        if model in self.cost_per_1k_tokens:
            input_cost = (prompt_tokens / 1000) * self.cost_per_1k_tokens[model]["input"]
            output_cost = (completion_tokens / 1000) * self.cost_per_1k_tokens[model]["output"]
            cost = input_cost + output_cost
        
        usage_entry = {
            "timestamp": timestamp,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "duration_ms": duration_ms,
            "success": success,
            "estimated_cost": cost
        }
        
        self.usage_log.append(usage_entry)
        
        # Log to database or file
        try:
            # Example: Save to database
            pb.add(collection_name='llm_usage', body=usage_entry)
        except Exception as e:
            logger.error(f"Error logging LLM usage: {e}")
        
        # Log summary
        logger.info(
            f"LLM API call: model={model}, tokens={prompt_tokens}+{completion_tokens}={prompt_tokens+completion_tokens}, "
            f"duration={duration_ms}ms, cost=${cost:.6f}, success={success}"
        )
        
        return usage_entry
    
    def get_usage_summary(self, start_time=None, end_time=None):
        """Get summary of LLM usage."""
        filtered_log = self.usage_log
        
        if start_time:
            filtered_log = [entry for entry in filtered_log if entry["timestamp"] >= start_time]
        if end_time:
            filtered_log = [entry for entry in filtered_log if entry["timestamp"] <= end_time]
        
        if not filtered_log:
            return {"total_calls": 0, "total_tokens": 0, "total_cost": 0, "success_rate": 0}
        
        total_calls = len(filtered_log)
        successful_calls = sum(1 for entry in filtered_log if entry["success"])
        total_tokens = sum(entry["total_tokens"] for entry in filtered_log)
        total_cost = sum(entry["estimated_cost"] for entry in filtered_log)
        
        return {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "models_used": Counter(entry["model"] for entry in filtered_log)
        }
```

### 8. Add Streaming Support

Implement streaming for long responses:

```python
# Example implementation for streaming support
async def openai_llm_streaming(messages, model, callback, logger=None, **kwargs):
    """
    Make an asynchronous streaming call to the OpenAI API.
    
    Args:
        messages: List of message dictionaries to send to the API
        model: Model name to use for the API call
        callback: Function to call with each chunk of the response
        logger: Optional logger for logging API calls and errors
        **kwargs: Additional keyword arguments to pass to the API
        
    Returns:
        The complete content of the API response
    """
    if logger:
        logger.debug(f'Streaming messages:\n {messages}')
        logger.debug(f'model: {model}')
        logger.debug(f'kwargs:\n {kwargs}')
    
    try:
        response = await client.chat.completions.create(
            messages=messages,
            model=model,
            stream=True,
            **kwargs
        )
        
        full_content = ""
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                content_chunk = chunk.choices[0].delta.content
                full_content += content_chunk
                await callback(content_chunk)
        
        return full_content
    except Exception as e:
        logger.error(f"Error in streaming LLM call: {e}")
        raise
```

## Implementation Plan

The following implementation plan prioritizes the optimizations based on their impact and complexity:

### Phase 1: Immediate Improvements (High Impact, Low Complexity)

1. **Unify Error Handling**: Implement consistent error handling across all LLM wrappers
2. **Add Model Fallback**: Implement automatic fallback to secondary models
3. **Consolidate Prompt Templates**: Refactor to eliminate duplication

### Phase 2: Efficiency Optimizations (High Impact, Medium Complexity)

1. **Implement Caching System**: Add a comprehensive caching layer
2. **Optimize Token Usage**: Implement token counting and optimization
3. **Improve Request Batching**: Enhance the batch processing functionality

### Phase 3: Advanced Features (Medium Impact, High Complexity)

1. **Add Monitoring and Logging**: Implement detailed usage tracking
2. **Implement Streaming Support**: Add streaming for long responses

## Conclusion

The current LLM integration in WiseFlow provides a solid foundation but has several opportunities for optimization. By implementing the recommendations in this document, the system can achieve better performance, reliability, and cost-effectiveness.

The most critical improvements are unifying error handling, implementing a caching system, and adding model fallback mechanisms. These changes will provide immediate benefits with relatively low implementation complexity.

