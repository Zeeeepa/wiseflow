# -*- coding: utf-8 -*-
from core.utils.pb_api import PbTalker
from core.utils.general_utils import get_logger, extract_and_convert_dates, is_chinese, isURL
from core.agents.get_info import *
from core.agents.insights import InsightExtractor
import json
from core.scrapers import *
from core.utils.zhipu_search import run_v4_async
from urllib.parse import urlparse
from core.crawl4ai import AsyncWebCrawler, CacheMode
from datetime import datetime
import asyncio
import time
import feedparser
from core.plugins import PluginManager
from core.connectors import ConnectorBase, DataItem, initialize_all_connectors
from core.references import ReferenceManager
from core.analysis.multimodal_analysis import process_item_with_images
from core.analysis.multimodal_knowledge_integration import integrate_multimodal_analysis_with_knowledge_graph
from core.config import (
    PROJECT_DIR, PRIMARY_MODEL, SECONDARY_MODEL, ENABLE_MULTIMODAL,
    MAX_CONCURRENT_TASKS
)
from core.event_system import (
    EventType, Event, publish_sync,
    create_focus_point_event, create_task_event
)
from core.utils.error_handling import handle_exceptions, WiseflowError

# Initialize logger and PocketBase client
wiseflow_logger = get_logger('wiseflow', PROJECT_DIR)
pb = PbTalker(wiseflow_logger)

# Initialize plugin manager
plugin_manager = PluginManager(plugins_dir="core")

# Initialize reference manager
reference_manager = ReferenceManager(storage_path=os.path.join(PROJECT_DIR, "references"))

# Initialize insight extractor
insight_extractor = InsightExtractor(pb_client=pb)

# Initialize knowledge graph builder
try:
    from core.knowledge.graph import KnowledgeGraphBuilder
    knowledge_graph_builder = KnowledgeGraphBuilder(name="Wiseflow Knowledge Graph")
except ImportError:
    wiseflow_logger.warning("Knowledge graph module not available")
    knowledge_graph_builder = None

@handle_exceptions(default_message="Error processing information", log_error=True)
async def info_process(url: str, 
                       url_title: str, 
                       author: str, 
                       publish_date: str, 
                       contents: list, 
                       link_dict: dict, 
                       focus_id: str,
                       get_info_prompts: list):
    """Process information from a URL."""
    wiseflow_logger.debug(f'get_info for {url}')
    
    # Extract information using LLM
    infos = await get_info(contents, link_dict, get_info_prompts, author, publish_date, _logger=wiseflow_logger)
    if infos:
        wiseflow_logger.debug(f'get {len(infos)} infos, will save to pb')

    processed_items = []
    for info in infos:
        info['url'] = url
        info['url_title'] = url_title
        info['tag'] = focus_id
        
        # Extract and convert dates
        if 'date' in info and info['date']:
            try:
                info['date'] = extract_and_convert_dates(info['date'])
            except Exception as e:
                wiseflow_logger.error(f'Error converting date: {e}')
        
        # Translate content if needed
        if 'content' in info and info['content'] and not is_chinese(info['content']):
            try:
                from core.agents.translate import translate_text
                info['content'] = await translate_text(info['content'], PRIMARY_MODEL)
            except Exception as e:
                wiseflow_logger.error(f'Error translating content: {e}')
        
        # Save to database
        info_id = await pb.create('infos', info)
        if info_id:
            processed_items.append(info_id)
            
            # Publish event
            try:
                event = create_focus_point_event(
                    EventType.DATA_PROCESSED,
                    focus_id,
                    {"info_id": info_id}
                )
                publish_sync(event)
            except Exception as e:
                wiseflow_logger.warning(f"Failed to publish data processed event: {e}")
        
        # Process multimodal analysis if enabled
        if ENABLE_MULTIMODAL:
            try:
                # Get the saved item with retry logic
                saved_item = None
                max_retries = 3
                retry_count = 0
                
                while retry_count < max_retries:
                    saved_item = pb.read_one(collection_name='infos', id=info_id)
                    if saved_item:
                        break
                    
                    retry_count += 1
                    wiseflow_logger.warning(f"Retry {retry_count}/{max_retries} to get item {info_id}")
                    await asyncio.sleep(1)
                
                if saved_item:
                    # Check if the item has images
                    has_images = False
                    if 'content' in saved_item and saved_item['content']:
                        has_images = '![' in saved_item['content'] and '](' in saved_item['content']
                    
                    if has_images:
                        wiseflow_logger.info(f"Processing multimodal analysis for item {info_id}")
                        
                        # Process multimodal analysis
                        multimodal_result = await process_item_with_images(saved_item, VL_MODEL)
                        
                        # Update the item with multimodal analysis
                        if multimodal_result:
                            update_data = {
                                'multimodal_analysis': multimodal_result
                            }
                            pb.update(collection_name='infos', id=info_id, data=update_data)
                else:
                    wiseflow_logger.error(f"Failed to retrieve item {info_id} after {max_retries} attempts")
            except Exception as e:
                wiseflow_logger.error(f'Error processing multimodal analysis: {e}')
    
    return processed_items

@handle_exceptions(default_message="Error processing data with plugins", log_error=True)
async def process_data_with_plugins(data_item: DataItem, focus: dict, get_info_prompts: list[str]) -> List[Dict[str, Any]]:
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
        
        # Extract processed content
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
                        
                        # Publish event
                        try:
                            event = create_focus_point_event(
                                EventType.DATA_PROCESSED,
                                focus["id"],
                                {"info_id": info_id}
                            )
                            publish_sync(event)
                        except Exception as e:
                            wiseflow_logger.warning(f"Failed to publish data processed event: {e}")
                    else:
                        wiseflow_logger.error('add info failed, writing to cache_file')
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        with open(os.path.join(PROJECT_DIR, f'{timestamp}_cache_infos.json'), 'w', encoding='utf-8') as f:
                            json.dump(info, f, ensure_ascii=False, indent=4)
        
        return processed_items
    except Exception as e:
        wiseflow_logger.error(f"Error processing data item: {e}")
        return []

@handle_exceptions(default_message="Error collecting data from connector", log_error=True)
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

@handle_exceptions(default_message="Error processing URL with connector", log_error=True)
async def process_url_with_connector(url, connector, focus, get_info_prompts, semaphore):
    """Process a URL using a connector with concurrency control."""
    async with semaphore:
        wiseflow_logger.debug(f"Processing URL with connector: {url}")
        
        # Collect data from the URL
        data_items = await collect_from_connector(connector.name, {"urls": [url]})
        
        results = []
        for data_item in data_items:
            processed_results = await process_data_with_plugins(data_item, focus, get_info_prompts)
            results.extend(processed_results)
        
        return results

@handle_exceptions(default_message="Error processing URL with crawler", log_error=True)
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
            from core.crawl4ai.crawler_config import CrawlerRunConfig
            crawler_config = CrawlerRunConfig()
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
                    title = metadata_dict.get('title', '')
                    base_url = metadata_dict.get('base', '')
                    author = metadata_dict.get('author', '')
                    publish_date = metadata_dict.get('publish_date', '')
            else:
                raw_markdown = result.markdown
                media_dict = result.media if result.media else {}
                used_img = [d['src'] for d in media_dict.get('images', [])]
                title = metadata_dict.get('title', '')
                base_url = metadata_dict.get('base', '')
                author = metadata_dict.get('author', '')
                publish_date = metadata_dict.get('publish_date', '')
                
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
                    alt_author, alt_publish_date = await get_author_and_publish_date(main_content_text, SECONDARY_MODEL, _logger=wiseflow_logger)
                    if not author or author.lower() == 'na':
                        author = alt_author if alt_author else parsed_url.netloc
                    if not publish_date or publish_date.lower() == 'na':
                        publish_date = alt_publish_date
                except Exception as e:
                    wiseflow_logger.error(f"Error extracting author and publish date: {e}")
                    # Use defaults if extraction fails
                    if not author or author.lower() == 'na':
                        author = parsed_url.netloc
                    if not publish_date or publish_date.lower() == 'na':
                        publish_date = datetime.now().strftime("%Y-%m-%d")

            # Process the content and extract information
            focus = pb.read_one(collection_name='focus_point', id=focus_id)
            if not focus:
                wiseflow_logger.error(f"Focus point with ID {focus_id} not found")
                return
                
            return await info_process(url, title, author, publish_date, contents, link_dict, focus_id, get_info_prompts)
        except Exception as e:
            wiseflow_logger.error(f"Error processing URL {url}: {e}")
            return []

@handle_exceptions(default_message="Error in main process", log_error=True)
async def main_process(focus: dict, sites: list):
    """Main process for a focus point."""
    wiseflow_logger.info(f"Processing focus point: {focus.get('focuspoint', '')}")
    
    # Publish event
    try:
        event = create_focus_point_event(
            EventType.FOCUS_POINT_PROCESSED,
            focus["id"],
            {"sites_count": len(sites)}
        )
        publish_sync(event)
    except Exception as e:
        wiseflow_logger.warning(f"Failed to publish focus point processed event: {e}")
    
    # Initialize plugins
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
    if focus.get('references'):
        try:
            references = json.loads(focus['references'])
        except Exception as e:
            wiseflow_logger.error(f"Error parsing references: {e}")
    
    # Add references to reference manager
    for reference in references:
        reference_manager.add_reference(reference)
    
    # Generate prompts
    from core.agents.get_info_prompts import get_info_prompts, get_link_prompts
    get_info_prompts = get_info_prompts(focus.get('focuspoint', ''), focus.get('explanation', ''))
    get_link_prompts = get_link_prompts(focus.get('focuspoint', ''), focus.get('explanation', ''))
    
    # Check if search engine is enabled
    if focus.get('search_engine', False):
        wiseflow_logger.info("Search engine enabled, performing search")
        try:
            search_results = await run_v4_async(focus.get('focuspoint', ''), focus.get('explanation', ''))
            if search_results:
                wiseflow_logger.info(f"Got {len(search_results)} search results")
                
                # Process search results
                for result in search_results:
                    url = result.get('url', '')
                    if url:
                        # Create a data item from the search result
                        data_item = DataItem(
                            source_id=f"search_{focus['id']}",
                            content=result.get('content', ''),
                            metadata={
                                "title": result.get('title', ''),
                                "author": result.get('author', ''),
                                "publish_date": result.get('date', ''),
                                "source": "search_engine"
                            },
                            url=url,
                            content_type="text/plain"
                        )
                        
                        # Process the data item
                        await process_data_with_plugins(data_item, focus, get_info_prompts)
        except Exception as e:
            wiseflow_logger.error(f"Error performing search: {e}")
    
    # Process sites
    if not sites:
        wiseflow_logger.warning("No sites to process")
        return
    
    # Create a set to track processed URLs
    working_list = set()
    existing_urls = set()
    
    # Add URLs from sites to working list
    for site in sites:
        if site.get('type') == 'rss':
            # Process RSS feed
            try:
                feed = feedparser.parse(site['url'])
                if feed.entries:
                    wiseflow_logger.info(f"Found {len(feed.entries)} entries in RSS feed: {site['url']}")
                    
                    # Process each entry
                    for entry in feed.entries:
                        entry_url = entry.get('link', '')
                        if entry_url and entry_url not in existing_urls and isURL(entry_url):
                            working_list.add(entry_url)
                            existing_urls.add(entry_url)
            except Exception as e:
                wiseflow_logger.error(f"Error processing RSS feed {site['url']}: {e}")
        else:
            # Process web URL
            if site['url'] not in existing_urls and isURL(site['url']):
                working_list.add(site['url'])
                existing_urls.add(site['url'])

    # Check if we have a web connector plugin
    web_connector = plugin_manager.get_plugin("web_connector")
    
    if web_connector and isinstance(web_connector, ConnectorBase):
        wiseflow_logger.info("Using web connector plugin for data collection")
        
        # Process sites with the web connector
        all_processed_items = []
        
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(int(os.environ.get("MAX_CONCURRENT_REQUESTS", "5")))
        
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
        if ENABLE_MULTIMODAL and knowledge_graph_builder and all_processed_items:
            try:
                wiseflow_logger.info(f"Updating knowledge graph with {len(all_processed_items)} items")
                for item_id in all_processed_items:
                    item = pb.read_one(collection_name='infos', id=item_id)
                    if item:
                        knowledge_graph_builder.add_item(item)
                
                # Integrate multimodal analysis with knowledge graph
                await integrate_multimodal_analysis_with_knowledge_graph(
                    focus["id"],
                    knowledge_graph_builder
                )
            except Exception as e:
                wiseflow_logger.error(f"Error updating knowledge graph: {e}")
    else:
        # Fall back to default crawler
        wiseflow_logger.info("Web connector plugin not available, using default crawler")
        
        # Initialize crawler
        crawler = AsyncWebCrawler()
        await crawler.start()
        
        try:
            # Create a semaphore to limit concurrency
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
            
            # Initialize image recognition cache
            recognized_img_cache = {}
            
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
        finally:
            await crawler.close()
    
    wiseflow_logger.info(f"Finished processing focus point: {focus.get('focuspoint', '')}")
    
    # Generate insights if enabled
    if focus.get('generate_insights', True):
        wiseflow_logger.info(f"Generating insights for focus point: {focus.get('focuspoint', '')}")
        try:
            await insight_extractor.generate_insights_for_focus(focus["id"])
        except Exception as e:
            wiseflow_logger.error(f"Error generating insights: {e}")
    
    return True
