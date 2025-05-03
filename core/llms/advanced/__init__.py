"""
Advanced LLM integration for Wiseflow.

This module provides advanced LLM integration with specialized prompting strategies,
multi-step reasoning, and domain-specific fine-tuning.
"""

from core.llms.advanced.specialized_prompting import (
    SpecializedPromptProcessor,
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

# Define the AdvancedLLMProcessor class as an alias for SpecializedPromptProcessor
AdvancedLLMProcessor = SpecializedPromptProcessor

__all__ = [
    'SpecializedPromptProcessor',
    'AdvancedLLMProcessor',
    'CONTENT_TYPE_TEXT',
    'CONTENT_TYPE_HTML',
    'CONTENT_TYPE_MARKDOWN',
    'CONTENT_TYPE_CODE',
    'CONTENT_TYPE_ACADEMIC',
    'CONTENT_TYPE_VIDEO',
    'CONTENT_TYPE_SOCIAL',
    'TASK_EXTRACTION',
    'TASK_REASONING'
]

