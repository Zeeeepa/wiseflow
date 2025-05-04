# -*- coding: utf-8 -*-
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

import json
from urllib.parse import urlparse
from datetime import datetime
import asyncio
import time
import feedparser

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
    """Process information from a URL and save it to the database."""
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
    
    return processed_items

async def process_data_with_plugins(data_item: DataItem, focus: dict, get_info_prompts: list[str]):
    """Process a data item using the appropriate processor plugin."""
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
        return []


async def collect_from_connector(connector_name: str, params: dict) -> list[DataItem]:
    """Collect data from a connector."""
    connector = plugin_manager.get_plugin(connector_name)
    
    if not connector or not isinstance(connector, ConnectorBase):
        wiseflow_logger.error(f"Connector {connector_name} not found or not a valid connector")
        return []
    
    try:
        # Use the improved collect_with_retry method for better error handling
        return await connector.collect_with_retry(params)
    except Exception as e:
        wiseflow_logger.error(f"Error collecting data from connector {connector_name}: {e}")
        return []

async def process_url_with_connector(url, connector, focus, get_info_prompts, semaphore):
    """Process a URL using a connector with concurrency control."""
    async with semaphore:
        try:
            wiseflow_logger.debug(f"Processing URL with connector: {url}")
            
            # Collect data from the connector
            data_items = await collect_from_connector(connector.name, {"urls": [url]})
            
            if not data_items:
                wiseflow_logger.warning(f"No data collected from {url}")
                return []
            
            # Process each data item
            processed_items = []
            for data_item in data_items:
                items = await process_data_with_plugins(data_item, focus, get_info_prompts)
                processed_items.extend(items)
            
            return processed_items
        except Exception as e:
            wiseflow_logger.error(f"Error processing URL with connector: {e}")
            return []

async def process_url_with_crawler(url, crawler, focus_id, existing_urls, get_link_prompts, get_info_prompts, recognized_img_cache, semaphore):
    """Process a URL using the crawler with concurrency control and improved error handling."""
    async with semaphore:
        try:
            wiseflow_logger.debug(f"Processing URL with crawler: {url}")
            
            # Validate URL before processing
            if not url or not isinstance(url, str):
                wiseflow_logger.warning(f"Invalid URL: {url}, skipping")
                return
                
            # Check for common file extensions to skip
            has_common_ext = any(url.lower().endswith(ext) for ext in common_file_exts)
            if has_common_ext:
                wiseflow_logger.debug(f'{url} is a common file, skip')
                return

            # Parse URL and add to existing URLs to avoid duplicates
            try:
                parsed_url = urlparse(url)
                domain = parsed_url.netloc
                
                # Add variations of the URL to existing_urls to prevent duplicates
                existing_urls.add(f"{parsed_url.scheme}://{parsed_url.netloc}")
                existing_urls.add(f"{parsed_url.scheme}://{parsed_url.netloc}/")
            except Exception as e:
                wiseflow_logger.error(f"Error parsing URL {url}: {e}")
                return
                
            # Configure crawler cache mode
            crawler_config.cache_mode = CacheMode.WRITE_ONLY if url in [s['url'] for s in sites] else CacheMode.ENABLED
            
            # Crawl the URL with retry logic
            max_retries = 3
            retry_count = 0
            result = None
            
            while retry_count < max_retries:
                try:
                    result = await crawler.arun(url=url, config=crawler_config)
                    break
                except Exception as e:
                    retry_count += 1
                    wiseflow_logger.warning(f"Attempt {retry_count}/{max_retries} failed for {url}: {e}")
                    
                    if retry_count >= max_retries:
                        wiseflow_logger.error(f"Failed to crawl {url} after {max_retries} attempts: {e}")
                        return
                        
                    # Exponential backoff
                    await asyncio.sleep(2 ** retry_count)
            
            # Check if crawl was successful
            if not result or not result.success:
                wiseflow_logger.warning(f'{url} failed to crawl: {result.error_message if result else "Unknown error"}')
                return
                
            # Extract metadata
            metadata_dict = result.metadata if result.metadata else {}

            # Process based on domain-specific scrapers or default approach
            if domain in custom_scrapers:
                try:
                    result = custom_scrapers[domain](result)
                    raw_markdown = result.content
                    used_img = result.images
                    title = result.title
                    if title == 'maybe a new_type_article':
                        wiseflow_logger.warning(f'we found a new type here,{url}\n{result}')
                    base_url = result.base
                    author = result.author
                    publish_date = result.publish_date
                except Exception as e:
                    wiseflow_logger.error(f"Error in custom scraper for {domain}: {e}")
                    # Fall back to default processing
                    raw_markdown = result.markdown
                    media_dict = result.media if result.media else {}
                    used_img = [d['src'] for d in media_dict.get('images', [])]
                    title = ''
                    base_url = ''
                    author = ''
                    publish_date = ''
            else:
                raw_markdown = result.markdown
                media_dict = result.media if result.media else {}
                used_img = [d['src'] for d in media_dict.get('images', [])]
                title = ''
                base_url = ''
                author = ''
                publish_date = ''
                
            # Validate content
            if not raw_markdown:
                wiseflow_logger.warning(f'{url} no content\n{result}\nskip')
                return
                
            wiseflow_logger.debug('data preprocessing...')
            
            # Fill in missing metadata
            if not title:
                title = metadata_dict.get('title', '')
            if not base_url:
                base_url = metadata_dict.get('base', '')
            if not author:
                author = metadata_dict.get('author', '')
            if not publish_date:
                publish_date = metadata_dict.get('publish_date', '')

            # Process content and extract links
            try:
                link_dict, links_parts, contents, recognized_img_cache = await pre_process(raw_markdown, base_url, used_img, recognized_img_cache, existing_urls)
            except Exception as e:
                wiseflow_logger.error(f"Error preprocessing content from {url}: {e}")
                return

            # Process additional links if found
            if link_dict and links_parts:
                try:
                    wiseflow_logger.debug('links_parts exists, more links detecting...')
                    links_texts = []
                    for _parts in links_parts:
                        links_texts.extend(_parts.split('\n\n'))
                    more_url = await get_more_related_urls(links_texts, link_dict, get_link_prompts, _logger=wiseflow_logger)
                    if more_url:
                        wiseflow_logger.debug(f'get {len(more_url)} more related urls, will add to working list')
                        # Instead of adding to working_list, create new tasks for these URLs
                        for new_url in more_url - existing_urls:
                            existing_urls.add(new_url)
                            asyncio.create_task(process_url_with_crawler(new_url, crawler, focus_id, existing_urls, get_link_prompts, get_info_prompts, recognized_img_cache, semaphore))
                except Exception as e:
                    wiseflow_logger.error(f"Error processing additional links from {url}: {e}")
                    # Continue with main content processing even if link extraction fails
            
            # Skip if no content was extracted
            if not contents:
                wiseflow_logger.warning(f"No content extracted from {url}")
                return

            # Try to extract author and publish date if missing
            if not author or author.lower() == 'na' or not publish_date or publish_date.lower() == 'na':
                try:
                    wiseflow_logger.debug('no author or publish date from metadata, will try to get by llm')
                    main_content_text = re.sub(r'!\[.*?]\(.*?\)', '', raw_markdown)
                    main_content_text = re.sub(r'\[.*?]\(.*?\)', '', main_content_text)
                    alt_author, alt_publish_date = await get_author_and_publish_date(main_content_text, secondary_model, _logger=wiseflow_logger)
                    if not author or author.lower() == 'na':
                        author = alt_author if alt_author else 'NA'
                    if not publish_date or publish_date.lower() == 'na':
                        publish_date = alt_publish_date if alt_publish_date else 'NA'
                except Exception as e:
                    wiseflow_logger.error(f"Error extracting author and publish date: {e}")
                    if not author:
                        author = 'NA'
                    if not publish_date:
                        publish_date = 'NA'

            # Process the extracted content
            return await info_process(url, title, author, publish_date, contents, link_dict, focus_id, get_info_prompts)
        except Exception as e:
            wiseflow_logger.error(f"Error processing URL with crawler: {e}")
            return []

async def main_process(focus: dict, sites: list):
    """Main process for handling a focus point and its associated sites."""
    wiseflow_logger.info(f"Processing focus point: {focus.get('focuspoint', '')}")
    
    # Publish event for focus point processing start
    start_event = Event(
        EventType.FOCUS_POINT_PROCESSED,
        data={
            "focus_id": focus["id"],
            "focus_point": focus.get("focuspoint", ""),
            "sites_count": len(sites),
            "status": "started"
        },
        source="main_process"
    )
    await publish(start_event)
    
    # Initialize plugins
    wiseflow_logger.info("Initializing plugins...")
    plugins = plugin_manager.load_all_plugins()
    wiseflow_logger.info(f"Loaded {len(plugins)} plugins")
    
    # Initialize plugins with configurations
    configs = {}  # Load configurations from database or config files
    results = plugin_manager.initialize_all_plugins(configs)
    
    for name, success in results.items():
        if success:
            wiseflow_logger.info(f"Initialized plugin: {name}")
        else:
            wiseflow_logger.warning(f"Failed to initialize plugin: {name}")

    # Process references
    references = []
    if focus.get("references", []):
        wiseflow_logger.info(f"Processing {len(focus['references'])} references")
        for ref_id in focus["references"]:
            ref = pb.read_one("references", id=ref_id)
            if ref:
                references.append(ref)
                # Add to reference manager
                reference_manager.add_reference(
                    title=ref.get("title", ""),
                    content=ref.get("content", ""),
                    source=ref.get("source", ""),
                    reference_type=ref.get("type", "text"),
                    metadata={
                        "focus_id": focus["id"],
                        "focus_point": focus.get("focuspoint", "")
                    }
                )
    
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
        
        # Configure crawler
        crawler_config = CrawlerRunConfig()
        crawler_config.cache_mode = CacheMode.ENABLED
        
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
    """Generate insights for a focus point."""
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
