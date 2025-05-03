"""Example usage of the research connector."""

import os
import json
from core.plugins.connectors.research_connector import ResearchConnector
from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI

def main():
    """Run the research connector example."""
    # Set up API keys (replace with your actual API keys)
    os.environ["TAVILY_API_KEY"] = "your-tavily-api-key"
    os.environ["PERPLEXITY_API_KEY"] = "your-perplexity-api-key"
    os.environ["EXA_API_KEY"] = "your-exa-api-key"
    
    # Create a configuration
    config = Configuration(
        search_api=SearchAPI.TAVILY,
        research_mode=ResearchMode.LINEAR,
        max_search_depth=2,
        number_of_queries=2
    )
    
    # Initialize the research connector
    connector = ResearchConnector(config)
    
    # Perform research on a topic
    topic = "The impact of artificial intelligence on healthcare"
    results = connector.research(topic)
    
    # Print the results
    print(f"Research Results for: {results['topic']}")
    print(f"Research Mode: {results['metadata']['research_mode']}")
    print(f"Search API: {results['metadata']['search_api']}")
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
    follow_up_results = connector.continuous_research(results, follow_up_topic)
    
    print(f"\n\nFollow-up Research Results for: {follow_up_results['topic']}")
    print(f"Previous Topic: {follow_up_results['previous_topic']}")
    print("\nSections:")
    
    for section in follow_up_results["sections"]:
        print(f"\n## {section['title']}")
        print(section["content"][:300] + "..." if len(section["content"]) > 300 else section["content"])

if __name__ == "__main__":
    main()

