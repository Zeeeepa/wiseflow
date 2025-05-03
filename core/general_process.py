# -*- coding: utf-8 -*-
from utils.pb_api import PbTalker
from utils.general_utils import get_logger, extract_and_convert_dates, is_chinese, isURL
from agents.get_info import *
from agents.insights import InsightExtractor
import json
from scrapers import *
from utils.zhipu_search import run_v4_async
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, CacheMode
from datetime import datetime
import asyncio
import time
import feedparser
from plugins import PluginManager
from connectors import ConnectorBase, DataItem, initialize_all_connectors
from references import ReferenceManager
from analysis.multimodal_analysis import process_item_with_images
from analysis.multimodal_knowledge_integration import integrate_multimodal_analysis_with_knowledge_graph
from knowledge.graph import KnowledgeGraphBuilder

project_dir = os.environ.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)

wiseflow_logger = get_logger('wiseflow', project_dir)
pb = PbTalker(wiseflow_logger)

model = os.environ.get("PRIMARY_MODEL", "")
if not model:
    raise ValueError("PRIMARY_MODEL not set, please set it in environment variables or edit core/.env")
secondary_model = os.environ.get("SECONDARY_MODEL", model)

# Initialize plugin manager
plugin_manager = PluginManager(plugins_dir="core")

# Initialize reference manager
reference_manager = ReferenceManager(storage_path=os.path.join(project_dir, "references"))

# Initialize insight extractor
insight_extractor = InsightExtractor(pb_client=pb)

# Initialize knowledge graph builder
knowledge_graph_builder = KnowledgeGraphBuilder(name="Wiseflow Knowledge Graph")

async def info_process(url: str, 
                       url_title: str, 
                       author: str, 
                       publish_date: str, 
                       contents: list[str], 
                       link_dict: dict, 
                       focus_id: str,
                       get_info_prompts: list[str]):
    """Process information and save to database."""
    wiseflow_logger.debug('info summarising by llm...')
    infos = await get_info(contents, link_dict, get_info_prompts, author, publish_date, _logger=wiseflow_logger)
    if infos:
        wiseflow_logger.debug(f'get {len(infos)} infos, will save to pb')

    processed_items = []
    for info in infos:
        info['url'] = url
        info['url_title'] = url_title
        info['tag'] = focus_id

        # Process insights for each info item
        try:
            content = info.get('content', '')
            if content:
                # Extract insights from the content
                insights = await insight_extractor.process_item({
                    'id': info.get('id', str(uuid.uuid4())),
                    'content': content,
                    'title': info.get('title', url_title),
                    'url': url,
                    'author': author,
                    'publish_date': publish_date
                })
                
                # Add insights to the info object
                info['insights'] = insights
                wiseflow_logger.debug(f'Added insights to info item: {len(str(insights))} bytes')
        except Exception as e:
            wiseflow_logger.error(f'Error processing insights: {e}')
        
        # Save to database
        info_id = await pb.create('infos', info)
        if info_id:
            processed_items.append(info_id)
        
        # Process multimodal analysis if enabled
        if os.environ.get("ENABLE_MULTIMODAL", "false").lower() == "true":
            try:
                # Get the saved item with retry logic
                saved_item = None
                max_retries = 3
                retry_delay = 1  # seconds
                
                for attempt in range(max_retries):
                    saved_item = pb.read_one('infos', info_id)
                    if saved_item:
                        break
                    wiseflow_logger.warning(f"Item not found on attempt {attempt+1}, retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                
                if saved_item:
                    # Process the item for multimodal analysis
                    updated_item = await process_item_with_images(saved_item)
                    wiseflow_logger.info(f"Multimodal analysis completed for item {info_id}")
                    
                    # Verify the update was successful
                    if "error" in updated_item and not isinstance(updated_item["error"], str):
                        wiseflow_logger.error(f"Error in multimodal analysis: {updated_item.get('error', 'Unknown error')}")
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
            await info_process(
                data_item.url or "", 
                data_item.metadata.get("title", ""), 
                data_item.metadata.get("author", ""), 
                data_item.metadata.get("publish_date", ""), 
                [data_item.content],
                data_item.metadata.get("links", {}), 
                focus["id"],
                get_info_prompts
            )
        return
    
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


async def main_process(focus: dict, sites: list):
    wiseflow_logger.debug('new task initializing...')
    focus_id = focus["id"]
    focus_point = focus["focuspoint"].strip()
    explanation = focus["explanation"].strip() if focus["explanation"] else ''
    wiseflow_logger.debug(f'focus_id: {focus_id}, focus_point: {focus_point}, explanation: {explanation}, search_engine: {focus["search_engine"]}')
    existing_urls = {url['url'] for url in pb.read(collection_name='infos', fields=['url'], filter=f"tag='{focus_id}'")}
    focus_statement = f"{focus_point}"
    date_stamp = datetime.now().strftime('%Y-%m-%d')
    if is_chinese(focus_point):
        focus_statement = f"{focus_statement}\n注：{explanation}（目前日期是{date_stamp}）"
    else:
        focus_statement = f"{focus_statement}\nNote: {explanation}(today is {date_stamp})"

    if is_chinese(focus_statement):
        get_link_sys_prompt = get_link_system.replace('{focus_statement}', focus_statement)
        # get_link_sys_prompt = f"今天的日期是{date_stamp}，{get_link_sys_prompt}"
        get_link_suffix_prompt = get_link_suffix
        get_info_sys_prompt = get_info_system.replace('{focus_statement}', focus_statement)
        # get_info_sys_prompt = f"今天的日期是{date_stamp}，{get_info_sys_prompt}"
        get_info_suffix_prompt = get_info_suffix
    else:
        get_link_sys_prompt = get_link_system_en.replace('{focus_statement}', focus_statement)
        # get_link_sys_prompt = f"today is {date_stamp}, {get_link_sys_prompt}"
        get_link_suffix_prompt = get_link_suffix_en
        get_info_sys_prompt = get_info_system_en.replace('{focus_statement}', focus_statement)
        # get_info_sys_prompt = f"today is {date_stamp}, {get_info_sys_prompt}"
        get_info_suffix_prompt = get_info_suffix_en
    
    get_link_prompts = [get_link_sys_prompt, get_link_suffix_prompt, secondary_model]
    get_info_prompts = [get_info_sys_prompt, get_info_suffix_prompt, model]

    # Load plugins if not already loaded
    if not plugin_manager.plugins:
        wiseflow_logger.info("Loading plugins...")
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
    if focus.get("references"):
        try:
            references = json.loads(focus["references"])
        except:
            references = []
    
    for reference in references:
        ref_type = reference.get("type")
        ref_content = reference.get("content")
        
        if not ref_type or not ref_content:
            continue
        
        if ref_type == "url" and ref_content not in existing_urls:
            # Add URL to sites for processing
            sites.append({"url": ref_content, "type": "web"})
        elif ref_type == "text":
            # Process text reference
            data_item = DataItem(
                source_id=f"text_reference_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                content=ref_content,
                metadata={"title": reference.get("name", "Text Reference"), "type": "text"},
                content_type="text/plain"
            )
            await process_data_with_plugins(data_item, focus, get_info_prompts)

    working_list = set()
    if focus.get('search_engine', False):
        query = focus_point if not explanation else f"{focus_point}({explanation})"
        search_intent, search_content = await run_v4_async(query, _logger=wiseflow_logger)
        _intent = search_intent['search_intent'][0]['intent']
        _keywords = search_intent['search_intent'][0]['keywords']
        wiseflow_logger.info(f'\nquery: {query} keywords: {_keywords}')
        search_results = search_content['search_result']
        for result in search_results:
            if 'content' not in result or 'link' not in result:
                continue
            url = result['link']
            if url in existing_urls:
                continue
            if '（发布时间' not in result['title']:
                title = result['title']
                publish_date = ''
            else:
                title, publish_date = result['title'].split('（发布时间')
                publish_date = publish_date.strip('）')
                # 严格匹配YYYY-MM-DD格式
                date_match = re.search(r'\d{4}-\d{2}-\d{2}', publish_date)
                if date_match:
                    publish_date = date_match.group()
                    publish_date = extract_and_convert_dates(publish_date)
                else:
                    publish_date = ''
                    
            title = title.strip() + '(from search engine)'
            author = result.get('media', '')
            if not author:
                author = urlparse(url).netloc
            texts = [result['content']]
            await info_process(url, title, author, publish_date, texts, {}, focus_id, get_info_prompts)

    # Determine concurrency for this focus point
    concurrency = focus.get("concurrency", 1)
    if concurrency < 1:
        concurrency = 1
    
    # Create a semaphore to limit concurrency
    semaphore = asyncio.Semaphore(concurrency)

    recognized_img_cache = {}
    for site in sites:
        if site.get('type', 'web') == 'rss':
            try:
                feed = feedparser.parse(site['url'])
            except Exception as e:
                wiseflow_logger.warning(f"{site['url']} RSS feed is not valid: {e}")
                continue
            rss_urls = {entry.link for entry in feed.entries if entry.link and isURL(entry.link)}
            wiseflow_logger.debug(f'get {len(rss_urls)} urls from rss source {site["url"]}')
            working_list.update(rss_urls - existing_urls)
        else:
            if site['url'] not in existing_urls and isURL(site['url']):
                working_list.add(site['url'])

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
        if os.environ.get("ENABLE_KNOWLEDGE_GRAPH", "false").lower() == "true" and all_processed_items:
            try:
                await update_knowledge_graph(focus_id, all_processed_items)
            except Exception as e:
                wiseflow_logger.error(f"Error updating knowledge graph: {e}")
    else:
        wiseflow_logger.info("Web connector plugin not available, using default crawler")
        # Fall back to the original crawler implementation
        wiseflow_logger.info("Web connector plugin not available, using default crawler")
        crawler = AsyncWebCrawler(config=browser_cfg)
        await crawler.start()
        
        # Process URLs with concurrency control
        tasks = []
        for url in working_list:
            tasks.append(process_url_with_crawler(url, crawler, focus_id, existing_urls, get_link_prompts, get_info_prompts, recognized_img_cache, semaphore))
        
        if tasks:
            await asyncio.gather(*tasks)
        
        await crawler.close()
    
    wiseflow_logger.debug(f'task finished, focus_id: {focus_id}')


async def process_url_with_connector(url, connector, focus, get_info_prompts, semaphore):
    """Process a URL using a connector with concurrency control."""
    async with semaphore:
        try:
            wiseflow_logger.debug(f"Processing URL with connector: {url}")
            data_items = await collect_from_connector("web_connector", {"urls": [url]})
            
            processed_items = []
            for data_item in data_items:
                items = await process_data_with_plugins(data_item, focus, get_info_prompts)
                if items:
                    processed_items.extend(items)
            
            return processed_items
        except Exception as e:
            wiseflow_logger.error(f"Error processing URL {url} with connector: {e}")
            return []


async def process_url_with_crawler(url, crawler, focus_id, existing_urls, get_link_prompts, get_info_prompts, recognized_img_cache, semaphore):
    """Process a URL using the crawler with concurrency control."""
    async with semaphore:
        try:
            wiseflow_logger.debug(f"Processing URL with crawler: {url}")
            
            has_common_ext = any(url.lower().endswith(ext) for ext in common_file_exts)
            if has_common_ext:
                wiseflow_logger.debug(f'{url} is a common file, skip')
                return

            parsed_url = urlparse(url)
            existing_urls.add(f"{parsed_url.scheme}://{parsed_url.netloc}")
            existing_urls.add(f"{parsed_url.scheme}://{parsed_url.netloc}/")
            domain = parsed_url.netloc
                
            crawler_config.cache_mode = CacheMode.WRITE_ONLY if url in [s['url'] for s in sites] else CacheMode.ENABLED
            try:
                result = await crawler.arun(url=url, config=crawler_config)
            except Exception as e:
                wiseflow_logger.error(e)
                return
            if not result.success:
                wiseflow_logger.warning(f'{url} failed to crawl')
                return
            metadata_dict = result.metadata if result.metadata else {}

            if domain in custom_scrapers:
                result = custom_scrapers[domain](result)
                raw_markdown = result.content
                used_img = result.images
                title = result.title
                if title == 'maybe a new_type_article':
                    wiseflow_logger.warning(f'we found a new type here,{url}\n{result}')
                base_url = result.base
                author = result.author
                publish_date = result.publish_date
            else:
                raw_markdown = result.markdown
                media_dict = result.media if result.media else {}
                used_img = [d['src'] for d in media_dict.get('images', [])]
                title = ''
                base_url = ''
                author = ''
                publish_date = ''
            if not raw_markdown:
                wiseflow_logger.warning(f'{url} no content\n{result}\nskip')
                return
            wiseflow_logger.debug('data preprocessing...')
            if not title:
                title = metadata_dict.get('title', '')
            if not base_url:
                base_url = metadata_dict.get('base', '')
            if not base_url:
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

            if not author:
                author = metadata_dict.get('author', '')
            if not publish_date:
                publish_date = metadata_dict.get('publish_date', '')

            link_dict, links_parts, contents, recognized_img_cache = await pre_process(raw_markdown, base_url, used_img, recognized_img_cache, existing_urls)

            if link_dict and links_parts:
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
                
            if not contents:
                return

            if not author or author.lower() == 'na' or not publish_date or publish_date.lower() == 'na':
                wiseflow_logger.debug('no author or publish date from metadata, will try to get by llm')
                main_content_text = re.sub(r'!\[.*?]\(.*?\)', '', raw_markdown)
                main_content_text = re.sub(r'\[.*?]\(.*?\)', '', main_content_text)
                alt_author, alt_publish_date = await get_author_and_publish_date(main_content_text, secondary_model, _logger=wiseflow_logger)
                if not author or author.lower() == 'na':
                    author = alt_author if alt_author else parsed_url.netloc
                if not publish_date or publish_date.lower() == 'na':
                    publish_date = alt_publish_date if alt_publish_date else ''

            publish_date = extract_and_convert_dates(publish_date)

            await info_process(url, title, author, publish_date, contents, link_dict, focus_id, get_info_prompts)
        except Exception as e:
            wiseflow_logger.error(f"Error processing URL {url} with crawler: {e}")


async def process_focus_point(focus_id: str, focus_point: str, explanation: str, sites: list, search_engine: bool = False):
    """Process a focus point and generate collective insights."""
    try:
        wiseflow_logger.info(f'Processing focus point: {focus_point}')
        
        # Get all info items for this focus point
        info_items = pb.read(collection_name='infos', filter=f"tag='{focus_id}'")
        
        if not info_items:
            wiseflow_logger.warning(f'No information items found for focus ID {focus_id}')
            return
        
        # Extract insights from all items
        all_insights = []
        for item in info_items:
            if 'insights' in item and item['insights']:
                all_insights.append(item['insights'])
        
        if not all_insights:
            wiseflow_logger.warning(f'No insights found for focus ID {focus_id}')
            return
        
        # Generate collective insights
        collective_insights = await generate_collective_insights(
            all_insights,
            focus_point,
            explanation
        )
        
        # Save collective insights
        pb.update(
            collection_name='focus_point',
            id=focus_id,
            data={
                'collective_insights': collective_insights,
                'updated_at': datetime.now().isoformat()
            }
        )
        
        wiseflow_logger.info(f'Collective insights generated and saved for focus point {focus_id}')
        
        # Process multimodal knowledge integration if enabled
        if os.environ.get("ENABLE_MULTIMODAL", "false").lower() == "true":
            try:
                wiseflow_logger.info(f'Integrating multimodal analysis into knowledge graph for focus point {focus_id}')
                
                # Use a separate task for integration to avoid blocking
                integration_task = asyncio.create_task(
                    integrate_multimodal_analysis_with_knowledge_graph(focus_id)
                )
                
                # Set a timeout for the integration task
                try:
                    integration_result = await asyncio.wait_for(integration_task, timeout=300)  # 5 minute timeout
                    wiseflow_logger.info(f'Multimodal knowledge integration completed: {integration_result}')
                except asyncio.TimeoutError:
                    wiseflow_logger.warning(f'Multimodal knowledge integration timed out for focus point {focus_id}')
                    # Cancel the task instead of letting it run in the background
                    integration_task.cancel()
                    try:
                        await integration_task
                    except asyncio.CancelledError:
                        wiseflow_logger.info(f'Multimodal knowledge integration task for focus point {focus_id} was cancelled')
                    except Exception as e:
                        wiseflow_logger.error(f'Error while cancelling integration task: {e}')
                    
                    # Log the timeout as a partial result
                    pb.update(
                        collection_name='focus_point',
                        id=focus_id,
                        data={
                            'multimodal_integration_status': 'timeout',
                            'multimodal_integration_timestamp': datetime.now().isoformat()
                        }
                    )
            
            except Exception as e:
                wiseflow_logger.error(f'Error integrating multimodal analysis into knowledge graph: {e}')
    except Exception as e:
        wiseflow_logger.error(f'Error generating collective insights: {e}')
    
async def update_knowledge_graph(focus_id: str, item_ids: list[str]):
    """Update the knowledge graph with new items."""
    try:
        wiseflow_logger.info(f"Updating knowledge graph for focus {focus_id} with {len(item_ids)} items")
        
        # Get the items from the database
        items = []
        for item_id in item_ids:
            item = pb.read_one('infos', item_id)
            if item:
                items.append(item)
        
        if not items:
            wiseflow_logger.warning(f"No items found for knowledge graph update")
            return
        
        # Extract entities and relationships from items
        entities = []
        relationships = []
        
        for item in items:
            # Extract entities from content
            content_entities = await extract_entities_from_content(item.get('content', ''), item.get('url', ''))
            entities.extend(content_entities)
            
            # Extract relationships from insights
            if 'insights' in item and item['insights']:
                insight_relationships = await extract_relationships_from_insights(item['insights'], content_entities)
                relationships.extend(insight_relationships)
        
        # Update the knowledge graph
        graph_data = {
            "entities": entities,
            "relationships": relationships
        }
        
        # Get existing graph or create a new one
        existing_graph = pb.read_one('knowledge_graphs', filter=f"focus_id='{focus_id}'")
        if existing_graph:
            # Load the existing graph
            graph_path = existing_graph.get('path')
            if graph_path and os.path.exists(graph_path):
                knowledge_graph_builder.import_knowledge_graph(graph_path)
                
            # Enrich the graph with new data
            await knowledge_graph_builder.enrich_knowledge_graph(graph_data)
        else:
            # Build a new graph
            await knowledge_graph_builder.build_knowledge_graph(entities, relationships)
        
        # Export the updated graph
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        graph_dir = os.path.join(project_dir, "knowledge_graphs")
        os.makedirs(graph_dir, exist_ok=True)
        graph_path = os.path.join(graph_dir, f"{focus_id}_{timestamp}.json")
        
        knowledge_graph_builder.export_knowledge_graph(format="json", output_path=graph_path)
        
        # Save or update the graph record in the database
        graph_record = {
            "focus_id": focus_id,
            "path": graph_path,
            "timestamp": timestamp,
            "entity_count": len(knowledge_graph_builder.graph.entities),
            "relationship_count": sum(len(entity.relationships) for entity in knowledge_graph_builder.graph.entities.values()),
            "metadata": {
                "updated_at": datetime.now().isoformat()
            }
        }
        
        if existing_graph:
            pb.update('knowledge_graphs', existing_graph['id'], graph_record)
        else:
            pb.add('knowledge_graphs', graph_record)
        
        wiseflow_logger.info(f"Knowledge graph updated with {len(entities)} entities and {len(relationships)} relationships")
    except Exception as e:
        wiseflow_logger.error(f"Error updating knowledge graph: {e}")


async def extract_entities_from_content(content: str, source_url: str):
    """
    Extract entities from content using NLP techniques.
    
    This function uses a combination of rule-based and model-based approaches
    to extract entities from the content.
    
    Args:
        content: The text content to extract entities from
        source_url: The source URL of the content
        
    Returns:
        List of entity objects
    """
    try:
        wiseflow_logger.info(f"Extracting entities from content from {source_url}")
        
        # Import NLP libraries here to avoid loading them unless needed
        import spacy
        from collections import Counter
        
        # Load the NLP model (will download if not present)
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            wiseflow_logger.info("Downloading spaCy model...")
            import subprocess
            subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], 
                          check=True, capture_output=True)
            nlp = spacy.load("en_core_web_sm")
        
        # Process the content with spaCy
        # Limit content size to avoid memory issues
        max_content_length = 10000
        if len(content) > max_content_length:
            wiseflow_logger.warning(f"Content too large ({len(content)} chars), truncating to {max_content_length} chars")
            content = content[:max_content_length]
            
        doc = nlp(content)
        
        # Extract named entities
        entities = []
        entity_counter = Counter()
        
        for ent in doc.ents:
            # Filter out very common entities and unwanted types
            if ent.label_ in ["DATE", "TIME", "PERCENT", "MONEY", "QUANTITY", "ORDINAL", "CARDINAL"]:
                continue
                
            # Count entity occurrences
            entity_counter[f"{ent.text}|{ent.label_}"] += 1
        
        # Only keep entities that appear multiple times or are important types
        important_entity_types = ["PERSON", "ORG", "GPE", "LOC", "PRODUCT", "EVENT", "WORK_OF_ART"]
        
        for entity_key, count in entity_counter.items():
            entity_text, entity_type = entity_key.split("|")
            
            # Include entity if it appears multiple times or is an important type
            if count > 1 or entity_type in important_entity_types:
                entity_obj = {
                    "id": str(uuid.uuid4()),
                    "name": entity_text,
                    "type": entity_type,
                    "source": source_url,
                    "count": count,
                    "metadata": {
                        "extracted_at": datetime.now().isoformat()
                    }
                }
                entities.append(entity_obj)
        
        wiseflow_logger.info(f"Extracted {len(entities)} entities from content")
        return entities
    except Exception as e:
        wiseflow_logger.error(f"Error extracting entities: {e}")
        # Return empty list on error to avoid breaking the pipeline
        return []


async def extract_relationships_from_insights(insights, entities):
    """
    Extract relationships between entities from insights.
    
    This function analyzes the insights to find relationships between entities.
    
    Args:
        insights: The insights data
        entities: The list of entities to find relationships between
        
    Returns:
        List of relationship objects
    """
    try:
        if not insights or not entities:
            return []
            
        wiseflow_logger.info(f"Extracting relationships from insights with {len(entities)} entities")
        
        # Create a map of entity names to entity objects for quick lookup
        entity_map = {entity["name"].lower(): entity for entity in entities}
        
        # Extract the insight text
        insight_text = ""
        if isinstance(insights, str):
            insight_text = insights
        elif isinstance(insights, dict):
            # Extract text from various possible fields
            for field in ["summary", "content", "text", "analysis", "insights"]:
                if field in insights and isinstance(insights[field], str):
                    insight_text += insights[field] + " "
            
            # If we have a list of insights, concatenate them
            if "items" in insights and isinstance(insights["items"], list):
                for item in insights["items"]:
                    if isinstance(item, str):
                        insight_text += item + " "
                    elif isinstance(item, dict) and "text" in item:
                        insight_text += item["text"] + " "
        
        if not insight_text:
            wiseflow_logger.warning("No insight text found to extract relationships from")
            return []
        
        # Import NLP libraries here to avoid loading them unless needed
        import spacy
        
        # Load the NLP model (will download if not present)
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            wiseflow_logger.info("Downloading spaCy model...")
            import subprocess
            subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], 
                          check=True, capture_output=True)
            nlp = spacy.load("en_core_web_sm")
        
        # Process the insight text with spaCy
        doc = nlp(insight_text)
        
        # Extract relationships using dependency parsing
        relationships = []
        
        # Process each sentence to find relationships
        for sent in doc.sents:
            # Find all entity mentions in this sentence
            entity_mentions = []
            for token in sent:
                token_text = token.text.lower()
                # Check if this token is part of a known entity
                for entity_name, entity in entity_map.items():
                    if token_text in entity_name.split() or entity_name in token_text:
                        entity_mentions.append((token, entity))
            
            # If we have at least two entities in this sentence, they might be related
            if len(entity_mentions) >= 2:
                for i in range(len(entity_mentions)):
                    for j in range(i+1, len(entity_mentions)):
                        token1, entity1 = entity_mentions[i]
                        token2, entity2 = entity_mentions[j]
                        
                        # Skip if it's the same entity
                        if entity1["id"] == entity2["id"]:
                            continue
                        
                        # Find the relationship between these entities
                        relationship_text = extract_relationship_text(sent, token1, token2)
                        
                        if relationship_text:
                            relationship = {
                                "id": str(uuid.uuid4()),
                                "source_entity_id": entity1["id"],
                                "target_entity_id": entity2["id"],
                                "relationship_type": "mentioned_together",
                                "description": relationship_text,
                                "confidence": 0.7,  # Default confidence
                                "metadata": {
                                    "sentence": sent.text,
                                    "extracted_at": datetime.now().isoformat()
                                }
                            }
                            relationships.append(relationship)
        
        wiseflow_logger.info(f"Extracted {len(relationships)} relationships from insights")
        return relationships
    except Exception as e:
        wiseflow_logger.error(f"Error extracting relationships: {e}")
        # Return empty list on error to avoid breaking the pipeline
        return []


def extract_relationship_text(sentence, token1, token2):
    """
    Extract the text describing the relationship between two tokens in a sentence.
    
    Args:
        sentence: The spaCy sentence object
        token1: The first token
        token2: The second token
        
    Returns:
        A string describing the relationship, or None if no clear relationship
    """
    # Get the indices of the tokens
    idx1 = token1.i
    idx2 = token2.i
    
    # Ensure idx1 is the smaller index
    if idx1 > idx2:
        idx1, idx2 = idx2, idx1
        token1, token2 = token2, token1
    
    # Check if the tokens are close enough to have a meaningful relationship
    if idx2 - idx1 > 10:
        return None
    
    # Extract the text between the tokens, including the tokens
    relationship_span = sentence[idx1:idx2+1]
    
    # If the span is too long, it's probably not a clear relationship
    if len(relationship_span) > 15:
        return None
    
    return relationship_span.text
