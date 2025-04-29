"""
Text processor plugin for Wiseflow.

This module provides a processor for text content.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from core.plugins.processors import ProcessorBase, ProcessedData
from core.connectors import DataItem
from core.llms.openai_wrapper import openai_llm

logger = logging.getLogger(__name__)

class TextProcessor(ProcessorBase):
    """Processor for text content."""
    
    name: str = "text_processor"
    description: str = "Processor for text content using LLMs"
    processor_type: str = "text"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the text processor."""
        super().__init__(config)
        self.default_model = self.config.get("default_model", "gpt-3.5-turbo")
        self.default_temperature = self.config.get("default_temperature", 0.7)
        self.default_max_tokens = self.config.get("default_max_tokens", 1000)
        
    def initialize(self) -> bool:
        """Initialize the text processor."""
        try:
            logger.info(f"Initialized text processor with model: {self.default_model}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize text processor: {e}")
            return False
    
    def process(self, data_item: DataItem, params: Optional[Dict[str, Any]] = None) -> ProcessedData:
        """
        Process a text data item.
        
        Args:
            data_item: The data item to process
            params: Optional processing parameters
                - focus_point: The focus point for extraction
                - explanation: Additional explanation or context
                - prompts: List of prompts to use [system_prompt, user_prompt, model]
                - model: The model to use
                - temperature: The temperature to use
                - max_tokens: The maximum number of tokens to generate
                
        Returns:
            ProcessedData: The processed data
        """
        params = params or {}
        
        # Get processing parameters
        focus_point = params.get("focus_point", "")
        explanation = params.get("explanation", "")
        prompts = params.get("prompts", [])
        model = params.get("model", self.default_model)
        temperature = params.get("temperature", self.default_temperature)
        max_tokens = params.get("max_tokens", self.default_max_tokens)
        
        # Get content and metadata
        content = data_item.content
        metadata = data_item.metadata.copy()
        
        # Create prompts if not provided
        if not prompts:
            system_prompt = f"You are an expert in extracting information about {focus_point}."
            user_prompt = f"Extract key information about {focus_point} from the following text. {explanation}\n\n{content}"
            prompts = [system_prompt, user_prompt, model]
        
        # Process the content using LLM
        try:
            logger.info(f"Processing content with focus point: {focus_point}")
            
            # Call the LLM
            result = openai_llm(
                prompts[0],  # system prompt
                prompts[1],  # user prompt
                model=prompts[2] if len(prompts) > 2 else model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract the processed content
            processed_content = result.get("content", "")
            
            # Create processing info
            processing_info = {
                "focus_point": focus_point,
                "explanation": explanation,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "tokens_used": result.get("usage", {}).get("total_tokens", 0)
            }
            
            # Update metadata
            metadata.update({
                "processed_at": datetime.now().isoformat(),
                "processor": self.name,
                "focus_point": focus_point
            })
            
            # Create processed data
            processed_data = ProcessedData(
                original_item=data_item,
                processed_content=processed_content,
                metadata=metadata,
                processing_info=processing_info
            )
            
            logger.info(f"Successfully processed content, extracted {len(processed_content)} characters")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error processing content: {e}")
            
            # Create error processed data
            processed_data = ProcessedData(
                original_item=data_item,
                processed_content=f"Error processing content: {str(e)}",
                metadata=metadata,
                processing_info={
                    "error": str(e),
                    "focus_point": focus_point,
                    "explanation": explanation
                }
            )
            
            return processed_data

