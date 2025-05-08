"""
LLM integration for Wiseflow.

This module provides integration with various LLM providers.
"""

from typing import Dict, List, Any, Optional, Union
import os

# Import LLM wrappers
from core.llms.openai_wrapper import openai_llm
from core.llms.litellm_wrapper import litellm_llm, litellm_llm_async, LiteLLMWrapper

# Set default model from environment
DEFAULT_MODEL = os.environ.get("PRIMARY_MODEL", "gpt-3.5-turbo")
DEFAULT_TEMPERATURE = float(os.environ.get("DEFAULT_TEMPERATURE", "0.7"))
DEFAULT_MAX_TOKENS = int(os.environ.get("DEFAULT_MAX_TOKENS", "1000"))

__all__ = [
    "openai_llm", 
    "litellm_llm", 
    "litellm_llm_async", 
    "LiteLLMWrapper",
    "DEFAULT_MODEL",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_MAX_TOKENS"
]
