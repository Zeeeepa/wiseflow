"""
Connector plugins for Wiseflow.

This module provides connector plugins for various data sources.
"""

import logging
from typing import Dict, Any, Optional, List, Type

from core.plugins.base import ConnectorPlugin, plugin_manager
from core.connectors import ConnectorBase

logger = logging.getLogger(__name__)

# Register connector plugins
def register_connector_plugins():
    """
    Register all connector plugins with the plugin manager.
    
    This function discovers and registers all connector plugins.
    """
    try:
        # Import connector classes
        from core.connectors.academic import AcademicConnector
        from core.connectors.code_search import CodeSearchConnector
        from core.connectors.github import GitHubConnector
        from core.connectors.web import WebConnector
        from core.connectors.youtube import YouTubeConnector
        
        # Register connectors
        plugin_manager.register_connector(AcademicConnector.name, AcademicConnector)
        plugin_manager.register_connector(CodeSearchConnector.name, CodeSearchConnector)
        plugin_manager.register_connector(GitHubConnector.name, GitHubConnector)
        plugin_manager.register_connector(WebConnector.name, WebConnector)
        plugin_manager.register_connector(YouTubeConnector.name, YouTubeConnector)
        
        logger.info("Registered connector plugins")
    except ImportError as e:
        logger.warning(f"Failed to import connector plugins: {e}")
    except Exception as e:
        logger.error(f"Error registering connector plugins: {e}")
