#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example script demonstrating the usage of the improved LLM integration in WiseFlow.

This script shows how to use the various features of the LLM integration,
including basic generation, streaming, token management, and caching.
"""

import os
import asyncio
import logging
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import LLM manager
from core.llms import llm_manager

async def basic_generation_example():
    """Example of basic text generation."""
    logger.info("=== Basic Generation Example ===")
    
    # Simple prompt
    prompt = "Explain the concept of machine learning in simple terms."
    
    # Generate text
    logger.info(f"Generating response for prompt: {prompt}")
    response = await llm_manager.generate(
        prompt=prompt,
        max_tokens=200
    )
    
    logger.info(f"Response: {response}")
    
    # Using messages format
    messages = [
        {"role": "system", "content": "You are a helpful assistant specializing in technology."},
        {"role": "user", "content": "What are the key differences between AI, ML, and deep learning?"}
    ]
    
    logger.info(f"Generating response for messages")
    response = await llm_manager.generate(
        prompt=messages,
        max_tokens=300
    )
    
    logger.info(f"Response: {response}")

async def model_fallback_example():
    """Example of model fallback."""
    logger.info("=== Model Fallback Example ===")
    
    prompt = "Describe three innovative applications of blockchain technology beyond cryptocurrency."
    
    # Generate with fallback
    logger.info(f"Generating response with fallback for prompt: {prompt}")
    response, model_used = await llm_manager.generate(
        prompt=prompt,
        use_fallback=True,
        task_type="explanation",
        max_tokens=250
    )
    
    logger.info(f"Response from model {model_used}: {response}")

async def streaming_example():
    """Example of streaming responses."""
    logger.info("=== Streaming Example ===")
    
    prompt = "Write a short poem about technology and nature."
    
    # Define callback function for streaming
    async def handle_chunk(chunk):
        print(chunk, end="", flush=True)
    
    logger.info(f"Streaming response for prompt: {prompt}")
    print("\nStreaming response: ")
    
    full_response = await llm_manager.generate_streaming(
        prompt=prompt,
        callback=handle_chunk,
        max_tokens=200
    )
    
    print("\n")
    logger.info("Streaming completed")

async def token_management_example():
    """Example of token management."""
    logger.info("=== Token Management Example ===")
    
    # Count tokens
    text = "This is a sample text to count tokens in. It's not very long, but it will give us a token count."
    token_count = llm_manager.get_token_count(text)
    logger.info(f"Token count for text: {token_count}")
    
    # Count tokens in messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"},
        {"role": "assistant", "content": "The capital of France is Paris."},
        {"role": "user", "content": "What about Germany?"}
    ]
    token_count = llm_manager.get_token_count(messages)
    logger.info(f"Token count for messages: {token_count}")
    
    # Optimize a prompt
    long_prompt = "Explain the history and evolution of artificial intelligence " * 20
    logger.info(f"Original prompt token count: {llm_manager.get_token_count(long_prompt)}")
    
    optimized_prompt = llm_manager.optimize_prompt(long_prompt, 100)
    logger.info(f"Optimized prompt token count: {llm_manager.get_token_count(optimized_prompt)}")
    logger.info(f"Optimized prompt: {optimized_prompt}")
    
    # Estimate cost
    cost_estimate = llm_manager.estimate_cost(messages)
    logger.info(f"Cost estimate: {cost_estimate}")
    
    # Get usage summary
    usage_summary = llm_manager.get_usage_summary()
    logger.info(f"Usage summary: {usage_summary}")

async def caching_example():
    """Example of caching."""
    logger.info("=== Caching Example ===")
    
    prompt = "What are the three laws of robotics?"
    
    # First call (cache miss)
    logger.info("First call (should be cache miss)")
    start_time = asyncio.get_event_loop().time()
    response1 = await llm_manager.generate(
        prompt=prompt,
        use_cache=True,
        max_tokens=200
    )
    end_time = asyncio.get_event_loop().time()
    logger.info(f"Response time: {(end_time - start_time) * 1000:.2f}ms")
    
    # Second call (cache hit)
    logger.info("Second call (should be cache hit)")
    start_time = asyncio.get_event_loop().time()
    response2 = await llm_manager.generate(
        prompt=prompt,
        use_cache=True,
        max_tokens=200
    )
    end_time = asyncio.get_event_loop().time()
    logger.info(f"Response time: {(end_time - start_time) * 1000:.2f}ms")
    
    # Verify responses are the same
    logger.info(f"Responses match: {response1 == response2}")
    
    # Get cache statistics
    cache_stats = llm_manager.get_cache_stats()
    logger.info(f"Cache statistics: {cache_stats}")

async def specialized_prompting_example():
    """Example of specialized prompting."""
    logger.info("=== Specialized Prompting Example ===")
    
    from core.llms.advanced.specialized_prompting import ContentTypePromptStrategy
    
    prompt_strategy = ContentTypePromptStrategy()
    
    # Academic content
    academic_text = """
    Abstract: This paper explores the impact of climate change on global agriculture.
    We analyze data from 50 countries over a 30-year period to identify trends in crop yields,
    growing seasons, and extreme weather events. Our findings indicate that climate change
    has already reduced global crop yields by approximately 5-10%, with greater impacts in
    tropical regions. We propose several adaptation strategies that could mitigate these effects.
    
    Keywords: climate change, agriculture, crop yields, adaptation strategies
    """
    
    logger.info("Processing academic content")
    result = await prompt_strategy.process(
        content=academic_text,
        focus_point="Agricultural impacts of climate change",
        explanation="Focus on adaptation strategies",
        content_type="academic",
        task="extraction",
        model=llm_manager.default_model
    )
    
    logger.info(f"Result: {result}")
    
    # Code content
    code_text = """
    def calculate_climate_impact(temperature_change, precipitation_change, crop_type):
        \"\"\"
        Calculate the impact of climate change on crop yields.
        
        Args:
            temperature_change: Change in temperature in degrees Celsius
            precipitation_change: Change in precipitation in mm
            crop_type: Type of crop (wheat, corn, rice, etc.)
            
        Returns:
            Estimated change in crop yield as a percentage
        \"\"\"
        # Base impact factors (empirically derived)
        temp_impact_factor = -0.05  # 5% reduction per degree C increase
        precip_impact_factor = 0.002  # 0.2% increase per mm increase
        
        # Crop-specific adjustments
        if crop_type == "wheat":
            temp_impact_factor *= 1.2
            precip_impact_factor *= 0.8
        elif crop_type == "corn":
            temp_impact_factor *= 1.5
            precip_impact_factor *= 1.2
        elif crop_type == "rice":
            temp_impact_factor *= 0.8
            precip_impact_factor *= 1.5
        
        # Calculate impact
        temp_impact = temperature_change * temp_impact_factor
        precip_impact = precipitation_change * precip_impact_factor
        
        # Combined impact (simple addition for now)
        total_impact = temp_impact + precip_impact
        
        return total_impact * 100  # Convert to percentage
    """
    
    logger.info("Processing code content")
    result = await prompt_strategy.process(
        content=code_text,
        focus_point="Climate impact calculation",
        explanation="Analyze the methodology",
        content_type="code",
        task="analysis",
        metadata={"language": "python", "file_path": "climate_models.py"},
        model=llm_manager.default_model
    )
    
    logger.info(f"Result: {result}")

async def multi_step_reasoning_example():
    """Example of multi-step reasoning."""
    logger.info("=== Multi-step Reasoning Example ===")
    
    from core.llms.advanced import AdvancedLLMProcessor
    
    processor = AdvancedLLMProcessor()
    
    complex_text = """
    The transition to renewable energy sources presents both opportunities and challenges.
    On one hand, renewable energy can reduce greenhouse gas emissions and mitigate climate change.
    Solar panel prices have dropped by 89% since 2010, making them increasingly competitive with fossil fuels.
    Wind power capacity has grown by 15% annually over the past decade.
    
    On the other hand, renewable energy sources are intermittent, requiring energy storage solutions.
    Battery technology has improved, but still faces limitations in capacity and lifespan.
    The mining of rare earth minerals for renewable technologies raises environmental and ethical concerns.
    
    Economically, the renewable energy sector has created millions of jobs worldwide.
    However, communities dependent on fossil fuel industries face significant economic disruption.
    Government policies, including subsidies and carbon pricing, play a crucial role in shaping the transition.
    
    The pace of transition varies significantly by country, with some achieving over 50% renewable electricity,
    while others remain heavily dependent on coal and natural gas.
    """
    
    logger.info("Performing multi-step reasoning")
    result = await processor.multi_step_reasoning(
        content=complex_text,
        focus_point="Renewable energy transition",
        explanation="Analyze the economic, environmental, and social implications",
        content_type="text/plain",
        model=llm_manager.default_model
    )
    
    logger.info(f"Result: {result}")

async def main():
    """Run all examples."""
    try:
        await basic_generation_example()
        print("\n")
        
        await model_fallback_example()
        print("\n")
        
        await streaming_example()
        print("\n")
        
        await token_management_example()
        print("\n")
        
        await caching_example()
        print("\n")
        
        await specialized_prompting_example()
        print("\n")
        
        await multi_step_reasoning_example()
        
    except Exception as e:
        logger.error(f"Error in examples: {e}")

if __name__ == "__main__":
    asyncio.run(main())

