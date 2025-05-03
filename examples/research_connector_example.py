"""
Example script demonstrating how to use the Research Connector.
"""

import os
import json
import logging
from typing import Dict, Any

from core.plugins.connectors.research_connector import ResearchConnector

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Run the research connector example."""
    # Set API keys (replace with your actual API keys)
    api_keys = {
        "tavily": os.environ.get("TAVILY_API_KEY", ""),
        "perplexity": os.environ.get("PERPLEXITY_API_KEY", ""),
        "exa": os.environ.get("EXA_API_KEY", "")
    }
    
    # Create research connector with configuration
    config = {
        "research_mode": "linear",  # Options: linear, graph, multi_agent
        "search_api": "tavily",     # Options: tavily, perplexity, exa, etc.
        "api_keys": api_keys,
        "max_search_depth": 2,
        "number_of_queries": 3,
        "planner_model": "claude-3-7-sonnet-latest",
        "writer_model": "claude-3-5-sonnet-latest",
        "continuous_topic": False
    }
    
    connector = ResearchConnector(config)
    
    # Initialize the connector
    if not connector.initialize():
        logger.error("Failed to initialize research connector")
        return
    
    # Example 1: Basic research
    topic = "The impact of artificial intelligence on healthcare"
    logger.info(f"Researching topic: {topic}")
    
    result = connector.fetch_data(topic)
    
    # Print the research results
    print_research_results(result)
    
    # Example 2: Continuous research (building on previous topic)
    if config["continuous_topic"]:
        additional_topic = "Focus on AI diagnostic tools and their accuracy compared to human doctors"
        logger.info(f"Continuing research with: {additional_topic}")
        
        result = connector.fetch_data(additional_topic, continuous=True)
        
        # Print the research results
        print_research_results(result)
    
    # Example 3: Different research mode
    advanced_topic = "Recent advancements in quantum computing and potential applications"
    logger.info(f"Researching advanced topic with graph mode: {advanced_topic}")
    
    result = connector.fetch_data(
        advanced_topic,
        mode="graph",
        max_depth=3,
        num_queries=4
    )
    
    # Print the research results
    print_research_results(result)

def print_research_results(result: Dict[str, Any]) -> None:
    """Print the research results in a formatted way.
    
    Args:
        result: Research results dictionary
    """
    if "error" in result:
        logger.error(f"Research error: {result['error']}")
        return
    
    print("\n" + "="*80)
    print(f"RESEARCH TOPIC: {result['topic']}")
    print("="*80)
    
    # Print metadata
    metadata = result.get("metadata", {})
    if metadata:
        print("\nMETADATA:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
    
    # Print sections
    sections = result.get("sections", [])
    if sections:
        print("\nSECTIONS:")
        for section in sections:
            print(f"\n## {section.get('title', 'Untitled Section')}")
            print(f"{section.get('content', 'No content')}")
            
            # Print sources if available
            sources = section.get("sources", [])
            if sources:
                print("\nSources:")
                for source in sources:
                    print(f"  - {source}")
    
    # Print full report if available
    report = result.get("report", "")
    if report:
        print("\nFULL REPORT:")
        print(report)
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()

