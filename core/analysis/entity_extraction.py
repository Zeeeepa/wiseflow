"""
Entity extraction module for WiseFlow.

This module provides functions for extracting named entities from text
using LLM-based techniques.
"""
import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Set, Union
import re
from loguru import logger
from ..utils.general_utils import get_logger
from ..utils.pb_api import PbTalker
from ..llms.openai_wrapper import openai_llm as llm

project_dir = os.environ.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)
entity_extraction_logger = get_logger('entity_extraction', project_dir)
pb = PbTalker(entity_extraction_logger)

model = os.environ.get("PRIMARY_MODEL", "")
if not model:
    raise ValueError("PRIMARY_MODEL not set, please set it in environment variables or edit core/.env")

# Prompt for entity extraction
ENTITY_EXTRACTION_PROMPT = """You are an expert in entity extraction. Your task is to identify and extract named entities from the provided text.
Please identify the following types of entities:
- People (individuals, groups of people)
- Organizations (companies, institutions, agencies)
- Locations (countries, cities, geographical areas)
- Products (goods, services, brands)
- Technologies (technical terms, methodologies, frameworks)
- Events (conferences, meetings, incidents)
- Dates and Times
Text to analyze:
{text}
For each entity you identify, provide:
1. The entity name exactly as it appears in the text
2. The entity type (from the categories above)
3. A brief description or context (optional)
Format your response as a JSON array of objects with the following structure:
[
  {
    "name": "entity name",
    "type": "entity type",
    "description": "brief description or context"
  },
  ...
]
"""

async def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    Extract named entities from text.
    
    Args:
        text: The text to analyze
        
    Returns:
        List of dictionaries containing entity information
    """
    entity_extraction_logger.debug("Extracting entities from text")
    
    # Create the prompt
    prompt = ENTITY_EXTRACTION_PROMPT.format(text=text)
    
    # Generate the analysis
    result = await llm([
        {'role': 'system', 'content': 'You are an expert in entity extraction.'},
        {'role': 'user', 'content': prompt}
    ], model=model, temperature=0.1)
    
    # Parse the JSON response
    try:
        # Find JSON array in the response
        json_match = re.search(r'\[\s*\{.*\}\s*\]', result, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            entities = json.loads(json_str)
            entity_extraction_logger.debug(f"Extracted {len(entities)} entities")
            return entities
        else:
            entity_extraction_logger.warning("No valid JSON found in entity extraction response")
            return []
    except Exception as e:
        entity_extraction_logger.error(f"Error parsing entity extraction response: {e}")
        return []

async def extract_entities_batch(texts: List[str]) -> List[List[Dict[str, Any]]]:
    """
    Extract entities from multiple texts in parallel.
    
    Args:
        texts: List of texts to analyze
        
    Returns:
        List of lists of entity dictionaries, one list per input text
    """
    entity_extraction_logger.debug(f"Extracting entities from {len(texts)} texts in batch")
    
    # Create tasks for parallel execution
    tasks = [extract_entities(text) for text in texts]
    
    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks)
    
    entity_extraction_logger.debug(f"Batch entity extraction completed for {len(texts)} texts")
    return results

async def store_entities(entities: List[Dict[str, Any]], source_id: str, focus_id: str) -> List[str]:
    """
    Store extracted entities in the database.
    
    Args:
        entities: List of entity dictionaries
        source_id: ID of the source (e.g., document, webpage)
        focus_id: ID of the focus point
        
    Returns:
        List of entity IDs
    """
    entity_extraction_logger.debug(f"Storing {len(entities)} entities for source {source_id}")
    
    entity_ids = []
    for entity in entities:
        # Create entity record
        entity_record = {
            "name": entity.get("name", ""),
            "type": entity.get("type", ""),
            "description": entity.get("description", ""),
            "source_id": source_id,
            "focus_id": focus_id,
            "confidence": entity.get("confidence", 1.0)
        }
        
        # Store in database
        try:
            entity_id = pb.add(collection_name='entities', body=entity_record)
            if entity_id:
                entity_ids.append(entity_id)
        except Exception as e:
            entity_extraction_logger.error(f"Error storing entity {entity.get('name')}: {e}")
    
    entity_extraction_logger.debug(f"Stored {len(entity_ids)} entities successfully")
    return entity_ids
