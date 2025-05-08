import json
import re
from typing import Dict, List, Any, Optional, Union
from bs4 import BeautifulSoup
import logging
import asyncio
from .utils import sanitize_input_encode

logger = logging.getLogger(__name__)

class ExtractionStrategy:
    """
    Base class for content extraction strategies.
    
    This class defines the interface for extracting structured data from HTML content.
    """
    
    def __init__(self):
        """Initialize the extraction strategy."""
        pass
    
    def run(self, url: str, sections: List[str], **kwargs) -> Any:
        """
        Run the extraction strategy on the given HTML sections.
        
        Args:
            url: The URL of the page being processed
            sections: List of HTML sections to extract data from
            **kwargs: Additional parameters for the extraction
            
        Returns:
            Any: The extracted data
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    async def arun(self, url: str, sections: List[str], **kwargs) -> Any:
        """
        Asynchronously run the extraction strategy on the given HTML sections.
        
        Args:
            url: The URL of the page being processed
            sections: List of HTML sections to extract data from
            **kwargs: Additional parameters for the extraction
            
        Returns:
            Any: The extracted data
        """
        return await asyncio.to_thread(self.run, url, sections, **kwargs)


class JsonCssExtractionStrategy(ExtractionStrategy):
    """
    Extract structured data from HTML using CSS selectors defined in a schema.
    
    This strategy uses a JSON schema to define how to extract data from HTML using
    CSS selectors. The schema can be provided directly or generated using LLM.
    """
    
    def __init__(self, schema: Optional[Dict[str, Any]] = None):
        """
        Initialize the JSON CSS extraction strategy.
        
        Args:
            schema: Optional schema defining the extraction rules
        """
        super().__init__()
        self.schema = schema or {}
    
    def run(self, url: str, sections: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Extract structured data from HTML sections using the defined schema.
        
        Args:
            url: The URL of the page being processed
            sections: List of HTML sections to extract data from
            **kwargs: Additional parameters for the extraction
            
        Returns:
            List[Dict[str, Any]]: List of extracted items
        """
        if not self.schema:
            logger.warning("No schema provided for extraction")
            return []
        
        results = []
        for html in sections:
            if not html:
                continue
                
            soup = BeautifulSoup(html, 'html.parser')
            
            # Get the container selector from the schema
            container_selector = self.schema.get('container_selector', '')
            if container_selector:
                containers = soup.select(container_selector)
            else:
                # If no container selector, use the whole document
                containers = [soup]
            
            # Extract data from each container
            for container in containers:
                item = {}
                for field, field_config in self.schema.get('fields', {}).items():
                    selector = field_config.get('selector', '')
                    attribute = field_config.get('attribute', '')
                    
                    if not selector:
                        continue
                        
                    elements = container.select(selector)
                    if not elements:
                        item[field] = None
                        continue
                        
                    if attribute:
                        if attribute == 'text':
                            item[field] = elements[0].get_text(strip=True)
                        else:
                            item[field] = elements[0].get(attribute)
                    else:
                        item[field] = elements[0].get_text(strip=True)
                
                if item:
                    results.append(item)
        
        return results
    
    @staticmethod
    def generate_schema(html: str, target_json_example: str, query: str) -> Dict[str, Any]:
        """
        Generate a schema for extraction using LLM.
        
        This method would typically use an LLM to generate a schema based on the
        provided HTML, target JSON example, and query. For now, we'll return a
        basic schema that can be enhanced later.
        
        Args:
            html: The HTML content to analyze
            target_json_example: Example of the desired JSON output
            query: Natural language query describing what to extract
            
        Returns:
            Dict[str, Any]: Generated schema for extraction
        """
        # In a real implementation, this would call an LLM to generate the schema
        # For now, we'll return a basic schema
        try:
            target_json = json.loads(target_json_example)
            fields = {}
            
            for field in target_json.keys():
                fields[field] = {
                    "selector": f".{field}",  # Basic selector based on field name
                    "attribute": "text"
                }
            
            return {
                "container_selector": "div.result",  # Generic container selector
                "fields": fields
            }
        except Exception as e:
            logger.error(f"Error generating schema: {str(e)}")
            return {
                "container_selector": "",
                "fields": {}
            }

