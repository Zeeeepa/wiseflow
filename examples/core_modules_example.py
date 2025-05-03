#!/usr/bin/env python3
"""
Example demonstrating the usage of WiseFlow core modules.

This example shows how to use the centralized imports, configuration, and initialization
modules to set up and run a simple WiseFlow task.
"""

import asyncio
import os
import sys
import logging
from datetime import datetime

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from centralized imports and configuration modules
from core.imports import get_logger, get_pb_client, get_llm_client
from core.config import load_config, get_config, get
from core.initialize import (
    initialize_environment,
    initialize_resource_monitor,
    initialize_thread_pool,
    initialize_task_manager,
    initialize_plugin_system,
    initialize_connectors,
    initialize_reference_manager,
    initialize_insight_extractor,
    shutdown_all
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = get_logger("wiseflow_example")

async def process_content(content, focus_point, explanation=""):
    """Process content using the specialized prompt processor."""
    from core.llms.advanced.specialized_prompting import (
        SpecializedPromptProcessor,
        CONTENT_TYPE_TEXT,
        TASK_EXTRACTION
    )
    
    # Get LLM client
    llm_client = get_llm_client()
    
    # Create prompt processor
    prompt_processor = SpecializedPromptProcessor(
        default_model=get("llm.primary_model", "gpt-3.5-turbo"),
        default_temperature=get("llm.default_temperature", 0.7),
        default_max_tokens=get("llm.default_max_tokens", 1000)
    )
    
    # Process content
    logger.info(f"Processing content with focus point: {focus_point}")
    result = await prompt_processor.process(
        content=content,
        focus_point=focus_point,
        explanation=explanation,
        content_type=CONTENT_TYPE_TEXT,
        task=TASK_EXTRACTION,
        metadata={"timestamp": datetime.now().isoformat()}
    )
    
    return result

async def main():
    """Main entry point."""
    try:
        # Initialize environment and load configuration
        initialize_environment()
        config = load_config()
        
        logger.info("WiseFlow example started")
        
        # Initialize components
        components = {}
        
        # Initialize resource monitor
        components["resource_monitor"] = initialize_resource_monitor(
            check_interval=get("resources.resource_check_interval", 10.0),
            cpu_threshold=get("resources.cpu_threshold", 80.0),
            memory_threshold=get("resources.memory_threshold", 80.0),
            disk_threshold=get("resources.disk_threshold", 90.0)
        )
        
        # Initialize thread pool
        components["thread_pool"] = initialize_thread_pool(
            resource_monitor=components["resource_monitor"],
            min_workers=get("resources.min_workers", 2),
            max_workers=get("resources.max_concurrent_tasks", 4),
            adjust_interval=get("resources.adjust_interval", 30.0)
        )
        
        # Initialize task manager
        components["task_manager"] = initialize_task_manager(
            thread_pool=components["thread_pool"],
            resource_monitor=components["resource_monitor"],
            history_limit=1000
        )
        
        # Process sample content
        sample_content = """
        Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to natural intelligence displayed by animals including humans. 
        AI research has been defined as the field of study of intelligent agents, which refers to any system that perceives its environment and takes actions that maximize its chance of achieving its goals.
        
        The term "artificial intelligence" had previously been used to describe machines that mimic and display "human" cognitive skills that are associated with the human mind, such as "learning" and "problem-solving". 
        This definition has since been rejected by major AI researchers who now describe AI in terms of rationality and acting rationally, which does not limit how intelligence can be articulated.
        
        AI applications include advanced web search engines (e.g., Google), recommendation systems (used by YouTube, Amazon, and Netflix), understanding human speech (such as Siri and Alexa), self-driving cars (e.g., Waymo), generative or creative tools (ChatGPT and AI art), automated decision-making, and competing at the highest level in strategic game systems (such as chess and Go).
        
        As machines become increasingly capable, tasks considered to require "intelligence" are often removed from the definition of AI, a phenomenon known as the AI effect. For instance, optical character recognition is frequently excluded from things considered to be AI, having become a routine technology.
        """
        
        focus_point = "Recent developments and applications of AI"
        explanation = "I'm interested in understanding how AI is being applied in real-world scenarios"
        
        result = await process_content(sample_content, focus_point, explanation)
        
        # Print the result
        logger.info("Processing result:")
        if "summary" in result:
            logger.info(f"Summary: {result['summary']}")
        
        if "extracted_info" in result:
            logger.info("Extracted information:")
            for info in result["extracted_info"]:
                logger.info(f"- {info.get('content', '')}")
        
        # Shutdown components
        await shutdown_all(components)
        
        logger.info("WiseFlow example completed")
    
    except Exception as e:
        logger.error(f"Error in example: {e}")
        if "components" in locals():
            await shutdown_all(components)

if __name__ == "__main__":
    asyncio.run(main())

