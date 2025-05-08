"""
Connector plugins for Wiseflow.
"""

from core.plugins.base import ConnectorPlugin, plugin_manager
from core.plugins.connectors.github_connector import GitHubConnector
from core.plugins.connectors.youtube_connector import YouTubeConnector
from core.plugins.connectors.code_search_connector import CodeSearchConnector
from core.plugins.connectors.research_connector import ResearchConnector

# Register connectors
plugin_manager.register_connector('github', GitHubConnector)
plugin_manager.register_connector('youtube', YouTubeConnector)
plugin_manager.register_connector('code_search', CodeSearchConnector)
plugin_manager.register_connector('research', ResearchConnector)

__all__ = [
    'ConnectorPlugin',
    'GitHubConnector',
    'YouTubeConnector',
    'CodeSearchConnector',
    'ResearchConnector'
]
