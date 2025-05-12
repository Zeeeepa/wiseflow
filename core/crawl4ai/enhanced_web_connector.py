"""
Enhanced web connector integration module.

This module provides a factory function to create an enhanced web connector
with all the optimized components.
"""

from typing import Dict, Any, Optional

from core.connectors.web import WebConnector
from .enhanced_crawler_strategy import EnhancedCrawlerStrategy
from .enhanced_content_scraping import EnhancedWebScrapingStrategy
from .async_configs import AsyncConfigs
from .async_webcrawler import AsyncWebCrawler


def create_enhanced_web_connector(config: Optional[Dict[str, Any]] = None) -> WebConnector:
    """
    Create an enhanced web connector with optimized components.
    
    This factory function creates a web connector with enhanced crawler strategy
    and content scraping for better performance, error handling, and accuracy.
    
    Args:
        config: Configuration dictionary for the web connector
        
    Returns:
        WebConnector: Enhanced web connector instance
    """
    # Create the web connector
    connector = WebConnector(config)
    
    # Create enhanced crawler configuration
    crawler_config = AsyncConfigs()
    
    # Apply custom configurations if provided
    if config:
        if config.get("max_depth"):
            crawler_config.max_depth = config["max_depth"]
        if config.get("max_pages"):
            crawler_config.max_pages = config["max_pages"]
        if config.get("timeout"):
            crawler_config.timeout = config["timeout"]
        if config.get("user_agent"):
            crawler_config.user_agent = config["user_agent"]
        if config.get("javascript_enabled") is not None:
            crawler_config.javascript_enabled = config["javascript_enabled"]
        if config.get("wait_for_selector"):
            crawler_config.wait_for_selector = config["wait_for_selector"]
        if config.get("wait_time"):
            crawler_config.wait_time = config["wait_time"]
        if config.get("proxy"):
            crawler_config.proxy = config["proxy"]
        if config.get("headers"):
            crawler_config.headers = config["headers"]
    
    # Create enhanced crawler strategy
    enhanced_strategy = EnhancedCrawlerStrategy(
        browser_config=crawler_config,
        logger=None  # Will be set by AsyncWebCrawler
    )
    
    # Create enhanced content scraping strategy
    enhanced_scraping = EnhancedWebScrapingStrategy()
    
    # Set the enhanced strategy's content scraping
    enhanced_strategy.content_scraping_strategy = enhanced_scraping
    
    # Create the crawler with enhanced strategy
    crawler = AsyncWebCrawler(
        config=crawler_config,
        memory_threshold_percent=config.get("memory_threshold_percent", 85.0) if config else 85.0,
        memory_warning_percent=config.get("memory_warning_percent", 75.0) if config else 75.0,
        cooldown_period=config.get("cooldown_period", 300) if config else 300,
        max_retries=config.get("max_retries", 3) if config else 3,
        retry_delay=config.get("retry_delay", 5) if config else 5
    )
    
    # Set the enhanced strategy
    crawler.crawler_strategy = enhanced_strategy
    
    # Set the crawler on the connector
    connector.crawler = crawler
    
    return connector

