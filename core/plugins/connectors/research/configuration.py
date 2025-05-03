"""
Configuration classes for the research connector.
"""

import os
from enum import Enum
from dataclasses import dataclass, fields
from typing import Any, Optional, Dict

DEFAULT_REPORT_STRUCTURE = """Use this structure to create a report on the user-provided topic:

1. Introduction (no research needed)
   - Brief overview of the topic area

2. Main Body Sections:
   - Each section should focus on a sub-topic of the user-provided topic
   
3. Conclusion
   - Aim for 1 structural element (either a list of table) that distills the main body sections 
   - Provide a concise summary of the report"""

class SearchAPI(Enum):
    PERPLEXITY = "perplexity"
    TAVILY = "tavily"
    EXA = "exa"
    ARXIV = "arxiv"
    PUBMED = "pubmed"
    LINKUP = "linkup"
    DUCKDUCKGO = "duckduckgo"
    GOOGLESEARCH = "googlesearch"

class ResearchMode(Enum):
    LINEAR = "linear"
    GRAPH = "graph"
    MULTI_AGENT = "multi_agent"

@dataclass(kw_only=True)
class Configuration:
    """The configurable fields for the research connector."""
    # Common configuration
    report_structure: str = DEFAULT_REPORT_STRUCTURE # Defaults to the default report structure
    search_api: SearchAPI = SearchAPI.TAVILY # Default to TAVILY
    search_api_config: Optional[Dict[str, Any]] = None
    research_mode: ResearchMode = ResearchMode.LINEAR # Default to LINEAR mode
    
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

    @classmethod
    def from_dict(cls, config_dict: Optional[Dict[str, Any]] = None) -> "Configuration":
        """Create a Configuration instance from a dictionary."""
        if not config_dict:
            return cls()
        
        # Process enum values
        processed_dict = {}
        for key, value in config_dict.items():
            if key == 'search_api' and isinstance(value, str):
                processed_dict[key] = SearchAPI(value)
            elif key == 'research_mode' and isinstance(value, str):
                processed_dict[key] = ResearchMode(value)
            else:
                processed_dict[key] = value
        
        # Create instance with processed values
        return cls(**{k: v for k, v in processed_dict.items() if v is not None})

