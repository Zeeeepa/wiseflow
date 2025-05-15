"""Research module for wiseflow.

This module provides deep research capabilities using various search APIs and research modes.
"""

import logging
from typing import Optional

from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI
from core.plugins.connectors.research.graph import graph as linear_graph
from core.plugins.connectors.research.multi_agent import graph as multi_agent_graph
from core.plugins.connectors.research.graph_workflow import graph as graph_based_research

# Setup logger
logger = logging.getLogger(__name__)

def get_research_graph(config: Optional[Configuration] = None):
    """Get the appropriate research graph based on configuration.
    
    Args:
        config (Configuration, optional): Configuration for the research. Defaults to None.
        
    Returns:
        graph: The compiled research graph
    """
    if not config:
        config = Configuration()
    
    logger.info(f"Getting research graph for mode: {config.research_mode.value}")
    
    if config.research_mode == ResearchMode.GRAPH:
        logger.debug("Using graph-based research workflow")
        return graph_based_research
    elif config.research_mode == ResearchMode.MULTI_AGENT:
        logger.debug("Using multi-agent research workflow")
        return multi_agent_graph
    else:  # Default to LINEAR mode
        logger.debug("Using linear research workflow")
        return linear_graph
