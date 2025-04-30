"""
Connector plugins for Wiseflow.
"""

from core.plugins.base import registry
from core.plugins.connectors.github_connector import GitHubConnector
from core.plugins.connectors.youtube_connector import YouTubeConnector
from core.plugins.connectors.code_search_connector import CodeSearchConnector

# Register connectors
registry.register_connector('github', GitHubConnector)
registry.register_connector('youtube', YouTubeConnector)
registry.register_connector('code_search', CodeSearchConnector)

__all__ = [
    'GitHubConnector',
    'YouTubeConnector',
    'CodeSearchConnector'
]

