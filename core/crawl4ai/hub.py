from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseCrawler(ABC):
    """
    Base class for all crawlers in the Crawl4AI system.
    
    This abstract class defines the interface that all crawler implementations
    must follow. It provides metadata about the crawler and defines the run method
    that must be implemented by subclasses.
    """
    
    __meta__ = {
        "version": "1.0.0",
        "tested_on": [],
        "rate_limit": "10 RPM",
        "description": "Base crawler class",
    }
    
    def __init__(self):
        """Initialize the crawler with default settings."""
        self.config = {}
    
    @abstractmethod
    async def run(self, url: str = "", **kwargs) -> str:
        """
        Run the crawler on the specified URL with the given parameters.
        
        Args:
            url: The URL to crawl
            **kwargs: Additional parameters for the crawler
            
        Returns:
            str: The result of the crawl operation, typically JSON or HTML
        """
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about this crawler.
        
        Returns:
            Dict[str, Any]: Metadata about the crawler
        """
        return self.__meta__

