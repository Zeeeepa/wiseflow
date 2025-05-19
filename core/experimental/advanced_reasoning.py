"""
Advanced reasoning techniques for LLM interactions.

This module contains experimental reasoning techniques that are primarily used in testing
or specialized scenarios. These functions are moved from core/llms/advanced/specialized_prompting.py
to separate experimental features from core functionality.
"""

import logging
from typing import Dict, Any, Optional

from core.llms.advanced.specialized_prompting import (
    SpecializedPromptProcessor,
    CONTENT_TYPE_TEXT,
    TASK_REASONING
)

logger = logging.getLogger(__name__)

async def chain_of_thought(
    content: str,
    focus_point: str,
    explanation: str = "",
    content_type: str = CONTENT_TYPE_TEXT,
    metadata: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """
    Perform chain-of-thought reasoning on content.
    
    This is an experimental function that implements chain-of-thought prompting,
    a technique where the LLM is guided to break down complex reasoning into steps.
    
    Args:
        content: The content to process
        focus_point: The focus point for extraction
        explanation: Additional explanation or context
        content_type: The type of content
        metadata: Additional metadata
        model: The LLM model to use
        temperature: The temperature for LLM generation
        max_tokens: The maximum tokens for LLM generation
        
    Returns:
        Dict[str, Any]: The reasoning result
    
    Example:
        ```python
        result = await chain_of_thought(
            content="The GDP of Country A grew by 3% in Q1, 2% in Q2, and declined by 1% in Q3.",
            focus_point="Calculate the average quarterly growth and predict Q4 growth.",
            explanation="Use economic trends to make your prediction."
        )
        ```
    """
    processor = SpecializedPromptProcessor()
    return await processor.process(
        content=content,
        focus_point=focus_point,
        explanation=explanation,
        content_type=content_type,
        task="chain_of_thought",
        metadata=metadata,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens
    )

async def multi_step_reasoning(
    content: str,
    focus_point: str,
    explanation: str = "",
    content_type: str = CONTENT_TYPE_TEXT,
    metadata: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """
    Perform multi-step reasoning on content.
    
    This is an experimental function that implements multi-step reasoning,
    a technique where complex problems are broken down into multiple reasoning steps.
    
    Args:
        content: The content to process
        focus_point: The focus point for extraction
        explanation: Additional explanation or context
        content_type: The type of content
        metadata: Additional metadata
        model: The LLM model to use
        temperature: The temperature for LLM generation
        max_tokens: The maximum tokens for LLM generation
        
    Returns:
        Dict[str, Any]: The reasoning result
    
    Example:
        ```python
        result = await multi_step_reasoning(
            content="Patient presents with fever (101.3°F), cough, and fatigue for 3 days.",
            focus_point="Provide a differential diagnosis and recommended tests.",
            explanation="Consider common and uncommon causes based on the symptoms."
        )
        ```
    """
    processor = SpecializedPromptProcessor()
    return await processor.process(
        content=content,
        focus_point=focus_point,
        explanation=explanation,
        content_type=content_type,
        task=TASK_REASONING,
        metadata=metadata,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens
    )

