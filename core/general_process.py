# -*- coding: utf-8 -*-
"""
General processing module for WiseFlow.

This module contains the main processing logic for WiseFlow, including:
- Information extraction from various sources
- Processing data with plugins
- Collecting data from connectors
- Processing URLs with crawlers
- Generating insights for focus points

The module integrates with various components of WiseFlow, such as:
- LLM integration for information extraction
- Plugin system for extensibility
- Connectors for data collection
- Knowledge graph for entity and relationship management
- Reference management for contextual understanding
- Event system for notifications

Example usage:
    from core.general_process import process_focus_point
    
    # Process a focus point
    await process_focus_point(focus_id="focus_point_id")
"""

import os  # Add missing import
import json
import asyncio
import time
import traceback
from urllib.parse import urlparse
from datetime import datetime
import feedparser

from core.imports import (
    wiseflow_logger,
    PbTalker,
    extract_and_convert_dates,
    is_chinese,
    isURL,
    pre_process,
    extract_info_from_img,
    get_author_and_publish_date,
    get_more_related_urls,
    get_info,
    InsightExtractor,
    run_v4_async,
    AsyncWebCrawler,
    CacheMode,
    ConnectorBase,
    DataItem,
    initialize_all_connectors,
    ReferenceManager,
    process_item_with_images,
    integrate_multimodal_analysis_with_knowledge_graph,
    KnowledgeGraphBuilder,
    config,
    Event,
    EventType,
    publish,
    publish_sync
)

# Import CrawlerRunConfig
from core.crawl4ai.async_configs import CrawlerRunConfig

# Initialize PocketBase client
pb = PbTalker(wiseflow_logger)

# Initialize plugin manager
from core.plugins import PluginManager
plugin_manager = PluginManager()

# Initialize reference manager
project_dir = config.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)
reference_manager = ReferenceManager(storage_path=os.path.join(project_dir, "references"))

# Initialize insight extractor
insight_extractor = InsightExtractor(pb_client=pb)

# Initialize knowledge graph builder
knowledge_graph_builder = KnowledgeGraphBuilder(name="Wiseflow Knowledge Graph")

async def info_process(url: str, 
                       url_title: str, 
                       author: str, 
                       publish_date: str, 
                       contents: list, 
                       link_dict: dict, 
                       focus_id: str,
                       get_info_prompts: list[str]):
    """
    Process information from a URL and save it to the database.
    
    This function extracts information from the provided content using LLMs,
    saves it to the database, and optionally performs multimodal analysis
    if enabled.
    
    Args:
        url: URL of the content source
        url_title: Title of the URL
        author: Author of the content
        publish_date: Publication date of the content
        contents: List of content strings to process
        link_dict: Dictionary of links in the content
        focus_id: ID of the focus point
        get_info_prompts: List of prompts for the LLM
        
    Returns:
        List of processed item IDs
    """
    # Extract information using LLM
    infos = await get_info(contents, link_dict, get_info_prompts, author, publish_date, _logger=wiseflow_logger)
    
    if infos:
        wiseflow_logger.debug(f'get {len(infos)} infos, will save to pb')

    processed_items = []
    for info in infos:
        info['url'] = url
        info['url_title'] = url_title
        info['tag'] = focus_id
        
        # Check if this info already exists to avoid duplicates
        existing_infos = pb.read('infos', filter=f'tag="{focus_id}" && url="{url}" && content="{info["content"]}"', limit=1)
        if existing_infos:
            wiseflow_logger.debug(f'Info already exists, skipping: {info["content"][:50]}...')
            continue
        
        # Extract and convert dates in the content
        if 'content' in info and info['content']:
            dates = extract_and_convert_dates(info['content'])
            if dates:
                info['dates'] = dates
        
        # Determine language
        if 'content' in info and info['content']:
            info['is_chinese'] = is_chinese(info['content'])
        
        # Add timestamp
        info['created'] = datetime.now().isoformat()
        
        # Save to database
        info_id = await pb.create('infos', info)
        if info_id:
            processed_items.append(info_id)
        
        # Process multimodal analysis if enabled
        if config.get("ENABLE_MULTIMODAL", False):
            try:
                # Check if the info contains image URLs
                if 'images' in info and info['images']:
                    wiseflow_logger.info(f'Processing multimodal analysis for info with {len(info["images"])} images')
                    
                    # Process the item with images
                    multimodal_result = await process_item_with_images(
                        item_id=info_id,
                        content=info.get('content', ''),
                        image_urls=info['images'],
                        focus_point=pb.read_one('focus_point', id=focus_id).get('focuspoint', '')
                    )
                    
                    # Update the info with multimodal analysis results
                    if multimodal_result:
                        # Retry a few times if the item is not immediately available
                        max_retries = 3
                        retry_count = 0
                        updated_info = None
                        
                        while retry_count < max_retries:
                            updated_info = pb.read_one('infos', id=info_id)
                            if updated_info:
                                break
                            retry_count += 1
                            await asyncio.sleep(1)
                        
                        if updated_info:
                            updated_info['multimodal_analysis'] = multimodal_result
                            pb.update('infos', info_id, updated_info)
                            
                            # Integrate with knowledge graph if enabled
                            if config.get("ENABLE_KNOWLEDGE_GRAPH", False):
                                await integrate_multimodal_analysis_with_knowledge_graph(
                                    info_id=info_id,
                                    multimodal_result=multimodal_result,
                                    knowledge_graph=knowledge_graph_builder.graph
                                )
                        else:
                            wiseflow_logger.error(f"Failed to retrieve item {info_id} after {max_retries} attempts")
            except Exception as e:
                wiseflow_logger.error(f'Error processing multimodal analysis: {e}')
                wiseflow_logger.debug(f'Traceback: {traceback.format_exc()}')
    
    return processed_items

async def process_data_with_plugins(data_item: DataItem, focus: dict, get_info_prompts: list[str]):
    """
    Process a data item using the appropriate processor plugin.
    
    This function processes a data item using the appropriate processor plugin
    based on the content type. If no suitable plugin is found, it falls back to
    the default processing method.
    
    Args:
        data_item: Data item to process
        focus: Focus point dictionary
        get_info_prompts: List of prompts for the LLM
        
    Returns:
        List of processed item IDs
    """
    # Get the focus point processor
    processor_name = "text_processor"
    processor = plugin_manager.get_plugin(processor_name)
    
    if not processor:
        wiseflow_logger.warning(f"Processor {processor_name} not found, falling back to default processing")
        # Fall back to default processing
        if data_item.content_type.startswith("text/"):
            # Process using default method
            return await info_process(
                data_item.url or "", 
                data_item.metadata.get("title", ""), 
                data_item.metadata.get("author", ""), 
                data_item.metadata.get("publish_date", ""), 
                [data_item.content],
                data_item.metadata.get("links", {}), 
                focus["id"],
                get_info_prompts
            )
        return []
    
    try:
        # Process the data item
        processed_data = processor.process(data_item, {
            "focus_point": focus.get("focuspoint", ""),
            "explanation": focus.get("explanation", ""),
            "prompts": get_info_prompts
        })
        
        # Save processed data
        processed_items = []
        if processed_data and processed_data.processed_content:
            for info in processed_data.processed_content:
                if isinstance(info, dict):
                    info['url'] = data_item.url or ""
                    info['url_title'] = data_item.metadata.get("title", "")
                    info['tag'] = focus["id"]
                    info_id = pb.add(collection_name='infos', body=info)
                    if info_id:
                        processed_items.append(info_id)
                    else:
                        wiseflow_logger.error('add info failed, writing to cache_file')
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        with open(os.path.join(project_dir, f'{timestamp}_cache_infos.json'), 'w', encoding='utf-8') as f:
                            json.dump(info, f, ensure_ascii=False, indent=4)
        
        return processed_items
    except Exception as e:
        wiseflow_logger.error(f"Error processing data item: {e}")
        wiseflow_logger.debug(f"Traceback: {traceback.format_exc()}")
        return []


async def collect_from_connector(connector_name: str, params: dict) -> list[DataItem]:
    """
    Collect data from a connector.
    
    This function collects data from a connector using the provided parameters.
    
    Args:
        connector_name: Name of the connector to use
        params: Parameters for the connector
        
    Returns:
        List of collected data items
    """
    connector = plugin_manager.get_plugin(connector_name)
    if not connector or not isinstance(connector, ConnectorBase):
        wiseflow_logger.error(f"Connector {connector_name} not found or not a valid connector")
        return []
    
    try:
        # Collect data from the connector
        data_items = await connector.collect(params)
        return data_items
    except Exception as e:
        wiseflow_logger.error(f"Error collecting data from connector {connector_name}: {e}")
        wiseflow_logger.debug(f"Traceback: {traceback.format_exc()}")
        return []

async def process_url_with_connector(url: str, connector: ConnectorBase, focus: dict, get_info_prompts: list[str], semaphore: asyncio.Semaphore) -> list[str]:
    """
    Process a URL using a connector.
    
    This function processes a URL using a connector, extracting information
    and saving it to the database.
    
    Args:
        url: URL to process
        connector: Connector to use
        focus: Focus point dictionary
        get_info_prompts: List of prompts for the LLM
        semaphore: Semaphore for concurrency control
        
    Returns:
        List of processed item IDs
    """
    async with semaphore:
        try:
            wiseflow_logger.info(f"Processing URL with connector: {url}")
            
            # Collect data from the connector
            data_items = await connector.collect({
                "url": url,
                "focus_point": focus.get("focuspoint", ""),
                "explanation": focus.get("explanation", "")
            })
            
            # Process each data item
            processed_items = []
            for data_item in data_items:
                items = await process_data_with_plugins(data_item, focus, get_info_prompts)
                processed_items.extend(items)
            
            return processed_items
        except Exception as e:
            wiseflow_logger.error(f"Error processing URL with connector: {url}, error: {e}")
            wiseflow_logger.debug(f"Traceback: {traceback.format_exc()}")
            return []

async def process_url_with_crawler(url: str, crawler: AsyncWebCrawler, focus_id: str, existing_urls: set, 
                                  get_link_prompts: list[str], get_info_prompts: list[str], 
                                  recognized_img_cache: dict, semaphore: asyncio.Semaphore) -> list[str]:
    """
    Process a URL using a crawler.
    
    This function processes a URL using a crawler, extracting information
    and saving it to the database.
    
    Args:
        url: URL to process
        crawler: Crawler to use
        focus_id: ID of the focus point
        existing_urls: Set of already processed URLs
        get_link_prompts: List of prompts for link selection
        get_info_prompts: List of prompts for information extraction
        recognized_img_cache: Cache for recognized images
        semaphore: Semaphore for concurrency control
        
    Returns:
        List of processed item IDs
    """
    async with semaphore:
        try:
            wiseflow_logger.info(f"Processing URL with crawler: {url}")
            
            # Configure crawler
            crawler_config = CrawlerRunConfig()
            crawler_config.cache_mode = CacheMode.ENABLED
            
            # Crawl URL
            result = await crawler.arun(url=url, config=crawler_config)
            if not result.success:
                wiseflow_logger.warning(f'{url} failed to crawl')
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
            link_dict, links_parts, contents, recognized_img_cache = await pre_process(
                raw_markdown, base_url, used_img, recognized_img_cache, existing_urls
            )
            
            # Process information
            processed_items = await info_process(
                url, title, author, publish_date, contents, link_dict, focus_id, get_info_prompts
            )
            
            # Process related links if needed
            if config.get("PROCESS_RELATED_LINKS", False) and link_dict:
                related_urls = await get_more_related_urls(links_parts, get_link_prompts)
                for related_url in related_urls:
                    if related_url not in existing_urls:
                        existing_urls.add(related_url)
                        # Create a task to process the related URL
                        asyncio.create_task(
                            process_url_with_crawler(
                                related_url, crawler, focus_id, existing_urls, 
                                get_link_prompts, get_info_prompts, 
                                recognized_img_cache, semaphore
                            )
                        )
            
            return processed_items
        except Exception as e:
            wiseflow_logger.error(f"Error processing URL with crawler: {url}, error: {e}")
            wiseflow_logger.debug(f"Traceback: {traceback.format_exc()}")
            return []

async def process_focus_point(focus_id: str) -> bool:
    """
    Process a focus point.
    
    This function processes a focus point, collecting and analyzing data from
    various sources based on the focus point's configuration.
    
    Args:
        focus_id: ID of the focus point to process
        
    Returns:
        True if processing was successful, False otherwise
    """
    wiseflow_logger.info(f"Processing focus point: {focus_id}")
    
    # Get the focus point
    focus = pb.read_one('focus_point', id=focus_id)
    if not focus:
        wiseflow_logger.error(f"Focus point with ID {focus_id} not found")
        return False
    
    # Publish event for focus point processing start
    start_event = Event(
        EventType.FOCUS_POINT_PROCESSED,
        data={
            "focus_id": focus_id,
            "focus_point": focus.get("focuspoint", ""),
            "status": "started"
        },
        source="main_process"
    )
    await publish(start_event)
    
    # Get sites for this focus point
    sites = pb.read('sites', filter=f'tag="{focus_id}"')
    if not sites:
        wiseflow_logger.warning(f"No sites found for focus point: {focus.get('focuspoint', '')}")
        
        # Publish event for focus point processing completion
        end_event = Event(
            EventType.FOCUS_POINT_PROCESSED,
            data={
                "focus_id": focus_id,
                "focus_point": focus.get("focuspoint", ""),
                "sites_count": 0,
                "status": "completed"
            },
            source="main_process"
        )
        await publish(end_event)
        return True
    
    # Get references for this focus point
    references = []
    if config.get("ENABLE_REFERENCES", True):
        try:
            references = reference_manager.get_references_for_focus(focus_id)
        except Exception as e:
            wiseflow_logger.error(f"Error getting references for focus point {focus_id}: {e}")
            wiseflow_logger.debug(f"Traceback: {traceback.format_exc()}")
    
    # Publish event for focus point processing
    processing_event = Event(
        EventType.FOCUS_POINT_PROCESSED,
        data={
            "focus_id": focus_id,
            "focus_point": focus.get("focuspoint", ""),
            "sites_count": len(sites),
            "status": "processing"
        },
        source="main_process"
    )
    await publish(processing_event)
    
    # Get prompts for this focus point
    get_info_prompts = []
    get_link_prompts = []
    
    # Prepare prompts
    focus_point = focus.get('focuspoint', '')
    explanation = focus.get('explanation', '')
    
    # Add focus point and explanation to prompts
    get_info_prompts.append(f"Focus point: {focus_point}")
    if explanation:
        get_info_prompts.append(f"Explanation: {explanation}")
    
    # Add references to prompts if available
    if references:
        ref_prompt = "References:\n"
        for ref in references:
            ref_prompt += f"- {ref.get('title', '')}: {ref.get('content', '')[:200]}...\n"
        get_info_prompts.append(ref_prompt)
    
    # Add link selection prompt
    get_link_prompts.append(f"Focus point: {focus_point}")
    if explanation:
        get_link_prompts.append(f"Explanation: {explanation}")
    get_link_prompts.append("Select links that are likely to contain information relevant to the focus point.")
    
    # Initialize crawler
    crawler = AsyncWebCrawler()
    await crawler.start()
    
    try:
        # Initialize variables
        working_list = set()
        existing_urls = set()
        recognized_img_cache = {}
        
        # Add sites to working list
        for site in sites:
            if site['url'] not in existing_urls and isURL(site['url']):
                working_list.add(site['url'])

        # Check if we have a web connector plugin
        web_connector = plugin_manager.get_plugin("web_connector")
        
        if web_connector and isinstance(web_connector, ConnectorBase):
            wiseflow_logger.info("Using web connector plugin for data collection")
            
            # Process sites with the web connector
            all_processed_items = []
            
            # Create a semaphore to limit concurrency
            semaphore = asyncio.Semaphore(int(config.get("MAX_CONCURRENT_REQUESTS", 5)))
            
            # Process URLs with concurrency control
            tasks = []
            for site in sites:
                url = site.get("url", "")
                if url:
                    tasks.append(process_url_with_connector(url, web_connector, focus, get_info_prompts, semaphore))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        wiseflow_logger.error(f"Error processing URL: {result}")
                        wiseflow_logger.debug(f"Traceback: {traceback.format_exc()}")
                    elif result:
                        all_processed_items.extend(result)
            
            # Update knowledge graph with processed items if enabled
            if config.get("ENABLE_KNOWLEDGE_GRAPH", False) and all_processed_items:
                wiseflow_logger.info(f"Updating knowledge graph with {len(all_processed_items)} items")
                # Implementation for knowledge graph update
        else:
            wiseflow_logger.info("Web connector plugin not available, using default crawler")
            
            # Create a semaphore to limit concurrency
            semaphore = asyncio.Semaphore(int(config.get("MAX_CONCURRENT_REQUESTS", 5)))
            
            # Process URLs with concurrency control
            tasks = []
            for url in working_list:
                tasks.append(process_url_with_crawler(
                    url, crawler, focus["id"], existing_urls, 
                    get_link_prompts, get_info_prompts, 
                    recognized_img_cache, semaphore
                ))
            
            if tasks:
                await asyncio.gather(*tasks)
        
        # Process search engine if enabled
        if focus.get('search_engine', False):
            wiseflow_logger.info("Processing search engine")
            try:
                search_results = await run_v4_async(focus_point, explanation)
                if search_results:
                    wiseflow_logger.info(f"Got {len(search_results)} search results")
                    
                    # Process each search result
                    for result in search_results:
                        url = result.get('url')
                        if url and url not in existing_urls:
                            existing_urls.add(url)
                            await process_url_with_crawler(
                                url, crawler, focus["id"], existing_urls, 
                                get_link_prompts, get_info_prompts, 
                                recognized_img_cache, semaphore
                            )
            except Exception as e:
                wiseflow_logger.error(f"Error processing search engine: {e}")
                wiseflow_logger.debug(f"Traceback: {traceback.format_exc()}")
        
        # Process RSS feeds
        for site in sites:
            if site.get('type') == 'rss':
                wiseflow_logger.info(f"Processing RSS feed: {site.get('url')}")
                try:
                    feed = feedparser.parse(site.get('url'))
                    if feed.entries:
                        wiseflow_logger.info(f"Got {len(feed.entries)} RSS entries")
                        
                        # Process each RSS entry
                        for entry in feed.entries:
                            url = entry.get('link')
                            if url and url not in existing_urls:
                                existing_urls.add(url)
                                await process_url_with_crawler(
                                    url, crawler, focus["id"], existing_urls, 
                                    get_link_prompts, get_info_prompts, 
                                    recognized_img_cache, semaphore
                                )
                except Exception as e:
                    wiseflow_logger.error(f"Error processing RSS feed: {e}")
                    wiseflow_logger.debug(f"Traceback: {traceback.format_exc()}")
    
    finally:
        # Close crawler
        await crawler.close()
    
    # Publish event for focus point processing completion
    end_event = Event(
        EventType.FOCUS_POINT_PROCESSED,
        data={
            "focus_id": focus["id"],
            "focus_point": focus.get("focuspoint", ""),
            "sites_count": len(sites),
            "status": "completed"
        },
        source="main_process"
    )
    await publish(end_event)
    
    wiseflow_logger.info(f"Completed processing focus point: {focus.get('focuspoint', '')}")
    return True

async def generate_insights_for_focus(focus_id: str, time_period_days: int = 7):
    """
    Generate insights for a focus point.
    
    This function generates insights for a focus point based on the extracted
    information from the last N days.
    
    Args:
        focus_id: ID of the focus point
        time_period_days: Number of days to consider for insight generation
        
    Returns:
        Generated insights, or None if generation fails
    """
    wiseflow_logger.info(f"Generating insights for focus point: {focus_id}")
    
    # Get the focus point
    focus = pb.read_one('focus_point', id=focus_id)
    if not focus:
        wiseflow_logger.error(f"Focus point with ID {focus_id} not found")
        return None
    
    # Publish event for insight generation start
    start_event = Event(
        EventType.INSIGHT_GENERATED,
        data={
            "focus_id": focus_id,
            "focus_point": focus.get("focuspoint", ""),
            "status": "started"
        },
        source="generate_insights"
    )
    await publish(start_event)
    
    try:
        # Generate insights
        insights = await insight_extractor.generate_insights_for_focus(focus_id, time_period_days)
        
        if insights:
            # Save insights to database
            insight_record = {
                "focus_id": focus_id,
                "timestamp": datetime.now().isoformat(),
                "insights": insights,
                "metadata": {
                    "focus_point": focus.get("focuspoint", ""),
                    "time_period_days": time_period_days
                }
            }
            
            insight_id = pb.add(collection_name='insights', body=insight_record)
            
            if insight_id:
                wiseflow_logger.info(f"Saved insights for focus point: {focus.get('focuspoint', '')}")
                
                # Publish event for insight generation completion
                end_event = Event(
                    EventType.INSIGHT_GENERATED,
                    data={
                        "focus_id": focus_id,
                        "focus_point": focus.get("focuspoint", ""),
                        "insight_id": insight_id,
                        "status": "completed"
                    },
                    source="generate_insights"
                )
                await publish(end_event)
                
                return insights
            else:
                wiseflow_logger.error(f"Failed to save insights for focus point: {focus.get('focuspoint', '')}")
        else:
            wiseflow_logger.warning(f"No insights generated for focus point: {focus.get('focuspoint', '')}")
    
    except Exception as e:
        wiseflow_logger.error(f"Error generating insights for focus point {focus_id}: {e}")
        wiseflow_logger.debug(f"Traceback: {traceback.format_exc()}")
        
        # Publish event for insight generation failure
        error_event = Event(
            EventType.INSIGHT_GENERATED,
            data={
                "focus_id": focus_id,
                "focus_point": focus.get("focuspoint", ""),
                "status": "failed",
                "error": str(e)
            },
            source="generate_insights"
        )
        await publish(error_event)
    
    return None
