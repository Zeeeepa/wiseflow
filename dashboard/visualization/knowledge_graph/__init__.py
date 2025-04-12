"""
Knowledge Graph Visualization module for Wiseflow dashboard.

This module provides functionality for visualizing knowledge graphs in the dashboard.
"""

import os
import json
from typing import Dict, List, Any, Optional, Union
import logging
import networkx as nx
import matplotlib.pyplot as plt
from io import BytesIO
import base64

from ....core.knowledge.graph import KnowledgeGraphBuilder
from ....core.analysis import KnowledgeGraph

logger = logging.getLogger(__name__)

class KnowledgeGraphVisualizer:
    """Class for visualizing knowledge graphs."""
    
    def __init__(self, graph: Optional[KnowledgeGraph] = None):
        """
        Initialize the knowledge graph visualizer.
        
        Args:
            graph: Optional knowledge graph to visualize
        """
        self.graph = graph
        self.layout_cache = {}
        
    def set_graph(self, graph: KnowledgeGraph) -> None:
        """
        Set the knowledge graph to visualize.
        
        Args:
            graph: Knowledge graph to visualize
        """
        self.graph = graph
        self.layout_cache = {}
        
    def generate_visualization(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate a visualization of the knowledge graph.
        
        Args:
            config: Visualization configuration
            
        Returns:
            Dictionary with visualization data
        """
        if not self.graph:
            logger.warning("No knowledge graph to visualize")
            return {"error": "No knowledge graph to visualize"}
        
        config = config or {}
        
        # Create a NetworkX graph
        G = nx.DiGraph()
        
        # Add nodes
        for entity_id, entity in self.graph.entities.items():
            G.add_node(
                entity_id,
                name=entity.name,
                entity_type=entity.entity_type,
                sources=entity.sources,
                metadata=entity.metadata
            )
        
        # Add edges
        for entity in self.graph.entities.values():
            for rel in entity.relationships:
                G.add_edge(
                    rel.source_id,
                    rel.target_id,
                    relationship_type=rel.relationship_type,
                    metadata=rel.metadata
                )
        
        # Generate layout
        layout_type = config.get("layout", "spring")
        if layout_type == "spring":
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
        Generate an image of the knowledge graph.
        
        Args:
            config: Visualization configuration
            
        Returns:
            Base64-encoded image data
        """
        if not self.graph:
            logger.warning("No knowledge graph to visualize")
            return None
        
        config = config or {}
        
        # Create a NetworkX graph
        G = nx.DiGraph()
        
        # Add nodes
        for entity_id, entity in self.graph.entities.items():
            G.add_node(
                entity_id,
                name=entity.name,
                entity_type=entity.entity_type
            )
        
        # Add edges
        for entity in self.graph.entities.values():
            for rel in entity.relationships:
                G.add_edge(
                    rel.source_id,
                    rel.target_id,
                    relationship_type=rel.relationship_type
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
        
        plt.title(config.get("title", "Knowledge Graph"))
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
    
    def filter_graph(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter the knowledge graph based on criteria.
        
        Args:
            filters: Filter criteria
            
        Returns:
            Filtered visualization data
        """
        if not self.graph:
            logger.warning("No knowledge graph to filter")
            return {"error": "No knowledge graph to filter"}
        
        # Create a copy of the graph
        filtered_graph = KnowledgeGraph(name=self.graph.name, description=self.graph.description)
        
        # Apply entity type filter
        entity_types = filters.get("entity_types", [])
        if entity_types:
            for entity_id, entity in self.graph.entities.items():
                if entity.entity_type in entity_types:
                    filtered_graph.add_entity(entity)
        else:
            # No entity type filter, add all entities
            for entity_id, entity in self.graph.entities.items():
                filtered_graph.add_entity(entity)
        
        # Apply relationship type filter
        relationship_types = filters.get("relationship_types", [])
        if relationship_types:
            for entity in filtered_graph.entities.values():
                entity.relationships = [rel for rel in entity.relationships 
                                       if rel.relationship_type in relationship_types]
        
        # Set the filtered graph
        self.set_graph(filtered_graph)
        
        # Generate visualization
        return self.generate_visualization(filters.get("config", {}))
    
    def get_entity_details(self, entity_id: str) -> Dict[str, Any]:
        """
        Get detailed information about an entity.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Dictionary with entity details
        """
        if not self.graph:
            logger.warning("No knowledge graph to get entity details from")
            return {"error": "No knowledge graph to get entity details from"}
        
        entity = self.graph.entities.get(entity_id)
        if not entity:
            logger.warning(f"Entity {entity_id} not found")
            return {"error": f"Entity {entity_id} not found"}
        
        # Get relationships
        relationships = []
        for rel in entity.relationships:
            target_entity = self.graph.entities.get(rel.target_id)
            if target_entity:
                relationships.append({
                    "relationship_id": rel.relationship_id,
                    "relationship_type": rel.relationship_type,
                    "target_id": rel.target_id,
                    "target_name": target_entity.name,
                    "target_type": target_entity.entity_type,
                    "metadata": rel.metadata
                })
        
        # Get incoming relationships
        incoming_relationships = []
        for other_entity in self.graph.entities.values():
            for rel in other_entity.relationships:
                if rel.target_id == entity_id:
                    incoming_relationships.append({
                        "relationship_id": rel.relationship_id,
                        "relationship_type": rel.relationship_type,
                        "source_id": rel.source_id,
                        "source_name": other_entity.name,
                        "source_type": other_entity.entity_type,
                        "metadata": rel.metadata
                    })
        
        return {
            "entity_id": entity_id,
            "name": entity.name,
            "entity_type": entity.entity_type,
            "sources": entity.sources,
            "metadata": entity.metadata,
            "relationships": relationships,
            "incoming_relationships": incoming_relationships
        }


# Create a singleton instance
knowledge_graph_visualizer = KnowledgeGraphVisualizer()

def visualize_knowledge_graph(graph: KnowledgeGraph, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate a visualization of a knowledge graph.
    
    Args:
        graph: Knowledge graph to visualize
        config: Visualization configuration
        
    Returns:
        Dictionary with visualization data
    """
    knowledge_graph_visualizer.set_graph(graph)
    return knowledge_graph_visualizer.generate_visualization(config)

def generate_knowledge_graph_image(graph: KnowledgeGraph, config: Dict[str, Any] = None) -> Optional[str]:
    """
    Generate an image of a knowledge graph.
    
    Args:
        graph: Knowledge graph to visualize
        config: Visualization configuration
        
    Returns:
        Base64-encoded image data
    """
    knowledge_graph_visualizer.set_graph(graph)
    return knowledge_graph_visualizer.generate_image(config)

def filter_knowledge_graph(graph: KnowledgeGraph, filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter a knowledge graph based on criteria.
    
    Args:
        graph: Knowledge graph to filter
        filters: Filter criteria
        
    Returns:
        Filtered visualization data
    """
    knowledge_graph_visualizer.set_graph(graph)
    return knowledge_graph_visualizer.filter_graph(filters)

def get_entity_details(graph: KnowledgeGraph, entity_id: str) -> Dict[str, Any]:
    """
    Get detailed information about an entity in a knowledge graph.
    
    Args:
        graph: Knowledge graph containing the entity
        entity_id: Entity ID
        
    Returns:
        Dictionary with entity details
    """
    knowledge_graph_visualizer.set_graph(graph)
    return knowledge_graph_visualizer.get_entity_details(entity_id)
