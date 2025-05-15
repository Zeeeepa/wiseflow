"""Research connector for wiseflow.

This connector provides deep research capabilities using various search APIs and research modes.
It's based on the open_deep_research library but implemented directly in wiseflow.
"""

from typing import Dict, Any, Optional, List
from enum import Enum
import logging
import traceback

from core.connectors import ConnectorBase, DataItem
from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI
from core.plugins.connectors.research.utils import format_sections
from core.plugins.connectors.research.state import ReportState, Sections

logger = logging.getLogger(__name__)

class ResearchConnector(ConnectorBase):
    """Research connector for wiseflow.
    
    This connector provides deep research capabilities using various search APIs and research modes.
    It supports:
    - Multiple research modes (linear, graph-based, multi-agent)
    - Configurable search APIs (Tavily, Perplexity, Exa, etc.)
    - Continuous topic research (building on previous queries)
    - Customizable parameters for search depth and query generation
    """
    
    name = "research_connector"
    description = "Deep research connector for wiseflow"
    source_type = "research"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the research connector.
        
        Args:
            config (Dict[str, Any], optional): Configuration for the research. Defaults to None.
        """
        super().__init__(config or {})
        self.research_config = Configuration()
        
        # Update research config from plugin config if provided
        if config:
            self._update_research_config_from_plugin_config()
    
    def _update_research_config_from_plugin_config(self):
        """Update research configuration from plugin configuration."""
        try:
            # Map plugin config to research config
            if 'search_api' in self.config:
                self.research_config.search_api = SearchAPI[self.config['search_api']]
            
            if 'research_mode' in self.config:
                self.research_config.research_mode = ResearchMode[self.config['research_mode']]
            
            # Copy other configuration parameters
            for key in ['max_search_depth', 'number_of_queries', 'max_iterations']:
                if key in self.config:
                    setattr(self.research_config, key, self.config[key])
        except Exception as e:
            logger.error(f"Error updating research config: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
    
    def initialize(self) -> bool:
        """Initialize the research connector.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Verify that required modules are available
            from core.plugins.connectors.research import get_research_graph
            
            # Test creating a graph to ensure the configuration is valid
            graph = get_research_graph(self.research_config)
            
            logger.info(f"Initialized research connector with mode: {self.research_config.research_mode.name}")
            return super().initialize()
        except Exception as e:
            logger.error(f"Failed to initialize research connector: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            self.error = str(e)
            return False
    
    def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect research data based on the provided parameters.
        
        Args:
            params (Dict[str, Any], optional): Parameters for the research. Must include 'topic'.
                Can also include other research configuration overrides.
        
        Returns:
            List[DataItem]: List of data items containing research results
        
        Raises:
            ValueError: If topic is not provided in params
        """
        params = params or {}
        
        if 'topic' not in params:
            raise ValueError("Topic must be provided in params")
        
        topic = params.pop('topic')
        
        # Check if this is a continuation of previous research
        if 'previous_results' in params:
            results = self.continuous_research(params.pop('previous_results'), topic, **params)
        else:
            results = self.research(topic, **params)
        
        # Convert results to DataItem
        data_items = []
        
        # Create a data item for the overall research
        main_item = DataItem(
            source_id=f"research_{topic.replace(' ', '_')}",
            content="\n\n".join([section['content'] for section in results['sections']]),
            metadata={
                'topic': topic,
                'sections': results['sections'],
                'metadata': results['metadata']
            },
            content_type="application/json"
        )
        data_items.append(main_item)
        
        # Create individual data items for each section
        for i, section in enumerate(results['sections']):
            section_item = DataItem(
                source_id=f"research_{topic.replace(' ', '_')}_section_{i}",
                content=section['content'],
                metadata={
                    'topic': topic,
                    'section_title': section['title'],
                    'section_index': i,
                    'metadata': results['metadata']
                },
                content_type="text/plain"
            )
            data_items.append(section_item)
        
        return data_items
    
    def research(self, topic: str, **kwargs) -> Dict[str, Any]:
        """Perform research on a topic.
        
        Args:
            topic (str): The topic to research
            **kwargs: Additional arguments to override configuration
            
        Returns:
            Dict[str, Any]: The research results including report sections and metadata
        """
        # Create a copy of the research config to avoid modifying the original
        config = Configuration()
        config.__dict__.update(self.research_config.__dict__)
        
        # Update config with any kwargs
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        # Get the appropriate research graph based on configuration
        from core.plugins.connectors.research import get_research_graph
        graph = get_research_graph(config)
        
        # Initialize the state
        state = ReportState(
            topic=topic,
            sections=Sections(sections=[]),
            queries=[],
            search_results=[],
            feedback=None,
            config=config
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
                "search_api": config.search_api.value,
                "research_mode": config.research_mode.value,
                "search_depth": config.max_search_depth,
                "queries_per_iteration": config.number_of_queries
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
        # Create a copy of the research config to avoid modifying the original
        config = Configuration()
        config.__dict__.update(self.research_config.__dict__)
        
        # Update config with any kwargs
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        # Get the appropriate research graph based on configuration
        from core.plugins.connectors.research import get_research_graph
        graph = get_research_graph(config)
        
        # Initialize the state with previous context
        state = ReportState(
            topic=new_topic,
            sections=previous_results.get("raw_sections", Sections(sections=[])),
            queries=[],
            search_results=[],
            feedback=None,
            config=config,
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
                "search_api": config.search_api.value,
                "research_mode": config.research_mode.value,
                "search_depth": config.max_search_depth,
                "queries_per_iteration": config.number_of_queries,
                "continuous": True
            }
        }
    
    def set_config(self, **kwargs) -> None:
        """Update the configuration.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.research_config, key):
                setattr(self.research_config, key, value)
    
    def shutdown(self) -> bool:
        """Shutdown the connector and release resources.
        
        Returns:
            bool: True if shutdown was successful, False otherwise
        """
        try:
            # Clean up any resources specific to this connector
            logger.info(f"Shutting down research connector")
            
            # Call parent shutdown to handle common cleanup
            return super().shutdown()
        except Exception as e:
            logger.error(f"Error shutting down research connector: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return False
