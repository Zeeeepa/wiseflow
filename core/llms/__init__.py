"""
LLM integration module for WiseFlow.

This module provides wrappers and utilities for interacting with
various language models.
"""

from core.llms.openai_wrapper import openai_llm
from core.llms.litellm_wrapper import litellm_wrapper

# Import advanced LLM functionality
from core.llms.advanced import (
    AdvancedLLMProcessor,
    SpecializedPromptProcessor
)

__all__ = [
    'openai_llm',
    'litellm_wrapper',
    'AdvancedLLMProcessor',
    'SpecializedPromptProcessor'
]

