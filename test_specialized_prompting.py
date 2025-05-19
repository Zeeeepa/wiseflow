#!/usr/bin/env python3
"""
Test script for the specialized prompting module.
"""

import asyncio
import json
import os
from core.llms.advanced.specialized_prompting import (
    SpecializedPromptProcessor,
)
from core.content_types import (
    CONTENT_TYPE_TEXT,
    TASK_EXTRACTION,
    TASK_REASONING
)

async def test_specialized_prompting():
    """Test the specialized prompting module."""
    # Initialize the processor
    processor = SpecializedPromptProcessor(
        default_model=os.environ.get("PRIMARY_MODEL", "gpt-3.5-turbo"),
        default_temperature=0.7,
        default_max_tokens=1000
    )
    
    # Test content
    content = """
    Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to intelligence displayed by animals including humans. 
    AI research has been defined as the field of study of intelligent agents, which refers to any system that perceives its environment and takes actions that maximize its chance of achieving its goals.
    
    The term "artificial intelligence" had previously been used to describe machines that mimic and display "human" cognitive skills that are associated with the human mind, such as "learning" and "problem-solving". This definition has since been rejected by major AI researchers who now describe AI in terms of rationality and acting rationally, which does not limit how intelligence can be articulated.
    
    AI applications include advanced web search engines (e.g., Google), recommendation systems (used by YouTube, Amazon, and Netflix), understanding human speech (such as Siri and Alexa), self-driving cars (e.g., Waymo), generative or creative tools (ChatGPT and AI art), automated decision-making, and competing at the highest level in strategic game systems (such as chess and Go).
    
    As machines become increasingly capable, tasks considered to require "intelligence" are often removed from the definition of AI, a phenomenon known as the AI effect. For instance, optical character recognition is frequently excluded from things considered to be AI, having become a routine technology.
    """
    
    # Test focus point
    focus_point = "The evolution and applications of artificial intelligence"
    explanation = "Looking for information about how AI has evolved and its current applications"
    
    # Test basic extraction
    print("Testing basic extraction...")
    result = await processor.process(
        content=content,
        focus_point=focus_point,
        explanation=explanation,
        content_type=CONTENT_TYPE_TEXT,
        task=TASK_EXTRACTION
    )
    print(json.dumps(result, indent=2))
    print("\n" + "-" * 80 + "\n")
    
    # Test multi-step reasoning
    print("Testing multi-step reasoning...")
    result = await processor.multi_step_reasoning(
        content=content,
        focus_point=focus_point,
        explanation=explanation
    )
    print(json.dumps(result, indent=2))
    print("\n" + "-" * 80 + "\n")
    
    # Test chain of thought
    print("Testing chain of thought...")
    result = await processor.chain_of_thought(
        content=content,
        focus_point=focus_point,
        explanation=explanation
    )
    print(json.dumps(result, indent=2))
    print("\n" + "-" * 80 + "\n")
    
    # Test contextual understanding
    print("Testing contextual understanding...")
    references = """
    Recent advancements in AI:
    1. Large language models like GPT-4 have demonstrated remarkable capabilities in natural language understanding and generation.
    2. Multimodal models can now process and generate content across text, images, and audio.
    3. AI systems are increasingly being deployed in critical domains like healthcare, finance, and autonomous vehicles.
    4. Concerns about AI safety, ethics, and regulation have become more prominent.
    """
    result = await processor.contextual_understanding(
        content=content,
        focus_point=focus_point,
        explanation=explanation,
        references=references
    )
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(test_specialized_prompting())
