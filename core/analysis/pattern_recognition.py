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
        Detect correlations between entities and topics.
        
        Args:
            data: List of data items with entities and topics
            entity_field: Field name for the entity
            topic_field: Field name for the topic
            min_correlation: Minimum correlation coefficient to be considered significant
            
        Returns:
            List of correlation patterns
        """
        pattern_logger.info(f"Detecting correlations in {len(data)} data items")
        
        if not data:
            return []
        
        # Extract entities and topics
        entity_topic_pairs = []
        for item in data:
            entities = item.get(entity_field, [])
            topics = item.get(topic_field, [])
            
            if not isinstance(entities, list):
                entities = [entities]
            if not isinstance(topics, list):
                topics = [topics]
            
            for entity in entities:
                for topic in topics:
                    entity_topic_pairs.append((entity, topic))
        
        # Count co-occurrences
        entity_counter = Counter()
        topic_counter = Counter()
        pair_counter = Counter(entity_topic_pairs)
        
        for entity, topic in entity_topic_pairs:
            entity_counter[entity] += 1
            topic_counter[topic] += 1
        
        # Calculate correlations
        patterns = []
        total_items = len(data)
        
        for (entity, topic), pair_count in pair_counter.items():
            entity_count = entity_counter[entity]
            topic_count = topic_counter[topic]
            
            # Calculate phi coefficient (correlation)
            a = pair_count
            b = entity_count - pair_count
            c = topic_count - pair_count
            d = total_items - entity_count - topic_count + pair_count
            
            try:
                phi = (a * d - b * c) / np.sqrt((a + b) * (a + c) * (b + d) * (c + d))
            except ZeroDivisionError:
                phi = 0
            
            if abs(phi) >= min_correlation:
                # Calculate confidence score
                confidence = min(1.0, abs(phi) * 2)  # Scale to 0-1
                
                if confidence >= self.min_confidence:
                    # Create a pattern
                    pattern_id = str(uuid.uuid4())
                    sources = list(set(item.get("source", "unknown") for item in data))
                    
                    correlation_type = "positive" if phi > 0 else "negative"
                    pattern = Pattern(
                        pattern_id=pattern_id,
                        pattern_type=f"{correlation_type}_correlation",
                        description=f"{correlation_type.capitalize()} correlation between entity '{entity}' and topic '{topic}'",
                        entities=[entity],
                        sources=sources,
                        confidence_score=confidence,
                        metadata={
                            "topic": topic,
                            "correlation": phi,
                            "entity_count": entity_count,
                            "topic_count": topic_count,
                            "co_occurrence_count": pair_count,
                            "total_items": total_items
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
        patterns: List[Pattern],
        output_path: Optional[str] = None
    ) -> str:
        """
        Visualize entity correlations as a network graph.
        
        Args:
            patterns: List of correlation patterns
            output_path: Path to save the visualization
            
        Returns:
            Path to the saved visualization
        """
        # Filter correlation patterns
        correlation_patterns = [p for p in patterns if "correlation" in p.pattern_type]
        
        if not correlation_patterns:
            pattern_logger.warning("No correlation patterns to visualize")
            return ""
        
        # Create a graph
        G = nx.Graph()
        
        # Add nodes and edges
        for pattern in correlation_patterns:
            entity = pattern.entities[0]
            topic = pattern.metadata.get("topic", "unknown")
            correlation = pattern.metadata.get("correlation", 0)
            
            # Add nodes
            if entity not in G:
                G.add_node(entity, type="entity")
            if topic not in G:
                G.add_node(topic, type="topic")
            
            # Add edge
            G.add_edge(entity, topic, weight=abs(correlation), correlation_type=pattern.pattern_type)
        
        # Create visualization
        plt.figure(figsize=(12, 10))
        
        # Define node colors
        node_colors = []
        for node in G.nodes():
            if G.nodes[node]["type"] == "entity":
                node_colors.append("skyblue")
            else:
                node_colors.append("lightgreen")
        
        # Define edge colors
        edge_colors = []
        for u, v, data in G.edges(data=True):
            if data["correlation_type"] == "positive_correlation":
                edge_colors.append("green")
            else:
                edge_colors.append("red")
        
        # Define edge widths
        edge_widths = [data["weight"] * 3 for _, _, data in G.edges(data=True)]
        
        # Create layout
        pos = nx.spring_layout(G, seed=42)
        
        # Draw the graph
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=500)
        nx.draw_networkx_edges(G, pos, edge_color=edge_colors, width=edge_widths, alpha=0.7)
        nx.draw_networkx_labels(G, pos, font_size=10)
        
        # Add legend
        plt.legend(
            handles=[
                plt.Line2D([0], [0], color="skyblue", marker="o", markersize=10, linestyle="", label="Entity"),
                plt.Line2D([0], [0], color="lightgreen", marker="o", markersize=10, linestyle="", label="Topic"),
                plt.Line2D([0], [0], color="green", linewidth=2, label="Positive Correlation"),
                plt.Line2D([0], [0], color="red", linewidth=2, label="Negative Correlation")
            ],
            loc="upper right"
        )
        
        plt.title("Entity-Topic Correlation Network")
        plt.axis("off")
        
        # Save visualization
        if output_path is None:
            output_dir = os.path.join(project_dir, "visualizations")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"correlation_network_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        
        plt.savefig(output_path)
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
