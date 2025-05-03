"""Research connector for wiseflow.

This connector provides deep research capabilities using various search APIs and research modes.
It's based on the open_deep_research library but implemented directly in wiseflow.
"""

from typing import Dict, Any, Optional, List
from enum import Enum

from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI
from core.plugins.connectors.research.utils import format_sections
from core.plugins.connectors.research.state import ReportState, Sections

class ResearchConnector:
    """Research connector for wiseflow.
    
    This connector provides deep research capabilities using various search APIs and research modes.
    It supports:
    - Multiple research modes (linear, graph-based, multi-agent)
    - Configurable search APIs (Tavily, Perplexity, Exa, etc.)
    - Continuous topic research (building on previous queries)
    - Customizable parameters for search depth and query generation
    """
    
    def __init__(self, config: Optional[Configuration] = None):
        """Initialize the research connector.
        
        Args:
            config (Configuration, optional): Configuration for the research. Defaults to None.
        """
        self.config = config or Configuration()
        
    def research(self, topic: str, **kwargs) -> Dict[str, Any]:
        """Perform research on a topic.
        
        Args:
            topic (str): The topic to research
            **kwargs: Additional arguments to override configuration
            
        Returns:
            Dict[str, Any]: The research results including report sections and metadata
        """
        # Update config with any kwargs
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Get the appropriate research graph based on configuration
        from core.plugins.connectors.research import get_research_graph
        graph = get_research_graph(self.config)
        
        # Initialize the state
        state = ReportState(
            topic=topic,
            sections=Sections(sections=[]),
            queries=[],
            search_results=[],
            feedback=None,
            config=self.config
        )
        
        # Run the research graph
        result = graph.invoke(state)
        
        # Format the results
        formatted_sections = format_sections(result.sections)
        
        return {
            "topic": topic,
            "sections": formatted_sections,
            "raw_sections": result.sections,
            "metadata": {
                "search_api": self.config.search_api.value,
                "research_mode": self.config.research_mode.value,
                "search_depth": self.config.max_search_depth,
                "queries_per_iteration": self.config.number_of_queries
            }
        }
    
    def continuous_research(self, previous_results: Dict[str, Any], new_topic: str, **kwargs) -> Dict[str, Any]:
        """Continue research based on previous results.
        
        Args:
            previous_results (Dict[str, Any]): Results from a previous research call
            new_topic (str): The new topic or follow-up question
            **kwargs: Additional arguments to override configuration
            
        Returns:
            Dict[str, Any]: The research results including report sections and metadata
        """
        # Update config with any kwargs
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Get the appropriate research graph based on configuration
        from core.plugins.connectors.research import get_research_graph
        graph = get_research_graph(self.config)
        
        # Initialize the state with previous context
        state = ReportState(
            topic=new_topic,
            sections=previous_results.get("raw_sections", Sections(sections=[])),
            queries=[],
            search_results=[],
            feedback=None,
            config=self.config,
            previous_topic=previous_results.get("topic", "")
        )
        
        # Run the research graph
        result = graph.invoke(state)
        
        # Format the results
        formatted_sections = format_sections(result.sections)
        
        return {
            "topic": new_topic,
            "previous_topic": previous_results.get("topic", ""),
            "sections": formatted_sections,
            "raw_sections": result.sections,
            "metadata": {
                "search_api": self.config.search_api.value,
                "research_mode": self.config.research_mode.value,
                "search_depth": self.config.max_search_depth,
                "queries_per_iteration": self.config.number_of_queries,
                "continuous": True
            }
        }
    
    def set_config(self, **kwargs) -> None:
        """Update the configuration.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

