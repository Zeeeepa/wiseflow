"""
Analyzer plugins for Wiseflow.
"""

from core.plugins.base import AnalyzerPlugin, plugin_manager
from core.plugins.analyzers.entity_analyzer import EntityAnalyzer
from core.plugins.analyzers.trend_analyzer import TrendAnalyzer

# Register analyzers
plugin_manager.register_analyzer('entity', EntityAnalyzer)
plugin_manager.register_analyzer('trend', TrendAnalyzer)

__all__ = [
    'AnalyzerPlugin',
    'EntityAnalyzer',
    'TrendAnalyzer'
]
