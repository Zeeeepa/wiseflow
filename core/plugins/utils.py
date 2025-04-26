"""
Utility functions for the plugin system.

This module provides common utility functions used by plugins.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class TextExtractor:
    """Utility class for extracting text from various data structures."""
    
    @staticmethod
    def extract_text(processed_content: Any) -> str:
        """
        Extract text from processed content of various types.
        
        Args:
            processed_content: Content to extract text from (can be str, dict, list, etc.)
            
        Returns:
            Extracted text as a string
        """
        if isinstance(processed_content, str):
            return processed_content
        
        if isinstance(processed_content, list):
            # Try to extract text from a list of items
            text_parts = []
            for item in processed_content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict) and "content" in item:
                    text_parts.append(item["content"])
            
            return "\n\n".join(text_parts)
        
        if isinstance(processed_content, dict):
            # Try to extract text from a dictionary
            if "content" in processed_content:
                return processed_content["content"]
            
            # Try to find any text fields
            text_parts = []
            for key, value in processed_content.items():
                if isinstance(value, str) and len(value) > 50:  # Assume longer strings are content
                    text_parts.append(value)
            
            return "\n\n".join(text_parts)
        
        return str(processed_content)
