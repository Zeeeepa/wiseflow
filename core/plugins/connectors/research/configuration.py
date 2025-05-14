"""Configuration for research module."""

import os
from enum import Enum
from dataclasses import dataclass, fields, field
from typing import Any, Optional, Dict 

from langchain_core.runnables import RunnableConfig

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

@dataclass(kw_only=True)
class Configuration:
    """The configurable fields for the research module."""
    # Common configuration
    report_structure: str = DEFAULT_REPORT_STRUCTURE # Defaults to the default report structure
    search_api: SearchAPI = SearchAPI.TAVILY # Default to TAVILY
    search_api_config: Optional[Dict[str, Any]] = field(default_factory=dict) # API-specific configuration
    research_mode: ResearchMode = ResearchMode.LINEAR # Default to LINEAR mode
    
    # Graph-specific configuration
    number_of_queries: int = 2 # Number of search queries to generate per iteration
    max_search_depth: int = 2 # Maximum number of reflection + search iterations
    planner_provider: str = "anthropic"  # Defaults to Anthropic as provider
    planner_model: str = "claude-3-7-sonnet-latest" # Defaults to claude-3-7-sonnet-latest
    planner_model_kwargs: Optional[Dict[str, Any]] = field(default_factory=dict) # kwargs for planner_model
    writer_provider: str = "anthropic" # Defaults to Anthropic as provider
    writer_model: str = "claude-3-5-sonnet-latest" # Defaults to claude-3-5-sonnet-latest
    writer_model_kwargs: Optional[Dict[str, Any]] = field(default_factory=dict) # kwargs for writer_model
    visualization_enabled: bool = True # Enable visualization for graph-based research
    visualization_path: str = "research_graph.html" # Path to save visualization
    
    # Multi-agent specific configuration
    supervisor_model: str = "openai:gpt-4.1" # Model for supervisor agent in multi-agent setup
    researcher_model: str = "openai:gpt-4.1" # Model for research agents in multi-agent setup 

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls)
            if f.init
        }
        return cls(**{k: v for k, v in values.items() if v})
    
    def copy(self) -> "Configuration":
        """Create a copy of the configuration.
        
        Returns:
            Configuration: A new Configuration instance with the same values
        """
        return Configuration(
            report_structure=self.report_structure,
            search_api=self.search_api,
            search_api_config=self.search_api_config.copy() if self.search_api_config else {},
            research_mode=self.research_mode,
            number_of_queries=self.number_of_queries,
            max_search_depth=self.max_search_depth,
            planner_provider=self.planner_provider,
            planner_model=self.planner_model,
            planner_model_kwargs=self.planner_model_kwargs.copy() if self.planner_model_kwargs else {},
            writer_provider=self.writer_provider,
            writer_model=self.writer_model,
            writer_model_kwargs=self.writer_model_kwargs.copy() if self.writer_model_kwargs else {},
            visualization_enabled=self.visualization_enabled,
            visualization_path=self.visualization_path,
            supervisor_model=self.supervisor_model,
            researcher_model=self.researcher_model
        )
