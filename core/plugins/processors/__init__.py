"""
Processor plugins for Wiseflow.
"""

from core.plugins.base import ProcessorPlugin, plugin_manager
from core.plugins.processors.text_processor import TextProcessor

# Register processors
plugin_manager.register_processor('text', TextProcessor)

__all__ = [
    'ProcessorPlugin',
    'TextProcessor'
]
