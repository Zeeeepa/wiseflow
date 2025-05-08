"""
Multimodal Knowledge Integration Module for Wiseflow.

This module provides functionality for integrating multimodal analysis results
into the knowledge graph, enhancing entity relationships with visual information.
"""

import os
import json
import asyncio
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
import uuid

from ..utils.general_utils import get_logger
from ..utils.pb_api import PbTalker
from ..llms.openai_wrapper import openai_llm as llm
from .entity_extraction import extract_entities, extract_relationships
from .entity_linking import link_entities, merge_entities
from ..knowledge.graph import KnowledgeGraphBuilder

# Set up logging
project_dir = os.environ.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)
integration_logger = get_logger('multimodal_knowledge_integration', project_dir)
pb = PbTalker(integration_logger)

# Get the model from environment variables
model = os.environ.get("PRIMARY_MODEL", "")
if not model:
    raise ValueError("PRIMARY_MODEL not set, please set it in environment variables or edit core/.env")

# Initialize knowledge graph builder
knowledge_graph_builder = KnowledgeGraphBuilder(name="Multimodal Knowledge Graph")

async def integrate_multimodal_analysis_with_knowledge_graph(focus_id: str, max_retries: int = 3) -> Dict[str, Any]:
    """
    Integrate multimodal analysis results into the knowledge graph.
    
    Args:
        focus_id: ID of the focus point
        max_retries: Maximum number of retries for failed operations
        
    Returns:
        Dictionary with integration results
    """
    integration_logger.info(f"Integrating multimodal analysis for focus {focus_id} into knowledge graph")
    
    try:
        # Get all info items for this focus point
        info_items = pb.read(collection_name='infos', filter=f"tag='{focus_id}'")
        
        if not info_items:
            integration_logger.warning(f"No info items found for focus {focus_id}")
            return {"success": False, "error": "No info items found", "focus_id": focus_id}
        
        integration_logger.info(f"Found {len(info_items)} info items for focus {focus_id}")
        
        # Process each info item
        all_entities = []
        all_relationships = []
        
        for item in info_items:
            try:
                # Check if the item has image analysis results
                if "image_analysis" in item and item["image_analysis"]:
                    # Process the item with image analysis
                    result = await process_item_with_images(item)
                    
                    if result and "entities" in result:
                        all_entities.extend(result["entities"])
                    
                    if result and "relationships" in result:
                        all_relationships.extend(result["relationships"])
                else:
                    # Process text-only item
                    if "content" in item and item["content"]:
                        # Extract entities from text
                        entities_data = await extract_entities(item["content"])
                        
                        # Convert to Entity objects
                        entities = []
                        for entity_data in entities_data:
                            entity = Entity(
                                name=entity_data["name"],
                                entity_type=entity_data["type"],
                                sources=[item["id"]],
                                metadata={
                                    "confidence": entity_data.get("confidence", 0.5),
                                    "source_type": "text",
                                    "focus_id": focus_id
                                }
                            )
                            entities.append(entity)
                        
                        all_entities.extend(entities)
                        
                        # Extract relationships between entities
                        if len(entities) > 1:
                            relationships_data = await extract_relationships(item["content"], entities_data)
                            
                            # Convert to Relationship objects
                            for rel_data in relationships_data:
                                # Find the source and target entities
                                source_entity = next((e for e in entities if e.name == rel_data["source"]), None)
                                target_entity = next((e for e in entities if e.name == rel_data["target"]), None)
                                
                                if source_entity and target_entity:
                                    relationship = Relationship(
                                        source_id=source_entity.entity_id,
                                        target_id=target_entity.entity_id,
                                        relationship_type=rel_data["type"],
                                        metadata={
                                            "confidence": rel_data.get("confidence", 0.5),
                                            "source_type": "text",
                                            "focus_id": focus_id
                                        }
                                    )
                                    all_relationships.append(relationship)
            except Exception as e:
                integration_logger.error(f"Error processing item {item.get('id', 'unknown')}: {str(e)}")
                integration_logger.error(traceback.format_exc())
                continue
        
        # Link entities that refer to the same real-world entity
        if all_entities:
            linked_entities = await link_entities(all_entities)
            
            # Merge linked entities
            merged_entities = []
            for canonical_id, entity_group in linked_entities.items():
                if len(entity_group) > 1:
                    # Merge the entities in this group
                    merged_entity = merge_entities(entity_group)
                    merged_entities.append(merged_entity)
                    
                    # Update relationships to use the merged entity
                    for relationship in all_relationships:
                        for entity in entity_group:
                            if relationship.source_id == entity.entity_id:
                                relationship.source_id = merged_entity.entity_id
                            if relationship.target_id == entity.entity_id:
                                relationship.target_id = merged_entity.entity_id
                else:
                    # Keep the single entity as is
                    merged_entities.append(entity_group[0])
            
            # Replace the original entities with the merged ones
            all_entities = merged_entities
        
        # Build the knowledge graph
        knowledge_graph = await knowledge_graph_builder.build_knowledge_graph(all_entities, all_relationships)
        
        # Validate the knowledge graph
        validation_results = knowledge_graph_builder.validate_knowledge_graph()
        
        # Store the knowledge graph in the database
        graph_data = knowledge_graph.to_dict()
        graph_data["focus_id"] = focus_id
        graph_data["created_at"] = datetime.now().isoformat()
        
        # Check if a knowledge graph already exists for this focus
        existing_graph = pb.read(collection_name='knowledge_graphs', filter=f"focus_id='{focus_id}'")
        
        if existing_graph:
            # Update the existing graph
            pb.update(collection_name='knowledge_graphs', record_id=existing_graph[0]["id"], data=graph_data)
            graph_id = existing_graph[0]["id"]
        else:
            # Create a new graph
            result = pb.create(collection_name='knowledge_graphs', data=graph_data)
            graph_id = result["id"]
        
        integration_logger.info(f"Knowledge graph integration complete for focus {focus_id}")
        
        return {
            "success": True,
            "focus_id": focus_id,
            "graph_id": graph_id,
            "entity_count": len(all_entities),
            "relationship_count": len(all_relationships),
            "validation": validation_results
        }
    except Exception as e:
        integration_logger.error(f"Error integrating multimodal analysis with knowledge graph: {str(e)}")
        integration_logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "error": str(e),
            "focus_id": focus_id
        }

def extract_entities_from_multimodal(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract entities from multimodal analysis results.
    
    Args:
        item: Item with multimodal analysis
        
    Returns:
        List of extracted entities
    """
    entities = []
    
    # Get multimodal analysis
    multimodal_analysis = item.get("multimodal_analysis", {})
    
    # Extract entities from key_entities field
    key_entities = multimodal_analysis.get("key_entities", [])
    for entity in key_entities:
        entity_id = str(uuid.uuid4())
        entities.append({
            "entity_id": entity_id,
            "name": entity.get("name", ""),
            "entity_type": entity.get("type", "unknown"),
            "confidence": entity.get("confidence", 0.5),
            "source": entity.get("source", "multimodal"),
            "metadata": {
                "item_id": item.get("id", ""),
                "url": item.get("url", ""),
                "multimodal": True
            },
            "sources": ["multimodal_analysis"]
        })
    
    # Extract entities from integrated_summary field
    integrated_summary = multimodal_analysis.get("integrated_summary", "")
    if integrated_summary:
        # Use entity extraction to find additional entities
        from .entity_extraction import extract_entities
        additional_entities = extract_entities(integrated_summary)
        
        # Convert to our entity format
        for entity in additional_entities:
            entity_id = str(uuid.uuid4())
            entities.append({
                "entity_id": entity_id,
                "name": entity.get("name", ""),
                "entity_type": entity.get("type", "unknown"),
                "confidence": entity.get("confidence", 0.5),
                "source": "integrated_summary",
                "metadata": {
                    "item_id": item.get("id", ""),
                    "url": item.get("url", ""),
                    "multimodal": True,
                    "description": entity.get("description", "")
                },
                "sources": ["multimodal_analysis"]
            })
    
    return entities

def extract_relationships_from_multimodal(item: Dict[str, Any], entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract relationships from multimodal analysis results.
    
    Args:
        item: Item with multimodal analysis
        entities: List of extracted entities
        
    Returns:
        List of extracted relationships
    """
    relationships = []
    
    # Get multimodal analysis
    multimodal_analysis = item.get("multimodal_analysis", {})
    
    # Extract relationships from integrated_summary field
    integrated_summary = multimodal_analysis.get("integrated_summary", "")
    if integrated_summary and entities:
        # Use relationship extraction to find relationships
        from .entity_extraction import extract_relationships
        extracted_relationships = extract_relationships(integrated_summary, entities)
        
        # Convert to our relationship format
        for rel in extracted_relationships:
            # Find source and target entities
            source_entity = None
            target_entity = None
            
            for entity in entities:
                if entity.get("name", "").lower() == rel.get("source", "").lower():
                    source_entity = entity
                if entity.get("name", "").lower() == rel.get("target", "").lower():
                    target_entity = entity
            
            if source_entity and target_entity:
                relationship_id = str(uuid.uuid4())
                relationships.append({
                    "relationship_id": relationship_id,
                    "source_id": source_entity.get("entity_id", ""),
                    "target_id": target_entity.get("entity_id", ""),
                    "relationship_type": rel.get("type", "related_to"),
                    "confidence": rel.get("confidence", 0.5),
                    "metadata": {
                        "item_id": item.get("id", ""),
                        "url": item.get("url", ""),
                        "multimodal": True,
                        "description": rel.get("description", "")
                    }
                })
    
    # Infer additional relationships based on context
    additional_relationships = infer_relationships_from_context(multimodal_analysis, entities)
    relationships.extend(additional_relationships)
    
    return relationships

def infer_relationships_from_context(multimodal_analysis: Dict[str, Any], entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Infer additional relationships based on multimodal context.
    
    Args:
        multimodal_analysis: Multimodal analysis results
        entities: List of extracted entities
        
    Returns:
        List of inferred relationships
    """
    relationships = []
    
    # Get additional context
    additional_context = multimodal_analysis.get("additional_context", "")
    if not additional_context or len(entities) < 2:
        return relationships
    
    # For entities that appear in the same image, create "appears_with" relationships
    entity_ids = [entity.get("entity_id", "") for entity in entities]
    
    for i, source_id in enumerate(entity_ids):
        for target_id in entity_ids[i+1:]:
            if source_id and target_id:
                relationship_id = str(uuid.uuid4())
                relationships.append({
                    "relationship_id": relationship_id,
                    "source_id": source_id,
                    "target_id": target_id,
                    "relationship_type": "appears_with",
                    "confidence": 0.7,
                    "metadata": {
                        "multimodal": True,
                        "inferred": True,
                        "context": "Entities appear in the same visual context"
                    }
                })
    
    return relationships

async def process_all_focuses_for_multimodal_integration() -> List[Dict[str, Any]]:
    """
    Process all active focus points for multimodal knowledge integration.
    
    Returns:
        List of processing results for each focus point
    """
    integration_logger.info("Processing all active focus points for multimodal knowledge integration")
    
    # Get all active focus points
    active_focuses = pb.read(collection_name='focus_point', filter="activated=true")
    
    if not active_focuses:
        integration_logger.warning("No active focus points found")
        return []
    
    integration_logger.info(f"Found {len(active_focuses)} active focus points")
    
    # Process each focus point
    results = []
    for focus in active_focuses:
        try:
            result = await integrate_multimodal_analysis_with_knowledge_graph(focus["id"])
            results.append(result)
        except Exception as e:
            integration_logger.error(f"Error processing focus ID {focus['id']}: {e}")
            results.append({
                "focus_id": focus["id"],
                "error": str(e)
            })
    
    return results

async def process_item_with_images(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process an item with image analysis results.
    
    Args:
        item: Item with image analysis
        
    Returns:
        Dictionary with processed entities and relationships
    """
    integration_logger.info(f"Processing item {item.get('id', 'unknown')} with image analysis")
    
    # Extract entities from image analysis
    entities = extract_entities_from_image(item)
    
    # Extract relationships from image analysis
    relationships = extract_relationships_from_image(item, entities)
    
    return {
        "entities": entities,
        "relationships": relationships
    }

def extract_entities_from_image(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract entities from image analysis results.
    
    Args:
        item: Item with image analysis
        
    Returns:
        List of extracted entities
    """
    entities = []
    
    # Get image analysis
    image_analysis = item.get("image_analysis", {})
    
    # Extract entities from key_entities field
    key_entities = image_analysis.get("key_entities", [])
    for entity in key_entities:
        entity_id = str(uuid.uuid4())
        entities.append({
            "entity_id": entity_id,
            "name": entity.get("name", ""),
            "entity_type": entity.get("type", "unknown"),
            "confidence": entity.get("confidence", 0.5),
            "source": entity.get("source", "image"),
            "metadata": {
                "item_id": item.get("id", ""),
                "url": item.get("url", ""),
                "image": True
            },
            "sources": ["image_analysis"]
        })
    
    # Extract entities from integrated_summary field
    integrated_summary = image_analysis.get("integrated_summary", "")
    if integrated_summary:
        # Use entity extraction to find additional entities
        from .entity_extraction import extract_entities
        additional_entities = extract_entities(integrated_summary)
        
        # Convert to our entity format
        for entity in additional_entities:
            entity_id = str(uuid.uuid4())
            entities.append({
                "entity_id": entity_id,
                "name": entity.get("name", ""),
                "entity_type": entity.get("type", "unknown"),
                "confidence": entity.get("confidence", 0.5),
                "source": "integrated_summary",
                "metadata": {
                    "item_id": item.get("id", ""),
                    "url": item.get("url", ""),
                    "image": True,
                    "description": entity.get("description", "")
                },
                "sources": ["image_analysis"]
            })
    
    return entities

def extract_relationships_from_image(item: Dict[str, Any], entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract relationships from image analysis results.
    
    Args:
        item: Item with image analysis
        entities: List of extracted entities
        
    Returns:
        List of extracted relationships
    """
    relationships = []
    
    # Get image analysis
    image_analysis = item.get("image_analysis", {})
    
    # Extract relationships from integrated_summary field
    integrated_summary = image_analysis.get("integrated_summary", "")
    if integrated_summary and entities:
        # Use relationship extraction to find relationships
        from .entity_extraction import extract_relationships
        extracted_relationships = extract_relationships(integrated_summary, entities)
        
        # Convert to our relationship format
        for rel in extracted_relationships:
            # Find source and target entities
            source_entity = None
            target_entity = None
            
            for entity in entities:
                if entity.get("name", "").lower() == rel.get("source", "").lower():
                    source_entity = entity
                if entity.get("name", "").lower() == rel.get("target", "").lower():
                    target_entity = entity
            
            if source_entity and target_entity:
                relationship_id = str(uuid.uuid4())
                relationships.append({
                    "relationship_id": relationship_id,
                    "source_id": source_entity.get("entity_id", ""),
                    "target_id": target_entity.get("entity_id", ""),
                    "relationship_type": rel.get("type", "related_to"),
                    "confidence": rel.get("confidence", 0.5),
                    "metadata": {
                        "item_id": item.get("id", ""),
                        "url": item.get("url", ""),
                        "image": True,
                        "description": rel.get("description", "")
                    }
                })
    
    # Infer additional relationships based on context
    additional_relationships = infer_relationships_from_context(image_analysis, entities)
    relationships.extend(additional_relationships)
    
    return relationships
