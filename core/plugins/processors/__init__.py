"""
Processor plugins for Wiseflow.
"""

from core.plugins.base import registry
from core.plugins.processors.text_processor import TextProcessor

# Register processors
registry.register_processor('text', TextProcessor)

__all__ = [
    'TextProcessor'
]

