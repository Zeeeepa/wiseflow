"""Utility functions for research module."""

import os
import json
import logging
import time
import functools
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
import importlib.util
import traceback

from langchain_core.runnables import RunnableConfig
from langchain.chat_models import init_chat_model

from core.plugins.connectors.research.state import Sections, Section
from core.plugins.connectors.research.configuration import Configuration, SearchAPI

# Setup logger
logger = logging.getLogger(__name__)

# Simple in-memory cache for search results
_search_cache = {}
_cache_timestamps = {}

def format_sections(sections: Sections) -> List[Dict[str, Any]]:
    """Format sections for output.
    
    Args:
        sections (Sections): The sections to format
        
    Returns:
        List[Dict[str, Any]]: The formatted sections
    """
    formatted_sections = []
    
    for section in sections.sections:
        formatted_section = {
            "title": section.title,
            "content": section.content,
            "subsections": []
        }
        
        for subsection in section.subsections:
            formatted_subsection = {
                "title": subsection.title,
                "content": subsection.content
            }
            formatted_section["subsections"].append(formatted_subsection)
        
        formatted_sections.append(formatted_section)
    
    return formatted_sections

def get_config_value(key: str, config: Optional[RunnableConfig] = None) -> Any:
    """Get a configuration value from environment or RunnableConfig.
    
    Args:
        key (str): The configuration key
        config (Optional[RunnableConfig], optional): The RunnableConfig. Defaults to None.
        
    Returns:
        Any: The configuration value
    """
    if config and "configurable" in config and key in config["configurable"]:
        return config["configurable"][key]
    
    env_key = key.upper()
    if env_key in os.environ:
        return os.environ[env_key]
    
    return None

def get_search_params(config: Optional[Configuration] = None) -> Dict[str, Any]:
    """Get search parameters from configuration.
    
    Args:
        config (Optional[Configuration], optional): The configuration. Defaults to None.
        
    Returns:
        Dict[str, Any]: The search parameters
    """
    if not config:
        config = Configuration()
    
    search_api = config.search_api
    search_params = config.search_api_config or {}
    
    # Add API keys from environment variables if not provided
    if search_api == SearchAPI.TAVILY and "api_key" not in search_params:
        search_params["api_key"] = os.environ.get("TAVILY_API_KEY")
    
    elif search_api == SearchAPI.PERPLEXITY and "api_key" not in search_params:
        search_params["api_key"] = os.environ.get("PERPLEXITY_API_KEY")
    
    elif search_api == SearchAPI.EXA and "api_key" not in search_params:
        search_params["api_key"] = os.environ.get("EXA_API_KEY")
    
    elif search_api == SearchAPI.LINKUP and "api_key" not in search_params:
        search_params["api_key"] = os.environ.get("LINKUP_API_KEY")
    
    # Add common parameters
    search_params["max_retries"] = config.max_retries
    search_params["retry_delay"] = config.retry_delay
    
    return search_params

def cache_key(query: str, search_api: SearchAPI, params: Dict[str, Any]) -> str:
    """Generate a cache key for search results.
    
    Args:
        query (str): The search query
        search_api (SearchAPI): The search API used
        params (Dict[str, Any]): The search parameters
        
    Returns:
        str: The cache key
    """
    # Create a deterministic representation of the parameters
    param_str = json.dumps(params, sort_keys=True)
    key_str = f"{query}:{search_api.value}:{param_str}"
    
    # Create a hash of the key string
    return hashlib.md5(key_str.encode()).hexdigest()

def clear_expired_cache(ttl: int = 3600) -> None:
    """Clear expired cache entries.
    
    Args:
        ttl (int, optional): Cache time-to-live in seconds. Defaults to 3600.
    """
    now = datetime.now()
    expired_keys = []
    
    for key, timestamp in _cache_timestamps.items():
        if (now - timestamp).total_seconds() > ttl:
            expired_keys.append(key)
    
    for key in expired_keys:
        if key in _search_cache:
            del _search_cache[key]
        if key in _cache_timestamps:
            del _cache_timestamps[key]
    
    logger.debug(f"Cleared {len(expired_keys)} expired cache entries")

def with_retry(max_retries: int = 3, retry_delay: float = 1.0):
    """Decorator for functions that should be retried on failure.
    
    Args:
        max_retries (int, optional): Maximum number of retries. Defaults to 3.
        retry_delay (float, optional): Delay between retries in seconds. Defaults to 1.0.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = retry_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed: {str(e)}. "
                            f"Retrying in {delay:.2f} seconds..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed. Last error: {str(e)}"
                        )
            
            # If we get here, all attempts failed
            raise last_exception
        
        return wrapper
    
    return decorator

def select_and_execute_search(
    query: str, 
    search_api: SearchAPI, 
    search_params: Dict[str, Any],
    config: Optional[Configuration] = None
) -> List[Dict[str, Any]]:
    """Select and execute a search API with fallback support.
    
    Args:
        query (str): The search query
        search_api (SearchAPI): The search API to use
        search_params (Dict[str, Any]): The search parameters
        config (Optional[Configuration], optional): The configuration. Defaults to None.
        
    Returns:
        List[Dict[str, Any]]: The search results
    """
    if not config:
        config = Configuration()
    
    # Check cache first if enabled
    if config.enable_search_cache:
        cache_k = cache_key(query, search_api, search_params)
        clear_expired_cache(config.cache_ttl)
        
        if cache_k in _search_cache:
            logger.debug(f"Cache hit for query: {query}")
            return _search_cache[cache_k]
    
    # Try primary search API
    try:
        logger.info(f"Executing search with {search_api.value} for query: {query}")
        results = _execute_search(query, search_api, search_params)
        
        # Cache results if enabled
        if config.enable_search_cache and results:
            cache_k = cache_key(query, search_api, search_params)
            _search_cache[cache_k] = results
            _cache_timestamps[cache_k] = datetime.now()
            logger.debug(f"Cached results for query: {query}")
        
        return results
    except Exception as e:
        logger.error(f"Error executing search with {search_api.value}: {str(e)}")
        logger.debug(f"Error details: {traceback.format_exc()}")
        
        # Try fallback APIs if enabled
        if config.enable_fallback_apis and config.fallback_apis:
            for fallback_api in config.fallback_apis:
                if fallback_api != search_api:
                    try:
                        logger.info(f"Trying fallback API {fallback_api.value} for query: {query}")
                        results = _execute_search(query, fallback_api, search_params)
                        
                        # Cache results if enabled
                        if config.enable_search_cache and results:
                            cache_k = cache_key(query, fallback_api, search_params)
                            _search_cache[cache_k] = results
                            _cache_timestamps[cache_k] = datetime.now()
                            logger.debug(f"Cached results from fallback API for query: {query}")
                        
                        return results
                    except Exception as fallback_e:
                        logger.error(f"Error executing fallback search with {fallback_api.value}: {str(fallback_e)}")
                        logger.debug(f"Fallback error details: {traceback.format_exc()}")
        
        # If all APIs fail, return empty results
        logger.error(f"All search APIs failed for query: {query}")
        return []

def _execute_search(query: str, search_api: SearchAPI, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute a search with the specified API.
    
    Args:
        query (str): The search query
        search_api (SearchAPI): The search API to use
        search_params (Dict[str, Any]): The search parameters
        
    Returns:
        List[Dict[str, Any]]: The search results
    """
    if search_api == SearchAPI.TAVILY:
        return _execute_tavily_search(query, search_params)
    elif search_api == SearchAPI.PERPLEXITY:
        return _execute_perplexity_search(query, search_params)
    elif search_api == SearchAPI.EXA:
        return _execute_exa_search(query, search_params)
    elif search_api == SearchAPI.ARXIV:
        return _execute_arxiv_search(query, search_params)
    elif search_api == SearchAPI.PUBMED:
        return _execute_pubmed_search(query, search_params)
    elif search_api == SearchAPI.LINKUP:
        return _execute_linkup_search(query, search_params)
    elif search_api == SearchAPI.DUCKDUCKGO:
        return _execute_duckduckgo_search(query, search_params)
    elif search_api == SearchAPI.GOOGLESEARCH:
        return _execute_googlesearch_search(query, search_params)
    else:
        raise ValueError(f"Unsupported search API: {search_api}")

@with_retry()
def _execute_tavily_search(query: str, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute a Tavily search.
    
    Args:
        query (str): The search query
        search_params (Dict[str, Any]): The search parameters
        
    Returns:
        List[Dict[str, Any]]: The search results
    """
    try:
        from tavily import TavilyClient
        
        api_key = search_params.get("api_key")
        if not api_key:
            raise ValueError("Tavily API key not provided")
        
        client = TavilyClient(api_key=api_key)
        
        search_depth = search_params.get("search_depth", "basic")
        max_results = search_params.get("max_results", 10)
        
        logger.debug(f"Executing Tavily search with depth={search_depth}, max_results={max_results}")
        
        response = client.search(
            query=query,
            search_depth=search_depth,
            max_results=max_results
        )
        
        results = response.get("results", [])
        logger.debug(f"Tavily search returned {len(results)} results")
        
        return results
    except ImportError:
        logger.error("Tavily package not installed. Please install with 'pip install tavily'")
        raise
    except Exception as e:
        logger.error(f"Error executing Tavily search: {str(e)}")
        raise

@with_retry()
def _execute_perplexity_search(query: str, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute a Perplexity search.
    
    Args:
        query (str): The search query
        search_params (Dict[str, Any]): The search parameters
        
    Returns:
        List[Dict[str, Any]]: The search results
    """
    try:
        import requests
        
        api_key = search_params.get("api_key")
        if not api_key:
            raise ValueError("Perplexity API key not provided")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        max_results = search_params.get("max_results", 10)
        
        data = {
            "query": query,
            "max_results": max_results
        }
        
        logger.debug(f"Executing Perplexity search with max_results={max_results}")
        
        response = requests.post(
            "https://api.perplexity.ai/search",
            headers=headers,
            json=data,
            timeout=30  # Add timeout to prevent hanging
        )
        
        if response.status_code != 200:
            logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
            raise ValueError(f"Perplexity API error: {response.status_code} - {response.text}")
        
        results = response.json().get("results", [])
        
        # Format results to match Tavily format
        formatted_results = []
        for result in results:
            formatted_results.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "score": result.get("relevance_score", 0)
            })
        
        logger.debug(f"Perplexity search returned {len(formatted_results)} results")
        
        return formatted_results
    except ImportError:
        logger.error("Requests package not installed. Please install with 'pip install requests'")
        raise
    except Exception as e:
        logger.error(f"Error executing Perplexity search: {str(e)}")
        raise

@with_retry()
def _execute_exa_search(query: str, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute an Exa search.
    
    Args:
        query (str): The search query
        search_params (Dict[str, Any]): The search parameters
        
    Returns:
        List[Dict[str, Any]]: The search results
    """
    try:
        from exa_py import Exa
        
        api_key = search_params.get("api_key")
        if not api_key:
            raise ValueError("Exa API key not provided")
        
        exa = Exa(api_key=api_key)
        
        max_results = search_params.get("max_results", 10)
        use_autoprompt = search_params.get("use_autoprompt", True)
        
        logger.debug(f"Executing Exa search with max_results={max_results}, use_autoprompt={use_autoprompt}")
        
        response = exa.search(
            query=query,
            num_results=max_results,
            use_autoprompt=use_autoprompt
        )
        
        # Format results to match Tavily format
        formatted_results = []
        for result in response.results:
            formatted_results.append({
                "title": result.title,
                "url": result.url,
                "content": result.text,
                "score": result.relevance_score
            })
        
        logger.debug(f"Exa search returned {len(formatted_results)} results")
        
        return formatted_results
    except ImportError:
        logger.error("Exa package not installed. Please install with 'pip install exa-py'")
        raise
    except Exception as e:
        logger.error(f"Error executing Exa search: {str(e)}")
        raise

@with_retry()
def _execute_arxiv_search(query: str, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute an arXiv search.
    
    Args:
        query (str): The search query
        search_params (Dict[str, Any]): The search parameters
        
    Returns:
        List[Dict[str, Any]]: The search results
    """
    try:
        import arxiv
        
        max_results = search_params.get("max_results", 10)
        
        logger.debug(f"Executing arXiv search with max_results={max_results}")
        
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        results = list(client.results(search))
        
        # Format results to match Tavily format
        formatted_results = []
        for result in results:
            formatted_results.append({
                "title": result.title,
                "url": result.pdf_url,
                "content": result.summary,
                "authors": [author.name for author in result.authors],
                "published": result.published.strftime("%Y-%m-%d"),
                "score": 1.0  # arXiv doesn't provide relevance scores
            })
        
        logger.debug(f"arXiv search returned {len(formatted_results)} results")
        
        return formatted_results
    except ImportError:
        logger.error("arXiv package not installed. Please install with 'pip install arxiv'")
        raise
    except Exception as e:
        logger.error(f"Error executing arXiv search: {str(e)}")
        raise

@with_retry()
def _execute_pubmed_search(query: str, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute a PubMed search.
    
    Args:
        query (str): The search query
        search_params (Dict[str, Any]): The search parameters
        
    Returns:
        List[Dict[str, Any]]: The search results
    """
    try:
        from pymed import PubMed
        
        max_results = search_params.get("max_results", 10)
        email = search_params.get("email", "example@example.com")
        
        logger.debug(f"Executing PubMed search with max_results={max_results}")
        
        pubmed = PubMed(tool="WiseflowResearch", email=email)
        results = pubmed.query(query, max_results=max_results)
        
        # Format results to match Tavily format
        formatted_results = []
        for article in results:
            formatted_results.append({
                "title": article.title,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{article.pubmed_id}/",
                "content": article.abstract,
                "authors": [author.get("lastname", "") + " " + author.get("firstname", "") for author in article.authors],
                "published": article.publication_date.strftime("%Y-%m-%d") if article.publication_date else "",
                "score": 1.0  # PubMed doesn't provide relevance scores
            })
        
        logger.debug(f"PubMed search returned {len(formatted_results)} results")
        
        return formatted_results
    except ImportError:
        logger.error("PyMed package not installed. Please install with 'pip install pymed'")
        raise
    except Exception as e:
        logger.error(f"Error executing PubMed search: {str(e)}")
        raise

@with_retry()
def _execute_linkup_search(query: str, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute a LinkUp search.
    
    Args:
        query (str): The search query
        search_params (Dict[str, Any]): The search parameters
        
    Returns:
        List[Dict[str, Any]]: The search results
    """
    try:
        import requests
        
        api_key = search_params.get("api_key")
        if not api_key:
            raise ValueError("LinkUp API key not provided")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        max_results = search_params.get("max_results", 10)
        
        data = {
            "query": query,
            "limit": max_results
        }
        
        logger.debug(f"Executing LinkUp search with max_results={max_results}")
        
        response = requests.post(
            "https://api.linkup.com/v1/search",
            headers=headers,
            json=data,
            timeout=30  # Add timeout to prevent hanging
        )
        
        if response.status_code != 200:
            logger.error(f"LinkUp API error: {response.status_code} - {response.text}")
            raise ValueError(f"LinkUp API error: {response.status_code} - {response.text}")
        
        results = response.json().get("results", [])
        
        # Format results to match Tavily format
        formatted_results = []
        for result in results:
            formatted_results.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("description", ""),
                "company": result.get("company", ""),
                "location": result.get("location", ""),
                "score": result.get("relevance_score", 0)
            })
        
        logger.debug(f"LinkUp search returned {len(formatted_results)} results")
        
        return formatted_results
    except ImportError:
        logger.error("Requests package not installed. Please install with 'pip install requests'")
        raise
    except Exception as e:
        logger.error(f"Error executing LinkUp search: {str(e)}")
        raise

@with_retry()
def _execute_duckduckgo_search(query: str, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute a DuckDuckGo search.
    
    Args:
        query (str): The search query
        search_params (Dict[str, Any]): The search parameters
        
    Returns:
        List[Dict[str, Any]]: The search results
    """
    try:
        from duckduckgo_search import DDGS
        
        max_results = search_params.get("max_results", 10)
        
        logger.debug(f"Executing DuckDuckGo search with max_results={max_results}")
        
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=max_results))
        
        # Format results to match Tavily format
        formatted_results = []
        for result in results:
            formatted_results.append({
                "title": result.get("title", ""),
                "url": result.get("href", ""),
                "content": result.get("body", ""),
                "score": 1.0  # DuckDuckGo doesn't provide relevance scores
            })
        
        logger.debug(f"DuckDuckGo search returned {len(formatted_results)} results")
        
        return formatted_results
    except ImportError:
        logger.error("DuckDuckGo Search package not installed. Please install with 'pip install duckduckgo-search'")
        raise
    except Exception as e:
        logger.error(f"Error executing DuckDuckGo search: {str(e)}")
        raise

@with_retry()
def _execute_googlesearch_search(query: str, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute a Google search.
    
    Args:
        query (str): The search query
        search_params (Dict[str, Any]): The search parameters
        
    Returns:
        List[Dict[str, Any]]: The search results
    """
    try:
        from googlesearch import search
        import requests
        from bs4 import BeautifulSoup
        
        max_results = search_params.get("max_results", 10)
        
        logger.debug(f"Executing Google search with max_results={max_results}")
        
        # Get URLs from Google search
        urls = list(search(query, num_results=max_results))
        
        # Format results to match Tavily format
        formatted_results = []
        for url in urls:
            try:
                # Fetch page content
                response = requests.get(url, timeout=5)
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Extract title and content
                title = soup.title.string if soup.title else url
                
                # Extract main content (simplified)
                paragraphs = soup.find_all("p")
                content = " ".join([p.get_text() for p in paragraphs[:5]])
                
                formatted_results.append({
                    "title": title,
                    "url": url,
                    "content": content[:1000],  # Limit content length
                    "score": 1.0  # Google search doesn't provide relevance scores
                })
            except Exception as e:
                logger.warning(f"Error fetching content for URL {url}: {str(e)}")
                # Add URL without content
                formatted_results.append({
                    "title": url,
                    "url": url,
                    "content": "",
                    "score": 1.0
                })
        
        logger.debug(f"Google search returned {len(formatted_results)} results")
        
        return formatted_results
    except ImportError:
        logger.error("Required packages not installed. Please install with 'pip install googlesearch-python requests beautifulsoup4'")
        raise
    except Exception as e:
        logger.error(f"Error executing Google search: {str(e)}")
        raise
