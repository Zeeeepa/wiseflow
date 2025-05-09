"""
Utility functions for prompt handling and token management.

This module provides utility functions for handling prompts, managing tokens,
and processing LLM responses.
"""

import os
import json
import logging
import re
import random
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

try:
    import tiktoken
except ImportError:
    tiktoken = None

logger = logging.getLogger(__name__)

def get_token_count(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Count the number of tokens in a text string.
    
    Args:
        text: The text to count tokens for
        model: The model to use for token counting
        
    Returns:
        int: The number of tokens
    """
    if not text:
        return 0
        
    try:
        if tiktoken:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        else:
            # Fallback to approximate count (1 token ≈ 4 chars for English text)
            return len(text) // 4
    except Exception as e:
        logger.warning(f"Error counting tokens: {e}. Using approximate count.")
        # Fallback to approximate count
        return len(text) // 4

def get_model_token_limit(model: str) -> int:
    """
    Get the token limit for a specific model.
    
    Args:
        model: The model name
        
    Returns:
        int: The token limit
    """
    # Define token limits for known models
    token_limits = {
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-16k": 16384,
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-turbo": 128000,
        "claude-instant-1": 100000,
        "claude-2": 100000,
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000
    }
    
    # Return the token limit for the model, or a default value
    return token_limits.get(model, 4096)

def chunk_content(content: str, max_chunk_tokens: int = 4000, model: str = "gpt-3.5-turbo") -> List[str]:
    """
    Split content into chunks that fit within token limits.
    
    Args:
        content: The content to chunk
        max_chunk_tokens: Maximum tokens per chunk
        model: The model to use for token counting
        
    Returns:
        List[str]: List of content chunks
    """
    if not content:
        return []
        
    # If content is small enough, return as is
    if get_token_count(content, model) <= max_chunk_tokens:
        return [content]
    
    # Split by paragraphs first
    paragraphs = content.split("\n\n")
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If a single paragraph is too large, split it by sentences
        if get_token_count(paragraph, model) > max_chunk_tokens:
            sentences = paragraph.split(". ")
            for sentence in sentences:
                sentence_with_period = sentence + ". "
                if get_token_count(current_chunk + sentence_with_period, model) > max_chunk_tokens:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence_with_period
                else:
                    current_chunk += sentence_with_period
        else:
            if get_token_count(current_chunk + paragraph + "\n\n", model) > max_chunk_tokens:
                chunks.append(current_chunk)
                current_chunk = paragraph + "\n\n"
            else:
                current_chunk += paragraph + "\n\n"
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def truncate_content_to_fit(content: str, max_tokens: int, model: str = "gpt-3.5-turbo") -> str:
    """
    Truncate content to fit within token limits while preserving meaning.
    
    Args:
        content: The content to truncate
        max_tokens: Maximum tokens allowed
        model: The model to use for token counting
        
    Returns:
        str: Truncated content
    """
    if not content:
        return ""
        
    # If content already fits, return as is
    if get_token_count(content, model) <= max_tokens:
        return content
    
    # Try to preserve the beginning and end of the content
    if max_tokens >= 1000:
        # For larger token limits, keep more of the beginning and end
        beginning_ratio = 0.7  # 70% from the beginning
        beginning_tokens = int(max_tokens * beginning_ratio)
        end_tokens = max_tokens - beginning_tokens - 50  # Reserve 50 tokens for the ellipsis and buffer
        
        # Get beginning content
        beginning_content = ""
        remaining_content = content
        while get_token_count(beginning_content, model) < beginning_tokens and remaining_content:
            # Take one paragraph at a time
            parts = remaining_content.split("\n\n", 1)
            if len(parts) > 1:
                paragraph, remaining_content = parts
                beginning_content += paragraph + "\n\n"
            else:
                # No more paragraphs, take what's left
                beginning_content += remaining_content
                remaining_content = ""
        
        # Get end content
        end_content = ""
        remaining_content = content
        while get_token_count(end_content, model) < end_tokens and remaining_content:
            # Take one paragraph at a time from the end
            parts = remaining_content.rsplit("\n\n", 1)
            if len(parts) > 1:
                remaining_content, paragraph = parts
                end_content = paragraph + "\n\n" + end_content
            else:
                # No more paragraphs, take what's left
                end_content = remaining_content + end_content
                remaining_content = ""
        
        # Combine with ellipsis
        truncated_content = beginning_content + "\n\n[...content truncated...]\n\n" + end_content
        
        # If still too large, reduce further
        while get_token_count(truncated_content, model) > max_tokens and len(truncated_content) > 100:
            # Reduce by removing from the middle (reduce the beginning)
            beginning_content = beginning_content[:int(len(beginning_content) * 0.9)]
            truncated_content = beginning_content + "\n\n[...content truncated...]\n\n" + end_content
    else:
        # For smaller token limits, just take from the beginning
        truncated_content = content
        while get_token_count(truncated_content, model) > max_tokens and len(truncated_content) > 100:
            truncated_content = truncated_content[:int(len(truncated_content) * 0.9)]
    
    return truncated_content

def parse_json_from_llm_response(response: str) -> Dict[str, Any]:
    """
    Parse JSON from an LLM response with robust error handling.
    
    Args:
        response: The LLM response text
        
    Returns:
        Dict[str, Any]: Parsed JSON or error information
    """
    try:
        # Try to extract JSON from the response using regex patterns
        json_pattern = r'```json\s*([\\s\\S]*?)\s*```'
        json_matches = re.findall(json_pattern, response)
        
        if json_matches:
            for match in json_matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        # Try alternative JSON pattern
        alt_json_pattern = r'({[\s\S]*})'
        alt_matches = re.findall(alt_json_pattern, response)
        
        if alt_matches:
            for match in alt_matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        # If no JSON found or parsing failed, try to parse the entire response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # If all parsing attempts fail, return the raw response
        logger.warning(f"Failed to parse JSON from LLM response: {response[:100]}...")
        return {"raw_response": response, "parsing_error": "Could not extract valid JSON"}
    except Exception as e:
        logger.error(f"Error parsing LLM response: {e}")
        return {"raw_response": response, "parsing_error": str(e)}

async def process_in_chunks(
    content: str,
    process_func: callable,
    max_chunk_tokens: int = 4000,
    model: str = "gpt-3.5-turbo",
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Process large content in chunks and combine results.
    
    Args:
        content: The content to process
        process_func: Async function to process each chunk
        max_chunk_tokens: Maximum tokens per chunk
        model: The model to use for token counting
        **kwargs: Additional arguments to pass to process_func
        
    Returns:
        List[Dict[str, Any]]: Combined results from all chunks
    """
    if not content:
        return []
    
    # Split content into chunks
    chunks = chunk_content(content, max_chunk_tokens, model)
    
    if not chunks:
        return []
    
    # Process each chunk
    tasks = []
    for i, chunk in enumerate(chunks):
        # Add chunk index to kwargs
        chunk_kwargs = kwargs.copy()
        chunk_kwargs["chunk_index"] = i
        chunk_kwargs["total_chunks"] = len(chunks)
        
        # Create task for processing this chunk
        task = asyncio.create_task(process_func(chunk, **chunk_kwargs))
        tasks.append(task)
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions and combine results
    combined_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Error processing chunk: {result}")
        else:
            combined_results.append(result)
    
    return combined_results

