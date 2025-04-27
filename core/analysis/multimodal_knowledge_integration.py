"""
Multimodal Knowledge Integration Module for Wiseflow.

This module provides functionality for integrating multimodal analysis results
into the knowledge graph, enhancing entity relationships with visual information.
"""

import os
import json
import asyncio
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

async def integrate_multimodal_analysis_with_knowledge_graph(focus_id: str) -> Dict[str, Any]:
    """
    Integrate multimodal analysis results into the knowledge graph.
    
    Args:
        focus_id: ID of the focus point
        
    Returns:
        Dictionary with integration results
    """
    integration_logger.info(f"Integrating multimodal analysis for focus {focus_id} into knowledge graph")
    
    # Get all info items for this focus point
    info_items = pb.read(collection_name='infos', filter=f"tag='{focus_id}'")
    
    if not info_items:
        integration_logger.warning(f"No information items found for focus ID {focus_id}")
        return {"error": f"No information items found for focus ID {focus_id}"}
    
    # Filter items that have multimodal analysis
    items_with_multimodal = []
    for item in info_items:
        if item.get("multimodal_analysis"):
            try:
                if isinstance(item["multimodal_analysis"], str):
                    item["multimodal_analysis"] = json.loads(item["multimodal_analysis"])
                items_with_multimodal.append(item)
            except Exception as e:
                integration_logger.error(f"Error parsing multimodal analysis for item {item.get('id')}: {e}")
    
    if not items_with_multimodal:
        integration_logger.warning(f"No items with multimodal analysis found for focus ID {focus_id}")
        # Process items to generate multimodal analysis
        from .multimodal_analysis import process_focus_for_multimodal_analysis
        await process_focus_for_multimodal_analysis(focus_id)
        
        # Try again to get items with multimodal analysis
        info_items = pb.read(collection_name='infos', filter=f"tag='{focus_id}'")
        for item in info_items:
            if item.get("multimodal_analysis"):
                try:
                    if isinstance(item["multimodal_analysis"], str):
                        item["multimodal_analysis"] = json.loads(item["multimodal_analysis"])
                    items_with_multimodal.append(item)
                except Exception as e:
                    integration_logger.error(f"Error parsing multimodal analysis for item {item.get('id')}: {e}")
    
    if not items_with_multimodal:
        integration_logger.warning(f"Still no items with multimodal analysis found for focus ID {focus_id}")
        return {"error": "No items with multimodal analysis available"}
    
    # Extract entities and relationships from multimodal analysis
    all_entities = []
    all_relationships = []
    
    for item in items_with_multimodal:
        # Extract entities from multimodal analysis
        multimodal_entities = extract_entities_from_multimodal(item)
        all_entities.extend(multimodal_entities)
        
        # Extract relationships from multimodal analysis
        multimodal_relationships = extract_relationships_from_multimodal(item, multimodal_entities)
        all_relationships.extend(multimodal_relationships)
    
    # Link entities to create a unified view
    linked_entities = await link_entities(all_entities)
    
    # Merge linked entities
    merged_entities = []
    for entity_group in linked_entities.values():
        if len(entity_group) > 1:
            merged_entity = await merge_entities(entity_group)
            merged_entities.append(merged_entity)
        else:
            merged_entities.extend(entity_group)
    
    # Build knowledge graph with merged entities and relationships
    knowledge_graph = await knowledge_graph_builder.build_knowledge_graph(merged_entities, all_relationships)
    
    # Save the knowledge graph
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    output_path = os.path.join(project_dir, f"multimodal_knowledge_graph_{focus_id}_{timestamp}.json")
    knowledge_graph_builder.save_patterns(output_path)
    
    # Generate visualization
    visualization_path = os.path.join(project_dir, f"multimodal_knowledge_graph_{focus_id}_{timestamp}.png")
    knowledge_graph_builder.visualize_knowledge_graph(output_path=visualization_path)
    
    # Save to database
    try:
        graph_data = knowledge_graph.to_dict()
        
        # Check if there's an existing knowledge graph for this focus
        existing_graph = pb.read(collection_name='knowledge_graphs', filter=f"focus_id='{focus_id}'")
        
        if existing_graph:
            # Update existing graph
            pb.update('knowledge_graphs', existing_graph[0]['id'], {
                'graph_data': json.dumps(graph_data),
                'entity_count': len(merged_entities),
                'relationship_count': len(all_relationships),
                'multimodal_count': len(items_with_multimodal),
                'visualization_path': visualization_path,
                'updated_at': datetime.now().isoformat()
            })
            graph_id = existing_graph[0]['id']
        else:
            # Create new graph
            graph_record = {
                'focus_id': focus_id,
                'graph_data': json.dumps(graph_data),
                'entity_count': len(merged_entities),
                'relationship_count': len(all_relationships),
                'multimodal_count': len(items_with_multimodal),
                'visualization_path': visualization_path,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            graph_id = pb.add('knowledge_graphs', graph_record)
        
        integration_logger.info(f"Knowledge graph saved to database with ID {graph_id}")
    except Exception as e:
        integration_logger.error(f"Error saving knowledge graph to database: {e}")
    
    # Return results
    return {
        'focus_id': focus_id,
        'entity_count': len(merged_entities),
        'relationship_count': len(all_relationships),
        'multimodal_count': len(items_with_multimodal),
        'visualization_path': visualization_path,
        'output_path': output_path,
        'timestamp': datetime.now().isoformat()
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
