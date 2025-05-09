"""
Connector plugins for Wiseflow.
"""

import logging
import importlib
import traceback
from typing import Dict, Any, Type

from core.plugins.base import ConnectorPlugin, plugin_manager

logger = logging.getLogger(__name__)

# Dictionary to store connector classes
connector_classes = {}

def register_connector(name: str, connector_class: Type[ConnectorPlugin]) -> None:
    """
    Register a connector class.
    
    Args:
        name: Name of the connector
        connector_class: Connector class to register
    """
    connector_classes[name] = connector_class
    logger.debug(f"Registered connector: {name}")

def get_connector_class(name: str) -> Type[ConnectorPlugin]:
    """
    Get a connector class by name.
    
    Args:
        name: Name of the connector
        
    Returns:
        Connector class if found, None otherwise
    """
    return connector_classes.get(name)

# Import connector classes
try:
    from core.plugins.connectors.github_connector import GitHubConnector
    register_connector('github', GitHubConnector)
except ImportError as e:
    logger.warning(f"Could not import GitHubConnector: {e}")
    logger.debug(f"Traceback: {traceback.format_exc()}")

try:
    from core.plugins.connectors.youtube_connector import YouTubeConnector
    register_connector('youtube', YouTubeConnector)
except ImportError as e:
    logger.warning(f"Could not import YouTubeConnector: {e}")
    logger.debug(f"Traceback: {traceback.format_exc()}")

try:
    from core.plugins.connectors.code_search_connector import CodeSearchConnector
    register_connector('code_search', CodeSearchConnector)
except ImportError as e:
    logger.warning(f"Could not import CodeSearchConnector: {e}")
    logger.debug(f"Traceback: {traceback.format_exc()}")

try:
    from core.plugins.connectors.research_connector import ResearchConnector
    register_connector('research', ResearchConnector)
except ImportError as e:
    logger.warning(f"Could not import ResearchConnector: {e}")
    logger.debug(f"Traceback: {traceback.format_exc()}")

# Register connectors with the plugin manager
for name, connector_class in connector_classes.items():
    try:
        plugin_manager.register_connector(name, connector_class)
        logger.info(f"Registered connector with plugin manager: {name}")
    except Exception as e:
        logger.error(f"Failed to register connector {name} with plugin manager: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")

__all__ = [
    'ConnectorPlugin',
    'register_connector',
    'get_connector_class'
] + list(connector_classes.keys())
