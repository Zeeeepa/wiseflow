"""
Processor plugins for Wiseflow.
"""

from core.plugins.base import ProcessorPlugin, plugin_manager
from core.plugins.exceptions import PluginInterfaceError

# Import processor plugins
try:
    from core.plugins.processors.text_processor import TextProcessor
    # Validate plugin implementation
    TextProcessor.validate_implementation()
    # Register processor
    plugin_manager.register_processor('text', TextProcessor)
except (ImportError, PluginInterfaceError) as e:
    import logging
    logging.getLogger(__name__).error(f"Failed to load TextProcessor: {e}")

__all__ = [
    'ProcessorPlugin',
    'TextProcessor'
]
