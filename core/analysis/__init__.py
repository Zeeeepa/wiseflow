"""
Analysis module for WiseFlow.

This module provides functions for analyzing collected data
and extracting insights.
"""


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
    extract_entities_batch,
    store_entities
)

from .entity_linking import (
    link_entities,
    resolve_entity,
    link_entities_across_sources,
    manual_correction
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
    
    # Entity extraction functions
    'extract_entities',
    'extract_entities_batch',
    'store_entities',
    
    # Entity linking functions
    'link_entities',
    'resolve_entity',
    'link_entities_across_sources',
    'manual_correction'
]
