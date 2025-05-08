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
import traceback
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
        confidence: float,
        metadata: Dict[str, Any] = None,
        timestamp: Optional[datetime] = None
    ):
        """Initialize a pattern."""
        self.pattern_id = pattern_id or f"pattern_{uuid.uuid4().hex[:8]}"
        self.pattern_type = pattern_type
        self.description = description
        self.entities = entities
        self.sources = sources
        self.confidence = confidence
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
            "confidence": self.confidence,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Pattern':
        """Create a pattern from a dictionary."""
        return cls(
            pattern_id=data.get("pattern_id"),
            pattern_type=data.get("pattern_type", ""),
            description=data.get("description", ""),
            entities=data.get("entities", []),
            sources=data.get("sources", []),
            confidence=data.get("confidence", 0.0),
            metadata=data.get("metadata", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None
        )

class PatternRecognition:
    """Class for recognizing patterns in data."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the pattern recognition engine."""
        self.config = config or {}
        self.min_confidence = self.config.get("min_confidence", 0.5)
        self.min_frequency = self.config.get("min_frequency", 2)
        self.time_window = self.config.get("time_window", 7)  # days
        self.patterns = []
    
    def detect_frequency_patterns(self, entities: List[Entity], min_frequency: int = None) -> List[Pattern]:
        """
        Detect patterns based on entity frequency.
        
        Args:
            entities: List of entities to analyze
            min_frequency: Minimum frequency to consider (overrides instance setting)
            
        Returns:
            List of detected patterns
        """
        if not entities:
            pattern_logger.warning("No entities provided for frequency pattern detection")
            return []
        
        try:
            min_freq = min_frequency or self.min_frequency
            
            # Count entity occurrences
            entity_counts = Counter()
            entity_sources = defaultdict(set)
            entity_objects = {}
            
            for entity in entities:
                entity_counts[entity.name] += 1
                for source in entity.sources:
                    entity_sources[entity.name].add(source)
                entity_objects[entity.name] = entity
            
            # Find frequent entities
            patterns = []
            for entity_name, count in entity_counts.items():
                if count >= min_freq:
                    # Calculate confidence based on frequency and source diversity
                    source_count = len(entity_sources[entity_name])
                    frequency_factor = min(1.0, count / (min_freq * 2))
                    source_factor = min(1.0, source_count / 3)
                    confidence = (frequency_factor * 0.7) + (source_factor * 0.3)
                    
                    entity = entity_objects[entity_name]
                    
                    pattern = Pattern(
                        pattern_id=f"freq_{uuid.uuid4().hex[:8]}",
                        pattern_type="frequency",
                        description=f"Frequent occurrence of {entity_name} ({count} times across {source_count} sources)",
                        entities=[entity.entity_id],
                        sources=list(entity_sources[entity_name]),
                        confidence=confidence,
                        metadata={
                            "frequency": count,
                            "source_count": source_count,
                            "entity_type": entity.entity_type
                        }
                    )
                    patterns.append(pattern)
            
            pattern_logger.info(f"Detected {len(patterns)} frequency patterns")
            return patterns
        except Exception as e:
            pattern_logger.error(f"Error detecting frequency patterns: {str(e)}")
            pattern_logger.error(traceback.format_exc())
            return []
    
    def detect_co_occurrence_patterns(self, entities: List[Entity], time_window: int = None) -> List[Pattern]:
        """
        Detect patterns based on entity co-occurrence.
        
        Args:
            entities: List of entities to analyze
            time_window: Time window in days to consider co-occurrence (overrides instance setting)
            
        Returns:
            List of detected patterns
        """
        if not entities:
            pattern_logger.warning("No entities provided for co-occurrence pattern detection")
            return []
        
        try:
            window = time_window or self.time_window
            
            # Group entities by source and time
            source_entities = defaultdict(list)
            for entity in entities:
                for source in entity.sources:
                    source_entities[source].append(entity)
            
            # Find co-occurring entities
            co_occurrences = Counter()
            entity_pairs = {}
            
            for source, source_entities_list in source_entities.items():
                # Only consider sources with multiple entities
                if len(source_entities_list) < 2:
                    continue
                
                # Check all pairs of entities in this source
                for i in range(len(source_entities_list)):
                    for j in range(i+1, len(source_entities_list)):
                        entity1 = source_entities_list[i]
                        entity2 = source_entities_list[j]
                        
                        # Skip if same entity
                        if entity1.entity_id == entity2.entity_id:
                            continue
                        
                        # Create a unique key for this entity pair
                        pair_key = tuple(sorted([entity1.entity_id, entity2.entity_id]))
                        co_occurrences[pair_key] += 1
                        
                        if pair_key not in entity_pairs:
                            entity_pairs[pair_key] = (entity1, entity2, set())
                        
                        entity_pairs[pair_key][2].add(source)
            
            # Create patterns for significant co-occurrences
            patterns = []
            for pair_key, count in co_occurrences.items():
                if count >= self.min_frequency:
                    entity1, entity2, sources = entity_pairs[pair_key]
                    
                    # Calculate confidence based on frequency and source diversity
                    source_count = len(sources)
                    frequency_factor = min(1.0, count / (self.min_frequency * 2))
                    source_factor = min(1.0, source_count / 3)
                    confidence = (frequency_factor * 0.6) + (source_factor * 0.4)
                    
                    pattern = Pattern(
                        pattern_id=f"co_occur_{uuid.uuid4().hex[:8]}",
                        pattern_type="co_occurrence",
                        description=f"Co-occurrence of {entity1.name} and {entity2.name} ({count} times across {source_count} sources)",
                        entities=[entity1.entity_id, entity2.entity_id],
                        sources=list(sources),
                        confidence=confidence,
                        metadata={
                            "frequency": count,
                            "source_count": source_count,
                            "entity1_type": entity1.entity_type,
                            "entity2_type": entity2.entity_type
                        }
                    )
                    patterns.append(pattern)
            
            pattern_logger.info(f"Detected {len(patterns)} co-occurrence patterns")
            return patterns
        except Exception as e:
            pattern_logger.error(f"Error detecting co-occurrence patterns: {str(e)}")
            pattern_logger.error(traceback.format_exc())
            return []


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
