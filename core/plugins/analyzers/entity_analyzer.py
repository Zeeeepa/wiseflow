"""
Entity analyzer plugin for extracting and analyzing entities from text.
"""

import re
import logging
from typing import Any, Dict, List, Optional, Union, Set, Tuple
import nltk
from nltk.tokenize import word_tokenize
from nltk.chunk import ne_chunk
from nltk.tag import pos_tag
import networkx as nx

from core.plugins.base import AnalyzerPlugin

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
        
    def initialize(self) -> bool:
        """Initialize the entity analyzer.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        self.initialized = True
        return True
        
    def analyze(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Analyze text data for entities.
        
        Args:
            data: Text data to analyze
            **kwargs: Additional parameters:
                - extract_relationships: Override config setting
                - build_knowledge_graph: Override config setting
                - min_relationship_confidence: Override config setting
                - max_entities: Override config setting
                - entity_types: Override config setting
                
        Returns:
            Dict[str, Any]: Analysis results containing entities and relationships
        """
        if not self.initialized:
            self.initialize()
            
        # Get text from input data
        if isinstance(data, str):
            text = data
        elif isinstance(data, dict) and 'processed_text' in data:
            # Handle output from TextProcessor
            text = data['processed_text']
        elif hasattr(data, 'text') or hasattr(data, 'content'):
            # Handle requests.Response or similar objects
            text = getattr(data, 'text', None) or getattr(data, 'content', '').decode('utf-8')
        else:
            # Try to convert to string
            try:
                text = str(data)
            except Exception as e:
                logger.error(f"Could not convert data to text: {str(e)}")
                return {'error': 'Invalid input data type', 'entities': []}
                
        # Override config settings with kwargs if provided
        extract_relationships = kwargs.get('extract_relationships', self.extract_relationships)
        build_knowledge_graph = kwargs.get('build_knowledge_graph', self.build_knowledge_graph)
        min_relationship_confidence = kwargs.get('min_relationship_confidence', self.min_relationship_confidence)
        max_entities = kwargs.get('max_entities', self.max_entities)
        entity_types = kwargs.get('entity_types', self.entity_types)
        
        # Extract entities
        entities = self._extract_entities(text, entity_types, max_entities)
        
        result = {'entities': entities}
        
        # Extract relationships if requested
        if extract_relationships and len(entities) > 1:
            relationships = self._extract_relationships(text, entities, min_relationship_confidence)
            result['relationships'] = relationships
            
        # Build knowledge graph if requested
        if build_knowledge_graph and len(entities) > 0:
            if 'relationships' not in result:
                relationships = self._extract_relationships(text, entities, min_relationship_confidence)
                result['relationships'] = relationships
                
            graph = self._build_knowledge_graph(entities, result['relationships'])
            result['knowledge_graph'] = graph
            
        return result
        
    def _extract_entities(self, text: str, entity_types: List[str], max_entities: int) -> List[Dict[str, Any]]:
        """Extract entities from text.
        
        Args:
            text: Input text
            entity_types: List of entity types to extract
            max_entities: Maximum number of entities to extract
            
        Returns:
            List[Dict[str, Any]]: List of extracted entities with metadata
        """
        try:
            # Tokenize text
            tokens = word_tokenize(text)
            
            # Part-of-speech tagging
            tagged = pos_tag(tokens)
            
            # Named entity recognition
            chunks = ne_chunk(tagged)
            
            # Extract entities
            entities = []
            entity_set = set()  # To track unique entities
            
            for chunk in chunks:
                if hasattr(chunk, 'label') and chunk.label() in entity_types:
                    entity_text = ' '.join(c[0] for c in chunk)
                    entity_type = chunk.label()
                    
                    # Skip if already processed or if we've reached the maximum
                    if entity_text.lower() in entity_set or len(entities) >= max_entities:
                        continue
                        
                    entity_set.add(entity_text.lower())
                    
                    # Find positions in text
                    positions = []
                    for match in re.finditer(re.escape(entity_text), text):
                        positions.append((match.start(), match.end()))
                        
                    # Create entity object
                    entity = {
                        'text': entity_text,
                        'type': entity_type,
                        'positions': positions[:10],  # Limit to 10 positions
                        'confidence': 1.0  # Default confidence
                    }
                    
                    entities.append(entity)
                    
                    if len(entities) >= max_entities:
                        break
                        
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            return []
            
    def _extract_relationships(self, text: str, entities: List[Dict[str, Any]], min_confidence: float) -> List[Dict[str, Any]]:
        """Extract relationships between entities.
        
        Args:
            text: Input text
            entities: List of extracted entities
            min_confidence: Minimum confidence for relationships
            
        Returns:
            List[Dict[str, Any]]: List of extracted relationships with metadata
        """
        relationships = []
        
        try:
            # Create a simple co-occurrence based relationship extraction
            # Entities that appear close to each other in text are likely related
            
            # Create a map of entity text to entity object
            entity_map = {entity['text']: entity for entity in entities}
            
            # Split text into sentences
            sentences = nltk.sent_tokenize(text)
            
            for sentence in sentences:
                # Find entities in this sentence
                sentence_entities = []
                for entity_text in entity_map:
                    if entity_text in sentence:
                        sentence_entities.append(entity_map[entity_text])
                        
                # Create relationships between entities in the same sentence
                for i in range(len(sentence_entities)):
                    for j in range(i + 1, len(sentence_entities)):
                        entity1 = sentence_entities[i]
                        entity2 = sentence_entities[j]
                        
                        # Calculate confidence based on entity types and distance
                        # This is a simple heuristic and can be improved
                        confidence = 0.7  # Base confidence for entities in same sentence
                        
                        # Adjust confidence based on entity types
                        if entity1['type'] == 'PERSON' and entity2['type'] == 'ORGANIZATION':
                            confidence += 0.1  # Person-Organization relationships are common
                        elif entity1['type'] == 'ORGANIZATION' and entity2['type'] == 'PERSON':
                            confidence += 0.1
                        elif entity1['type'] == 'PERSON' and entity2['type'] == 'LOCATION':
                            confidence += 0.05  # Person-Location relationships
                        elif entity1['type'] == 'LOCATION' and entity2['type'] == 'PERSON':
                            confidence += 0.05
                            
                        # Only include relationships with sufficient confidence
                        if confidence >= min_confidence:
                            relationship = {
                                'source': entity1['text'],
                                'source_type': entity1['type'],
                                'target': entity2['text'],
                                'target_type': entity2['type'],
                                'type': 'co-occurrence',  # Default relationship type
                                'confidence': confidence,
                                'context': sentence[:100] + '...' if len(sentence) > 100 else sentence
                            }
                            
                            # Check if this relationship already exists
                            is_duplicate = False
                            for rel in relationships:
                                if (rel['source'] == relationship['source'] and rel['target'] == relationship['target']) or \
                                   (rel['source'] == relationship['target'] and rel['target'] == relationship['source']):
                                    is_duplicate = True
                                    # Update confidence if this instance has higher confidence
                                    if relationship['confidence'] > rel['confidence']:
                                        rel['confidence'] = relationship['confidence']
                                        rel['context'] = relationship['context']
                                    break
                                    
                            if not is_duplicate:
                                relationships.append(relationship)
                                
            return relationships
            
        except Exception as e:
            logger.error(f"Error extracting relationships: {str(e)}")
            return []
            
    def _build_knowledge_graph(self, entities: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
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
                G.add_node(entity['text'], type=entity['type'])
                
            # Add relationships as edges
            for rel in relationships:
                G.add_edge(
                    rel['source'],
                    rel['target'],
                    type=rel['type'],
                    confidence=rel['confidence']
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

