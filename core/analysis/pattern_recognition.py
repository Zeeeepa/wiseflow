"""
Pattern Recognition Module for Wiseflow.

This module provides functionality for identifying patterns and trends in collected data
across time periods and sources. It supports temporal pattern detection, frequency analysis,
correlation detection between entities and topics, and provides confidence scores for
detected patterns along with visualization capabilities.
"""

from typing import Dict, List, Any, Optional, Union, Tuple, Set
import logging
import uuid
from datetime import datetime, timedelta
import os
import json
import re
from collections import Counter, defaultdict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
from scipy import stats
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN

from ..utils.general_utils import get_logger
from ..utils.pb_api import PbTalker
from . import Entity, Relationship

# Set up logging
project_dir = os.environ.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)
pattern_logger = get_logger('pattern_recognition', project_dir)

# Initialize PocketBase connection
pb = PbTalker(pattern_logger)

class Pattern:
    """Represents a pattern detected in the data."""
    
    def __init__(
        self,
        pattern_id: str,
        pattern_type: str,
        description: str,
        entities: List[str],
        sources: List[str],
        time_period: Optional[Tuple[datetime, datetime]] = None,
        confidence_score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        """Initialize a pattern."""
        self.pattern_id = pattern_id
        self.pattern_type = pattern_type
        self.description = description
        self.entities = entities
        self.sources = sources
        self.time_period = time_period
        self.confidence_score = confidence_score
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the pattern to a dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "entities": self.entities,
            "sources": self.sources,
            "time_period": [t.isoformat() if t else None for t in self.time_period] if self.time_period else None,
            "confidence_score": self.confidence_score,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Pattern':
        """Create a pattern from a dictionary."""
        time_period = None
        if data.get("time_period"):
            time_period = (
                datetime.fromisoformat(data["time_period"][0]) if data["time_period"][0] else None,
                datetime.fromisoformat(data["time_period"][1]) if data["time_period"][1] else None
            )
        
        timestamp = None
        if data.get("timestamp"):
            timestamp = datetime.fromisoformat(data["timestamp"])
        
        return cls(
            pattern_id=data["pattern_id"],
            pattern_type=data["pattern_type"],
            description=data["description"],
            entities=data["entities"],
            sources=data["sources"],
            time_period=time_period,
            confidence_score=data["confidence_score"],
            metadata=data.get("metadata", {}),
            timestamp=timestamp
        )


class PatternRecognition:
    """
    Pattern recognition system for identifying trends and patterns in collected data.
    
    This class provides methods for:
    - Temporal pattern detection
    - Frequency analysis
    - Correlation detection between entities and topics
    - Confidence scoring for detected patterns
    - Visualization of patterns
    """
    
    def __init__(self, min_confidence: float = 0.6):
        """
        Initialize the pattern recognition system.
        
        Args:
            min_confidence: Minimum confidence score for patterns to be considered valid
        """
        self.min_confidence = min_confidence
        self.patterns: List[Pattern] = []
    
    def detect_temporal_patterns(
        self,
        data: List[Dict[str, Any]],
        time_field: str = "timestamp",
        entity_field: str = "entity",
        time_window: timedelta = timedelta(days=7),
        min_occurrences: int = 3
    ) -> List[Pattern]:
        """
        Detect temporal patterns in the data.
        
        Args:
            data: List of data items with timestamps and entities
            time_field: Field name for the timestamp
            entity_field: Field name for the entity
            time_window: Time window for grouping data
            min_occurrences: Minimum number of occurrences to be considered a pattern
            
        Returns:
            List of detected temporal patterns
        """
        pattern_logger.info(f"Detecting temporal patterns in {len(data)} data items")
        
        # Convert timestamps to datetime objects if they are strings
        processed_data = []
        for item in data:
            if isinstance(item[time_field], str):
                item = item.copy()
                item[time_field] = datetime.fromisoformat(item[time_field].replace('Z', '+00:00'))
            processed_data.append(item)
        
        # Sort data by timestamp
        processed_data.sort(key=lambda x: x[time_field])
        
        # Group data by time windows
        time_windows = defaultdict(list)
        if not processed_data:
            return []
            
        start_time = processed_data[0][time_field]
        end_time = processed_data[-1][time_field]
        
        current_window_start = start_time
        while current_window_start <= end_time:
            current_window_end = current_window_start + time_window
            window_key = (current_window_start, current_window_end)
            
            for item in processed_data:
                if current_window_start <= item[time_field] < current_window_end:
                    time_windows[window_key].append(item)
            
            current_window_start = current_window_end
        
        # Analyze entity frequency in each time window
        patterns = []
        for window, window_data in time_windows.items():
            if len(window_data) < min_occurrences:
                continue
                
            # Count entity occurrences
            entity_counter = Counter()
            for item in window_data:
                entities = item.get(entity_field, [])
                if isinstance(entities, list):
                    for entity in entities:
                        entity_counter[entity] += 1
                else:
                    entity_counter[entities] += 1
            
            # Find entities that occur frequently
            for entity, count in entity_counter.items():
                if count >= min_occurrences:
                    # Calculate confidence score based on frequency
                    confidence = min(1.0, count / len(window_data))
                    
                    if confidence >= self.min_confidence:
                        # Create a pattern
                        pattern_id = str(uuid.uuid4())
                        sources = list(set(item.get("source", "unknown") for item in window_data))
                        
                        pattern = Pattern(
                            pattern_id=pattern_id,
                            pattern_type="temporal_frequency",
                            description=f"Frequent occurrence of '{entity}' between {window[0].strftime('%Y-%m-%d')} and {window[1].strftime('%Y-%m-%d')}",
                            entities=[entity],
                            sources=sources,
                            time_period=window,
                            confidence_score=confidence,
                            metadata={
                                "occurrences": count,
                                "total_items": len(window_data)
                            }
                        )
                        
                        patterns.append(pattern)
        
        pattern_logger.info(f"Detected {len(patterns)} temporal patterns")
        self.patterns.extend(patterns)
        return patterns
    
    def analyze_frequency(
        self,
        data: List[Dict[str, Any]],
        entity_field: str = "entity",
        min_frequency: float = 0.1
    ) -> List[Pattern]:
        """
        Analyze frequency of entities in the data.
        
        Args:
            data: List of data items with entities
            entity_field: Field name for the entity
            min_frequency: Minimum frequency (0-1) to be considered significant
            
        Returns:
            List of frequency patterns
        """
        pattern_logger.info(f"Analyzing frequency in {len(data)} data items")
        
        if not data:
            return []
        
        # Count entity occurrences
        entity_counter = Counter()
        for item in data:
            entities = item.get(entity_field, [])
            if isinstance(entities, list):
                for entity in entities:
                    entity_counter[entity] += 1
            else:
                entity_counter[entities] += 1
        
        # Calculate frequencies
        total_items = len(data)
        patterns = []
        
        for entity, count in entity_counter.items():
            frequency = count / total_items
            
            if frequency >= min_frequency:
                # Calculate confidence score based on statistical significance
                # Using binomial test p-value as confidence
                p_value = stats.binom_test(count, total_items, p=min_frequency)
                confidence = 1.0 - p_value
                
                if confidence >= self.min_confidence:
                    # Create a pattern
                    pattern_id = str(uuid.uuid4())
                    sources = list(set(item.get("source", "unknown") for item in data))
                    
                    pattern = Pattern(
                        pattern_id=pattern_id,
                        pattern_type="frequency",
                        description=f"High frequency of '{entity}' ({frequency:.1%})",
                        entities=[entity],
                        sources=sources,
                        confidence_score=confidence,
                        metadata={
                            "occurrences": count,
                            "total_items": total_items,
                            "frequency": frequency
                        }
                    )
                    
                    patterns.append(pattern)
        
        pattern_logger.info(f"Detected {len(patterns)} frequency patterns")
        self.patterns.extend(patterns)
        return patterns
    
    def detect_correlations(
        self,
        data: List[Dict[str, Any]],
        entity_field: str = "entity",
        topic_field: str = "topic",
        min_correlation: float = 0.3
    ) -> List[Pattern]:
        """
        Detect correlations between entities and topics in the data.
        
        Args:
            data: List of data items with entities and topics
            entity_field: Field name for the entity
            topic_field: Field name for the topic
            min_correlation: Minimum correlation coefficient to be considered significant
        
        Returns:
            List of detected correlation patterns
        """
        pattern_logger.info(f"Detecting correlations in {len(data)} data items")
        
        if not data:
            return []
        
        # Extract entities and topics from data
        all_entities = set()
        all_topics = set()
        
        for item in data:
            entities = item.get(entity_field, [])
            topics = item.get(topic_field, [])
            
            if isinstance(entities, list):
                all_entities.update(entities)
            else:
                all_entities.add(entities)
            
            if isinstance(topics, list):
                all_topics.update(topics)
            else:
                all_topics.add(topics)
        
        # Create co-occurrence matrices
        entity_topic_matrix = defaultdict(lambda: defaultdict(int))
        entity_entity_matrix = defaultdict(lambda: defaultdict(int))
        topic_topic_matrix = defaultdict(lambda: defaultdict(int))
        
        # Count co-occurrences
        for item in data:
            entities = item.get(entity_field, [])
            topics = item.get(topic_field, [])
            
            if not isinstance(entities, list):
                entities = [entities]
            
            if not isinstance(topics, list):
                topics = [topics]
            
            # Entity-Topic co-occurrences
            for entity in entities:
                for topic in topics:
                    entity_topic_matrix[entity][topic] += 1
            
            # Entity-Entity co-occurrences
            for i, entity1 in enumerate(entities):
                for entity2 in entities[i+1:]:
                    entity_entity_matrix[entity1][entity2] += 1
                    entity_entity_matrix[entity2][entity1] += 1
            
            # Topic-Topic co-occurrences
            for i, topic1 in enumerate(topics):
                for topic2 in topics[i+1:]:
                    topic_topic_matrix[topic1][topic2] += 1
                    topic_topic_matrix[topic2][topic1] += 1
        
        # Calculate entity and topic frequencies
        entity_counts = Counter()
        topic_counts = Counter()
        
        for item in data:
            entities = item.get(entity_field, [])
            topics = item.get(topic_field, [])
            
            if not isinstance(entities, list):
                entities = [entities]
            
            if not isinstance(topics, list):
                topics = [topics]
            
            for entity in entities:
                entity_counts[entity] += 1
            
            for topic in topics:
                topic_counts[topic] += 1
        
        # Calculate correlations and create patterns
        patterns = []
        
        # Entity-Topic correlations
        for entity in all_entities:
            for topic in all_topics:
                co_occurrence = entity_topic_matrix[entity][topic]
                
                if co_occurrence > 0:
                    # Calculate correlation coefficient using phi coefficient
                    entity_count = entity_counts[entity]
                    topic_count = topic_counts[topic]
                    total_items = len(data)
                    
                    a = co_occurrence  # Both entity and topic present
                    b = entity_count - a  # Entity present, topic absent
                    c = topic_count - a  # Topic present, entity absent
                    d = total_items - a - b - c  # Both entity and topic absent
                    
                    # Calculate phi coefficient
                    try:
                        phi = (a * d - b * c) / np.sqrt((a + b) * (a + c) * (b + d) * (c + d))
                    except ZeroDivisionError:
                        phi = 0
                    
                    # If correlation is significant, create a pattern
                    if abs(phi) >= min_correlation:
                        pattern_id = str(uuid.uuid4())
                        sources = list(set(item.get("source", "unknown") for item in data))
                        
                        # Determine relationship type
                        if phi > 0:
                            relationship_type = "positive_correlation"
                            description = f"Positive correlation between entity '{entity}' and topic '{topic}'"
                        else:
                            relationship_type = "negative_correlation"
                            description = f"Negative correlation between entity '{entity}' and topic '{topic}'"
                        
                        pattern = Pattern(
                            pattern_id=pattern_id,
                            pattern_type=relationship_type,
                            description=description,
                            entities=[entity],
                            sources=sources,
                            time_period=None,  # No specific time period
                            confidence_score=abs(phi),
                            metadata={
                                "topic": topic,
                                "co_occurrence": co_occurrence,
                                "entity_count": entity_count,
                                "topic_count": topic_count,
                                "total_items": total_items,
                                "phi_coefficient": phi
                            }
                        )
                        
                        patterns.append(pattern)
        
        # Entity-Entity correlations
        for entity1 in all_entities:
            for entity2 in all_entities:
                if entity1 >= entity2:  # Skip self-correlations and duplicates
                    continue
                
                co_occurrence = entity_entity_matrix[entity1][entity2]
                
                if co_occurrence > 0:
                    # Calculate correlation coefficient
                    entity1_count = entity_counts[entity1]
                    entity2_count = entity_counts[entity2]
                    total_items = len(data)
                    
                    a = co_occurrence  # Both entities present
                    b = entity1_count - a  # Entity1 present, entity2 absent
                    c = entity2_count - a  # Entity2 present, entity1 absent
                    d = total_items - a - b - c  # Both entities absent
                    
                    # Calculate phi coefficient
                    try:
                        phi = (a * d - b * c) / np.sqrt((a + b) * (a + c) * (b + d) * (c + d))
                    except ZeroDivisionError:
                        phi = 0
                    
                    # If correlation is significant, create a pattern
                    if abs(phi) >= min_correlation:
                        pattern_id = str(uuid.uuid4())
                        sources = list(set(item.get("source", "unknown") for item in data))
                        
                        # Determine relationship type
                        if phi > 0:
                            relationship_type = "entity_co_occurrence"
                            description = f"Entities '{entity1}' and '{entity2}' frequently appear together"
                        else:
                            relationship_type = "entity_mutual_exclusion"
                            description = f"Entities '{entity1}' and '{entity2}' rarely appear together"
                        
                        pattern = Pattern(
                            pattern_id=pattern_id,
                            pattern_type=relationship_type,
                            description=description,
                            entities=[entity1, entity2],
                            sources=sources,
                            time_period=None,  # No specific time period
                            confidence_score=abs(phi),
                            metadata={
                                "co_occurrence": co_occurrence,
                                "entity1_count": entity1_count,
                                "entity2_count": entity2_count,
                                "total_items": total_items,
                                "phi_coefficient": phi
                            }
                        )
                        
                        patterns.append(pattern)
        
        pattern_logger.info(f"Detected {len(patterns)} correlation patterns")
        self.patterns.extend(patterns)
        return patterns
    
    def visualize_temporal_patterns(
        self,
        patterns: List[Pattern],
        output_path: Optional[str] = None
    ) -> str:
        """
        Visualize temporal patterns.
        
        Args:
            patterns: List of temporal patterns
            output_path: Path to save the visualization
            
        Returns:
            Path to the saved visualization
        """
        # Filter temporal patterns
        temporal_patterns = [p for p in patterns if p.pattern_type == "temporal_frequency" and p.time_period]
        
        if not temporal_patterns:
            pattern_logger.warning("No temporal patterns to visualize")
            return ""
        
        # Prepare data for visualization
        data_points = []
        for pattern in temporal_patterns:
            start_time, end_time = pattern.time_period
            mid_time = start_time + (end_time - start_time) / 2
            
            for entity in pattern.entities:
                data_points.append({
                    "time": mid_time,
                    "entity": entity,
                    "confidence": pattern.confidence_score,
                    "occurrences": pattern.metadata.get("occurrences", 0)
                })
        
        # Create DataFrame
        df = pd.DataFrame(data_points)
        
        # Create visualization
        plt.figure(figsize=(12, 8))
        
        # Plot occurrences over time
        plt.subplot(2, 1, 1)
        sns.scatterplot(data=df, x="time", y="occurrences", hue="entity", size="confidence", sizes=(50, 200))
        plt.title("Entity Occurrences Over Time")
        plt.xlabel("Time")
        plt.ylabel("Occurrences")
        plt.xticks(rotation=45)
        
        # Plot confidence over time
        plt.subplot(2, 1, 2)
        sns.lineplot(data=df, x="time", y="confidence", hue="entity")
        plt.title("Pattern Confidence Over Time")
        plt.xlabel("Time")
        plt.ylabel("Confidence Score")
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # Save visualization
        if output_path is None:
            output_dir = os.path.join(project_dir, "visualizations")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"temporal_patterns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        
        plt.savefig(output_path)
        plt.close()
        
        pattern_logger.info(f"Saved temporal pattern visualization to {output_path}")
        return output_path
    
    def visualize_entity_correlations(
        self,
        patterns: List[Pattern] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        Visualize entity correlations as a network.
        
        Args:
            patterns: List of correlation patterns to visualize
            output_path: Path to save the visualization
            
        Returns:
            Path to the saved visualization
        """
        if patterns is None:
            patterns = [p for p in self.patterns if p.pattern_type in 
                       ["entity_co_occurrence", "entity_mutual_exclusion", 
                        "positive_correlation", "negative_correlation"]]
        
        if not patterns:
            pattern_logger.warning("No correlation patterns to visualize")
            return ""
        
        # Create a graph
        G = nx.Graph()
        
        # Add nodes and edges
        for pattern in patterns:
            if len(pattern.entities) >= 2:
                # Entity-Entity correlation
                entity1, entity2 = pattern.entities[:2]
                
                # Add nodes if they don't exist
                if not G.has_node(entity1):
                    G.add_node(entity1, type="entity")
                
                if not G.has_node(entity2):
                    G.add_node(entity2, type="entity")
                
                # Add edge with correlation information
                G.add_edge(
                    entity1, 
                    entity2, 
                    weight=pattern.confidence_score,
                    type=pattern.pattern_type,
                    description=pattern.description
                )
            elif len(pattern.entities) == 1 and "topic" in pattern.metadata:
                # Entity-Topic correlation
                entity = pattern.entities[0]
                topic = pattern.metadata["topic"]
                
                # Add nodes if they don't exist
                if not G.has_node(entity):
                    G.add_node(entity, type="entity")
                
                if not G.has_node(topic):
                    G.add_node(topic, type="topic")
                
                # Add edge with correlation information
                G.add_edge(
                    entity, 
                    topic, 
                    weight=pattern.confidence_score,
                    type=pattern.pattern_type,
                    description=pattern.description
                )
        
        if len(G.nodes()) == 0:
            pattern_logger.warning("No nodes to visualize")
            return ""
        
        # Generate the visualization
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            output_path = f"correlation_network_{timestamp}.png"
        
        plt.figure(figsize=(12, 10))
        
        # Position nodes using spring layout
        pos = nx.spring_layout(G, k=0.3, iterations=50)
        
        # Get node types
        node_types = nx.get_node_attributes(G, "type")
        
        # Draw nodes by type
        entity_nodes = [n for n, t in node_types.items() if t == "entity"]
        topic_nodes = [n for n, t in node_types.items() if t == "topic"]
        
        nx.draw_networkx_nodes(G, pos, nodelist=entity_nodes, node_color="skyblue", 
                              node_size=500, alpha=0.8, label="Entity")
        nx.draw_networkx_nodes(G, pos, nodelist=topic_nodes, node_color="lightgreen", 
                              node_size=500, alpha=0.8, label="Topic")
        
        # Draw edges by type
        edge_types = nx.get_edge_attributes(G, "type")
        
        positive_edges = [(u, v) for (u, v), t in edge_types.items() 
                         if t in ["entity_co_occurrence", "positive_correlation"]]
        negative_edges = [(u, v) for (u, v), t in edge_types.items() 
                         if t in ["entity_mutual_exclusion", "negative_correlation"]]
        
        # Get edge weights for line thickness
        edge_weights = nx.get_edge_attributes(G, "weight")
        
        # Scale weights for visualization
        max_weight = max(edge_weights.values()) if edge_weights else 1.0
        scaled_weights = {e: 1 + 5 * (w / max_weight) for e, w in edge_weights.items()}
        
        # Draw positive correlations
        nx.draw_networkx_edges(G, pos, edgelist=positive_edges, 
                              width=[scaled_weights.get((u, v), 1.0) for u, v in positive_edges],
                              edge_color="green", style="solid", alpha=0.7,
                              label="Positive Correlation")
        
        # Draw negative correlations
        nx.draw_networkx_edges(G, pos, edgelist=negative_edges, 
                              width=[scaled_weights.get((u, v), 1.0) for u, v in negative_edges],
                              edge_color="red", style="dashed", alpha=0.7,
                              label="Negative Correlation")
        
        # Draw labels
        nx.draw_networkx_labels(G, pos, font_size=10, font_family="sans-serif")
        
        plt.title("Entity and Topic Correlation Network")
        plt.legend()
        plt.axis("off")
        
        # Save the figure
        plt.savefig(output_path, format="png", dpi=300, bbox_inches="tight")
        plt.close()
        
        pattern_logger.info(f"Saved correlation network visualization to {output_path}")
        return output_path
    
    def save_patterns(self, output_path: Optional[str] = None) -> str:
        """
        Save detected patterns to a JSON file.
        
        Args:
            output_path: Path to save the patterns
            
        Returns:
            Path to the saved patterns file
        """
        if not self.patterns:
            pattern_logger.warning("No patterns to save")
            return ""
        
        # Prepare data for saving
        patterns_data = [pattern.to_dict() for pattern in self.patterns]
        
        # Save to file
        if output_path is None:
            output_dir = os.path.join(project_dir, "patterns")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"patterns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        with open(output_path, "w") as f:
            json.dump(patterns_data, f, indent=2)
        
        pattern_logger.info(f"Saved {len(self.patterns)} patterns to {output_path}")
        return output_path
    
    def load_patterns(self, input_path: str) -> List[Pattern]:
        """
        Load patterns from a JSON file.
        
        Args:
            input_path: Path to the patterns file
            
        Returns:
            List of loaded patterns
        """
        pattern_logger.info(f"Loading patterns from {input_path}")
        
        with open(input_path, "r") as f:
            patterns_data = json.load(f)
        
        patterns = [Pattern.from_dict(data) for data in patterns_data]
        self.patterns.extend(patterns)
        
        pattern_logger.info(f"Loaded {len(patterns)} patterns")
        return patterns
    
    def get_patterns_by_entity(self, entity: str) -> List[Pattern]:
        """
        Get patterns related to a specific entity.
        
        Args:
            entity: Entity name
            
        Returns:
            List of patterns related to the entity
        """
        return [p for p in self.patterns if entity in p.entities]
    
    def get_patterns_by_time_period(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Pattern]:
        """
        Get patterns within a specific time period.
        
        Args:
            start_time: Start time
            end_time: End time
            
        Returns:
            List of patterns within the time period
        """
        return [
            p for p in self.patterns 
            if p.time_period and p.time_period[0] <= end_time and p.time_period[1] >= start_time
        ]
    
    def get_patterns_by_confidence(self, min_confidence: float) -> List[Pattern]:
        """
        Get patterns with a minimum confidence score.
        
        Args:
            min_confidence: Minimum confidence score
            
        Returns:
            List of patterns with the minimum confidence score
        """
        return [p for p in self.patterns if p.confidence_score >= min_confidence]


def analyze_data_for_patterns(
    data: List[Dict[str, Any]],
    min_confidence: float = 0.6,
    time_field: str = "timestamp",
    entity_field: str = "entity",
    topic_field: str = "topic",
    time_window: timedelta = timedelta(days=7),
    min_occurrences: int = 3,
    min_frequency: float = 0.1,
    min_correlation: float = 0.3,
    visualize: bool = True,
    save_results: bool = True,
    output_dir: Optional[str] = None
) -> Tuple[List[Pattern], Dict[str, str]]:
    """
    Analyze data for patterns and trends.
    
    Args:
        data: List of data items to analyze
        min_confidence: Minimum confidence score for patterns
        time_field: Field name for the timestamp
        entity_field: Field name for the entity
        topic_field: Field name for the topic
        time_window: Time window for temporal pattern detection
        min_occurrences: Minimum occurrences for temporal patterns
        min_frequency: Minimum frequency for frequency analysis
        min_correlation: Minimum correlation coefficient
        visualize: Whether to generate visualizations
        save_results: Whether to save results to files
        output_dir: Directory to save results
        
    Returns:
        Tuple of (patterns, visualization_paths)
    """
    pattern_logger.info(f"Analyzing {len(data)} data items for patterns")
    
    # Initialize pattern recognition
    pattern_recognition = PatternRecognition(min_confidence=min_confidence)
    
    # Detect temporal patterns
    temporal_patterns = pattern_recognition.detect_temporal_patterns(
        data=data,
        time_field=time_field,
        entity_field=entity_field,
        time_window=time_window,
        min_occurrences=min_occurrences
    )
    
    # Analyze frequency
    frequency_patterns = pattern_recognition.analyze_frequency(
        data=data,
        entity_field=entity_field,
        min_frequency=min_frequency
    )
    
    # Detect correlations
    correlation_patterns = pattern_recognition.detect_correlations(
        data=data,
        entity_field=entity_field,
        topic_field=topic_field,
        min_correlation=min_correlation
    )
    
    # Combine all patterns
    all_patterns = temporal_patterns + frequency_patterns + correlation_patterns
    
    # Generate visualizations
    visualization_paths = {}
    if visualize:
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Temporal patterns visualization
        if temporal_patterns:
            temporal_viz_path = None
            if output_dir:
                temporal_viz_path = os.path.join(output_dir, f"temporal_patterns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            viz_path = pattern_recognition.visualize_temporal_patterns(
                patterns=temporal_patterns,
                output_path=temporal_viz_path
            )
            if viz_path:
                visualization_paths["temporal"] = viz_path
        
        # Correlation network visualization
        if correlation_patterns:
            correlation_viz_path = None
            if output_dir:
                correlation_viz_path = os.path.join(output_dir, f"correlation_network_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            viz_path = pattern_recognition.visualize_entity_correlations(
                patterns=correlation_patterns,
                output_path=correlation_viz_path
            )
            if viz_path:
                visualization_paths["correlation"] = viz_path
    
    # Save results
    if save_results and all_patterns:
        patterns_path = None
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            patterns_path = os.path.join(output_dir, f"patterns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        saved_path = pattern_recognition.save_patterns(output_path=patterns_path)
        if saved_path:
            visualization_paths["patterns_json"] = saved_path
    
    pattern_logger.info(f"Analysis complete. Found {len(all_patterns)} patterns.")
    return all_patterns, visualization_paths


def fetch_data_from_pocketbase(
    focus_point: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Fetch data from PocketBase for pattern analysis.
    
    Args:
        focus_point: Focus point to filter by
        start_date: Start date for data
        end_date: End date for data
        limit: Maximum number of records to fetch
        
    Returns:
        List of data items
    """
    pattern_logger.info(f"Fetching data from PocketBase for pattern analysis")
    
    # Build filter
    filter_str = ""
    if focus_point:
        filter_str += f'tag="{focus_point}"'
    
    if start_date:
        if filter_str:
            filter_str += " && "
        filter_str += f'created>="{start_date.isoformat()}"'
    
    if end_date:
        if filter_str:
            filter_str += " && "
        filter_str += f'created<="{end_date.isoformat()}"'
    
    # Fetch data
    try:
        infos = pb.get_infos(filter_str=filter_str, limit=limit)
        
        # Process data for pattern analysis
        processed_data = []
        for info in infos:
            # Extract entities from content using simple regex
            # In a real implementation, you would use the entity extraction from data_mining.py
            content = info.get("content", "")
            entities = re.findall(r'\b[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*\b', content)
            
            # Extract topics (simplified)
            topics = [info.get("tag", "")]
            
            processed_data.append({
                "id": info.get("id"),
                "timestamp": info.get("created"),
                "entity": entities,
                "topic": topics,
                "source": info.get("url", ""),
                "content": content
            })
        
        pattern_logger.info(f"Fetched {len(processed_data)} data items from PocketBase")
        return processed_data
    
    except Exception as e:
        pattern_logger.error(f"Error fetching data from PocketBase: {str(e)}")
        return []


if __name__ == "__main__":
    # Example usage
    data = fetch_data_from_pocketbase(limit=500)
    
    if data:
        patterns, viz_paths = analyze_data_for_patterns(
            data=data,
            min_confidence=0.6,
            visualize=True,
            save_results=True
        )
        
        print(f"Found {len(patterns)} patterns")
        for path_type, path in viz_paths.items():
            print(f"{path_type} visualization saved to: {path}")
    else:
        print("No data available for pattern analysis")
