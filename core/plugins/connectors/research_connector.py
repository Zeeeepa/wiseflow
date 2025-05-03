"""
Research connector plugin for performing deep research on topics using open_deep_research.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union
import asyncio
import json

from core.plugins.base import ConnectorPlugin

# Import open_deep_research components
try:
    from open_deep_research import get_research_graph
    from open_deep_research.configuration import Configuration, ResearchMode, SearchAPI
    from open_deep_research.state import ReportState
except ImportError:
    logging.error("open_deep_research package not found. Please install it with: pip install open-deep-research")

logger = logging.getLogger(__name__)


class ResearchConnector(ConnectorPlugin):
    """Connector for performing deep research on topics using open_deep_research."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Research connector.
        
        Args:
            config: Configuration dictionary with the following keys:
                - research_mode: Research mode (linear, graph, multi_agent)
                - search_api: Search API to use (tavily, perplexity, exa, etc.)
                - api_keys: Dict of API keys for search services
                - max_search_depth: Maximum search depth for graph-based research
                - number_of_queries: Number of search queries to generate per iteration
                - planner_model: Model to use for planning (default: claude-3-7-sonnet-latest)
                - writer_model: Model to use for writing (default: claude-3-5-sonnet-latest)
                - continuous_topic: Whether to maintain a continuous research topic
        """
        super().__init__(config)
        self.research_mode = self.config.get('research_mode', 'linear')
        self.search_api = self.config.get('search_api', 'tavily')
        self.api_keys = self.config.get('api_keys', {})
        self.max_search_depth = self.config.get('max_search_depth', 2)
        self.number_of_queries = self.config.get('number_of_queries', 2)
        self.planner_model = self.config.get('planner_model', 'claude-3-7-sonnet-latest')
        self.writer_model = self.config.get('writer_model', 'claude-3-5-sonnet-latest')
        self.continuous_topic = self.config.get('continuous_topic', False)
        self.current_topic = None
        self.research_config = None
        
    def initialize(self) -> bool:
        """Initialize the Research connector.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        if not self.validate_config():
            logger.error("Invalid Research connector configuration")
            return False
        
        # Set API keys in environment variables
        for api, key in self.api_keys.items():
            if key:
                os.environ[f"{api.upper()}_API_KEY"] = key
        
        # Create research configuration
        try:
            research_mode = ResearchMode(self.research_mode)
            search_api = SearchAPI(self.search_api)
            
            self.research_config = Configuration(
                research_mode=research_mode,
                search_api=search_api,
                max_search_depth=self.max_search_depth,
                number_of_queries=self.number_of_queries,
                planner_model=self.planner_model,
                writer_model=self.writer_model
            )
            
            return True
        except (ImportError, ValueError) as e:
            logger.error(f"Error initializing Research connector: {str(e)}")
            return False
    
    def validate_config(self) -> bool:
        """Validate the Research connector configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        # Check if open_deep_research is installed
        try:
            import open_deep_research
            return True
        except ImportError:
            logger.error("open_deep_research package not found. Please install it with: pip install open-deep-research")
            return False
    
    def connect(self) -> bool:
        """Connect to the research service.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        return self.initialize()
    
    def fetch_data(self, query: str, **kwargs) -> Dict[str, Any]:
        """Perform research on the given topic.
        
        Args:
            query: Topic to research
            **kwargs: Additional parameters for the research
                - mode: Research mode (linear, graph, multi_agent)
                - search_api: Search API to use (tavily, perplexity, exa, etc.)
                - max_depth: Maximum search depth for graph-based research
                - num_queries: Number of search queries to generate per iteration
                - continuous: Whether to continue from previous research
        
        Returns:
            Dict[str, Any]: Dictionary containing the research results
        """
        # Update configuration with kwargs if provided
        mode = kwargs.get('mode', self.research_mode)
        search_api = kwargs.get('search_api', self.search_api)
        max_depth = kwargs.get('max_depth', self.max_search_depth)
        num_queries = kwargs.get('num_queries', self.number_of_queries)
        continuous = kwargs.get('continuous', self.continuous_topic)
        
        # If continuous mode is enabled and we have a current topic,
        # append the new query to the current topic
        if continuous and self.current_topic:
            topic = f"{self.current_topic}\nAdditional research: {query}"
        else:
            topic = query
            self.current_topic = topic
        
        # Update research configuration
        try:
            research_mode = ResearchMode(mode)
            search_api_enum = SearchAPI(search_api)
            
            self.research_config = Configuration(
                research_mode=research_mode,
                search_api=search_api_enum,
                max_search_depth=max_depth,
                number_of_queries=num_queries,
                planner_model=self.planner_model,
                writer_model=self.writer_model
            )
        except ValueError as e:
            logger.error(f"Error updating research configuration: {str(e)}")
            return {"error": str(e)}
        
        # Get the appropriate research graph
        try:
            graph = get_research_graph(self.research_config)
            
            # Create initial state
            state = {"topic": topic}
            
            # Run the research graph
            result = asyncio.run(graph.ainvoke(state))
            
            # Process and return the results
            return self._process_research_results(result)
        except Exception as e:
            logger.error(f"Error performing research: {str(e)}")
            return {"error": str(e)}
    
    def _process_research_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Process the research results.
        
        Args:
            result: Raw research results
            
        Returns:
            Dict[str, Any]: Processed research results
        """
        processed_result = {
            "topic": result.get("topic", ""),
            "report": result.get("report", ""),
            "sections": []
        }
        
        # Process sections if available
        sections = result.get("sections", {})
        if sections and isinstance(sections, dict):
            for section_id, section_data in sections.items():
                if isinstance(section_data, dict):
                    processed_result["sections"].append({
                        "id": section_id,
                        "title": section_data.get("title", ""),
                        "content": section_data.get("content", ""),
                        "sources": section_data.get("sources", [])
                    })
        
        # Add metadata
        processed_result["metadata"] = {
            "research_mode": self.research_config.research_mode.value,
            "search_api": self.research_config.search_api.value,
            "max_search_depth": self.research_config.max_search_depth,
            "number_of_queries": self.research_config.number_of_queries
        }
        
        return processed_result
    
    def disconnect(self) -> bool:
        """Disconnect from the research service.
        
        Returns:
            bool: True if disconnection was successful, False otherwise
        """
        # Nothing to disconnect from
        return True

