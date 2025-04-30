"""
Analyzer plugins for Wiseflow.
"""

from core.plugins.base import registry
from core.plugins.analyzers.entity_analyzer import EntityAnalyzer
from core.plugins.analyzers.trend_analyzer import TrendAnalyzer

# Register analyzers
registry.register_analyzer('entity', EntityAnalyzer)
registry.register_analyzer('trend', TrendAnalyzer)

__all__ = [
    'EntityAnalyzer',
    'TrendAnalyzer'
]

