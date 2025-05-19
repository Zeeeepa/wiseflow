"""
Advanced LLM Integration with Specialized Prompting Strategies

This module implements specialized prompting strategies for different content types
and multi-step reasoning for complex extraction tasks. It enhances the LLM integration
with contextual understanding and reference support.

The module provides:
- Content type constants for different types of data (text, HTML, markdown, code, etc.)
- Task type constants for different processing operations (extraction, summarization, etc.)
- SpecializedPromptProcessor class for content-aware prompting
- Chain-of-thought reasoning for complex tasks
- Multi-step reasoning for breaking down complex tasks
- Content-specific prompt templates optimized for different data types

This module is a key component of WiseFlow's intelligence layer, enabling
sophisticated processing of diverse content types with specialized prompting
strategies tailored to each type's unique characteristics.

Implementation based on the requirements from the upgrade plan - Phase 3: Intelligence.
"""

import os
import json
import logging
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import asyncio

from core.llms.litellm_wrapper import litellm_llm, litellm_llm_async

logger = logging.getLogger(__name__)

# Content type constants
CONTENT_TYPE_TEXT = "text/plain"
CONTENT_TYPE_HTML = "text/html"
CONTENT_TYPE_MARKDOWN = "text/markdown"
CONTENT_TYPE_CODE = "code"
CONTENT_TYPE_ACADEMIC = "academic"
CONTENT_TYPE_VIDEO = "video"
CONTENT_TYPE_SOCIAL = "social"
