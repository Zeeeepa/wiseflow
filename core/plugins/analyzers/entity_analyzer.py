"""
Entity Analyzer Plugin for Wiseflow.

This plugin analyzes processed data to extract entities and their relationships.
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

from core.plugins.analyzers import AnalyzerBase, AnalysisResult
from core.plugins.processors import ProcessedData
from core.plugins.utils import TextExtractor
from core.llms.litellm_wrapper import litellm_llm

logger = logging.getLogger(__name__)

class EntityAnalyzer(AnalyzerBase):
    """Analyzer for extracting entities from processed data."""
    
    name: str = "entity_analyzer"
    description: str = "Extracts entities and their relationships from processed data"
    analyzer_type: str = "entity"
    
    # Default prompts for entity extraction
    DEFAULT_ENTITY_PROMPT = """
    You are an expert in entity extraction. Extract all named entities from the following text.
    For each entity, provide:
    1. The entity name
    2. The entity type (person, organization, location, product, technology, event, date, etc.)
    3. A brief description based on the context
    
    Format your response as a JSON array of objects with the following structure:
    [
      {
        "name": "entity name",
        "type": "entity type",
        "description": "brief description"
      }
    ]
    
    Text to analyze:
    {text}
    """
    
    DEFAULT_RELATIONSHIP_PROMPT = """
    You are an expert in relationship extraction. Identify relationships between the entities in the text.
    For each relationship, provide:
    1. The source entity name
    2. The target entity name
    3. The relationship type (e.g., "works for", "located in", "developed by", etc.)
    4. A brief description of the relationship
    
    Format your response as a JSON array of objects with the following structure:
    [
      {
        "source": "source entity name",
        "target": "target entity name",
        "type": "relationship type",
        "description": "brief description"
      }
    ]
    
    Text to analyze:
    {text}
    
    Entities already identified:
    {entities}
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the entity analyzer."""
        super().__init__(config)
        self.entity_prompt = self.config.get("entity_prompt", self.DEFAULT_ENTITY_PROMPT)
        self.relationship_prompt = self.config.get("relationship_prompt", self.DEFAULT_RELATIONSHIP_PROMPT)
        self.model = self.config.get("model", "gpt-3.5-turbo")
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_min_wait = self.config.get("retry_min_wait", 4)
        self.retry_max_wait = self.config.get("retry_max_wait", 10)
        
    def analyze(self, processed_data: ProcessedData, params: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """Analyze processed data to extract entities and relationships."""
        params = params or {}
        
        if not processed_data or not processed_data.processed_content:
            logger.warning("No processed content to analyze")
            return AnalysisResult(
                processed_data=processed_data,
                analysis_content={"entities": [], "relationships": []},
                metadata={"error": "No processed content to analyze"}
            )
        
        try:
            # Extract text from processed content
            text = TextExtractor.extract_text(processed_data.processed_content)
            
            if not text:
                logger.warning("No text content found in processed data")
                return AnalysisResult(
                    processed_data=processed_data,
                    analysis_content={"entities": [], "relationships": []},
                    metadata={"error": "No text content found in processed data"}
                )
            
            # Extract entities
            entities = self._extract_entities(text)
            
            # Extract relationships if entities were found
            relationships = []
            if entities:
                relationships = self._extract_relationships(text, entities)
            
            # Create analysis result
            analysis_content = {
                "entities": entities,
                "relationships": relationships
            }
            
            metadata = {
                "entity_count": len(entities),
                "relationship_count": len(relationships),
                "source_type": processed_data.metadata.get("source_type", "unknown"),
                "analysis_time": datetime.now().isoformat()
            }
            
            return AnalysisResult(
                processed_data=processed_data,
                analysis_content=analysis_content,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error analyzing data: {e}")
            return AnalysisResult(
                processed_data=processed_data,
                analysis_content={"entities": [], "relationships": []},
                metadata={"error": str(e)}
            )
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities from text using LLM with retry logic."""
        try:
            # Prepare the prompt
            prompt = self.entity_prompt.format(text=text)
            
            # Call the LLM
            messages = [
                {"role": "system", "content": "You are an expert in entity extraction."},
                {"role": "user", "content": prompt}
            ]
            
            response = litellm_llm(messages, self.model)
            
            # Parse the response
            return self._parse_json_response(response)
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            raise  # Let retry handle the error
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _extract_relationships(self, text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract relationships between entities using LLM with retry logic."""
        try:
            # Prepare the prompt
            entities_str = json.dumps(entities, indent=2)
            prompt = self.relationship_prompt.format(text=text, entities=entities_str)
            
            # Call the LLM
            messages = [
                {"role": "system", "content": "You are an expert in relationship extraction."},
                {"role": "user", "content": prompt}
            ]
            
            response = litellm_llm(messages, self.model)
            
            # Parse the response
            return self._parse_json_response(response)
            
        except Exception as e:
            logger.error(f"Error extracting relationships: {e}")
            raise  # Let retry handle the error
    
    def _parse_json_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse JSON response from LLM."""
        try:
            # Extract JSON from the response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            
            # If no JSON array found, try to parse the entire response
            return json.loads(response)
            
        except Exception as e:
            logger.error(f"Error parsing JSON response: {e}")
            logger.debug(f"Response: {response}")
            return []
