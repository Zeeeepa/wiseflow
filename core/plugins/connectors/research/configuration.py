"""Configuration for research module."""

import os
import logging
from enum import Enum
from dataclasses import dataclass, fields, field
from typing import Any, Optional, Dict, List, Union

from langchain_core.runnables import RunnableConfig

# Setup logger
logger = logging.getLogger(__name__)

DEFAULT_REPORT_STRUCTURE = """Use this structure to create a report on the user-provided topic:

1. Introduction (no research needed)
   - Brief overview of the topic area

2. Main Body Sections:
   - Each section should focus on a sub-topic of the user-provided topic
   
3. Conclusion
   - Aim for 1 structural element (either a list of table) that distills the main body sections 
   - Provide a concise summary of the report"""

class SearchAPI(Enum):
    """Search API options for research."""
    PERPLEXITY = "perplexity"
    TAVILY = "tavily"
    EXA = "exa"
    ARXIV = "arxiv"
    PUBMED = "pubmed"
    LINKUP = "linkup"
    DUCKDUCKGO = "duckduckgo"
    GOOGLESEARCH = "googlesearch"

class ResearchMode(Enum):
    """Research mode options."""
    LINEAR = "linear"
    GRAPH = "graph"
    MULTI_AGENT = "multi_agent"

# Default fallback order for search APIs when primary API fails
DEFAULT_FALLBACK_APIS = [SearchAPI.TAVILY, SearchAPI.PERPLEXITY, SearchAPI.EXA, SearchAPI.DUCKDUCKGO]

@dataclass(kw_only=True)
class Configuration:
    """The configurable fields for the research module."""
    # Common configuration
    report_structure: str = DEFAULT_REPORT_STRUCTURE # Defaults to the default report structure
    search_api: SearchAPI = SearchAPI.TAVILY # Default to TAVILY
    search_api_config: Optional[Dict[str, Any]] = None
    research_mode: ResearchMode = ResearchMode.LINEAR # Default to LINEAR mode
    
    # Error handling and recovery configuration
    enable_fallback_apis: bool = True  # Whether to try fallback APIs when primary API fails
    fallback_apis: List[SearchAPI] = field(default_factory=lambda: [api for api in DEFAULT_FALLBACK_APIS])
    max_retries: int = 3  # Maximum number of retries for failed API calls
    retry_delay: float = 1.0  # Delay between retries in seconds
    
    # Logging configuration
    log_level: str = "INFO"  # Default log level
    enable_debug_logging: bool = False  # Enable detailed debug logging
    
    # Caching configuration
    enable_search_cache: bool = True  # Whether to cache search results
    cache_ttl: int = 3600  # Cache time-to-live in seconds (1 hour)
    
    # Graph-specific configuration
    number_of_queries: int = 2 # Number of search queries to generate per iteration
    max_search_depth: int = 2 # Maximum number of reflection + search iterations
    planner_provider: str = "anthropic"  # Defaults to Anthropic as provider
    planner_model: str = "claude-3-7-sonnet-latest" # Defaults to claude-3-7-sonnet-latest
    planner_model_kwargs: Optional[Dict[str, Any]] = None # kwargs for planner_model
    writer_provider: str = "anthropic" # Defaults to Anthropic as provider
    writer_model: str = "claude-3-5-sonnet-latest" # Defaults to claude-3-5-sonnet-latest
    writer_model_kwargs: Optional[Dict[str, Any]] = None # kwargs for writer_model
    visualization_enabled: bool = True # Enable visualization for graph-based research
    visualization_path: str = "research_graph.html" # Path to save visualization
    
    # Multi-agent specific configuration
    supervisor_model: str = "openai:gpt-4.1" # Model for supervisor agent in multi-agent setup
    researcher_model: str = "openai:gpt-4.1" # Model for research agents in multi-agent setup
    max_concurrent_researchers: int = 3  # Maximum number of concurrent researcher agents
    enable_parallel_execution: bool = True  # Whether to run researcher agents in parallel

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        values: dict[str, Any] = {}
        
        # Process each field
        for f in fields(cls):
            if not f.init:
                continue
                
            # Check environment variables first (with appropriate type conversion)
            env_key = f.name.upper()
            env_value = os.environ.get(env_key)
            
            # Check configurable dict next
            config_value = configurable.get(f.name)
            
            # Determine the final value
            if env_value is not None:
                # Convert environment variable to appropriate type
                if f.type == bool or f.type == Optional[bool]:
                    values[f.name] = env_value.lower() in ('true', 'yes', '1', 'y')
                elif f.type == int or f.type == Optional[int]:
                    values[f.name] = int(env_value)
                elif f.type == float or f.type == Optional[float]:
                    values[f.name] = float(env_value)
                elif f.type == List[SearchAPI] or f.type == Optional[List[SearchAPI]]:
                    api_names = env_value.split(',')
                    values[f.name] = [SearchAPI(name.strip()) for name in api_names if name.strip()]
                elif f.type == SearchAPI or f.type == Optional[SearchAPI]:
                    values[f.name] = SearchAPI(env_value)
                elif f.type == ResearchMode or f.type == Optional[ResearchMode]:
                    values[f.name] = ResearchMode(env_value)
                else:
                    values[f.name] = env_value
            elif config_value is not None:
                values[f.name] = config_value
        
        # Create instance with non-None values
        instance = cls(**{k: v for k, v in values.items() if v is not None})
        
        # Configure logging based on settings
        if instance.enable_debug_logging:
            logging.getLogger("core.plugins.connectors.research").setLevel(logging.DEBUG)
        else:
            logging.getLogger("core.plugins.connectors.research").setLevel(
                getattr(logging, instance.log_level)
            )
        
        return instance
