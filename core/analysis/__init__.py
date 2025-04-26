"""
Analysis module for WiseFlow.

This module provides functions for analyzing collected data
and extracting insights.
"""

# Import core data structures
from .models import Entity, Relationship, KnowledgeGraph

from .data_mining import (
    extract_entities as extract_entities_dm,
    extract_topics,
    extract_sentiment,
    extract_relationships,
    analyze_temporal_patterns,
    generate_knowledge_graph,
    analyze_info_items,
    get_analysis_for_focus
)

from .entity_extraction import (
    extract_entities,
    store_entities
)

from .entity_linking import (
    link_entities,
    resolve_entity,
    link_entities_across_sources,
    manual_correction
)

from .pattern_recognition import (
    Pattern,
    PatternRecognition,
    analyze_data_for_patterns
)

from .trend_analysis import (
    TimeGranularity,
    analyze_trends,
    get_trend_analysis_for_focus
)

__all__ = [
    # Data mining functions
    'extract_entities_dm',
    'extract_topics',
    'extract_sentiment',
    'extract_relationships',
    'analyze_temporal_patterns',
    'generate_knowledge_graph',
    'analyze_info_items',
    'get_analysis_for_focus',
    
    # Pattern recognition functions
    'Pattern',
    'PatternRecognition',
    'analyze_data_for_patterns',
    
    # Trend analysis functions
    'TimeGranularity',
    'analyze_trends',
    'get_trend_analysis_for_focus',
    
    # Core data structures
    'Entity',
    'Relationship',
    'KnowledgeGraph'
]
