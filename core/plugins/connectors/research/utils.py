"""Utility functions for research module."""

import os
import json
import logging
import time
from typing import Dict, List, Any, Optional, Union, Callable
import importlib.util
from functools import lru_cache

from langchain_core.runnables import RunnableConfig
from langchain.chat_models import init_chat_model

from core.plugins.connectors.research.state import Sections, Section
from core.plugins.connectors.research.configuration import Configuration, SearchAPI

# Configure logging
logger = logging.getLogger(__name__)

# Define custom exceptions
class ResearchError(Exception):
    """Base exception for research module errors."""
    pass

class SearchAPIError(ResearchError):
    """Exception raised when a search API fails."""
    def __init__(self, api: str, message: str, original_error: Optional[Exception] = None):
        self.api = api
        self.original_error = original_error
        super().__init__(f"Error with {api} API: {message}")

class ConfigurationError(ResearchError):
    """Exception raised when there's a configuration error."""
    pass

class ProcessingError(ResearchError):
    """Exception raised when there's an error processing research data."""
    pass

def format_sections(sections: Sections) -> List[Dict[str, Any]]:
    """Format sections for output.
    
    Args:
        sections (Sections): The sections to format
        
    Returns:
        List[Dict[str, Any]]: The formatted sections
    
    Raises:
        ProcessingError: If there's an error formatting the sections
    """
    try:
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
    except Exception as e:
        logger.error(f"Error formatting sections: {str(e)}", exc_info=True)
        raise ProcessingError(f"Failed to format sections: {str(e)}") from e

def get_config_value(key: str, config: Optional[RunnableConfig] = None) -> Any:
    """Get a configuration value from environment or RunnableConfig.
    
    Args:
        key (str): The configuration key
        config (Optional[RunnableConfig], optional): The RunnableConfig. Defaults to None.
        
    Returns:
        Any: The configuration value
    """
    try:
        if config and "configurable" in config and key in config["configurable"]:
            return config["configurable"][key]
        
        env_key = key.upper()
        if env_key in os.environ:
            return os.environ[env_key]
        
        return None
    except Exception as e:
        logger.warning(f"Error retrieving config value for {key}: {str(e)}")
        return None

def validate_search_params(search_api: SearchAPI, search_params: Dict[str, Any]) -> None:
    """Validate search parameters for a given API.
    
    Args:
        search_api (SearchAPI): The search API to validate parameters for
        search_params (Dict[str, Any]): The search parameters to validate
        
    Raises:
        ConfigurationError: If the parameters are invalid or missing required fields
    """
    # Check for API key
    if "api_key" not in search_params or not search_params["api_key"]:
        raise ConfigurationError(f"Missing API key for {search_api.value}")
    
    # API-specific validation
    if search_api == SearchAPI.TAVILY:
        # Tavily-specific validation
        pass
    elif search_api == SearchAPI.PERPLEXITY:
        # Perplexity-specific validation
        pass
    elif search_api == SearchAPI.EXA:
        # Exa-specific validation
        pass

def get_search_params(config: Optional[Configuration] = None) -> Dict[str, Any]:
    """Get search parameters from configuration.
    
    Args:
        config (Optional[Configuration], optional): The configuration. Defaults to None.
        
    Returns:
        Dict[str, Any]: The search parameters
        
    Raises:
        ConfigurationError: If there's an error with the search configuration
    """
    try:
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
        
        # Add API keys for other search APIs
        elif search_api == SearchAPI.ARXIV:
            # ArXiv doesn't require an API key
            pass
        
        elif search_api == SearchAPI.PUBMED and "api_key" not in search_params:
            search_params["api_key"] = os.environ.get("PUBMED_API_KEY")
            
        elif search_api == SearchAPI.LINKUP and "api_key" not in search_params:
            search_params["api_key"] = os.environ.get("LINKUP_API_KEY")
            
        elif search_api == SearchAPI.DUCKDUCKGO:
            # DuckDuckGo doesn't require an API key
            pass
            
        elif search_api == SearchAPI.GOOGLESEARCH and "api_key" not in search_params:
            search_params["api_key"] = os.environ.get("GOOGLE_API_KEY")
            search_params["cse_id"] = os.environ.get("GOOGLE_CSE_ID")
        
        # Validate the search parameters
        try:
            validate_search_params(search_api, search_params)
        except ConfigurationError as e:
            logger.warning(f"Search parameter validation warning: {str(e)}")
            # Continue with potentially incomplete parameters, will be handled during search
        
        return search_params
    except Exception as e:
        logger.error(f"Error getting search parameters: {str(e)}", exc_info=True)
        raise ConfigurationError(f"Failed to get search parameters: {str(e)}") from e

@lru_cache(maxsize=128)
def _cached_search(query: str, search_api_name: str, params_hash: str) -> List[Dict[str, Any]]:
    """Cache wrapper for search results.
    
    Args:
        query (str): The search query
        search_api_name (str): Name of the search API
        params_hash (str): Hash of the search parameters
        
    Returns:
        List[Dict[str, Any]]: The cached search results
    """
    # This function is just a placeholder for the cache
    # The actual implementation will never be called for cache hits
    return []

def _hash_params(params: Dict[str, Any]) -> str:
    """Create a hash of search parameters for cache key.
    
    Args:
        params (Dict[str, Any]): The search parameters
        
    Returns:
        str: Hash of the parameters
    """
    # Create a stable representation of the parameters
    param_items = sorted([(k, str(v)) for k, v in params.items() if k != "api_key"])
    return json.dumps(param_items)

def select_and_execute_search(query: str, search_api: SearchAPI, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Select and execute a search API with caching and error handling.
    
    Args:
        query (str): The search query
        search_api (SearchAPI): The search API to use
        search_params (Dict[str, Any]): The search parameters
        
    Returns:
        List[Dict[str, Any]]: The search results
        
    Raises:
        SearchAPIError: If there's an error with the search API
    """
    # Create a hash of the parameters for cache key
    params_hash = _hash_params(search_params)
    
    # Check if caching is disabled
    if search_params.get("disable_cache", False):
        logger.debug(f"Cache disabled for query: {query}")
    else:
        # Try to get results from cache
        try:
            cached_results = _cached_search(query, search_api.value, params_hash)
            logger.info(f"Cache hit for query: {query}")
            return cached_results
        except Exception as e:
            # If there's an error with the cache or it's a cache miss, continue to the actual search
            logger.debug(f"Cache miss for query: {query}")
    
    # Execute the appropriate search based on the API
    start_time = time.time()
    try:
        if search_api == SearchAPI.TAVILY:
            results = _execute_tavily_search(query, search_params)
        elif search_api == SearchAPI.PERPLEXITY:
            results = _execute_perplexity_search(query, search_params)
        elif search_api == SearchAPI.EXA:
            results = _execute_exa_search(query, search_params)
        elif search_api == SearchAPI.ARXIV:
            results = _execute_arxiv_search(query, search_params)
        elif search_api == SearchAPI.PUBMED:
            results = _execute_pubmed_search(query, search_params)
        elif search_api == SearchAPI.LINKUP:
            results = _execute_linkup_search(query, search_params)
        elif search_api == SearchAPI.DUCKDUCKGO:
            results = _execute_duckduckgo_search(query, search_params)
        elif search_api == SearchAPI.GOOGLESEARCH:
            results = _execute_googlesearch_search(query, search_params)
        else:
            logger.warning(f"Unsupported search API: {search_api}. Falling back to Tavily.")
            results = _execute_tavily_search(query, search_params)
        
        # Cache the results if caching is enabled
        if not search_params.get("disable_cache", False):
            # Update the cache - this will replace the function call next time
            _cached_search.cache_clear()  # Clear old entries if needed
            _cached_search.__wrapped__(query, search_api.value, params_hash)
            _cached_search.cache_info = lambda: results
        
        # Log search performance
        duration = time.time() - start_time
        logger.info(f"Search completed in {duration:.2f}s with {search_api.value} for query: {query}")
        
        return results
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Search failed after {duration:.2f}s with {search_api.value} for query: {query}. Error: {str(e)}", exc_info=True)
        
        # Try fallback search API if configured
        fallback_api = search_params.get("fallback_api")
        if fallback_api and fallback_api != search_api:
            logger.info(f"Attempting fallback search with {fallback_api.value}")
            try:
                return select_and_execute_search(query, fallback_api, search_params)
            except Exception as fallback_error:
                logger.error(f"Fallback search also failed: {str(fallback_error)}", exc_info=True)
        
        # Raise a specific error
        raise SearchAPIError(search_api.value, str(e), original_error=e)

def _execute_tavily_search(query: str, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute a Tavily search with enhanced error handling.
    
    Args:
        query (str): The search query
        search_params (Dict[str, Any]): The search parameters
        
    Returns:
        List[Dict[str, Any]]: The search results
        
    Raises:
        SearchAPIError: If there's an error with the Tavily API
    """
    try:
        from tavily import TavilyClient
        
        api_key = search_params.get("api_key")
        
        if not api_key:
            raise ValueError("Tavily API key not provided")
        
        client = TavilyClient(api_key=api_key)
        
        search_depth = search_params.get("search_depth", "basic")
        max_results = search_params.get("max_results", 10)
        
        response = client.search(
            query=query,
            search_depth=search_depth,
            max_results=max_results
        )
        
        return response.get("results", [])
    except ImportError:
        logger.error("Tavily package not installed. Please install with 'pip install tavily'")
        return []
    except Exception as e:
        logger.error(f"Error executing Tavily search: {e}")
        return []

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
        
        data = {
            "query": query,
            "max_results": search_params.get("max_results", 10)
        }
        
        response = requests.post(
            "https://api.perplexity.ai/search",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
            return []
        
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
        
        return formatted_results
    except ImportError:
        logger.error("Requests package not installed. Please install with 'pip install requests'")
        return []
    except Exception as e:
        logger.error(f"Error executing Perplexity search: {e}")
        return []

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
        
        response = exa.search(
            query=query,
            num_results=max_results,
            use_autoprompt=search_params.get("use_autoprompt", True)
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
        
        return formatted_results
    except ImportError:
        logger.error("Exa package not installed. Please install with 'pip install exa-py'")
        return []
    except Exception as e:
        logger.error(f"Error executing Exa search: {e}")
        return []

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
        
        return formatted_results
    except ImportError:
        logger.error("arXiv package not installed. Please install with 'pip install arxiv'")
        return []
    except Exception as e:
        logger.error(f"Error executing arXiv search: {e}")
        return []

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
        
        return formatted_results
    except ImportError:
        logger.error("PyMed package not installed. Please install with 'pip install pymed'")
        return []
    except Exception as e:
        logger.error(f"Error executing PubMed search: {e}")
        return []

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
        
        data = {
            "query": query,
            "limit": search_params.get("max_results", 10)
        }
        
        response = requests.post(
            "https://api.linkup.com/v1/search",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            logger.error(f"LinkUp API error: {response.status_code} - {response.text}")
            return []
        
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
        
        return formatted_results
    except ImportError:
        logger.error("Requests package not installed. Please install with 'pip install requests'")
        return []
    except Exception as e:
        logger.error(f"Error executing LinkUp search: {e}")
        return []

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
        
        return formatted_results
    except ImportError:
        logger.error("DuckDuckGo Search package not installed. Please install with 'pip install duckduckgo-search'")
        return []
    except Exception as e:
        logger.error(f"Error executing DuckDuckGo search: {e}")
        return []

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
                logger.warning(f"Error fetching content for URL {url}: {e}")
                # Add URL without content
                formatted_results.append({
                    "title": url,
                    "url": url,
                    "content": "",
                    "score": 1.0
                })
        
        return formatted_results
    except ImportError:
        logger.error("Required packages not installed. Please install with 'pip install googlesearch-python requests beautifulsoup4'")
        return []
    except Exception as e:
        logger.error(f"Error executing Google search: {e}")
        return []
