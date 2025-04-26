"""
Example script demonstrating the WiseFlow plugin system.

This script shows how to load and use plugins in WiseFlow.
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.plugins.loader import load_all_plugins, get_processor, get_analyzer
from core.connectors import DataItem
from core.plugins.processors import ProcessedData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Run the plugin example."""
    logger.info("Starting WiseFlow plugin example")
    
    # Load all plugins
    logger.info("Loading plugins...")
    plugins = load_all_plugins()
    logger.info(f"Loaded {len(plugins)} plugins")
    
    # Create a sample data item
    sample_text = """
    OpenAI released GPT-4 in March 2023, marking a significant advancement in AI language models.
    The new model demonstrates improved capabilities in reasoning, creativity, and handling complex instructions.
    Microsoft has been a major investor in OpenAI, contributing to the development of these technologies.
    Researchers at various universities, including Stanford and MIT, are studying the implications of these models.
    The development of large language models has raised concerns about their potential impact on jobs and society.
    """
    
    data_item = DataItem(
        source_id="example-1",
        content=sample_text,
        metadata={
            "author": "Example Author",
            "publish_date": "2023-04-01",
            "source": "Example Source"
        },
        url="https://example.com/article1",
        timestamp=datetime.now(),
        content_type="text"
    )
    
    # Process the data using the text processor
    logger.info("Processing data with text processor...")
    text_processor = get_processor("text_processor")
    if text_processor:
        processed_data = text_processor.process(
            data_item,
            params={
                "focus_point": "AI language models",
                "explanation": "Information about AI language models and their impact",
                "prompts": [
                    "You are an expert in extracting information about AI language models.",
                    "Extract key information about AI language models from the text.",
                    "gpt-3.5-turbo"
                ]
            }
        )
        logger.info(f"Processed data: {processed_data.processed_content}")
    else:
        logger.warning("Text processor not found")
        # Create a simple processed data for demonstration
        processed_data = ProcessedData(
            original_item=data_item,
            processed_content=sample_text,
            metadata={"source_type": "text"}
        )
    
    # Analyze the processed data using the entity analyzer
    logger.info("Analyzing data with entity analyzer...")
    entity_analyzer = get_analyzer("entity_analyzer")
    if entity_analyzer:
        entity_result = entity_analyzer.analyze(processed_data)
        logger.info(f"Entity analysis result: {entity_result.analysis_content}")
    else:
        logger.warning("Entity analyzer not found")
    
    # Analyze the processed data using the trend analyzer
    logger.info("Analyzing data with trend analyzer...")
    trend_analyzer = get_analyzer("trend_analyzer")
    if trend_analyzer:
        trend_result = trend_analyzer.analyze(processed_data)
        logger.info(f"Trend analysis result: {trend_result.analysis_content}")
    else:
        logger.warning("Trend analyzer not found")
    
    logger.info("Plugin example completed")

if __name__ == "__main__":
    main()
