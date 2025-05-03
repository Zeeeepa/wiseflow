"""
Research module for wiseflow.
"""

from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI
from core.plugins.connectors.research.graph import run_linear_research

__all__ = [
    'Configuration',
    'ResearchMode',
    'SearchAPI',
    'run_linear_research'
]

