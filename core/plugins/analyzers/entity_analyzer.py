"""
Entity analyzer plugin for extracting and analyzing entities from text.
"""

import re
import logging
import traceback
from typing import Any, Dict, List, Optional, Union, Set, Tuple
import nltk
from nltk.tokenize import word_tokenize
from nltk.chunk import ne_chunk
from nltk.tag import pos_tag
import networkx as nx

from core.plugins.base import AnalyzerPlugin
from core.analysis import Entity, Relationship

logger = logging.getLogger(__name__)

# Download NLTK resources if needed
try:
    nltk.data.find('punkt')
    nltk.data.find('averaged_perceptron_tagger')
    nltk.data.find('maxent_ne_chunker')
    nltk.data.find('words')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
    nltk.download('maxent_ne_chunker', quiet=True)
    nltk.download('words', quiet=True)


class EntityAnalyzer(AnalyzerPlugin):
    """Analyzer for extracting and analyzing entities from text."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the entity analyzer.
        
        Args:
            config: Configuration dictionary with the following keys:
                - extract_relationships: Whether to extract entity relationships (default: True)
                - build_knowledge_graph: Whether to build a knowledge graph (default: True)
                - min_relationship_confidence: Minimum confidence for relationships (default: 0.5)
                - max_entities: Maximum number of entities to extract (default: 100)
                - entity_types: List of entity types to extract (default: all)
        """
        super().__init__(config)
        self.extract_relationships = self.config.get('extract_relationships', True)
        self.build_knowledge_graph = self.config.get('build_knowledge_graph', True)
        self.min_relationship_confidence = self.config.get('min_relationship_confidence', 0.5)
        self.max_entities = self.config.get('max_entities', 100)
        self.entity_types = self.config.get('entity_types', ['PERSON', 'ORGANIZATION', 'LOCATION', 'GPE', 'FACILITY', 'DATE', 'TIME', 'MONEY', 'PERCENT'])
        self.entity_cache = {}
        self.relationship_cache = {}
    
    def initialize(self) -> bool:
        """Initialize the entity analyzer.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Verify NLTK resources are available
            nltk.data.find('punkt')
            nltk.data.find('averaged_perceptron_tagger')
            nltk.data.find('maxent_ne_chunker')
            nltk.data.find('words')
            
            self.initialized = True
            return True
        except LookupError as e:
            logger.error(f"Failed to initialize EntityAnalyzer: {str(e)}")
            return False
    
    def analyze(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze text to extract entities and relationships.
        
        Args:
            text: Text to analyze
            context: Additional context for the analysis
            
        Returns:
            Dictionary with analysis results
        """
        if not self.initialized:
            logger.warning("EntityAnalyzer not initialized, initializing now")
            if not self.initialize():
                return {"error": "Failed to initialize EntityAnalyzer"}
        
        try:
            # Extract entities using NLTK
            entities = self._extract_entities_nltk(text)
            
            # Limit the number of entities
            if len(entities) > self.max_entities:
                logger.warning(f"Too many entities ({len(entities)}), limiting to {self.max_entities}")
                entities = entities[:self.max_entities]
            
            # Extract relationships if configured
            relationships = []
            if self.extract_relationships and len(entities) > 1:
                relationships = self._extract_relationships(text, entities)
            
            # Build knowledge graph if configured
            knowledge_graph = None
            if self.build_knowledge_graph and entities:
                knowledge_graph = self._build_knowledge_graph(entities, relationships)
            
            # Prepare the result
            result = {
                "entities": [e.to_dict() for e in entities],
                "entity_count": len(entities),
                "relationship_count": len(relationships)
            }
            
            if relationships:
                result["relationships"] = [r.to_dict() for r in relationships]
            
            if knowledge_graph:
                result["knowledge_graph"] = knowledge_graph
            
            return result
        except Exception as e:
            logger.error(f"Error in entity analysis: {str(e)}")
            logger.error(traceback.format_exc())
            return {"error": str(e)}
    
    def _extract_entities_nltk(self, text: str) -> List[Entity]:
        """Extract entities from text using NLTK.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of extracted entities
        """
        try:
            # Tokenize and tag the text
            tokens = word_tokenize(text)
            tagged = pos_tag(tokens)
            
            # Extract named entities
            named_entities = ne_chunk(tagged)
            
            # Process the named entities
            entities = []
            current_entity = []
            current_type = None
            
            for chunk in named_entities:
                if hasattr(chunk, 'label'):
                    # This is a named entity
                    entity_type = chunk.label()
                    
                    # Skip entity types not in the configured list
                    if self.entity_types and entity_type not in self.entity_types:
                        continue
                    
                    # Extract the entity text
                    entity_text = ' '.join(word for word, tag in chunk.leaves())
                    
                    # Create an Entity object
                    entity = Entity(
                        name=entity_text,
                        entity_type=entity_type,
                        sources=["nltk_extraction"],
                        metadata={
                            "confidence": 0.8,  # NLTK entities are generally reliable
                            "extraction_method": "nltk"
                        }
                    )
                    
                    # Cache the entity to avoid duplicates
                    cache_key = f"{entity_text}|{entity_type}"
                    if cache_key in self.entity_cache:
                        entity = self.entity_cache[cache_key]
                    else:
                        self.entity_cache[cache_key] = entity
                    
                    entities.append(entity)
            
            logger.info(f"Extracted {len(entities)} entities using NLTK")
            return entities
        except Exception as e:
            logger.error(f"Error extracting entities with NLTK: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    def _extract_relationships(self, text: str, entities: List[Entity]) -> List[Relationship]:
        """Extract relationships between entities.
        
        Args:
            text: Text to extract relationships from
            entities: List of entities to find relationships between
            
        Returns:
            List of extracted relationships
        """
        try:
            # Simple co-occurrence based relationship extraction
            # In a real implementation, this would use more sophisticated techniques
            relationships = []
            
            # Only consider entities that are close to each other in the text
            for i in range(len(entities)):
                for j in range(i+1, len(entities)):
                    entity1 = entities[i]
                    entity2 = entities[j]
                    
                    # Skip if same entity
                    if entity1.entity_id == entity2.entity_id:
                        continue
                    
                    # Check if the entities are mentioned close to each other
                    # This is a simple heuristic and could be improved
                    if entity1.name in text and entity2.name in text:
                        idx1 = text.find(entity1.name)
                        idx2 = text.find(entity2.name)
                        
                        if abs(idx1 - idx2) < 100:  # Entities within 100 characters of each other
                            # Create a relationship
                            relationship_type = "co_occurrence"
                            confidence = 0.6  # Simple co-occurrence has moderate confidence
                            
                            # Determine a more specific relationship type based on entity types
                            if entity1.entity_type == "PERSON" and entity2.entity_type == "ORGANIZATION":
                                relationship_type = "affiliation"
                                confidence = 0.7
                            elif entity1.entity_type == "PERSON" and entity2.entity_type == "PERSON":
                                relationship_type = "association"
                                confidence = 0.6
                            elif entity1.entity_type == "ORGANIZATION" and entity2.entity_type == "LOCATION":
                                relationship_type = "located_in"
                                confidence = 0.7
                            
                            # Skip low-confidence relationships
                            if confidence < self.min_relationship_confidence:
                                continue
                            
                            # Create the relationship
                            relationship = Relationship(
                                source_id=entity1.entity_id,
                                target_id=entity2.entity_id,
                                relationship_type=relationship_type,
                                metadata={
                                    "confidence": confidence,
                                    "extraction_method": "co_occurrence",
                                    "distance": abs(idx1 - idx2)
                                }
                            )
                            
                            # Cache the relationship to avoid duplicates
                            cache_key = f"{entity1.entity_id}|{entity2.entity_id}|{relationship_type}"
                            if cache_key in self.relationship_cache:
                                relationship = self.relationship_cache[cache_key]
                            else:
                                self.relationship_cache[cache_key] = relationship
                            
                            relationships.append(relationship)
            
            logger.info(f"Extracted {len(relationships)} relationships")
            return relationships
        except Exception as e:
            logger.error(f"Error extracting relationships: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    def _build_knowledge_graph(self, entities: List[Entity], relationships: List[Relationship]) -> Dict[str, Any]:
        """Build a knowledge graph from entities and relationships.
        
        Args:
            entities: List of extracted entities
            relationships: List of extracted relationships
            
        Returns:
            Dict[str, Any]: Knowledge graph representation
        """
        try:
            # Create a directed graph
            G = nx.DiGraph()
            
            # Add entities as nodes
            for entity in entities:
                G.add_node(entity.entity_id, type=entity.entity_type)
                
            # Add relationships as edges
            for rel in relationships:
                G.add_edge(
                    rel.source_id,
                    rel.target_id,
                    type=rel.relationship_type,
                    confidence=rel.metadata['confidence']
                )
                
            # Convert to serializable format
            nodes = []
            for node in G.nodes(data=True):
                nodes.append({
                    'id': node[0],
                    'type': node[1]['type']
                })
                
            edges = []
            for edge in G.edges(data=True):
                edges.append({
                    'source': edge[0],
                    'target': edge[1],
                    'type': edge[2]['type'],
                    'confidence': edge[2]['confidence']
                })
                
            # Calculate basic graph metrics
            metrics = {
                'node_count': G.number_of_nodes(),
                'edge_count': G.number_of_edges(),
                'density': nx.density(G)
            }
            
            # Identify central entities
            if G.number_of_nodes() > 0:
                try:
                    centrality = nx.degree_centrality(G)
                    central_entities = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:5]
                    metrics['central_entities'] = [{'entity': e[0], 'centrality': e[1]} for e in central_entities]
                except Exception as e:
                    logger.error(f"Error calculating centrality: {str(e)}")
                    
            return {
                'nodes': nodes,
                'edges': edges,
                'metrics': metrics
            }
            
        except Exception as e:
            logger.error(f"Error building knowledge graph: {str(e)}")
            return {'nodes': [], 'edges': [], 'metrics': {}}
