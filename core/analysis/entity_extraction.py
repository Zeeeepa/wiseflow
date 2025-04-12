"""

Entity Extraction Module for WiseFlow.

This module provides functions for extracting named entities from collected data
using LLM-based techniques. It supports entity linking and knowledge graph construction.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Set, Union
import re
from collections import Counter, defaultdict
import networkx as nx
import matplotlib.pyplot as plt
from loguru import logger

from ..utils.general_utils import get_logger
from ..utils.pb_api import PbTalker
from ..llms.openai_wrapper import openai_llm as llm

project_dir = os.environ.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)

entity_logger = get_logger('entity_extraction', project_dir)
pb = PbTalker(entity_logger)

model = os.environ.get("PRIMARY_MODEL", "")
if not model:
    raise ValueError("PRIMARY_MODEL not set, please set it in environment variables or edit core/.env")


# Prompts for entity extraction
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
3. A confidence score between 0 and 1
4. A brief description or context based on the text

Format your response as a JSON array of objects with the following structure:
[
  {
    "name": "entity name",
    "type": "entity type",

    "confidence": 0.95,
    "description": "brief description or context"
  }
]

Only include entities that are clearly mentioned in the text. Aim for precision over recall.
"""

RELATIONSHIP_EXTRACTION_PROMPT = """You are an expert in relationship extraction. Your task is to identify relationships between entities in the provided text.

Text to analyze:
{text}

Entities identified in the text:
{entities}

For each relationship you identify, provide:
1. The source entity name
2. The target entity name
3. The relationship type (e.g., "works for", "located in", "developed by", "part of", etc.)
4. A confidence score between 0 and 1
5. A brief description of the relationship based on the text

Format your response as a JSON array of objects with the following structure:
[
  {
    "source": "source entity name",
    "target": "target entity name",
    "type": "relationship type",
    "confidence": 0.85,
    "description": "brief description of the relationship"
  }
]

Only include relationships that are clearly mentioned in the text. Aim for precision over recall.
"""

async def extract_entities(text: str) -> List[Dict[str, Any]]:
    """

    Extract named entities from text using LLM.
    
    Args:
        text: Text to extract entities from
        
    Returns:
        List of extracted entities with their types and metadata
    """
    if not text:
        return []
    
    # Truncate text if it's too long
    max_text_length = 8000
    if len(text) > max_text_length:
        entity_logger.warning(f"Text too long ({len(text)} chars), truncating to {max_text_length} chars")
        text = text[:max_text_length]
    
    try:
        # Format the prompt with the text
        prompt = ENTITY_EXTRACTION_PROMPT.format(text=text)
        
        # Call the LLM to extract entities
        response = await llm.agenerate(prompt, model=model, temperature=0.1, max_tokens=2000)
        
        # Parse the response
        try:
            # Extract JSON from the response
            json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                entities = json.loads(json_str)
            else:
                # Try to parse the entire response as JSON
                entities = json.loads(response)
            
            # Validate the entities
            valid_entities = []
            for entity in entities:
                if isinstance(entity, dict) and 'name' in entity and 'type' in entity:
                    # Ensure confidence is a float between 0 and 1
                    if 'confidence' not in entity:
                        entity['confidence'] = 0.8
                    else:
                        entity['confidence'] = float(entity['confidence'])
                        entity['confidence'] = max(0, min(1, entity['confidence']))
                    
                    # Ensure description exists
                    if 'description' not in entity:
                        entity['description'] = ""
                    
                    valid_entities.append(entity)
            
            return valid_entities
        except Exception as e:
            entity_logger.error(f"Error parsing entity extraction response: {e}")
            entity_logger.debug(f"Response: {response}")
            return []
    
    except Exception as e:
        entity_logger.error(f"Error extracting entities: {e}")
        return []

async def extract_relationships(text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract relationships between entities from text using LLM.
    
    Args:
        text: Text to extract relationships from
        entities: List of entities extracted from the text
        
    Returns:
        List of extracted relationships with their types and metadata
    """
    if not text or not entities or len(entities) < 2:
        return []
    
    # Truncate text if it's too long
    max_text_length = 8000
    if len(text) > max_text_length:
        entity_logger.warning(f"Text too long ({len(text)} chars), truncating to {max_text_length} chars")
        text = text[:max_text_length]
    
    try:
        # Format the entities as a string
        entities_str = json.dumps(entities, indent=2)
        
        # Format the prompt with the text and entities
        prompt = RELATIONSHIP_EXTRACTION_PROMPT.format(text=text, entities=entities_str)
        
        # Call the LLM to extract relationships
        response = await llm.agenerate(prompt, model=model, temperature=0.1, max_tokens=2000)
        
        # Parse the response
        try:
            # Extract JSON from the response
            json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                relationships = json.loads(json_str)
            else:
                # Try to parse the entire response as JSON
                relationships = json.loads(response)
            
            # Validate the relationships
            valid_relationships = []
            for rel in relationships:
                if isinstance(rel, dict) and 'source' in rel and 'target' in rel and 'type' in rel:
                    # Ensure confidence is a float between 0 and 1
                    if 'confidence' not in rel:
                        rel['confidence'] = 0.7
                    else:
                        rel['confidence'] = float(rel['confidence'])
                        rel['confidence'] = max(0, min(1, rel['confidence']))
                    
                    # Ensure description exists
                    if 'description' not in rel:
                        rel['description'] = ""
                    
                    valid_relationships.append(rel)
            
            return valid_relationships
        except Exception as e:
            entity_logger.error(f"Error parsing relationship extraction response: {e}")
            entity_logger.debug(f"Response: {response}")
            return []
    
    except Exception as e:
        entity_logger.error(f"Error extracting relationships: {e}")
        return []

async def store_entities(entities: List[Dict[str, Any]], focus_id: str) -> List[str]:
    """
    Store extracted entities in the database.
    
    Args:

        entities: List of entities to store
        focus_id: ID of the focus point
        
    Returns:
        List of entity IDs
    """

    entity_ids = []
    
    for entity in entities:
        # Check if entity already exists
        filter_query = f"name='{entity['name']}' && type='{entity['type']}'"
        existing_entities = pb.read(collection_name='entities', filter=filter_query)
        
        if existing_entities:
            # Update existing entity
            existing_entity = existing_entities[0]
            entity_id = existing_entity['id']
            
            # Update occurrence count
            occurrence_count = existing_entity.get('occurrence_count', 0) + 1
            
            # Update last_seen
            last_seen = datetime.now().isoformat()
            
            # Update focus_points
            focus_points = existing_entity.get('focus_points', [])
            if isinstance(focus_points, str):
                try:
                    focus_points = json.loads(focus_points)
                except:
                    focus_points = []
            
            if focus_id not in focus_points:
                focus_points.append(focus_id)
            
            # Update entity
            pb.update('entities', entity_id, {
                'occurrence_count': occurrence_count,
                'last_seen': last_seen,
                'focus_points': json.dumps(focus_points)
            })
        else:
            # Create new entity
            entity_data = {
                'name': entity['name'],
                'type': entity['type'],
                'description': entity.get('description', ''),
                'confidence': entity.get('confidence', 0.8),
                'first_seen': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'occurrence_count': 1,
                'focus_points': json.dumps([focus_id])
            }
            
            entity_id = pb.add('entities', entity_data)
        
        if entity_id:
            entity_ids.append(entity_id)
    
    return entity_ids

async def store_relationships(relationships: List[Dict[str, Any]], entity_map: Dict[str, str], focus_id: str) -> List[str]:
    """
    Store extracted relationships in the database.
    
    Args:
        relationships: List of relationships to store
        entity_map: Mapping of entity names to entity IDs
        focus_id: ID of the focus point
        
    Returns:
        List of relationship IDs
    """
    relationship_ids = []
    
    for rel in relationships:
        source_name = rel['source']
        target_name = rel['target']
        
        # Skip if source or target entity is not in the entity map
        if source_name not in entity_map or target_name not in entity_map:
            continue
        
        source_id = entity_map[source_name]
        target_id = entity_map[target_name]
        
        # Check if relationship already exists
        filter_query = f"source_entity_id='{source_id}' && target_entity_id='{target_id}' && relationship_type='{rel['type']}'"
        existing_relationships = pb.read(collection_name='relationships', filter=filter_query)
        
        if existing_relationships:
            # Update existing relationship
            existing_rel = existing_relationships[0]
            rel_id = existing_rel['id']
            
            # Update occurrence count
            occurrence_count = existing_rel.get('occurrence_count', 0) + 1
            
            # Update last_seen
            last_seen = datetime.now().isoformat()
            
            # Update focus_points
            focus_points = existing_rel.get('focus_points', [])
            if isinstance(focus_points, str):
                try:
                    focus_points = json.loads(focus_points)
                except:
                    focus_points = []
            
            if focus_id not in focus_points:
                focus_points.append(focus_id)
            
            # Update relationship
            pb.update('relationships', rel_id, {
                'occurrence_count': occurrence_count,
                'last_seen': last_seen,
                'focus_points': json.dumps(focus_points)
            })
        else:
            # Create new relationship
            rel_data = {
                'source_entity_id': source_id,
                'target_entity_id': target_id,
                'relationship_type': rel['type'],
                'description': rel.get('description', ''),
                'confidence': rel.get('confidence', 0.7),
                'first_seen': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'occurrence_count': 1,
                'focus_points': json.dumps([focus_id])
            }
            
            rel_id = pb.add('relationships', rel_data)
        
        if rel_id:
            relationship_ids.append(rel_id)
    
    return relationship_ids

async def process_item_for_entities(item_id: str, content: str, focus_id: str) -> Dict[str, Any]:
    """
    Process an item to extract entities and relationships.
    
    Args:
        item_id: ID of the item
        content: Content to process
        focus_id: ID of the focus point
        
    Returns:
        Dictionary with extracted entities and relationships
    """
    # Extract entities
    entities = await extract_entities(content)
    
    # Extract relationships
    relationships = await extract_relationships(content, entities)
    
    # Store entities and get entity IDs
    entity_ids = await store_entities(entities, focus_id)
    
    # Create a mapping of entity names to entity IDs
    entity_map = {}
    for i, entity in enumerate(entities):
        if i < len(entity_ids):
            entity_map[entity['name']] = entity_ids[i]
    
    # Store relationships and get relationship IDs
    relationship_ids = await store_relationships(relationships, entity_map, focus_id)
    
    # Create entity links for the item
    entity_links = []
    for i, entity in enumerate(entities):
        if i < len(entity_ids):
            entity_links.append({
                'entity_id': entity_ids[i],
                'entity_name': entity['name'],
                'entity_type': entity['type'],
                'confidence': entity['confidence']
            })
    
    # Update the item with entity links
    if entity_links:
        pb.update('infos', item_id, {'entity_links': json.dumps(entity_links)})
    
    # Create insights record
    timestamp = datetime.now().isoformat()
    insights_data = {
        'item_id': item_id,
        'timestamp': timestamp,
        'entities': json.dumps(entities),
        'relationships': json.dumps(relationships),
        'entity_links': json.dumps(entity_links)
    }
    
    insights_id = pb.add('insights', insights_data)
    
    return {
        'entities': entities,
        'relationships': relationships,
        'entity_links': entity_links,
        'entity_ids': entity_ids,
        'relationship_ids': relationship_ids,
        'insights_id': insights_id
    }

async def generate_knowledge_graph(focus_id: str) -> Dict[str, Any]:
    """
    Generate a knowledge graph for a focus point.
    
    Args:
        focus_id: ID of the focus point
        
    Returns:
        Dictionary with knowledge graph data
    """
    # Get all entities for this focus point
    filter_query = f"focus_points~'{focus_id}'"
    entities = pb.read(collection_name='entities', filter=filter_query)
    
    # Get all relationships for this focus point
    relationships = pb.read(collection_name='relationships', filter=filter_query)
    
    # Create a graph
    G = nx.DiGraph()
    
    # Add nodes (entities)
    for entity in entities:
        G.add_node(entity['id'], 
                  name=entity['name'], 
                  type=entity['type'], 
                  description=entity.get('description', ''),
                  occurrence_count=entity.get('occurrence_count', 1))
    
    # Add edges (relationships)
    for rel in relationships:
        source_id = rel['source_entity_id']
        target_id = rel['target_entity_id']
        
        # Skip if source or target is not in the graph
        if source_id not in G.nodes or target_id not in G.nodes:
            continue
        
        G.add_edge(source_id, target_id, 
                  type=rel['relationship_type'], 
                  description=rel.get('description', ''),
                  occurrence_count=rel.get('occurrence_count', 1))
    
    # Convert the graph to a dictionary for storage
    graph_data = {
        'nodes': [],
        'edges': []
    }
    
    for node_id, node_data in G.nodes(data=True):
        graph_data['nodes'].append({
            'id': node_id,
            'name': node_data.get('name', ''),
            'type': node_data.get('type', ''),
            'description': node_data.get('description', ''),
            'occurrence_count': node_data.get('occurrence_count', 1)
        })
    
    for source, target, edge_data in G.edges(data=True):
        graph_data['edges'].append({
            'source': source,
            'target': target,
            'type': edge_data.get('type', ''),
            'description': edge_data.get('description', ''),
            'occurrence_count': edge_data.get('occurrence_count', 1)
        })
    
    # Calculate some basic metrics
    metrics = {
        'node_count': len(graph_data['nodes']),
        'edge_count': len(graph_data['edges']),
        'density': nx.density(G),
        'connected_components': nx.number_weakly_connected_components(G),
        'avg_degree': sum(dict(G.degree()).values()) / max(1, len(G))
    }
    
    # Find central entities
    if len(G) > 0:
        try:
            centrality = nx.degree_centrality(G)
            central_entities = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:10]
            
            metrics['central_entities'] = []
            for entity_id, score in central_entities:
                entity_data = next((n for n in graph_data['nodes'] if n['id'] == entity_id), None)
                if entity_data:
                    metrics['central_entities'].append({
                        'id': entity_id,
                        'name': entity_data['name'],
                        'type': entity_data['type'],
                        'centrality_score': score
                    })
        except Exception as e:
            entity_logger.error(f"Error calculating centrality: {e}")
    
    return {
        'graph': graph_data,
        'metrics': metrics,
        'focus_id': focus_id,
        'timestamp': datetime.now().isoformat()
    }

async def process_focus_for_knowledge_graph(focus_id: str) -> Dict[str, Any]:
    """
    Process all items for a focus point to generate a knowledge graph.
    
    Args:
        focus_id: ID of the focus point
        
    Returns:
        Dictionary with knowledge graph data
    """
    # Get all info items for this focus point
    info_items = pb.read(collection_name='infos', filter=f"tag='{focus_id}'")
    
    if not info_items:
        entity_logger.warning(f"No information items found for focus ID {focus_id}")
        return {'error': f"No information items found for focus ID {focus_id}"}
    
    # Process each item to extract entities and relationships
    for item in info_items:
        item_id = item['id']
        content = item.get('content', '')
        
        # Skip items without content
        if not content:
            continue
        
        # Check if this item already has entity_links
        if item.get('entity_links'):
            entity_logger.debug(f"Item {item_id} already has entity_links, skipping")
            continue
        
        # Process the item
        await process_item_for_entities(item_id, content, focus_id)
    
    # Generate the knowledge graph
    knowledge_graph = await generate_knowledge_graph(focus_id)
    
    # Store the knowledge graph in collective_insights
    filter_query = f"focus_id='{focus_id}'"
    existing_insights = pb.read(collection_name='collective_insights', filter=filter_query)
    
    if existing_insights:
        # Update existing collective insights
        insight_id = existing_insights[0]['id']
        pb.update('collective_insights', insight_id, {
            'knowledge_graph': json.dumps(knowledge_graph),
            'timestamp': datetime.now().isoformat()
        })
    else:
        # Get focus point name
        focus_point = ""
        if info_items:
            focus_point = info_items[0].get('tag_name', '')
        
        # Create new collective insights
        insights_data = {
            'focus_id': focus_id,
            'focus_point': focus_point,
            'timestamp': datetime.now().isoformat(),
            'item_count': len(info_items),
            'knowledge_graph': json.dumps(knowledge_graph)
        }
        
        pb.add('collective_insights', insights_data)
    
    return knowledge_graph
