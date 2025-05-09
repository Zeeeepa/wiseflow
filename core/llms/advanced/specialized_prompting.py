"""
Advanced LLM Integration with Specialized Prompting Strategies

This module implements specialized prompting strategies for different content types
and multi-step reasoning for complex extraction tasks. It enhances the LLM integration
with contextual understanding and reference support.

Implementation based on the requirements from the upgrade plan - Phase 3: Intelligence.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
import os

from core.llms.advanced import (
    AdvancedLLMProcessor,
    CONTENT_TYPE_TEXT,
    CONTENT_TYPE_HTML,
    CONTENT_TYPE_MARKDOWN,
    CONTENT_TYPE_CODE,
    CONTENT_TYPE_ACADEMIC,
    CONTENT_TYPE_VIDEO,
    CONTENT_TYPE_SOCIAL,
    TASK_EXTRACTION,
    TASK_SUMMARIZATION,
    TASK_ANALYSIS,
    TASK_REASONING,
    TASK_COMPARISON,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS
)

logger = logging.getLogger(__name__)

class SpecializedPromptProcessor(AdvancedLLMProcessor):
    """
    Specialized prompt processor for different content types and tasks.
    
    This class extends the AdvancedLLMProcessor to provide specialized
    prompting strategies for different content types and tasks.
    """
    
    def __init__(
        self,
        default_model: Optional[str] = None,
        default_temperature: Optional[float] = None,
        default_max_tokens: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the specialized prompt processor.
        
        Args:
            default_model: Default LLM model to use
            default_temperature: Default temperature for LLM generation
            default_max_tokens: Default maximum tokens for LLM generation
            config: Optional configuration dictionary
        """
        super().__init__(
            default_model=default_model or DEFAULT_MODEL,
            default_temperature=default_temperature if default_temperature is not None else DEFAULT_TEMPERATURE,
            default_max_tokens=default_max_tokens or DEFAULT_MAX_TOKENS,
            config=config
        )
        
        # Additional initialization specific to specialized prompt processor
        self.content_type_mapping = {
            "text": CONTENT_TYPE_TEXT,
            "html": CONTENT_TYPE_HTML,
            "markdown": CONTENT_TYPE_MARKDOWN,
            "code": CONTENT_TYPE_CODE,
            "academic": CONTENT_TYPE_ACADEMIC,
            "video": CONTENT_TYPE_VIDEO,
            "social": CONTENT_TYPE_SOCIAL
        }
        
        self.task_mapping = {
            "extract": TASK_EXTRACTION,
            "summarize": TASK_SUMMARIZATION,
            "analyze": TASK_ANALYSIS,
            "reason": TASK_REASONING,
            "compare": TASK_COMPARISON
        }
    
    def get_content_type(self, content_type_str: str) -> str:
        """
        Get the standardized content type from a string.
        
        Args:
            content_type_str: String representation of content type
            
        Returns:
            str: Standardized content type
        """
        content_type_str = content_type_str.lower()
        
        if content_type_str in self.content_type_mapping:
            return self.content_type_mapping[content_type_str]
        
        if "/" in content_type_str:
            return content_type_str
        
        return CONTENT_TYPE_TEXT
    
    def get_task_type(self, task_str: str) -> str:
        """
        Get the standardized task type from a string.
        
        Args:
            task_str: String representation of task
            
        Returns:
            str: Standardized task type
        """
        task_str = task_str.lower()
        
        if task_str in self.task_mapping:
            return self.task_mapping[task_str]
        
        return TASK_EXTRACTION
