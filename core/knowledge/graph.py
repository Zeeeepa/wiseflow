"""
Knowledge Graph Construction module for Wiseflow.

This module provides functionality for building and maintaining a comprehensive knowledge graph
from extracted information across different data sources.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Set, Union, Callable
import re
from collections import Counter, defaultdict
import networkx as nx
import matplotlib.pyplot as plt
from loguru import logger
import numpy as np
import threading
from ..utils.general_utils import get_logger
from ..utils.pb_api import PbTalker
from ..llms.openai_wrapper import openai_llm as llm
from ..analysis import Entity, Relationship, KnowledgeGraph
from ..analysis.entity_linking import (
    link_entities, 
    merge_entities, 
    get_entity_by_id, 
    get_entities_by_name,
    update_entity_link,
    visualize_entity_network
)

project_dir = os.environ.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)
knowledge_graph_logger = get_logger('knowledge_graph', project_dir)
pb = PbTalker(knowledge_graph_logger)

model = os.environ.get("PRIMARY_MODEL", "")
if not model:
    raise ValueError("PRIMARY_MODEL not set, please set it in environment variables or edit core/.env")

# Prompt for relationship inference
RELATIONSHIP_INFERENCE_PROMPT = """You are an expert in knowledge graph reasoning. Your task is to infer new relationships between entities based on existing relationships in a knowledge graph.

Existing relationships:
{existing_relationships}

Based on these existing relationships, infer new relationships that are likely to exist but are not explicitly stated.
For each inferred relationship, provide:
1. The source entity
2. The target entity
3. The relationship type
4. A confidence score (0.0-1.0)
5. The reasoning behind your inference

Format your response as a JSON array of objects with the following structure:
[
  {
    "source_id": "source entity ID",
    "target_id": "target entity ID",
    "relationship_type": "inferred relationship type",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation of your inference"
  },
  ...
]
"""

class KnowledgeGraphBuilder:
    """Class for building and maintaining knowledge graphs."""
    
    def __init__(self, name: str = "Wiseflow Knowledge Graph", description: str = ""):
        """Initialize the knowledge graph builder."""
        self.graph = KnowledgeGraph(name=name, description=description)
        self.cache = {}
        self.lock = threading.RLock()  # Reentrant lock for thread safety
        knowledge_graph_logger.info(f"Initialized knowledge graph builder for '{name}'")
    
    async def build_knowledge_graph(self, entities: List[Entity], relationships: List[Relationship]) -> KnowledgeGraph:
        """
        Build a knowledge graph from entities and relationships.
        
        Args:
            entities: List of entities to add to the graph
            relationships: List of relationships to add to the graph
            
        Returns:
            The constructed knowledge graph
        """
        knowledge_graph_logger.info(f"Building knowledge graph with {len(entities)} entities and {len(relationships)} relationships")
        
        try:
            with self.lock:
                # Add entities to the graph
                for entity in entities:
                    if not entity or not isinstance(entity, Entity):
                        knowledge_graph_logger.warning(f"Skipping invalid entity: {entity}")
                        continue
                    self.graph.add_entity(entity)
                
                # Add relationships to the graph
                for relationship in relationships:
                    if not relationship or not isinstance(relationship, Relationship):
                        knowledge_graph_logger.warning(f"Skipping invalid relationship: {relationship}")
                        continue
                    
                    # Verify that source and target entities exist
                    if relationship.source_id not in self.graph.entities:
                        knowledge_graph_logger.warning(f"Skipping relationship with missing source entity: {relationship.source_id}")
                        continue
                    if relationship.target_id not in self.graph.entities:
                        knowledge_graph_logger.warning(f"Skipping relationship with missing target entity: {relationship.target_id}")
                        continue
                    
                    self.graph.add_relationship(relationship)
            
            knowledge_graph_logger.info(f"Knowledge graph built with {len(self.graph.entities)} entities")
            return self.graph
        except Exception as e:
            knowledge_graph_logger.error(f"Error building knowledge graph: {str(e)}")
            raise
    
    async def enrich_knowledge_graph(self, new_data: Dict[str, Any]) -> KnowledgeGraph:
        """
        Enrich an existing knowledge graph with new data.
        
        Args:
            new_data: Dictionary containing new entities and relationships
            
        Returns:
            The enriched knowledge graph
        """
        knowledge_graph_logger.info("Enriching knowledge graph with new data")
        
        new_entities = new_data.get("entities", [])
        new_relationships = new_data.get("relationships", [])
        
        # Link new entities with existing ones
        all_entities = list(self.graph.entities.values()) + new_entities
        linked_entities = await link_entities(all_entities)
        
        # Merge linked entities
        for entity_group in linked_entities.values():
            if len(entity_group) > 1:
                merged_entity = await merge_entities(entity_group)
                # Replace all entities in the group with the merged entity
                for entity in entity_group:
                    if entity.entity_id in self.graph.entities:
                        self.graph.entities[entity.entity_id] = merged_entity
        
        # Add new entities that weren't linked to existing ones
        for entity in new_entities:
            if entity.entity_id not in self.graph.entities:
                self.graph.add_entity(entity)
        
        # Add new relationships
        for relationship in new_relationships:
            self.graph.add_relationship(relationship)
        
        # Infer new relationships
        await self.infer_relationships()
        
        knowledge_graph_logger.info(f"Knowledge graph enriched, now contains {len(self.graph.entities)} entities")
        return self.graph
    
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Query the knowledge graph for specific information.
        
        Args:
            query: Dictionary containing query parameters
            
        Returns:
            List of query results
        """
        knowledge_graph_logger.info(f"Querying knowledge graph: {query}")
        
        try:
            with self.lock:
                query_type = query.get("type", "entity")
                results = []
                
                if query_type == "entity":
                    # Query for entities
                    entity_id = query.get("entity_id")
                    entity_name = query.get("entity_name")
                    entity_type = query.get("entity_type")
                    
                    # Create an index for faster lookups if needed
                    if entity_name and not hasattr(self, '_entity_name_index'):
                        self._build_entity_name_index()
                    
                    if entity_id:
                        # Direct lookup by ID (O(1) operation)
                        entity = self.graph.get_entity(entity_id)
                        if entity:
                            results.append(entity.to_dict())
                    elif entity_name and hasattr(self, '_entity_name_index'):
                        # Use the name index for faster lookup
                        entity_ids = self._entity_name_index.get(entity_name.lower(), [])
                        for eid in entity_ids:
                            entity = self.graph.get_entity(eid)
                            if entity and (not entity_type or entity.entity_type == entity_type):
                                results.append(entity.to_dict())
                    else:
                        # Filter entities based on criteria
                        for entity_id, entity in self.graph.entities.items():
                            if (not entity_name or entity.name.lower() == entity_name.lower()) and \
                               (not entity_type or entity.entity_type == entity_type):
                                results.append(entity.to_dict())
                
                elif query_type == "relationship":
                    # Query for relationships
                    source_id = query.get("source_id")
                    target_id = query.get("target_id")
                    relationship_type = query.get("relationship_type")
                    
                    if source_id:
                        # Get relationships from a specific source
                        relationships = self.graph.get_relationships(source_id)
                        for rel in relationships:
                            if (not target_id or rel.target_id == target_id) and \
                               (not relationship_type or rel.relationship_type == relationship_type):
                                results.append(rel.to_dict())
                    elif target_id:
                        # Find relationships targeting a specific entity
                        # This is more expensive as we need to check all relationships
                        for entity_id, entity in self.graph.entities.items():
                            for rel in entity.relationships:
                                if rel.target_id == target_id and \
                                   (not relationship_type or rel.relationship_type == relationship_type):
                                    results.append(rel.to_dict())
                    else:
                        # Get all relationships of a specific type
                        for entity_id, entity in self.graph.entities.items():
                            for rel in entity.relationships:
                                if not relationship_type or rel.relationship_type == relationship_type:
                                    results.append(rel.to_dict())
                
                elif query_type == "path":
                    # Find paths between entities
                    source_id = query.get("source_id")
                    target_id = query.get("target_id")
                    max_length = query.get("max_length", 3)
                    
                    if source_id and target_id:
                        paths = self._find_paths(source_id, target_id, max_length)
                        results = paths
                
                knowledge_graph_logger.info(f"Query returned {len(results)} results")
                return results
        except Exception as e:
            knowledge_graph_logger.error(f"Error querying knowledge graph: {str(e)}")
            return []
    
    def _build_entity_name_index(self):
        """Build an index of entity names for faster lookups."""
        self._entity_name_index = defaultdict(list)
        for entity_id, entity in self.graph.entities.items():
            if entity.name:
                self._entity_name_index[entity.name.lower()].append(entity_id)
        knowledge_graph_logger.info(f"Built entity name index with {len(self._entity_name_index)} unique names")
    
    async def infer_relationships(self) -> List[Relationship]:
        """
        Infer new relationships based on existing knowledge.
        
        Returns:
            List of inferred relationships
        """
        knowledge_graph_logger.info("Inferring new relationships")
        
        # Get existing relationships
        existing_relationships = []
        for entity in self.graph.entities.values():
            for rel in entity.relationships:
                source_entity = self.graph.get_entity(rel.source_id)
                target_entity = self.graph.get_entity(rel.target_id)
                
                if source_entity and target_entity:
                    existing_relationships.append({
                        "source_id": rel.source_id,
                        "source_name": source_entity.name,
                        "source_type": source_entity.entity_type,
                        "target_id": rel.target_id,
                        "target_name": target_entity.name,
                        "target_type": target_entity.entity_type,
                        "relationship_type": rel.relationship_type
                    })
        
        # If there are too few relationships, don't try to infer new ones
        if len(existing_relationships) < 5:
            knowledge_graph_logger.info("Too few relationships to infer new ones")
            return []
        
        # Use LLM to infer new relationships
        prompt = RELATIONSHIP_INFERENCE_PROMPT.format(
            existing_relationships=json.dumps(existing_relationships, indent=2)
        )
        
        result = await llm([
            {'role': 'system', 'content': 'You are an expert in knowledge graph reasoning.'},
            {'role': 'user', 'content': prompt}
        ], model=model, temperature=0.2)
        
        # Parse the JSON response
        try:
            # Find JSON array in the response
            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                inferred_relationships_data = json.loads(json_str)
                
                # Create Relationship objects
                inferred_relationships = []
                for rel_data in inferred_relationships_data:
                    # Only add relationships with sufficient confidence
                    if rel_data.get("confidence", 0) >= 0.7:
                        relationship_id = f"inferred_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(inferred_relationships)}"
                        relationship = Relationship(
                            relationship_id=relationship_id,
                            source_id=rel_data["source_id"],
                            target_id=rel_data["target_id"],
                            relationship_type=rel_data["relationship_type"],
                            metadata={
                                "inferred": True,
                                "confidence": rel_data.get("confidence", 0.7),
                                "reasoning": rel_data.get("reasoning", "")
                            }
                        )
                        inferred_relationships.append(relationship)
                        
                        # Add the relationship to the graph
                        self.graph.add_relationship(relationship)
                
                knowledge_graph_logger.info(f"Inferred {len(inferred_relationships)} new relationships")
                return inferred_relationships
            else:
                knowledge_graph_logger.warning("No valid JSON found in relationship inference response")
                return []
        except Exception as e:
            knowledge_graph_logger.error(f"Error parsing relationship inference response: {e}")
            return []
    
    def _find_paths(self, source_id: str, target_id: str, max_length: int = 3) -> List[List[Dict[str, Any]]]:
        """
        Find paths between two entities in the knowledge graph.
        
        Args:
            source_id: ID of the source entity
            target_id: ID of the target entity
            max_length: Maximum path length
            
        Returns:
            List of paths, where each path is a list of relationships
        """
        knowledge_graph_logger.debug(f"Finding paths from {source_id} to {target_id} with max length {max_length}")
        
        # Create a directed graph using NetworkX
        G = nx.DiGraph()
        
        # Add edges
        for entity in self.graph.entities.values():
            for rel in entity.relationships:
                G.add_edge(
                    rel.source_id,
                    rel.target_id,
                    relationship_type=rel.relationship_type,
                    relationship_id=rel.relationship_id
                )
        
        # Find all simple paths
        try:
            paths = list(nx.all_simple_paths(G, source=source_id, target=target_id, cutoff=max_length))
            
            # Convert paths to a more detailed format
            detailed_paths = []
            for path in paths:
                detailed_path = []
                for i in range(len(path) - 1):
                    source_id = path[i]
                    target_id = path[i + 1]
                    
                    # Get edge data
                    edge_data = G.get_edge_data(source_id, target_id)
                    
                    # Get entity names
                    source_entity = self.graph.get_entity(source_id)
                    target_entity = self.graph.get_entity(target_id)
                    
                    detailed_path.append({
                        "source_id": source_id,
                        "source_name": source_entity.name if source_entity else "Unknown",
                        "target_id": target_id,
                        "target_name": target_entity.name if target_entity else "Unknown",
                        "relationship_type": edge_data.get("relationship_type", "unknown"),
                        "relationship_id": edge_data.get("relationship_id", "")
                    })
                
                detailed_paths.append(detailed_path)
            
            knowledge_graph_logger.debug(f"Found {len(detailed_paths)} paths")
            return detailed_paths
        except nx.NetworkXNoPath:
            knowledge_graph_logger.debug(f"No path found from {source_id} to {target_id}")
            return []
    
    def visualize_knowledge_graph(self, output_path: Optional[str] = None, max_nodes: int = 100) -> str:
        """
        Generate visualization of the knowledge graph.
        
        Args:
            output_path: Path to save the visualization
            max_nodes: Maximum number of nodes to include in the visualization
            
        Returns:
            Path to the saved visualization
        """
        knowledge_graph_logger.info("Generating knowledge graph visualization")
        
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            output_path = os.path.join(project_dir, f"knowledge_graph_{timestamp}.png")
        
        # Create a directed graph
        G = nx.DiGraph()
        
        # Add nodes and edges
        entities = list(self.graph.entities.values())
        
        # If there are too many entities, select a subset
        if len(entities) > max_nodes:
            knowledge_graph_logger.info(f"Limiting visualization to {max_nodes} nodes")
            # Sort entities by number of relationships
            entities.sort(key=lambda e: len(e.relationships), reverse=True)
            entities = entities[:max_nodes]
        
        # Add nodes
        for entity in entities:
            G.add_node(entity.entity_id, name=entity.name, type=entity.entity_type)
        
        # Add edges
        for entity in entities:
            for rel in entity.relationships:
                if rel.source_id in G.nodes and rel.target_id in G.nodes:
                    G.add_edge(
                        rel.source_id,
                        rel.target_id,
                        relationship_type=rel.relationship_type
                    )
        
        knowledge_graph_logger.debug(f"Visualization graph created with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
        
        # Visualize the graph
        try:
            plt.figure(figsize=(15, 10))
            
            # Position nodes using spring layout
            pos = nx.spring_layout(G, k=0.3, iterations=50)
            
            # Draw nodes
            node_types = {node: data.get('type', 'unknown') for node, data in G.nodes(data=True)}
            unique_types = set(node_types.values())
            color_map = {t: plt.cm.tab10(i/10) for i, t in enumerate(unique_types)}
            
            for node_type in unique_types:
                nodes = [node for node, t in node_types.items() if t == node_type]
                nx.draw_networkx_nodes(G, pos, nodelist=nodes, node_color=[color_map[node_type]], label=node_type, node_size=100)
            
            # Draw edges
            nx.draw_networkx_edges(G, pos, width=0.5, alpha=0.6, arrowsize=10)
            
            # Draw labels
            node_labels = {node: data.get('name', node) for node, data in G.nodes(data=True)}
            nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=6)
            
            # Draw edge labels (only if there are not too many edges)
            if G.number_of_edges() <= 50:
                edge_labels = {(u, v): d.get('relationship_type', '') for u, v, d in G.edges(data=True)}
                nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=5)
            
            plt.title(f"Knowledge Graph: {self.graph.name}")
            plt.legend()
            plt.axis('off')
            
            # Save the figure
            plt.savefig(output_path, format='png', dpi=300, bbox_inches='tight')
            plt.close()
            
            knowledge_graph_logger.info(f"Knowledge graph visualization saved to {output_path}")
            return output_path
        except Exception as e:
            knowledge_graph_logger.error(f"Error visualizing knowledge graph: {e}")
            return ""
    
    def validate_knowledge_graph(self) -> Dict[str, Any]:
        """
        Validate the consistency of the knowledge graph.
        
        Returns:
            Dictionary with validation results
        """
        knowledge_graph_logger.info("Validating knowledge graph")
        
        try:
            with self.lock:
                validation_results = {
                    "is_valid": True,
                    "issues": [],
                    "stats": {
                        "entity_count": len(self.graph.entities),
                        "relationship_count": sum(len(e.relationships) for e in self.graph.entities.values()),
                        "entity_types": Counter(e.entity_type for e in self.graph.entities.values()),
                        "relationship_types": Counter(r.relationship_type for e in self.graph.entities.values() for r in e.relationships)
                    }
                }
                
                # Check for relationships with missing entities
                missing_entities = set()
                invalid_relationships = []
                
                for entity_id, entity in self.graph.entities.items():
                    for relationship in entity.relationships:
                        if relationship.target_id not in self.graph.entities:
                            missing_entities.add(relationship.target_id)
                            invalid_relationships.append(relationship.relationship_id)
                            validation_results["is_valid"] = False
                            validation_results["issues"].append({
                                "type": "missing_target_entity",
                                "entity_id": relationship.target_id,
                                "relationship_id": relationship.relationship_id
                            })
                
                # Check for duplicate entity IDs (should not happen with proper implementation)
                entity_ids = list(self.graph.entities.keys())
                if len(entity_ids) != len(set(entity_ids)):
                    validation_results["is_valid"] = False
                    validation_results["issues"].append({
                        "type": "duplicate_entity_ids",
                        "details": "There are duplicate entity IDs in the graph"
                    })
                
                # Check for duplicate relationship IDs
                relationship_ids = []
                for entity in self.graph.entities.values():
                    for relationship in entity.relationships:
                        relationship_ids.append(relationship.relationship_id)
                
                if len(relationship_ids) != len(set(relationship_ids)):
                    validation_results["is_valid"] = False
                    validation_results["issues"].append({
                        "type": "duplicate_relationship_ids",
                        "details": "There are duplicate relationship IDs in the graph"
                    })
                
                # Check for self-referential relationships
                self_refs = []
                for entity_id, entity in self.graph.entities.items():
                    for relationship in entity.relationships:
                        if relationship.source_id == relationship.target_id:
                            self_refs.append(relationship.relationship_id)
                
                if self_refs and not query.get("allow_self_references", False):
                    validation_results["is_valid"] = False
                    validation_results["issues"].append({
                        "type": "self_referential_relationships",
                        "relationship_ids": self_refs
                    })
                
                # Add additional validation statistics
                validation_results["stats"]["missing_entity_count"] = len(missing_entities)
                validation_results["stats"]["invalid_relationship_count"] = len(invalid_relationships)
                validation_results["stats"]["self_referential_count"] = len(self_refs)
                
                knowledge_graph_logger.info(f"Knowledge graph validation completed: valid={validation_results['is_valid']}, issues={len(validation_results['issues'])}")
                return validation_results
        except Exception as e:
            knowledge_graph_logger.error(f"Error validating knowledge graph: {str(e)}")
            return {
                "is_valid": False,
                "issues": [{
                    "type": "validation_error",
                    "details": str(e)
                }],
                "stats": {}
            }
    
    def export_knowledge_graph(self, format: str = "json", output_path: Optional[str] = None) -> str:
        """
        Export the knowledge graph in different formats.
        
        Args:
            format: Export format (json, csv, graphml)
            output_path: Path to save the exported file
            
        Returns:
            Path to the exported file
        """
        knowledge_graph_logger.info(f"Exporting knowledge graph in {format} format")
        
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            output_path = os.path.join(project_dir, f"knowledge_graph_{timestamp}.{format}")
        
        if format == "json":
            # Export as JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.graph.to_dict(), f, ensure_ascii=False, indent=2)
        
        elif format == "csv":
            # Export as CSV (entities and relationships)
            entities_path = output_path.replace(f".{format}", f"_entities.{format}")
            relationships_path = output_path.replace(f".{format}", f"_relationships.{format}")
            
            # Export entities
            with open(entities_path, 'w', encoding='utf-8') as f:
                f.write("entity_id,name,entity_type,sources,metadata\n")
                for entity in self.graph.entities.values():
                    sources = "|".join(entity.sources)
                    metadata = json.dumps(entity.metadata).replace(",", ";").replace("\"", "'")
                    f.write(f"{entity.entity_id},{entity.name},{entity.entity_type},{sources},{metadata}\n")
            
            # Export relationships
            with open(relationships_path, 'w', encoding='utf-8') as f:
                f.write("relationship_id,source_id,target_id,relationship_type,metadata\n")
                for entity in self.graph.entities.values():
                    for rel in entity.relationships:
                        metadata = json.dumps(rel.metadata).replace(",", ";").replace("\"", "'")
                        f.write(f"{rel.relationship_id},{rel.source_id},{rel.target_id},{rel.relationship_type},{metadata}\n")
            
            output_path = f"{entities_path}, {relationships_path}"
        
        elif format == "graphml":
            # Export as GraphML
            G = nx.DiGraph()
            
            # Add nodes
            for entity_id, entity in self.graph.entities.items():
                G.add_node(
                    entity_id,
                    name=entity.name,
                    entity_type=entity.entity_type,
                    sources="|".join(entity.sources),
                    metadata=json.dumps(entity.metadata)
                )
            
            # Add edges
            for entity in self.graph.entities.values():
                for rel in entity.relationships:
                    G.add_edge(
                        rel.source_id,
                        rel.target_id,
                        relationship_id=rel.relationship_id,
                        relationship_type=rel.relationship_type,
                        metadata=json.dumps(rel.metadata)
                    )
            
            # Write to file
            nx.write_graphml(G, output_path)
        
        else:
            knowledge_graph_logger.error(f"Unsupported export format: {format}")
            return ""
        
        knowledge_graph_logger.info(f"Knowledge graph exported to {output_path}")
        return output_path
    
    def import_knowledge_graph(self, filepath: str, format: str = "json") -> bool:
        """
        Import a knowledge graph from a file.
        
        Args:
            filepath: Path to the file to import
            format: File format (json, graphml)
            
        Returns:
            True if successful, False otherwise
        """
        knowledge_graph_logger.info(f"Importing knowledge graph from {filepath}")
        
        try:
            if format == "json":
                # Import from JSON
                imported_graph = KnowledgeGraph.load(filepath)
                if imported_graph:
                    self.graph = imported_graph
                    return True
            
            elif format == "graphml":
                # Import from GraphML
                G = nx.read_graphml(filepath)
                
                # Create a new knowledge graph
                self.graph = KnowledgeGraph(name="Imported Knowledge Graph")
                
                # Add entities
                for node_id, node_data in G.nodes(data=True):
                    entity = Entity(
                        entity_id=node_id,
                        name=node_data.get("name", node_id),
                        entity_type=node_data.get("entity_type", "unknown"),
                        sources=node_data.get("sources", "").split("|"),
                        metadata=json.loads(node_data.get("metadata", "{}"))
                    )
                    self.graph.add_entity(entity)
                
                # Add relationships
                for source_id, target_id, edge_data in G.edges(data=True):
                    relationship = Relationship(
                        relationship_id=edge_data.get("relationship_id", f"rel_{source_id}_{target_id}"),
                        source_id=source_id,
                        target_id=target_id,
                        relationship_type=edge_data.get("relationship_type", "unknown"),
                        metadata=json.loads(edge_data.get("metadata", "{}"))
                    )
                    self.graph.add_relationship(relationship)
                
                return True
            
            else:
                knowledge_graph_logger.error(f"Unsupported import format: {format}")
                return False
        
        except Exception as e:
            knowledge_graph_logger.error(f"Error importing knowledge graph: {e}")
            return False
        
        return False

# Create a singleton instance
knowledge_graph_builder = KnowledgeGraphBuilder()

async def build_knowledge_graph(entities: List[Entity], relationships: List[Relationship]) -> KnowledgeGraph:
    """
    Build a knowledge graph from entities and relationships.
    
    Args:
        entities: List of entities to add to the graph
        relationships: List of relationships to add to the graph
        
    Returns:
        The constructed knowledge graph
    """
    return await knowledge_graph_builder.build_knowledge_graph(entities, relationships)

async def enrich_knowledge_graph(graph: KnowledgeGraph, new_data: Dict[str, Any]) -> KnowledgeGraph:
    """
    Enrich an existing knowledge graph with new data.
    
    Args:
        graph: The knowledge graph to enrich
        new_data: Dictionary containing new entities and relationships
        
    Returns:
        The enriched knowledge graph
    """
    # Set the builder's graph to the provided graph
    knowledge_graph_builder.graph = graph
    return await knowledge_graph_builder.enrich_knowledge_graph(new_data)

async def query_knowledge_graph(graph: KnowledgeGraph, query: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Query the knowledge graph for specific information.
    
    Args:
        graph: The knowledge graph to query
        query: Dictionary containing query parameters
        
    Returns:
        List of query results
    """
    # Set the builder's graph to the provided graph
    knowledge_graph_builder.graph = graph
    return await knowledge_graph_builder.query_knowledge_graph(query)

async def infer_relationships(graph: KnowledgeGraph) -> List[Relationship]:
    """
    Infer new relationships based on existing knowledge.
    
    Args:
        graph: The knowledge graph to analyze
        
    Returns:
        List of inferred relationships
    """
    # Set the builder's graph to the provided graph
    knowledge_graph_builder.graph = graph
    return await knowledge_graph_builder.infer_relationships()

def visualize_knowledge_graph(graph: KnowledgeGraph, output_path: Optional[str] = None) -> str:
    """
    Generate visualization of the knowledge graph.
    
    Args:
        graph: The knowledge graph to visualize
        output_path: Path to save the visualization
        
    Returns:
        Path to the saved visualization
    """
    # Set the builder's graph to the provided graph
    knowledge_graph_builder.graph = graph
    return knowledge_graph_builder.visualize_knowledge_graph(output_path)

def validate_knowledge_graph(graph: KnowledgeGraph) -> Dict[str, Any]:
    """
    Validate the consistency of the knowledge graph.
    
    Args:
        graph: The knowledge graph to validate
        
    Returns:
        Dictionary with validation results
    """
    # Set the builder's graph to the provided graph
    knowledge_graph_builder.graph = graph
    return knowledge_graph_builder.validate_knowledge_graph()

def export_knowledge_graph(graph: KnowledgeGraph, format: str = "json", output_path: Optional[str] = None) -> str:
    """
    Export the knowledge graph in different formats.
    
    Args:
        graph: The knowledge graph to export
        format: Export format (json, csv, graphml)
        output_path: Path to save the exported file
        
    Returns:
        Path to the exported file
    """
    # Set the builder's graph to the provided graph
    knowledge_graph_builder.graph = graph
    return knowledge_graph_builder.export_knowledge_graph(format, output_path)
