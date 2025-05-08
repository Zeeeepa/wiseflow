"""
Text processor plugin for Wiseflow.

This plugin processes text data using LLM-based extraction.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import json
import asyncio
import re
import traceback
from datetime import datetime
import gc

from core.plugins.processors import ProcessorBase, ProcessedData
from core.connectors import DataItem
from core.llms.litellm_wrapper import litellm_llm
from core.event_system import EventType, publish_sync, create_resource_event

logger = logging.getLogger(__name__)

class TextProcessor(ProcessorBase):
    """Processor for text data."""
    
    name: str = "text_processor"
    description: str = "Processes text data using LLM-based extraction"
    processor_type: str = "text"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the text processor."""
        super().__init__(config or {})
        self.model = self.config.get("model", "gpt-3.5-turbo")
        self.max_chunk_size = self.config.get("max_chunk_size", 8000)
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 2)
        self.memory_threshold = self.config.get("memory_threshold", 0.9)  # 90% memory usage threshold
        
    def process(self, data_item: DataItem, params: Optional[Dict[str, Any]] = None) -> ProcessedData:
        """Process a text data item."""
        params = params or {}
        
        # Extract focus point information
        focus_point = params.get("focus_point", "")
        explanation = params.get("explanation", "")
        prompts = params.get("prompts", [])
        
        if not focus_point:
            logger.warning("No focus point provided for text processing")
            return ProcessedData(
                original_item=data_item,
                processed_content=[],
                metadata={"error": "No focus point provided"}
            )
        
        if not data_item.content:
            logger.warning(f"No content in data item {data_item.source_id}")
            return ProcessedData(
                original_item=data_item,
                processed_content=[],
                metadata={"error": "No content in data item"}
            )
        
        # Process the text using LLM
        try:
            # Run the processing in an event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            processed_content = loop.run_until_complete(
                self._process_with_llm(
                    data_item.content, 
                    focus_point, 
                    explanation, 
                    prompts,
                    data_item.metadata.get("author", ""),
                    data_item.metadata.get("publish_date", "")
                )
            )
            loop.close()
            
            return ProcessedData(
                original_item=data_item,
                processed_content=processed_content,
                metadata={
                    "focus_point": focus_point,
                    "explanation": explanation,
                    "source_type": data_item.content_type,
                    "processing_time": datetime.now().isoformat()
                }
            )
        except Exception as e:
            error_msg = f"Error processing text data: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return ProcessedData(
                original_item=data_item,
                processed_content=[],
                metadata={
                    "error": error_msg,
                    "error_type": type(e).__name__,
                    "focus_point": focus_point
                }
            )
    
    async def _process_with_llm(self, content: str, focus_point: str, explanation: str, prompts: List[str], author: str, publish_date: str) -> List[Dict[str, Any]]:
        """Process text content with LLM."""
        if not prompts or len(prompts) < 3:
            logger.warning("Insufficient prompts provided")
            return []
        
        system_prompt, user_prompt, model = prompts
        
        # Prepare the content
        # Split content into chunks if it's too long
        chunks = self._split_content(content, self.max_chunk_size)
        
        results = []
        for i, chunk in enumerate(chunks):
            try:
                # Check memory usage before processing
                if self._check_memory_usage():
                    # Force garbage collection to free memory
                    gc.collect()
                
                # Retry logic for LLM calls
                retry_count = 0
                success = False
                last_error = None
                
                while retry_count < self.max_retries and not success:
                    try:
                        messages = [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"{chunk}\n\n{user_prompt}"}
                        ]
                        
                        response = litellm_llm(messages, model or self.model)
                        
                        # Parse the response
                        parsed_results = self._parse_llm_response(response, author, publish_date)
                        results.extend(parsed_results)
                        
                        success = True
                        logger.info(f"Successfully processed chunk {i+1}/{len(chunks)}")
                        
                    except Exception as e:
                        retry_count += 1
                        last_error = e
                        logger.warning(f"Error processing chunk {i+1}/{len(chunks)} with LLM (attempt {retry_count}/{self.max_retries}): {e}")
                        
                        if retry_count < self.max_retries:
                            # Exponential backoff
                            delay = self.retry_delay * (2 ** (retry_count - 1))
                            logger.info(f"Retrying in {delay:.2f} seconds...")
                            await asyncio.sleep(delay)
                
                if not success:
                    logger.error(f"Failed to process chunk {i+1}/{len(chunks)} after {self.max_retries} attempts: {last_error}")
                    # Add error information to results
                    results.append({
                        "content": f"Error processing content: {str(last_error)}",
                        "author": author,
                        "publish_date": publish_date,
                        "type": "error",
                        "error": str(last_error)
                    })
                
            except Exception as e:
                logger.error(f"Error processing chunk {i+1}/{len(chunks)}: {e}")
                logger.error(traceback.format_exc())
                # Add error information to results
                results.append({
                    "content": f"Error processing content: {str(e)}",
                    "author": author,
                    "publish_date": publish_date,
                    "type": "error",
                    "error": str(e)
                })
        
        return results
    
    def _check_memory_usage(self) -> bool:
        """
        Check if memory usage is above threshold.
        
        Returns:
            bool: True if memory usage is above threshold, False otherwise
        """
        try:
            import psutil
            memory_percent = psutil.virtual_memory().percent / 100.0
            
            if memory_percent > self.memory_threshold:
                logger.warning(f"Memory usage is high: {memory_percent*100:.1f}% (threshold: {self.memory_threshold*100:.1f}%)")
                
                # Publish resource warning event
                try:
                    event = create_resource_event(
                        EventType.RESOURCE_WARNING,
                        "memory",
                        memory_percent * 100,
                        self.memory_threshold * 100
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish resource warning event: {e}")
                
                return True
            
            return False
        except ImportError:
            logger.warning("psutil not available, cannot check memory usage")
            return False
        except Exception as e:
            logger.warning(f"Error checking memory usage: {e}")
            return False
    
    def _split_content(self, content: str, max_size: int) -> List[str]:
        """Split content into chunks of maximum size."""
        if len(content) <= max_size:
            return [content]
        
        # Split by paragraphs
        paragraphs = content.split("\n\n")
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) + 2 <= max_size:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If a single paragraph is too long, split it further
                if len(paragraph) > max_size:
                    # Split by sentences
                    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                    current_chunk = ""
                    
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) + 1 <= max_size:
                            if current_chunk:
                                current_chunk += " "
                            current_chunk += sentence
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            
                            # If a single sentence is too long, just truncate it
                            if len(sentence) > max_size:
                                for i in range(0, len(sentence), max_size):
                                    chunks.append(sentence[i:i+max_size])
                            else:
                                current_chunk = sentence
                else:
                    current_chunk = paragraph
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # Log chunk information
        logger.info(f"Split content into {len(chunks)} chunks (max size: {max_size})")
        
        return chunks
    
    def _parse_llm_response(self, response: str, author: str, publish_date: str) -> List[Dict[str, Any]]:
        """Parse the LLM response into structured data."""
        try:
            # Try to parse as JSON
            if response.startswith("```json") and response.endswith("```"):
                json_str = response[7:-3].strip()
                data = json.loads(json_str)
                if isinstance(data, list):
                    # Add author and publish_date to each item if not present
                    for item in data:
                        if isinstance(item, dict):
                            if "author" not in item:
                                item["author"] = author
                            if "publish_date" not in item:
                                item["publish_date"] = publish_date
                            if "type" not in item:
                                item["type"] = "text"
                    return data
                elif isinstance(data, dict):
                    # Add author and publish_date if not present
                    if "author" not in data:
                        data["author"] = author
                    if "publish_date" not in data:
                        data["publish_date"] = publish_date
                    if "type" not in data:
                        data["type"] = "text"
                    return [data]
            
            # Try to extract JSON from the response
            json_pattern = r'```json\s*([\s\S]*?)\s*```'
            matches = re.findall(json_pattern, response)
            if matches:
                for match in matches:
                    try:
                        data = json.loads(match)
                        if isinstance(data, list):
                            # Add author and publish_date to each item if not present
                            for item in data:
                                if isinstance(item, dict):
                                    if "author" not in item:
                                        item["author"] = author
                                    if "publish_date" not in item:
                                        item["publish_date"] = publish_date
                                    if "type" not in item:
                                        item["type"] = "text"
                            return data
                        elif isinstance(data, dict):
                            # Add author and publish_date if not present
                            if "author" not in data:
                                data["author"] = author
                            if "publish_date" not in data:
                                data["publish_date"] = publish_date
                            if "type" not in data:
                                data["type"] = "text"
                            return [data]
                    except json.JSONDecodeError:
                        continue
            
            # If we can't parse as JSON, create a simple structure
            return [{
                "content": response,
                "author": author,
                "publish_date": publish_date,
                "type": "text"
            }]
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            logger.error(traceback.format_exc())
            return [{
                "content": response,
                "author": author,
                "publish_date": publish_date,
                "type": "text",
                "parsing_error": str(e)
            }]
