"""
Core Interface Module for WiseFlow.

This module provides a centralized interface for accessing the core components
of the WiseFlow system, making it easier to import and use them consistently.
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import core components
from core.utils.pb_api import PbTalker
from core.utils.general_utils import get_logger
from core.config import config, PROJECT_DIR
from core.event_system import (
    EventType, Event, subscribe, publish, publish_sync,
    create_focus_point_event, create_task_event
)
from core.utils.error_handling import handle_exceptions, WiseflowError

class WiseflowInterface:
    """
    Central interface for accessing WiseFlow components.
    
    This class provides a unified interface for accessing the various components
    of the WiseFlow system, making it easier to use them consistently across
    different parts of the application.
    """
    
    def __init__(self, project_dir: Optional[str] = None):
        """
        Initialize the WiseFlow interface.
        
        Args:
            project_dir: Optional directory for storing project files
        """
        self.project_dir = project_dir or PROJECT_DIR
        if self.project_dir:
            os.makedirs(self.project_dir, exist_ok=True)
        
        # Initialize logger
        self.logger = get_logger('wiseflow_interface', self.project_dir)
        
        # Initialize components
        self.pb = PbTalker(self.logger)
        
        # Initialize LLM
        self.model = config.get("PRIMARY_MODEL", "")
        if not self.model:
            raise ValueError("PRIMARY_MODEL not set, please set it in environment variables or edit core/.env")
        self.secondary_model = config.get("SECONDARY_MODEL", self.model)
        
        # Publish system startup event
        self._publish_startup_event()
    
    def _publish_startup_event(self):
        """Publish system startup event."""
        try:
            from core.event_system import create_system_startup_event, publish_sync
            event = create_system_startup_event({
                "version": getattr(self, "__version__", "unknown"),
                "project_dir": self.project_dir
            })
            publish_sync(event)
        except Exception as e:
            self.logger.warning(f"Failed to publish startup event: {e}")
    
    @handle_exceptions(default_message="Failed to get active focus points", log_error=True)
    def get_active_focus_points(self) -> List[Dict[str, Any]]:
        """
        Get all active focus points.
        
        Returns:
            List of active focus points
        """
        return self.pb.read(collection_name='focus_point', filter="activated=true")
    
    @handle_exceptions(default_message="Failed to get focus point", log_error=True)
    def get_focus_point(self, focus_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a focus point by ID.
        
        Args:
            focus_id: ID of the focus point
            
        Returns:
            Focus point dictionary or None if not found
        """
        return self.pb.read_one(collection_name='focus_point', id=focus_id)
    
    @handle_exceptions(default_message="Failed to get info items", log_error=True)
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
    
    @handle_exceptions(default_message="Failed to save info item", log_error=True)
    def save_info_item(self, info: Dict[str, Any]) -> str:
        """
        Save an information item to the database.
        
        Args:
            info: Information item to save
            
        Returns:
            ID of the saved item
        """
        info_id = self.pb.add(collection_name='infos', body=info)
        
        # Publish event
        if info_id:
            try:
                event = create_focus_point_event(
                    EventType.DATA_PROCESSED,
                    info.get("tag", ""),
                    {"info_id": info_id}
                )
                publish_sync(event)
            except Exception as e:
                self.logger.warning(f"Failed to publish data processed event: {e}")
        
        return info_id
    
    @handle_exceptions(default_message="Failed to update info item", log_error=True)
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
    
    @handle_exceptions(default_message="Failed to process URL", log_error=True)
    async def process_url(self, url: str, focus_id: str) -> List[Dict[str, Any]]:
        """
        Process a URL and extract information based on focus point.
        
        Args:
            url: URL to process
            focus_id: ID of the focus point
            
        Returns:
            List of extracted information items
        """
        # Import here to avoid circular imports
        from core.agents.get_info import get_info, pre_process
        from core.crawl4ai import AsyncWebCrawler, CacheMode
        from core.agents.get_info_prompts import get_info_prompts
        
        self.logger.info(f"Processing URL: {url}")
        
        # Get focus point
        focus = self.get_focus_point(focus_id)
        if not focus:
            self.logger.error(f"Focus point with ID {focus_id} not found")
            return []
        
        # Initialize crawler
        crawler = AsyncWebCrawler()
        await crawler.start()
        
        try:
            # Configure crawler
            from core.crawl4ai.crawler_config import CrawlerRunConfig
            crawler_config = CrawlerRunConfig()
            crawler_config.cache_mode = CacheMode.ENABLED
            
            # Crawl URL
            result = await crawler.arun(url=url, config=crawler_config)
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
            
            # Get prompts for information extraction
            prompts = get_info_prompts(focus.get("focuspoint", ""), focus.get("explanation", ""))
            
            # Extract information
            infos = await get_info(contents, link_dict, prompts, author, publish_date, _logger=self.logger)
            
            # Add URL and focus ID to each info item
            for info in infos:
                info['url'] = url
                info['url_title'] = title
                info['tag'] = focus_id
                
                # Save to database
                self.save_info_item(info)
            
            return infos
        
        finally:
            await crawler.close()
    
    @handle_exceptions(default_message="Failed to generate insights", log_error=True)
    async def generate_insights(self, focus_id: str, time_period_days: int = 7) -> Dict[str, Any]:
        """
        Generate insights for a focus point.
        
        Args:
            focus_id: ID of the focus point
            time_period_days: Number of days to look back for information items
            
        Returns:
            Dictionary containing the generated insights
        """
        # Import here to avoid circular imports
        from core.agents.insights import generate_insights_for_focus
        
        insights = await generate_insights_for_focus(focus_id, time_period_days)
        
        # Publish event
        if insights:
            try:
                event = create_focus_point_event(
                    EventType.INSIGHT_GENERATED,
                    focus_id,
                    {"insights": insights}
                )
                publish_sync(event)
            except Exception as e:
                self.logger.warning(f"Failed to publish insight generated event: {e}")
        
        return insights
    
    @handle_exceptions(default_message="Failed to get insights", log_error=True)
    async def get_insights(self, focus_id: str, max_age_hours: int = 24) -> Dict[str, Any]:
        """
        Get insights for a focus point, generating new ones if needed.
        
        Args:
            focus_id: ID of the focus point
            max_age_hours: Maximum age of insights in hours before regenerating
            
        Returns:
            Dictionary containing the insights
        """
        # Import here to avoid circular imports
        from core.agents.insights import get_insights_for_focus
        
        return await get_insights_for_focus(focus_id, max_age_hours)
    
    def shutdown(self):
        """Shutdown the interface and publish shutdown event."""
        try:
            from core.event_system import create_system_shutdown_event, publish_sync
            event = create_system_shutdown_event()
            publish_sync(event)
        except Exception as e:
            self.logger.warning(f"Failed to publish shutdown event: {e}")

# Create a singleton instance for easy access
wiseflow = WiseflowInterface()

