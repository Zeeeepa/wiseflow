"""
Core Interface Module for Wiseflow.

This module provides a centralized interface for accessing the core components
of the Wiseflow system, making it easier to import and use them consistently.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import core components
from core.utils.pb_api import PbTalker
from core.utils.general_utils import get_logger
from core.agents.get_info import (
    pre_process,
    extract_info_from_img,
    get_author_and_publish_date,
    get_more_related_urls,
    get_info
)
from core.agents.insights import (
    generate_trend_analysis,
    generate_entity_analysis,
    generate_insight_summary,
    generate_insights_for_focus,
    get_insights_for_focus
)
from core.crawl4ai import AsyncWebCrawler, CacheMode
from core.plugins import PluginManager
from core.connectors import ConnectorBase, DataItem
from core.references import ReferenceManager
from core.analysis import (
    extract_entities,
    extract_topics,
    extract_sentiment,
    extract_relationships,
    analyze_temporal_patterns,
    generate_knowledge_graph,
    analyze_info_items,
    get_analysis_for_focus
)
from core.task import AsyncTaskManager, Task, create_task_id
from core.llms.openai_wrapper import openai_llm
from core.llms.litellm_wrapper import LiteLLMWrapper

class WiseflowInterface:
    """
    Central interface for accessing Wiseflow components.
    
    This class provides a unified interface for accessing the various components
    of the Wiseflow system, making it easier to use them consistently across
    different parts of the application.
    """
    
    def __init__(self, project_dir: Optional[str] = None):
        """
        Initialize the Wiseflow interface.
        
        Args:
            project_dir: Optional directory for storing project files
        """
        self.project_dir = project_dir or os.environ.get("PROJECT_DIR", "")
        if self.project_dir:
            os.makedirs(self.project_dir, exist_ok=True)
        
        # Initialize logger
        self.logger = get_logger('wiseflow_interface', self.project_dir)
        
        # Initialize components
        self.pb = PbTalker(self.logger)
        self.plugin_manager = PluginManager(plugins_dir="core")
        self.reference_manager = ReferenceManager(storage_path=os.path.join(self.project_dir, "references"))
        
        # Initialize LLM
        self.model = os.environ.get("PRIMARY_MODEL", "")
        if not self.model:
            raise ValueError("PRIMARY_MODEL not set, please set it in environment variables or edit core/.env")
        self.secondary_model = os.environ.get("SECONDARY_MODEL", self.model)
        
        # Load plugins
        self._load_plugins()
    
    def _load_plugins(self):
        """Load and initialize plugins."""
        self.logger.info("Loading plugins...")
        plugins = self.plugin_manager.load_all_plugins()
        self.logger.info(f"Loaded {len(plugins)} plugins")
        
        # Initialize plugins with configurations
        configs = {}  # Load configurations from database or config files
        results = self.plugin_manager.initialize_all_plugins(configs)
        
        for name, success in results.items():
            if success:
                self.logger.info(f"Initialized plugin: {name}")
            else:
                self.logger.error(f"Failed to initialize plugin: {name}")
    
    async def process_url(self, url: str, focus_id: str, get_info_prompts: List[str]) -> List[Dict[str, Any]]:
        """
        Process a URL and extract information based on focus point.
        
        Args:
            url: URL to process
            focus_id: ID of the focus point
            get_info_prompts: Prompts for information extraction
            
        Returns:
            List of extracted information items
        """
        self.logger.info(f"Processing URL: {url}")
        
        # Use web connector if available
        web_connector = self.plugin_manager.get_plugin("web_connector")
        if web_connector and isinstance(web_connector, ConnectorBase):
            self.logger.info("Using web connector plugin for data collection")
            data_items = await self._collect_from_connector("web_connector", {"urls": [url]})
            
            results = []
            for data_item in data_items:
                focus = self.pb.read_one(collection_name='focus_point', id=focus_id)
                if not focus:
                    self.logger.error(f"Focus point with ID {focus_id} not found")
                    continue
                
                processed_results = await self._process_data_with_plugins(data_item, focus, get_info_prompts)
                results.extend(processed_results)
            
            return results
        
        # Fall back to default crawler
        self.logger.info("Web connector plugin not available, using default crawler")
        crawler = AsyncWebCrawler()
        await crawler.start()
        
        try:
            result = await crawler.arun(url=url)
            if not result.success:
                self.logger.warning(f'{url} failed to crawl')
                return []
            
            # Process the crawled content
            raw_markdown = result.markdown
            metadata_dict = result.metadata if result.metadata else {}
            media_dict = result.media if result.media else {}
            used_img = [d['src'] for d in media_dict.get('images', [])]
            
            title = metadata_dict.get('title', '')
            base_url = metadata_dict.get('base', '')
            author = metadata_dict.get('author', '')
            publish_date = metadata_dict.get('publish_date', '')
            
            # Pre-process the content
            recognized_img_cache = {}
            existing_urls = set()
            link_dict, links_parts, contents, recognized_img_cache = await pre_process(
                raw_markdown, base_url, used_img, recognized_img_cache, existing_urls
            )
            
            # Extract information
            infos = await get_info(contents, link_dict, get_info_prompts, author, publish_date, _logger=self.logger)
            
            # Add URL and focus ID to each info item
            for info in infos:
                info['url'] = url
                info['url_title'] = title
                info['tag'] = focus_id
            
            return infos
        
        finally:
            await crawler.close()
    
    async def _collect_from_connector(self, connector_name: str, params: dict) -> List[DataItem]:
        """Collect data from a connector."""
        connector = self.plugin_manager.get_plugin(connector_name)
        
        if not connector or not isinstance(connector, ConnectorBase):
            self.logger.error(f"Connector {connector_name} not found or not a valid connector")
            return []
        
        try:
            return connector.collect(params)
        except Exception as e:
            self.logger.error(f"Error collecting data from connector {connector_name}: {e}")
            return []
    
    async def _process_data_with_plugins(self, data_item: DataItem, focus: dict, get_info_prompts: list[str]) -> List[Dict[str, Any]]:
        """Process a data item using the appropriate processor plugin."""
        # Get the focus point processor
        processor_name = "text_processor"
        processor = self.plugin_manager.get_plugin(processor_name)
        
        if not processor:
            self.logger.warning(f"Processor {processor_name} not found, falling back to default processing")
            # Fall back to default processing
            if data_item.content_type.startswith("text/"):
                # Process using default method
                infos = await get_info(
                    [data_item.content],
                    {},
                    get_info_prompts,
                    data_item.metadata.get("author", ""),
                    data_item.metadata.get("timestamp", ""),
                    _logger=self.logger
                )
                
                # Add metadata to each info item
                for info in infos:
                    info['url'] = data_item.url or ""
                    info['url_title'] = data_item.metadata.get("title", "")
                    info['tag'] = focus["id"]
                
                return infos
            return []
        
        try:
            # Process the data item
            processed_data = processor.process(data_item, {
                "focus_point": focus.get("focuspoint", ""),
                "explanation": focus.get("explanation", ""),
                "prompts": get_info_prompts
            })
            
            # Extract processed content
            results = []
            if processed_data and processed_data.processed_content:
                for info in processed_data.processed_content:
                    if isinstance(info, dict):
                        info['url'] = data_item.url or ""
                        info['url_title'] = data_item.metadata.get("title", "")
                        info['tag'] = focus["id"]
                        results.append(info)
            
            return results
        except Exception as e:
            self.logger.error(f"Error processing data item: {e}")
            return []
    
    async def generate_insights(self, focus_id: str, time_period_days: int = 7) -> Dict[str, Any]:
        """
        Generate insights for a focus point.
        
        Args:
            focus_id: ID of the focus point
            time_period_days: Number of days to look back for information items
            
        Returns:
            Dictionary containing the generated insights
        """
        return await generate_insights_for_focus(focus_id, time_period_days)
    
    async def get_insights(self, focus_id: str, max_age_hours: int = 24) -> Dict[str, Any]:
        """
        Get insights for a focus point, generating new ones if needed.
        
        Args:
            focus_id: ID of the focus point
            max_age_hours: Maximum age of insights in hours before regenerating
            
        Returns:
            Dictionary containing the insights
        """
        return await get_insights_for_focus(focus_id, max_age_hours)
    
    def get_active_focus_points(self) -> List[Dict[str, Any]]:
        """
        Get all active focus points.
        
        Returns:
            List of active focus points
        """
        return self.pb.read(collection_name='focus_point', filter="activated=true")
    
    def get_focus_point(self, focus_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a focus point by ID.
        
        Args:
            focus_id: ID of the focus point
            
        Returns:
            Focus point dictionary or None if not found
        """
        return self.pb.read_one(collection_name='focus_point', id=focus_id)
    
    def get_info_items(self, focus_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get information items for a focus point.
        
        Args:
            focus_id: ID of the focus point
            limit: Maximum number of items to return
            
        Returns:
            List of information items
        """
        return self.pb.read(
            collection_name='infos',
            filter=f"tag='{focus_id}'",
            sort="-created",
            limit=limit
        )
    
    def save_info_item(self, info: Dict[str, Any]) -> str:
        """
        Save an information item to the database.
        
        Args:
            info: Information item to save
            
        Returns:
            ID of the saved item
        """
        return self.pb.add(collection_name='infos', body=info)
    
    def update_info_item(self, info_id: str, data: Dict[str, Any]) -> bool:
        """
        Update an information item in the database.
        
        Args:
            info_id: ID of the information item
            data: Data to update
            
        Returns:
            True if successful, False otherwise
        """
        return self.pb.update(collection_name='infos', id=info_id, data=data)

# Create a singleton instance for easy access
wiseflow = WiseflowInterface()

