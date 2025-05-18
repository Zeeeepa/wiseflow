#!/usr/bin/env python3
"""
Integration example for the specialized prompting module.

This script demonstrates how to integrate the specialized prompting module
into the main Wiseflow application.
"""

import asyncio
import os
import logging
from typing import Dict, Any, List, Optional

from core.llms.advanced.specialized_prompting import (
    SpecializedPromptProcessor,
)
from core.content_types import (
    CONTENT_TYPE_TEXT,
    CONTENT_TYPE_HTML,
    CONTENT_TYPE_MARKDOWN,
    CONTENT_TYPE_CODE,
    CONTENT_TYPE_ACADEMIC,
    CONTENT_TYPE_VIDEO,
    CONTENT_TYPE_SOCIAL,
    TASK_EXTRACTION,
    TASK_REASONING
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class ContentProcessor:
    """
    Content processor that uses specialized prompting strategies.
    
    This class demonstrates how to integrate the specialized prompting module
    into the main Wiseflow application.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the content processor.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        
        # Initialize the specialized prompt processor
        self.prompt_processor = SpecializedPromptProcessor(
            default_model=os.environ.get("PRIMARY_MODEL", "gpt-3.5-turbo"),
            default_temperature=0.7,
            default_max_tokens=1000,
            config=self.config
        )
    
    async def process_content(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = CONTENT_TYPE_TEXT,
        use_multi_step_reasoning: bool = False,
        references: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process content using specialized prompting strategies.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            content_type: The type of content
            use_multi_step_reasoning: Whether to use multi-step reasoning
            references: Optional reference materials for contextual understanding
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The processing result
        """
        metadata = metadata or {}
        
        # Determine the appropriate processing method based on the parameters
        if references:
            logger.info(f"Processing content with contextual understanding: {content_type}")
            return await self.prompt_processor.contextual_understanding(
                content=content,
                focus_point=focus_point,
                references=references,
                explanation=explanation,
                content_type=content_type,
                metadata=metadata
            )
        elif use_multi_step_reasoning:
            logger.info(f"Processing content with multi-step reasoning: {content_type}")
            return await self.prompt_processor.multi_step_reasoning(
                content=content,
                focus_point=focus_point,
                explanation=explanation,
                content_type=content_type,
                metadata=metadata
            )
        else:
            logger.info(f"Processing content with basic extraction: {content_type}")
            return await self.prompt_processor.process(
                content=content,
                focus_point=focus_point,
                explanation=explanation,
                content_type=content_type,
                task=TASK_EXTRACTION,
                metadata=metadata
            )
    
    async def batch_process(
        self,
        items: List[Dict[str, Any]],
        focus_point: str,
        explanation: str = "",
        use_multi_step_reasoning: bool = False,
        max_concurrency: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Process multiple items concurrently.
        
        Args:
            items: List of items to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            use_multi_step_reasoning: Whether to use multi-step reasoning
            max_concurrency: Maximum number of concurrent processes
            
        Returns:
            List[Dict[str, Any]]: The processing results
        """
        task = TASK_REASONING if use_multi_step_reasoning else TASK_EXTRACTION
        
        logger.info(f"Batch processing {len(items)} items with task: {task}")
        
        return await self.prompt_processor.batch_process(
            items=items,
            focus_point=focus_point,
            explanation=explanation,
            task=task,
            max_concurrency=max_concurrency
        )

async def main():
    """Main function to demonstrate the integration."""
    # Initialize the content processor
    processor = ContentProcessor()
    
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
    print("Processing with basic extraction...")
    result = await processor.process_content(
        content=content,
        focus_point=focus_point,
        explanation=explanation
    )
    print(f"Basic extraction result: {result.get('summary', 'No summary available')}")
    
    # Process with multi-step reasoning
    print("\nProcessing with multi-step reasoning...")
    result = await processor.process_content(
        content=content,
        focus_point=focus_point,
        explanation=explanation,
        use_multi_step_reasoning=True
    )
    print(f"Multi-step reasoning result: {result.get('summary', 'No summary available')}")
    
    # Process with contextual understanding
    print("\nProcessing with contextual understanding...")
    references = """
    Recent advancements in AI:
    1. Large language models like GPT-4 have demonstrated remarkable capabilities in natural language understanding and generation.
    2. Multimodal models can now process and generate content across text, images, and audio.
    3. AI systems are increasingly being deployed in critical domains like healthcare, finance, and autonomous vehicles.
    4. Concerns about AI safety, ethics, and regulation have become more prominent.
    """
    result = await processor.process_content(
        content=content,
        focus_point=focus_point,
        explanation=explanation,
        references=references
    )
    print(f"Contextual understanding result: {result.get('summary', 'No summary available')}")
    
    # Batch processing example
    print("\nBatch processing example...")
    items = [
        {
            "content": "AI is transforming healthcare with applications in diagnosis, treatment planning, and drug discovery.",
            "content_type": CONTENT_TYPE_TEXT,
            "metadata": {"source": "healthcare_article"}
        },
        {
            "content": "Machine learning models are being used to predict climate change patterns and optimize energy usage.",
            "content_type": CONTENT_TYPE_TEXT,
            "metadata": {"source": "climate_article"}
        },
        {
            "content": "Natural language processing has advanced significantly with the development of transformer-based models.",
            "content_type": CONTENT_TYPE_TEXT,
            "metadata": {"source": "nlp_article"}
        }
    ]
    results = await processor.batch_process(
        items=items,
        focus_point="Applications of AI in different domains",
        explanation="Looking for information about how AI is being applied in various fields"
    )
    for i, result in enumerate(results):
        print(f"Batch item {i+1} result: {result.get('summary', 'No summary available')}")

if __name__ == "__main__":
    asyncio.run(main())
