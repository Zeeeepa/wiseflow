"""
Service adapters for the Code Search Connector.

This module provides service-specific adapters for different code hosting services.
"""

from typing import Dict, Any, Optional, Type
import logging

from .base import CodeSearchService
from .github import GitHubService
from .gitlab import GitLabService
from .bitbucket import BitbucketService
from .sourcegraph import SourcegraphService
from .searchcode import SearchcodeService

logger = logging.getLogger(__name__)

# Registry of available services
SERVICE_REGISTRY: Dict[str, Type[CodeSearchService]] = {
    "github": GitHubService,
    "gitlab": GitLabService,
    "bitbucket": BitbucketService,
    "sourcegraph": SourcegraphService,
    "searchcode": SearchcodeService
}

def get_service(service_name: str, config: Dict[str, Any]) -> Optional[CodeSearchService]:
    """
    Get a service adapter instance.
    
    Args:
        service_name: Name of the service
        config: Service configuration
        
    Returns:
        CodeSearchService: Service adapter instance or None if not found
    """
    service_class = SERVICE_REGISTRY.get(service_name.lower())
    if not service_class:
        logger.warning(f"Service '{service_name}' not found in registry")
        return None
    
    return service_class(config)
"""

