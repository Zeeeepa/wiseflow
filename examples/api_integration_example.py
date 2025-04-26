#!/usr/bin/env python3
"""
API Integration Example for WiseFlow.

This script demonstrates how to integrate with the WiseFlow API.
"""

import os
import asyncio
import logging
from typing import Dict, List, Any, Optional

from core.api.client import WiseFlowClient, AsyncWiseFlowClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# API configuration
API_BASE_URL = os.environ.get("WISEFLOW_API_URL", "http://localhost:8000")
API_KEY = os.environ.get("WISEFLOW_API_KEY", "dev-api-key")

async def main():
    """Main function to demonstrate the API integration."""
    # Initialize the API client
    client = WiseFlowClient(API_BASE_URL, API_KEY)
    async_client = AsyncWiseFlowClient(API_BASE_URL, API_KEY)
    
    # Check API health
    logger.info("Checking API health...")
    health = client.health_check()
    logger.info(f"API health: {health}")
    
    # Example content
    content = """
    Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to intelligence displayed by animals including humans. 
    AI research has been defined as the field of study of intelligent agents, which refers to any system that perceives its environment and takes actions that maximize its chance of achieving its goals.
    
    The term "artificial intelligence" had previously been used to describe machines that mimic and display "human" cognitive skills that are associated with the human mind, such as "learning" and "problem-solving". This definition has since been rejected by major AI researchers who now describe AI in terms of rationality and acting rationally, which does not limit how intelligence can be articulated.
    
    AI applications include advanced web search engines (e.g., Google), recommendation systems (used by YouTube, Amazon, and Netflix), understanding human speech (such as Siri and Alexa), self-driving cars (e.g., Waymo), generative or creative tools (ChatGPT and AI art), automated decision-making, and competing at the highest level in strategic game systems (such as chess and Go).
    
    As machines become increasingly capable, tasks considered to require "intelligence" are often removed from the definition of AI, a phenomenon known as the AI effect. For instance, optical character recognition is frequently excluded from things considered to be AI, having become a routine technology.
    """
    
    # Example focus point
    focus_point = "The evolution and applications of artificial intelligence"
    explanation = "Looking for information about how AI has evolved and its current applications"
    
    # Process with basic extraction
    logger.info("Processing with basic extraction...")
    result = client.process_content(
        content=content,
        focus_point=focus_point,
        explanation=explanation
    )
    logger.info(f"Basic extraction result: {result.get('summary', 'No summary available')}")
    
    # Process with multi-step reasoning
    logger.info("Processing with multi-step reasoning...")
    result = client.process_content(
        content=content,
        focus_point=focus_point,
        explanation=explanation,
        use_multi_step_reasoning=True
    )
    logger.info(f"Multi-step reasoning result: {result.get('summary', 'No summary available')}")
    
    # Process with contextual understanding
    logger.info("Processing with contextual understanding...")
    references = """
    Recent advancements in AI:
    1. Large language models like GPT-4 have demonstrated remarkable capabilities in natural language understanding and generation.
    2. Multimodal models can now process and generate content across text, images, and audio.
    3. AI systems are increasingly being deployed in critical domains like healthcare, finance, and autonomous vehicles.
    4. Concerns about AI safety, ethics, and regulation have become more prominent.
    """
    result = client.contextual_understanding(
        content=content,
        focus_point=focus_point,
        explanation=explanation,
        references=references
    )
    logger.info(f"Contextual understanding result: {result.get('contextual_understanding', 'No summary available')}")
    
    # Batch processing example
    logger.info("Batch processing example...")
    items = [
        {
            "content": "AI is transforming healthcare with applications in diagnosis, treatment planning, and drug discovery.",
            "content_type": "text",
            "metadata": {"source": "healthcare_article"}
        },
        {
            "content": "Machine learning models are being used to predict climate change patterns and optimize energy usage.",
            "content_type": "text",
            "metadata": {"source": "climate_article"}
        },
        {
            "content": "Natural language processing has advanced significantly with the development of transformer-based models.",
            "content_type": "text",
            "metadata": {"source": "nlp_article"}
        }
    ]
    results = client.batch_process(
        items=items,
        focus_point="Applications of AI in different domains",
        explanation="Looking for information about how AI is being applied in various fields"
    )
    for i, result in enumerate(results):
        logger.info(f"Batch item {i+1} result: {result.get('summary', 'No summary available')}")
    
    # Webhook management
    logger.info("Webhook management example...")
    
    # Register a webhook
    webhook_result = client.register_webhook(
        endpoint="https://example.com/webhook",
        events=["content.processed", "content.batch_processed"],
        description="Example webhook for content processing events"
    )
    logger.info(f"Webhook registration result: {webhook_result}")
    
    # List webhooks
    webhooks = client.list_webhooks()
    logger.info(f"Registered webhooks: {webhooks}")
    
    # Trigger a webhook
    if webhooks:
        webhook_id = webhooks[0].get("id")
        trigger_result = client.trigger_webhook(
            event="content.processed",
            data={
                "content_id": "example-123",
                "focus_point": focus_point,
                "timestamp": "2023-01-01T12:00:00Z"
            }
        )
        logger.info(f"Webhook trigger result: {trigger_result}")
    
    # Asynchronous API usage example
    logger.info("Asynchronous API usage example...")
    
    # Health check
    async_health = await async_client.health_check()
    logger.info(f"Async API health: {async_health}")
    
    # Process content
    async_result = await async_client.process_content(
        content=content,
        focus_point=focus_point,
        explanation=explanation
    )
    logger.info(f"Async processing result: {async_result.get('summary', 'No summary available')}")
    
    # Integration endpoints example
    logger.info("Integration endpoints example...")
    
    # Extract information
    extract_result = client.extract_information(
        content=content,
        focus_point=focus_point,
        explanation=explanation
    )
    logger.info(f"Extract information result: {extract_result.get('extracted_information', 'No information available')}")
    
    # Analyze content
    analyze_result = client.analyze_content(
        content=content,
        focus_point=focus_point,
        explanation=explanation
    )
    logger.info(f"Analyze content result: {analyze_result.get('analysis', 'No analysis available')}")
    
    logger.info("API integration example completed.")

if __name__ == "__main__":
    asyncio.run(main())
