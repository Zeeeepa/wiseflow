"""Example usage of the enhanced research connector."""

import os
import json
import time
import logging
from core.plugins.connectors.research_connector import ResearchConnector, ResearchStatus
from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI, CacheStrategy

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def progress_callback(message, progress):
    """Callback function for progress updates."""
    print(f"Progress: {progress:.1%} - {message}")

def error_callback(error):
    """Callback function for error handling."""
    print(f"Error: {str(error)}")

def main():
    """Run the research connector example."""
    # Set up API keys (replace with your actual API keys)
    os.environ["TAVILY_API_KEY"] = "your-tavily-api-key"
    os.environ["PERPLEXITY_API_KEY"] = "your-perplexity-api-key"
    os.environ["EXA_API_KEY"] = "your-exa-api-key"
    
    # Create a configuration with enhanced options
    config = Configuration(
        search_api=SearchAPI.TAVILY,
        fallback_search_api=SearchAPI.PERPLEXITY,  # Fallback API if primary fails
        research_mode=ResearchMode.GRAPH,  # Using the enhanced graph-based research
        max_search_depth=2,
        number_of_queries=3,
        cache_strategy=CacheStrategy.MEMORY,  # Enable in-memory caching
        cache_ttl=3600,  # Cache TTL in seconds
        max_retries=3,  # Maximum number of retries for failed operations
        visualization_enabled=True,  # Enable visualization
        visualization_path="research_visualization.html"  # Path to save visualization
    )
    
    # Initialize the research connector
    connector = ResearchConnector(config)
    
    # Register callbacks
    connector.register_progress_callback(progress_callback)
    connector.register_error_callback(error_callback)
    
    # Perform research on a topic
    topic = "The impact of artificial intelligence on healthcare"
    print(f"\n--- Researching: {topic} ---\n")
    
    start_time = time.time()
    results = connector.research(topic)
    duration = time.time() - start_time
    
    # Print the results
    print(f"\nResearch Results for: {results['topic']}")
    print(f"Research Mode: {results['metadata']['research_mode']}")
    print(f"Search API: {results['metadata']['search_api']}")
    print(f"Duration: {duration:.2f} seconds")
    print("\nSections:")
    
    for section in results["sections"]:
        print(f"\n## {section['title']}")
        print(section["content"][:300] + "..." if len(section["content"]) > 300 else section["content"])
        
        if section["subsections"]:
            for subsection in section["subsections"]:
                print(f"\n### {subsection['title']}")
                print(subsection["content"][:200] + "..." if len(subsection["content"]) > 200 else subsection["content"])
    
    # Example of continuous research
    follow_up_topic = "Ethical considerations in AI healthcare applications"
    print(f"\n\n--- Continuous Research: {follow_up_topic} ---\n")
    
    start_time = time.time()
    follow_up_results = connector.continuous_research(results, follow_up_topic)
    duration = time.time() - start_time
    
    print(f"\nFollow-up Research Results for: {follow_up_results['topic']}")
    print(f"Previous Topic: {follow_up_results['previous_topic']}")
    print(f"Duration: {duration:.2f} seconds")
    print("\nSections:")
    
    for section in follow_up_results["sections"]:
        print(f"\n## {section['title']}")
        print(section["content"][:300] + "..." if len(section["content"]) > 300 else section["content"])
    
    # Example of streaming research
    streaming_topic = "Future trends in AI-powered medical diagnostics"
    print(f"\n\n--- Streaming Research: {streaming_topic} ---\n")
    
    # Start streaming research
    stream_result, cancel_fn = connector.stream_research(streaming_topic)
    
    # In a real application, you would process updates as they come in
    # For this example, we'll just wait a bit and then check the status
    print("Research started in streaming mode. Waiting for 5 seconds...")
    time.sleep(5)
    
    # Check the status
    status = connector.get_status()
    print(f"Current research status: {status.value}")
    
    # In a real application, you might want to cancel the operation
    # cancel_fn()  # Uncomment to cancel
    
    # Save the configuration for future use
    connector.save_config("research_config.json")
    print("\nConfiguration saved to research_config.json")
    
    # Example of loading a saved configuration
    loaded_config = ResearchConnector.load_config("research_config.json")
    print(f"Loaded configuration with research mode: {loaded_config.research_mode.value}")

if __name__ == "__main__":
    main()
