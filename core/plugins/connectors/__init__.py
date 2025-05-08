"""
Connector plugins for Wiseflow.
"""

from core.plugins.base import ConnectorPlugin, plugin_manager
from core.plugins.exceptions import PluginInterfaceError

# Import connector plugins
try:
    from core.plugins.connectors.github_connector import GitHubConnector
    # Validate plugin implementation
    GitHubConnector.validate_implementation()
    # Register connector
    plugin_manager.register_connector('github', GitHubConnector)
except (ImportError, PluginInterfaceError) as e:
    import logging
    logging.getLogger(__name__).error(f"Failed to load GitHubConnector: {e}")

try:
    from core.plugins.connectors.youtube_connector import YouTubeConnector
    # Validate plugin implementation
    YouTubeConnector.validate_implementation()
    # Register connector
    plugin_manager.register_connector('youtube', YouTubeConnector)
except (ImportError, PluginInterfaceError) as e:
    import logging
    logging.getLogger(__name__).error(f"Failed to load YouTubeConnector: {e}")

try:
    from core.plugins.connectors.code_search_connector import CodeSearchConnector
    # Validate plugin implementation
    CodeSearchConnector.validate_implementation()
    # Register connector
    plugin_manager.register_connector('code_search', CodeSearchConnector)
except (ImportError, PluginInterfaceError) as e:
    import logging
    logging.getLogger(__name__).error(f"Failed to load CodeSearchConnector: {e}")

try:
    from core.plugins.connectors.research_connector import ResearchConnector
    # Validate plugin implementation
    ResearchConnector.validate_implementation()
    # Register connector
    plugin_manager.register_connector('research', ResearchConnector)
except (ImportError, PluginInterfaceError) as e:
    import logging
    logging.getLogger(__name__).error(f"Failed to load ResearchConnector: {e}")

__all__ = [
    'ConnectorPlugin',
    'GitHubConnector',
    'YouTubeConnector',
    'CodeSearchConnector',
    'ResearchConnector'
]
