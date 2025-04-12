"""
Knowledge Graph visualization module for Wiseflow dashboard.

This module provides visualization capabilities for knowledge graphs.
"""

from typing import Dict, List, Any, Optional
import logging
import json
import os
from datetime import datetime

from core.analysis import KnowledgeGraph, Entity, Relationship
from dashboard.visualization import KnowledgeGraphVisualization

logger = logging.getLogger(__name__)

def visualize_knowledge_graph(graph: KnowledgeGraph, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate a visualization of a knowledge graph.
    
    Args:
        graph: The knowledge graph to visualize
        config: Optional configuration options
    
    Returns:
        A dictionary containing the visualization data
    """
    config = config or {}
    
    # Create a visualization
    viz = KnowledgeGraphVisualization(
        name=f"{graph.name} Visualization",
        data_source={"type": "object", "graph": graph.to_dict()},
        config=config
    )
    
    # Render the visualization
    return viz.render()

def export_knowledge_graph_visualization(graph: KnowledgeGraph, filepath: str, config: Optional[Dict[str, Any]] = None) -> bool:
    """Export a knowledge graph visualization to a file.
    
    Args:
        graph: The knowledge graph to visualize
        filepath: The path to save the visualization to
        config: Optional configuration options
    
    Returns:
        True if the export was successful, False otherwise
    """
    try:
        # Generate the visualization
        visualization = visualize_knowledge_graph(graph, config)
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(visualization, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Knowledge graph visualization exported to {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error exporting knowledge graph visualization: {e}")
        return False

def filter_knowledge_graph(graph: KnowledgeGraph, filters: Dict[str, Any]) -> KnowledgeGraph:
    """Filter a knowledge graph based on specified criteria.
    
    Args:
        graph: The knowledge graph to filter
        filters: The filter criteria
    
    Returns:
        A filtered knowledge graph
    """
    filtered_graph = KnowledgeGraph(
        name=f"{graph.name} (Filtered)",
        description=f"Filtered version of {graph.description}"
    )
    
    # Apply entity type filter
    entity_types = filters.get("entity_types")
    
    # Apply source filter
    sources = filters.get("sources")
    
    # Apply name filter
    name_contains = filters.get("name_contains")
    
    # Apply relationship type filter
    relationship_types = filters.get("relationship_types")
    
    # Filter entities
    for entity_id, entity in graph.entities.items():
        # Apply entity type filter
        if entity_types and entity.entity_type not in entity_types:
            continue
        
        # Apply source filter
        if sources and not any(source in sources for source in entity.sources):
            continue
        
        # Apply name filter
        if name_contains and name_contains not in entity.name:
            continue
        
        # Entity passed all filters
        filtered_graph.add_entity(entity)
    
    # Filter relationships
    for entity_id, entity in filtered_graph.entities.items():
        filtered_relationships = []
        
        for relationship in entity.relationships:
            # Apply relationship type filter
            if relationship_types and relationship.relationship_type not in relationship_types:
                continue
            
            # Check if target entity exists in filtered graph
            if filtered_graph.get_entity(relationship.target_id):
                filtered_relationships.append(relationship)
        
        # Replace relationships with filtered list
        entity.relationships = filtered_relationships
    
    return filtered_graph
