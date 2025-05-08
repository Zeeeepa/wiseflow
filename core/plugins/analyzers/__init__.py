"""
Analyzer plugins for Wiseflow.
"""

from core.plugins.base import AnalyzerPlugin, plugin_manager
from core.plugins.exceptions import PluginInterfaceError

# Import analyzer plugins
try:
    from core.plugins.analyzers.entity_analyzer import EntityAnalyzer
    # Validate plugin implementation
    EntityAnalyzer.validate_implementation()
    # Register analyzer
    plugin_manager.register_analyzer('entity', EntityAnalyzer)
except (ImportError, PluginInterfaceError) as e:
    import logging
    logging.getLogger(__name__).error(f"Failed to load EntityAnalyzer: {e}")

try:
    from core.plugins.analyzers.trend_analyzer import TrendAnalyzer
    # Validate plugin implementation
    TrendAnalyzer.validate_implementation()
    # Register analyzer
    plugin_manager.register_analyzer('trend', TrendAnalyzer)
except (ImportError, PluginInterfaceError) as e:
    import logging
    logging.getLogger(__name__).error(f"Failed to load TrendAnalyzer: {e}")

__all__ = [
    'AnalyzerPlugin',
    'EntityAnalyzer',
    'TrendAnalyzer'
]
