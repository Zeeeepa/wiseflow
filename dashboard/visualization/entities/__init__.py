"""
Entity Visualization module for Wiseflow dashboard.

This module provides functionality for visualizing entities and their relationships.
"""

import os
import json
from typing import Dict, List, Any, Optional, Union
import logging
import networkx as nx
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from collections import Counter

from ....core.analysis.entity_linking import link_entities, visualize_entity_network

logger = logging.getLogger(__name__)

class EntityVisualizer:
    """Class for visualizing entities and their relationships."""
    
    def __init__(self):
        """Initialize the entity visualizer."""
        self.entities = []
        self.layout_cache = {}
        
    def set_entities(self, entities: List[Dict[str, Any]]) -> None:
        """
        Set the entities to visualize.
        
        Args:
            entities: List of entity dictionaries
        """
        self.entities = entities
        self.layout_cache = {}
        
    def generate_visualization(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate a visualization of the entities.
        
        Args:
            config: Visualization configuration
            
        Returns:
            Dictionary with visualization data
        """
        if not self.entities:
            logger.warning("No entities to visualize")
            return {"error": "No entities to visualize"}
        
        config = config or {}
        
        # Create a NetworkX graph
        G = nx.Graph()
        
        # Add nodes
        for entity in self.entities:
            entity_id = entity.get("entity_id", "")
            if not entity_id:
                continue
                
            G.add_node(
                entity_id,
                name=entity.get("name", ""),
                entity_type=entity.get("entity_type", ""),
                sources=entity.get("sources", []),
                metadata=entity.get("metadata", {})
            )
        
        # Add edges for relationships
        for entity in self.entities:
            entity_id = entity.get("entity_id", "")
            if not entity_id:
                continue
                
            relationships = entity.get("relationships", [])
            for rel in relationships:
                target_id = rel.get("target_id", "")
                if not target_id or target_id not in G:
                    continue
                    
                G.add_edge(
                    entity_id,
                    target_id,
                    relationship_type=rel.get("relationship_type", ""),
                    metadata=rel.get("metadata", {})
                )
        
        # Generate layout
        layout_type = config.get("layout", "spring")
        if layout_type in self.layout_cache:
            pos = self.layout_cache[layout_type]
        elif layout_type == "spring":
            pos = nx.spring_layout(G)
        elif layout_type == "circular":
            pos = nx.circular_layout(G)
        elif layout_type == "kamada_kawai":
            pos = nx.kamada_kawai_layout(G)
        else:
            pos = nx.spring_layout(G)
        
        # Cache the layout
        self.layout_cache[layout_type] = pos
        
        # Generate visualization data
        nodes = []
        for node_id, node_data in G.nodes(data=True):
            x, y = pos[node_id]
            nodes.append({
                "id": node_id,
                "name": node_data.get("name", ""),
                "type": node_data.get("entity_type", ""),
                "x": float(x),
                "y": float(y),
                "metadata": node_data.get("metadata", {})
            })
        
        edges = []
        for source, target, edge_data in G.edges(data=True):
            edges.append({
                "source": source,
                "target": target,
                "type": edge_data.get("relationship_type", ""),
                "metadata": edge_data.get("metadata", {})
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "layout": layout_type
        }
    
    def generate_image(self, config: Dict[str, Any] = None) -> Optional[str]:
        """
        Generate an image of the entity network.
        
        Args:
            config: Visualization configuration
            
        Returns:
            Base64-encoded image data
        """
        if not self.entities:
            logger.warning("No entities to visualize")
            return None
        
        config = config or {}
        
        # Create a NetworkX graph
        G = nx.Graph()
        
        # Add nodes
        for entity in self.entities:
            entity_id = entity.get("entity_id", "")
            if not entity_id:
                continue
                
            G.add_node(
                entity_id,
                name=entity.get("name", ""),
                entity_type=entity.get("entity_type", "")
            )
        
        # Add edges for relationships
        for entity in self.entities:
            entity_id = entity.get("entity_id", "")
            if not entity_id:
                continue
                
            relationships = entity.get("relationships", [])
            for rel in relationships:
                target_id = rel.get("target_id", "")
                if not target_id or target_id not in G:
                    continue
                    
                G.add_edge(
                    entity_id,
                    target_id,
                    relationship_type=rel.get("relationship_type", "")
                )
        
        # Generate the figure
        plt.figure(figsize=(12, 8))
        
        # Get layout
        layout_type = config.get("layout", "spring")
        if layout_type in self.layout_cache:
            pos = self.layout_cache[layout_type]
        elif layout_type == "spring":
            pos = nx.spring_layout(G)
        elif layout_type == "circular":
            pos = nx.circular_layout(G)
        elif layout_type == "kamada_kawai":
            pos = nx.kamada_kawai_layout(G)
        else:
            pos = nx.spring_layout(G)
        
        # Draw nodes
        node_types = {node: data.get("entity_type", "unknown") for node, data in G.nodes(data=True)}
        unique_types = set(node_types.values())
        color_map = {t: plt.cm.tab10(i/10) for i, t in enumerate(unique_types)}
        
        for node_type in unique_types:
            nodes = [node for node, t in node_types.items() if t == node_type]
            nx.draw_networkx_nodes(G, pos, nodelist=nodes, node_color=[color_map[node_type]], label=node_type)
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.7)
        
        # Draw labels if configured
        if config.get("show_labels", True):
            labels = {node: data.get("name", node) for node, data in G.nodes(data=True)}
            nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)
        
        # Draw edge labels if configured
        if config.get("show_edge_labels", True):
            edge_labels = {(u, v): d.get("relationship_type", "") for u, v, d in G.edges(data=True)}
            nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=6)
        
        plt.title(config.get("title", "Entity Network"))
        plt.legend()
        plt.axis("off")
        
        # Save to BytesIO
        buf = BytesIO()
        plt.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        plt.close()
        
        # Convert to base64
        buf.seek(0)
        img_data = base64.b64encode(buf.read()).decode("utf-8")
        
        return f"data:image/png;base64,{img_data}"
    
    def get_entity_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the entities.
        
        Returns:
            Dictionary with entity statistics
        """
        if not self.entities:
            logger.warning("No entities to get statistics from")
            return {"error": "No entities to get statistics from"}
        
        # Count entity types
        entity_types = [entity.get("entity_type", "unknown") for entity in self.entities]
        type_counts = Counter(entity_types)
        
        # Count relationship types
        relationship_types = []
        for entity in self.entities:
            relationships = entity.get("relationships", [])
            for rel in relationships:
                relationship_types.append(rel.get("relationship_type", "unknown"))
        
        relationship_counts = Counter(relationship_types)
        
        # Count sources
        sources = []
        for entity in self.entities:
            entity_sources = entity.get("sources", [])
            sources.extend(entity_sources)
        
        source_counts = Counter(sources)
        
        return {
            "entity_count": len(self.entities),
            "entity_types": dict(type_counts),
            "relationship_types": dict(relationship_counts),
            "sources": dict(source_counts)
        }
    
    def filter_entities(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter the entities based on criteria.
        
        Args:
            filters: Filter criteria
            
        Returns:
            Filtered visualization data
        """
        if not self.entities:
            logger.warning("No entities to filter")
            return {"error": "No entities to filter"}
        
        # Apply entity type filter
        entity_types = filters.get("entity_types", [])
        sources = filters.get("sources", [])
        
        filtered_entities = []
        for entity in self.entities:
            entity_type = entity.get("entity_type", "")
            entity_sources = entity.get("sources", [])
            
            # Apply entity type filter
            if entity_types and entity_type not in entity_types:
                continue
            
            # Apply source filter
            if sources and not any(source in entity_sources for source in sources):
                continue
            
            filtered_entities.append(entity)
        
        # Set the filtered entities
        self.set_entities(filtered_entities)
        
        # Generate visualization
        return self.generate_visualization(filters.get("config", {}))


# Create a singleton instance
entity_visualizer = EntityVisualizer()

def visualize_entities(entities: List[Dict[str, Any]], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate a visualization of entities.
    
    Args:
        entities: List of entity dictionaries
        config: Visualization configuration
        
    Returns:
        Dictionary with visualization data
    """
    entity_visualizer.set_entities(entities)
    return entity_visualizer.generate_visualization(config)

def generate_entity_image(entities: List[Dict[str, Any]], config: Dict[str, Any] = None) -> Optional[str]:
    """
    Generate an image of the entity network.
    
    Args:
        entities: List of entity dictionaries
        config: Visualization configuration
        
    Returns:
        Base64-encoded image data
    """
    entity_visualizer.set_entities(entities)
    return entity_visualizer.generate_image(config)

def get_entity_statistics(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get statistics about entities.
    
    Args:
        entities: List of entity dictionaries
        
    Returns:
        Dictionary with entity statistics
    """
    entity_visualizer.set_entities(entities)
    return entity_visualizer.get_entity_statistics()

def filter_entities(entities: List[Dict[str, Any]], filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter entities based on criteria.
    
    Args:
        entities: List of entity dictionaries
        filters: Filter criteria
        
    Returns:
        Filtered visualization data
    """
    entity_visualizer.set_entities(entities)
    return entity_visualizer.filter_entities(filters)
