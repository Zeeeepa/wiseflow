"""
Entity analyzer plugin for Wiseflow.

This module provides an analyzer for extracting entities from processed data.
"""

import logging
import json
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from core.plugins.analyzers import AnalyzerBase, AnalysisResult
from core.plugins.processors import ProcessedData
from core.llms.openai_wrapper import openai_llm
from core.analysis import Entity, Relationship

logger = logging.getLogger(__name__)

class EntityAnalyzer(AnalyzerBase):
    """Analyzer for extracting entities from processed data."""
    
    name: str = "entity_analyzer"
    description: str = "Analyzer for extracting entities from processed data"
    analyzer_type: str = "entity"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the entity analyzer."""
        super().__init__(config)
        self.default_model = self.config.get("default_model", "gpt-3.5-turbo")
        self.default_temperature = self.config.get("default_temperature", 0.2)
        self.default_max_tokens = self.config.get("default_max_tokens", 1500)
        self.entity_types = self.config.get("entity_types", [
            "person", "organization", "location", "product", "technology", 
            "event", "concept", "date", "number", "other"
        ])
        
    def initialize(self) -> bool:
        """Initialize the entity analyzer."""
        try:
            logger.info(f"Initialized entity analyzer with model: {self.default_model}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize entity analyzer: {e}")
            return False
    
    def analyze(self, processed_data: ProcessedData, params: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Analyze processed data to extract entities.
        
        Args:
            processed_data: The processed data to analyze
            params: Optional analysis parameters
                - model: The model to use
                - temperature: The temperature to use
                - max_tokens: The maximum number of tokens to generate
                - entity_types: List of entity types to extract
                
        Returns:
            AnalysisResult: The analysis result containing extracted entities
        """
        params = params or {}
        
        # Get analysis parameters
        model = params.get("model", self.default_model)
        temperature = params.get("temperature", self.default_temperature)
        max_tokens = params.get("max_tokens", self.default_max_tokens)
        entity_types = params.get("entity_types", self.entity_types)
        
        # Get content and metadata
        content = processed_data.processed_content
        metadata = processed_data.metadata.copy()
        
        # Create prompts for entity extraction
        system_prompt = f"""You are an expert in entity extraction and analysis. 
Your task is to identify and extract entities from the provided text.
For each entity, provide:
1. The entity name
2. The entity type (from the following list: {', '.join(entity_types)})
3. Any relevant attributes or properties of the entity
4. Relationships to other entities (if any)

Format your response as a JSON array of objects with the following structure:
[
  {{
    "name": "entity name",
    "type": "entity type",
    "attributes": {{"attribute1": "value1", "attribute2": "value2"}},
    "relationships": [
      {{
        "target": "related entity name",
        "type": "relationship type",
        "description": "brief description of the relationship"
      }}
    ]
  }},
  ...
]
"""
        user_prompt = f"Extract entities from the following text:\n\n{content}"
        
        # Extract entities using LLM
        try:
            logger.info(f"Extracting entities from processed content")
            
            # Call the LLM
            result = openai_llm(
                system_prompt,
                user_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract the analysis content
            analysis_content = result.get("content", "")
            
            # Parse entities from the analysis content
            entities = []
            relationships = []
            
            try:
                # Extract JSON from the response
                json_str = analysis_content
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0].strip()
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0].strip()
                
                # Parse JSON
                entity_data = json.loads(json_str)
                
                # Create entities and relationships
                for item in entity_data:
                    entity_id = f"entity_{uuid.uuid4().hex[:8]}"
                    entity = Entity(
                        entity_id=entity_id,
                        name=item.get("name", ""),
                        entity_type=item.get("type", "unknown"),
                        sources=[processed_data.original_item.source_id if processed_data.original_item else "unknown"],
                        metadata=item.get("attributes", {})
                    )
                    entities.append(entity)
                    
                    # Create relationships
                    for rel in item.get("relationships", []):
                        relationship_id = f"rel_{uuid.uuid4().hex[:8]}"
                        relationship = Relationship(
                            relationship_id=relationship_id,
                            source_id=entity_id,
                            target_id=rel.get("target", ""),  # This is a name, not an ID
                            relationship_type=rel.get("type", "unknown"),
                            metadata={"description": rel.get("description", "")}
                        )
                        relationships.append(relationship)
            except Exception as e:
                logger.error(f"Error parsing entities from analysis content: {e}")
            
            # Create analysis info
            analysis_info = {
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                "entity_count": len(entities),
                "relationship_count": len(relationships)
            }
            
            # Update metadata
            metadata.update({
                "analyzed_at": datetime.now().isoformat(),
                "analyzer": self.name,
                "entity_types": entity_types
            })
            
            # Create analysis result
            analysis_result = AnalysisResult(
                processed_data=processed_data,
                analysis_content=analysis_content,
                metadata=metadata,
                analysis_info=analysis_info
            )
            
            # Add entities and relationships to the analysis result
            analysis_result.metadata["entities"] = [entity.to_dict() for entity in entities]
            analysis_result.metadata["relationships"] = [rel.to_dict() for rel in relationships]
            
            logger.info(f"Successfully extracted {len(entities)} entities and {len(relationships)} relationships")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing content: {e}")
            
            # Create error analysis result
            analysis_result = AnalysisResult(
                processed_data=processed_data,
                analysis_content=f"Error analyzing content: {str(e)}",
                metadata=metadata,
                analysis_info={
                    "error": str(e)
                }
            )
            
            return analysis_result

