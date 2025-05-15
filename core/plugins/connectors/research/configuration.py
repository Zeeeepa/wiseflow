"""Configuration for research module."""

import os
import json
from enum import Enum
from dataclasses import dataclass, fields, field
from typing import Any, Optional, Dict, List, Union, Type, TypeVar, cast
import logging

from langchain_core.runnables import RunnableConfig

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
    
    @classmethod
    def from_string(cls, value: str) -> "SearchAPI":
        """Create a SearchAPI from a string value.
        
        Args:
            value (str): The string value
            
        Returns:
            SearchAPI: The corresponding SearchAPI enum
            
        Raises:
            ValueError: If the value is not a valid SearchAPI
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_values = [api.value for api in cls]
            raise ValueError(f"Invalid search API: {value}. Valid values are: {', '.join(valid_values)}")

class ResearchMode(Enum):
    """Research mode options."""
    LINEAR = "linear"
    GRAPH = "graph"
    MULTI_AGENT = "multi_agent"
    
    @classmethod
    def from_string(cls, value: str) -> "ResearchMode":
        """Create a ResearchMode from a string value.
        
        Args:
            value (str): The string value
            
        Returns:
            ResearchMode: The corresponding ResearchMode enum
            
        Raises:
            ValueError: If the value is not a valid ResearchMode
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_values = [mode.value for mode in cls]
            raise ValueError(f"Invalid research mode: {value}. Valid values are: {', '.join(valid_values)}")

class CacheStrategy(Enum):
    """Cache strategy options."""
    NONE = "none"  # No caching
    MEMORY = "memory"  # In-memory caching
    DISK = "disk"  # Disk-based caching
    DISTRIBUTED = "distributed"  # Distributed caching (e.g., Redis)

T = TypeVar('T')

@dataclass(kw_only=True)
class Configuration:
    """The configurable fields for the research module."""
    # Common configuration
    report_structure: str = DEFAULT_REPORT_STRUCTURE # Defaults to the default report structure
    search_api: SearchAPI = SearchAPI.TAVILY # Default to TAVILY
    search_api_config: Optional[Dict[str, Any]] = None
    fallback_search_api: Optional[SearchAPI] = None  # Fallback search API if primary fails
    research_mode: ResearchMode = ResearchMode.LINEAR # Default to LINEAR mode
    
    # Caching configuration
    cache_strategy: CacheStrategy = CacheStrategy.MEMORY  # Default to in-memory caching
    cache_ttl: int = 3600  # Cache time-to-live in seconds (1 hour)
    cache_max_size: int = 1000  # Maximum number of cached items
    
    # Error handling configuration
    max_retries: int = 3  # Maximum number of retries for failed operations
    retry_delay: float = 1.0  # Delay between retries in seconds
    
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
    num_researcher_agents: int = 3  # Number of researcher agents to use
    max_concurrent_agents: int = 2  # Maximum number of agents to run concurrently
    agent_timeout: int = 300  # Timeout for agent operations in seconds
    
    # Advanced configuration
    custom_plugins: List[str] = field(default_factory=list)  # Custom plugins to load
    debug_mode: bool = False  # Enable debug mode for additional logging
    telemetry_enabled: bool = True  # Enable telemetry for performance monitoring

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_configuration()
    
    def _validate_configuration(self):
        """Validate the configuration values."""
        # Validate search_api
        if not isinstance(self.search_api, SearchAPI):
            try:
                self.search_api = SearchAPI.from_string(str(self.search_api))
            except ValueError as e:
                logger.warning(f"Invalid search_api: {e}")
                self.search_api = SearchAPI.TAVILY  # Default to TAVILY
        
        # Validate fallback_search_api
        if self.fallback_search_api is not None and not isinstance(self.fallback_search_api, SearchAPI):
            try:
                self.fallback_search_api = SearchAPI.from_string(str(self.fallback_search_api))
            except ValueError:
                logger.warning(f"Invalid fallback_search_api: {self.fallback_search_api}")
                self.fallback_search_api = None
        
        # Validate research_mode
        if not isinstance(self.research_mode, ResearchMode):
            try:
                self.research_mode = ResearchMode.from_string(str(self.research_mode))
            except ValueError as e:
                logger.warning(f"Invalid research_mode: {e}")
                self.research_mode = ResearchMode.LINEAR  # Default to LINEAR
        
        # Validate numeric values
        self._validate_positive_int("number_of_queries", 1)
        self._validate_positive_int("max_search_depth", 1)
        self._validate_positive_int("cache_ttl", 60)
        self._validate_positive_int("cache_max_size", 100)
        self._validate_positive_int("max_retries", 1)
        self._validate_positive_float("retry_delay", 0.1)
        self._validate_positive_int("num_researcher_agents", 1)
        self._validate_positive_int("max_concurrent_agents", 1)
        self._validate_positive_int("agent_timeout", 30)
    
    def _validate_positive_int(self, field_name: str, min_value: int):
        """Validate that a field is a positive integer."""
        value = getattr(self, field_name)
        if not isinstance(value, int) or value < min_value:
            logger.warning(f"Invalid {field_name}: {value}. Must be an integer >= {min_value}. Using default.")
            setattr(self, field_name, min_value)
    
    def _validate_positive_float(self, field_name: str, min_value: float):
        """Validate that a field is a positive float."""
        value = getattr(self, field_name)
        if not isinstance(value, (int, float)) or value < min_value:
            logger.warning(f"Invalid {field_name}: {value}. Must be a number >= {min_value}. Using default.")
            setattr(self, field_name, min_value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the configuration
        """
        result = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if isinstance(value, Enum):
                result[f.name] = value.value
            else:
                result[f.name] = value
        return result
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "Configuration":
        """Create a Configuration instance from a dictionary.
        
        Args:
            config_dict (Dict[str, Any]): Dictionary with configuration values
            
        Returns:
            Configuration: New Configuration instance
        """
        # Convert string enum values to actual enums
        if "search_api" in config_dict and isinstance(config_dict["search_api"], str):
            config_dict["search_api"] = SearchAPI.from_string(config_dict["search_api"])
        
        if "fallback_search_api" in config_dict and isinstance(config_dict["fallback_search_api"], str):
            config_dict["fallback_search_api"] = SearchAPI.from_string(config_dict["fallback_search_api"])
        
        if "research_mode" in config_dict and isinstance(config_dict["research_mode"], str):
            config_dict["research_mode"] = ResearchMode.from_string(config_dict["research_mode"])
        
        if "cache_strategy" in config_dict and isinstance(config_dict["cache_strategy"], str):
            try:
                config_dict["cache_strategy"] = CacheStrategy(config_dict["cache_strategy"])
            except ValueError:
                config_dict["cache_strategy"] = CacheStrategy.MEMORY
        
        # Create instance with valid fields only
        valid_fields = {f.name for f in fields(cls)}
        valid_config = {k: v for k, v in config_dict.items() if k in valid_fields}
        
        return cls(**valid_config)

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig.
        
        Args:
            config (Optional[RunnableConfig]): The RunnableConfig
            
        Returns:
            Configuration: New Configuration instance
        """
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        
        # Get values from environment or config
        values: Dict[str, Any] = {}
        for f in fields(cls):
            if not f.init:
                continue
                
            # Try to get from environment first
            env_value = os.environ.get(f.name.upper())
            if env_value is not None:
                # Convert environment string values to appropriate types
                if f.type == bool:
                    values[f.name] = env_value.lower() in ("true", "1", "yes")
                elif f.type == int:
                    try:
                        values[f.name] = int(env_value)
                    except ValueError:
                        pass
                elif f.type == float:
                    try:
                        values[f.name] = float(env_value)
                    except ValueError:
                        pass
                else:
                    values[f.name] = env_value
            
            # Then try from config
            elif f.name in configurable:
                values[f.name] = configurable[f.name]
        
        # Create instance with non-None values
        return cls(**{k: v for k, v in values.items() if v is not None})
    
    def save_to_file(self, filepath: str) -> None:
        """Save configuration to a JSON file.
        
        Args:
            filepath (str): Path to save the configuration
        """
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> "Configuration":
        """Load configuration from a JSON file.
        
        Args:
            filepath (str): Path to the configuration file
            
        Returns:
            Configuration: New Configuration instance
        """
        with open(filepath, "r") as f:
            config_dict = json.load(f)
        
        return cls.from_dict(config_dict)
