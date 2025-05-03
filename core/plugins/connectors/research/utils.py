"""
Utility functions for the research connector.
"""

import os
import asyncio
import requests
import random
import time
import json
from typing import List, Dict, Any, Optional, Union
from urllib.parse import unquote
from bs4 import BeautifulSoup

from core.plugins.connectors.research.state import Section

def get_config_value(value):
    """
    Helper function to handle string, dict, and enum cases of configuration values
    """
    if isinstance(value, str):
        return value
    elif isinstance(value, dict):
        return value
    else:
        return value.value

def get_search_params(search_api: str, search_api_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Filters the search_api_config dictionary to include only parameters accepted by the specified search API.

    Args:
        search_api (str): The search API identifier (e.g., "exa", "tavily").
        search_api_config (Optional[Dict[str, Any]]): The configuration dictionary for the search API.

    Returns:
        Dict[str, Any]: A dictionary of parameters to pass to the search function.
    """
    # Define accepted parameters for each search API
    SEARCH_API_PARAMS = {
        "exa": ["max_characters", "num_results", "include_domains", "exclude_domains", "subpages"],
        "tavily": ["max_results", "topic"],
        "perplexity": [],  # Perplexity accepts no additional parameters
        "arxiv": ["load_max_docs", "get_full_documents", "load_all_available_meta"],
        "pubmed": ["top_k_results", "email", "api_key", "doc_content_chars_max"],
        "linkup": ["depth"],
        "duckduckgo": [],
        "googlesearch": ["num_results", "include_domains", "exclude_domains"],
    }

    # Get the list of accepted parameters for the given search API
    accepted_params = SEARCH_API_PARAMS.get(search_api, [])

    # If no config provided, return an empty dict
    if not search_api_config:
        return {}

    # Filter the config to only include accepted parameters
    return {k: v for k, v in search_api_config.items() if k in accepted_params}

def deduplicate_and_format_sources(search_response, max_tokens_per_source=5000, include_raw_content=True):
    """
    Takes a list of search responses and formats them into a readable string.
    Limits the raw_content to approximately max_tokens_per_source tokens.
 
    Args:
        search_responses: List of search response dicts, each containing:
            - query: str
            - results: List of dicts with fields:
                - title: str
                - url: str
                - content: str
                - score: float
                - raw_content: str|None
        max_tokens_per_source: int
        include_raw_content: bool
            
    Returns:
        str: Formatted string with deduplicated sources
    """
    # Collect all results
    sources_list = []
    for response in search_response:
        sources_list.extend(response['results'])
    
    # Deduplicate by URL
    unique_sources = {source['url']: source for source in sources_list}

    # Format output
    formatted_text = "Content from sources:\n"
    for i, source in enumerate(unique_sources.values(), 1):
        formatted_text += f"{'='*80}\n"  # Clear section separator
        formatted_text += f"Source: {source['title']}\n"
        formatted_text += f"{'-'*80}\n"  # Subsection separator
        formatted_text += f"URL: {source['url']}\n===\n"
        formatted_text += f"Most relevant content from source: {source['content']}\n===\n"
        if include_raw_content:
            # Using rough estimate of 4 characters per token
            char_limit = max_tokens_per_source * 4
            # Handle None raw_content
            raw_content = source.get('raw_content', '')
            if raw_content is None:
                raw_content = ''
                print(f"Warning: No raw_content found for source {source['url']}")
            if len(raw_content) > char_limit:
                raw_content = raw_content[:char_limit] + "... [truncated]"
            formatted_text += f"Full source content limited to {max_tokens_per_source} tokens: {raw_content}\n\n"
        formatted_text += f"{'='*80}\n\n" # End section separator
                
    return formatted_text.strip()

def format_sections(sections: List[Section]) -> str:
    """ Format a list of sections into a string """
    formatted_str = ""
    for idx, section in enumerate(sections, 1):
        formatted_str += f"""
{'='*60}
Section {idx}: {section.name}
{'='*60}
Description:
{section.description}
Requires Research: 
{section.research}

Content:
{section.content if section.content else '[Not yet written]'}

"""
    return formatted_str

async def tavily_search_async(search_queries, api_key=None, max_results=5, topic="general", include_raw_content=True):
    """
    Performs concurrent web searches with the Tavily API

    Args:
        search_queries (List[str]): List of search queries to process
        api_key (str, optional): Tavily API key. If not provided, uses TAVILY_API_KEY env var.
        max_results (int, optional): Maximum number of results to return. Defaults to 5.
        topic (str, optional): Topic for search context. Defaults to "general".
        include_raw_content (bool, optional): Whether to include raw content. Defaults to True.

    Returns:
        List[dict]: List of search responses from Tavily API
    """
    # Use provided API key or get from environment
    api_key = api_key or os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("Tavily API key not provided and TAVILY_API_KEY environment variable not set")
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    
    async def search_single_query(query):
        url = "https://api.tavily.com/search"
        payload = {
            "query": query,
            "search_depth": "advanced",
            "max_results": max_results,
            "include_raw_content": include_raw_content,
            "include_domains": [],
            "exclude_domains": [],
            "topic": topic
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "query": query,
                        "follow_up_questions": result.get("follow_up_questions"),
                        "answer": result.get("answer"),
                        "images": result.get("images", []),
                        "results": result.get("results", [])
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Tavily API error: {response.status} - {error_text}")
    
    # Import aiohttp here to avoid dependency issues if not using Tavily
    import aiohttp
    
    # Execute all searches concurrently
    search_tasks = [search_single_query(query) for query in search_queries]
    search_docs = await asyncio.gather(*search_tasks)
    return search_docs

def perplexity_search(search_queries, api_key=None):
    """
    Search the web using the Perplexity API.
    
    Args:
        search_queries (List[str]): List of search queries to process
        api_key (str, optional): Perplexity API key. If not provided, uses PERPLEXITY_API_KEY env var.
  
    Returns:
        List[dict]: List of search responses from Perplexity API
    """
    # Use provided API key or get from environment
    api_key = api_key or os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        raise ValueError("Perplexity API key not provided and PERPLEXITY_API_KEY environment variable not set")

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    search_docs = []
    for query in search_queries:
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": "Search the web and provide factual information with sources."
                },
                {
                    "role": "user",
                    "content": query
                }
            ]
        }
        
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()  # Raise exception for bad status codes
        
        # Parse the response
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        citations = data.get("citations", ["https://perplexity.ai"])
        
        # Create results list for this query
        results = []
        
        # First citation gets the full content
        results.append({
            "title": f"Perplexity Search, Source 1",
            "url": citations[0],
            "content": content,
            "raw_content": content,
            "score": 1.0  # Adding score to match Tavily format
        })
        
        # Add additional citations without duplicating content
        for i, citation in enumerate(citations[1:], start=2):
            results.append({
                "title": f"Perplexity Search, Source {i}",
                "url": citation,
                "content": "See primary source for full content",
                "raw_content": None,
                "score": 0.5  # Lower score for secondary sources
            })
        
        # Format response to match Tavily structure
        search_docs.append({
            "query": query,
            "follow_up_questions": None,
            "answer": None,
            "images": [],
            "results": results
        })
    
    return search_docs

async def exa_search(search_queries, api_key=None, max_characters=None, num_results=5, 
                     include_domains=None, exclude_domains=None, subpages=False):
    """
    Search the web using the Exa API.
    
    Args:
        search_queries (List[str]): List of search queries to process
        api_key (str, optional): Exa API key. If not provided, uses EXA_API_KEY env var.
        max_characters (int, optional): Maximum characters to return per result
        num_results (int, optional): Number of results to return per query
        include_domains (List[str], optional): Domains to include in search
        exclude_domains (List[str], optional): Domains to exclude from search
        subpages (bool, optional): Whether to include subpages in search
        
    Returns:
        List[dict]: List of search responses from Exa API
    """
    # Import Exa here to avoid dependency issues if not using Exa
    try:
        from exa_py import Exa
    except ImportError:
        raise ImportError("Exa Python client not installed. Install with: pip install exa-py")
    
    # Use provided API key or get from environment
    api_key = api_key or os.environ.get("EXA_API_KEY")
    if not api_key:
        raise ValueError("Exa API key not provided and EXA_API_KEY environment variable not set")
    
    exa_client = Exa(api_key)
    
    search_docs = []
    for query in search_queries:
        try:
            # Execute search
            results = exa_client.search(
                query,
                num_results=num_results,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                use_autoprompt=True,
                text=True,
                subpages=subpages
            )
            
            # Format results to match Tavily structure
            formatted_results = []
            for result in results.results:
                # Get content with character limit if specified
                content = result.text
                if max_characters and content and len(content) > max_characters:
                    content = content[:max_characters] + "... [truncated]"
                
                formatted_results.append({
                    "title": result.title,
                    "url": result.url,
                    "content": result.extract,  # Summary
                    "raw_content": content,     # Full content
                    "score": result.score
                })
            
            # Add to search docs
            search_docs.append({
                "query": query,
                "follow_up_questions": None,
                "answer": None,
                "images": [],
                "results": formatted_results
            })
            
        except Exception as e:
            print(f"Error in Exa search for query '{query}': {str(e)}")
            # Add empty result on error
            search_docs.append({
                "query": query,
                "follow_up_questions": None,
                "answer": None,
                "images": [],
                "results": [],
                "error": str(e)
            })
    
    return search_docs

async def select_and_execute_search(search_api: str, query_list: List[str], api_keys: Dict[str, str], params_to_pass: Dict[str, Any]) -> str:
    """
    Select and execute the appropriate search API.
    
    Args:
        search_api: Name of the search API to use
        query_list: List of search queries to execute
        api_keys: Dictionary of API keys for different search services
        params_to_pass: Parameters to pass to the search API
        
    Returns:
        Formatted string containing search results
        
    Raises:
        ValueError: If an unsupported search API is specified
    """
    if search_api == "tavily":
        api_key = api_keys.get("tavily")
        search_results = await tavily_search_async(query_list, api_key=api_key, **params_to_pass)
        return deduplicate_and_format_sources(search_results, max_tokens_per_source=4000)
    elif search_api == "perplexity":
        api_key = api_keys.get("perplexity")
        search_results = perplexity_search(query_list, api_key=api_key, **params_to_pass)
        return deduplicate_and_format_sources(search_results, max_tokens_per_source=4000)
    elif search_api == "exa":
        api_key = api_keys.get("exa")
        search_results = await exa_search(query_list, api_key=api_key, **params_to_pass)
        return deduplicate_and_format_sources(search_results, max_tokens_per_source=4000)
    else:
        raise ValueError(f"Unsupported search API: {search_api}")

