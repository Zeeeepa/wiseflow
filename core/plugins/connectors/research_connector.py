"""Research connector for wiseflow.

This connector provides deep research capabilities using various search APIs and research modes.
It's based on the open_deep_research library but implemented directly in wiseflow.
"""

import os
import logging
import json
import time
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from datetime import datetime

from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI
from core.plugins.connectors.research.utils import format_sections
from core.plugins.connectors.research.state import ReportState, Sections

# Setup logger
logger = logging.getLogger(__name__)

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
        
        # Configure logging based on settings
        if self.config.enable_debug_logging:
            logging.getLogger("core.plugins.connectors.research").setLevel(logging.DEBUG)
        else:
            logging.getLogger("core.plugins.connectors.research").setLevel(
                getattr(logging, self.config.log_level)
            )
        
        logger.info(f"Initialized ResearchConnector with mode={self.config.research_mode.value}, "
                   f"search_api={self.config.search_api.value}")
    
    def research(self, topic: str, **kwargs) -> Dict[str, Any]:
        """Perform research on a topic.
        
        Args:
            topic (str): The topic to research
            **kwargs: Additional arguments to override configuration
            
        Returns:
            Dict[str, Any]: The research results including report sections and metadata
        """
        start_time = time.time()
        logger.info(f"Starting research on topic: {topic}")
        
        # Update config with any kwargs
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.debug(f"Updated config: {key}={value}")
        
        try:
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
                config=self.config,
                metadata={"source": "direct_research"}
            )
            
            # Run the research graph
            logger.info(f"Running research graph with mode={self.config.research_mode.value}")
            result = graph.invoke(state)
            
            # Format the results
            formatted_sections = format_sections(result.sections)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            logger.info(f"Research completed in {execution_time:.2f} seconds")
            
            # Save state to file if configured
            if hasattr(self.config, "save_state") and self.config.save_state:
                state_path = os.path.join(
                    self.config.state_dir if hasattr(self.config, "state_dir") else ".",
                    f"research_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                result.save_to_file(state_path)
            
            return {
                "topic": topic,
                "sections": formatted_sections,
                "raw_sections": result.sections,
                "metadata": {
                    "search_api": self.config.search_api.value,
                    "research_mode": self.config.research_mode.value,
                    "search_depth": self.config.max_search_depth,
                    "queries_per_iteration": self.config.number_of_queries,
                    "execution_time": execution_time,
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error during research: {str(e)}", exc_info=True)
            # Return partial results if available
            if 'result' in locals() and hasattr(result, 'sections'):
                formatted_sections = format_sections(result.sections)
                return {
                    "topic": topic,
                    "sections": formatted_sections,
                    "raw_sections": result.sections,
                    "metadata": {
                        "search_api": self.config.search_api.value,
                        "research_mode": self.config.research_mode.value,
                        "error": str(e),
                        "status": "partial_results",
                        "timestamp": datetime.now().isoformat()
                    }
                }
            else:
                # Return error information
                return {
                    "topic": topic,
                    "sections": [],
                    "raw_sections": Sections(sections=[]),
                    "metadata": {
                        "search_api": self.config.search_api.value,
                        "research_mode": self.config.research_mode.value,
                        "error": str(e),
                        "status": "failed",
                        "timestamp": datetime.now().isoformat()
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
        start_time = time.time()
        logger.info(f"Starting continuous research on topic: {new_topic}")
        logger.info(f"Based on previous topic: {previous_results.get('topic', 'Unknown')}")
        
        # Update config with any kwargs
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.debug(f"Updated config: {key}={value}")
        
        try:
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
                previous_topic=previous_results.get("topic", ""),
                metadata={"source": "continuous_research"}
            )
            
            # Run the research graph
            logger.info(f"Running continuous research graph with mode={self.config.research_mode.value}")
            result = graph.invoke(state)
            
            # Format the results
            formatted_sections = format_sections(result.sections)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            logger.info(f"Continuous research completed in {execution_time:.2f} seconds")
            
            # Save state to file if configured
            if hasattr(self.config, "save_state") and self.config.save_state:
                state_path = os.path.join(
                    self.config.state_dir if hasattr(self.config, "state_dir") else ".",
                    f"continuous_research_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                result.save_to_file(state_path)
            
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
                    "continuous": True,
                    "execution_time": execution_time,
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error during continuous research: {str(e)}", exc_info=True)
            # Return partial results if available
            if 'result' in locals() and hasattr(result, 'sections'):
                formatted_sections = format_sections(result.sections)
                return {
                    "topic": new_topic,
                    "previous_topic": previous_results.get("topic", ""),
                    "sections": formatted_sections,
                    "raw_sections": result.sections,
                    "metadata": {
                        "search_api": self.config.search_api.value,
                        "research_mode": self.config.research_mode.value,
                        "continuous": True,
                        "error": str(e),
                        "status": "partial_results",
                        "timestamp": datetime.now().isoformat()
                    }
                }
            else:
                # Return error information
                return {
                    "topic": new_topic,
                    "previous_topic": previous_results.get("topic", ""),
                    "sections": [],
                    "raw_sections": Sections(sections=[]),
                    "metadata": {
                        "search_api": self.config.search_api.value,
                        "research_mode": self.config.research_mode.value,
                        "continuous": True,
                        "error": str(e),
                        "status": "failed",
                        "timestamp": datetime.now().isoformat()
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
                logger.debug(f"Updated config: {key}={value}")
    
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration.
        
        Returns:
            Dict[str, Any]: The current configuration
        """
        config_dict = {}
        for key, value in self.config.__dict__.items():
            if isinstance(value, Enum):
                config_dict[key] = value.value
            else:
                config_dict[key] = value
        return config_dict
