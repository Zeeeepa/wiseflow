# WiseFlow Examples

This document provides examples of how to use WiseFlow for various use cases.

## Table of Contents

- [Basic Usage](#basic-usage)
  - [Processing Content](#processing-content)
  - [Batch Processing](#batch-processing)
  - [Using References](#using-references)
- [API Integration](#api-integration)
  - [Python Client](#python-client)
  - [Asynchronous Python Client](#asynchronous-python-client)
  - [Webhook Integration](#webhook-integration)
- [Plugin Development](#plugin-development)
  - [Custom Connector](#custom-connector)
  - [Custom Processor](#custom-processor)
  - [Custom Analyzer](#custom-analyzer)
- [Advanced Use Cases](#advanced-use-cases)
  - [Knowledge Graph Construction](#knowledge-graph-construction)
  - [Multimodal Analysis](#multimodal-analysis)
  - [Cross-Source Analysis](#cross-source-analysis)

## Basic Usage

### Processing Content

This example demonstrates how to process content with WiseFlow.

```python
from core.general_process import info_process
import asyncio

async def process_example():
    # Define the content to process
    url = "https://example.com"
    url_title = "Example Website"
    author = "John Doe"
    publish_date = "2023-01-01"
    contents = ["This is an example content to process."]
    link_dict = {}
    focus_id = "focus_point_id"
    get_info_prompts = [
        "Focus point: Extract information about example content",
        "Explanation: Looking for examples of content processing"
    ]
    
    # Process the content
    processed_items = await info_process(
        url=url,
        url_title=url_title,
        author=author,
        publish_date=publish_date,
        contents=contents,
        link_dict=link_dict,
        focus_id=focus_id,
        get_info_prompts=get_info_prompts
    )
    
    print(f"Processed {len(processed_items)} items")

# Run the example
asyncio.run(process_example())
```

### Batch Processing

This example demonstrates how to process multiple items concurrently.

```python
from core.general_process import process_data_with_plugins
from core.connectors import DataItem
import asyncio

async def batch_process_example():
    # Define the items to process
    items = [
        DataItem(
            content="This is the first item to process.",
            content_type="text/plain",
            url="https://example.com/item1",
            metadata={"title": "Item 1"}
        ),
        DataItem(
            content="This is the second item to process.",
            content_type="text/plain",
            url="https://example.com/item2",
            metadata={"title": "Item 2"}
        ),
        DataItem(
            content="This is the third item to process.",
            content_type="text/plain",
            url="https://example.com/item3",
            metadata={"title": "Item 3"}
        )
    ]
    
    # Define the focus point
    focus = {
        "id": "focus_point_id",
        "focuspoint": "Extract information about example items",
        "explanation": "Looking for examples of batch processing"
    }
    
    # Define the prompts
    get_info_prompts = [
        f"Focus point: {focus['focuspoint']}",
        f"Explanation: {focus['explanation']}"
    ]
    
    # Process the items concurrently
    tasks = [
        process_data_with_plugins(item, focus, get_info_prompts)
        for item in items
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Count the total number of processed items
    total_processed = sum(len(result) for result in results)
    print(f"Processed {total_processed} items")

# Run the example
asyncio.run(batch_process_example())
```

### Using References

This example demonstrates how to use references for contextual understanding.

```python
from core.references import ReferenceManager
from core.general_process import info_process
import asyncio
import os

async def reference_example():
    # Initialize the reference manager
    reference_manager = ReferenceManager(storage_path="references")
    
    # Add a reference
    reference_manager.add_reference(
        title="Example Reference",
        content="This is an example reference for contextual understanding.",
        source="https://example.com/reference",
        reference_type="text",
        metadata={
            "focus_id": "focus_point_id",
            "focus_point": "Extract information with references"
        }
    )
    
    # Get references for the focus point
    references = reference_manager.get_references_for_focus("focus_point_id")
    
    # Create a reference prompt
    ref_prompt = "References:\n"
    for ref in references:
        ref_prompt += f"- {ref.title}: {ref.content[:200]}...\n"
    
    # Define the content to process
    url = "https://example.com"
    url_title = "Example Website"
    author = "John Doe"
    publish_date = "2023-01-01"
    contents = ["This is an example content to process with references."]
    link_dict = {}
    focus_id = "focus_point_id"
    get_info_prompts = [
        "Focus point: Extract information with references",
        "Explanation: Looking for examples of using references",
        ref_prompt
    ]
    
    # Process the content with references
    processed_items = await info_process(
        url=url,
        url_title=url_title,
        author=author,
        publish_date=publish_date,
        contents=contents,
        link_dict=link_dict,
        focus_id=focus_id,
        get_info_prompts=get_info_prompts
    )
    
    print(f"Processed {len(processed_items)} items with references")

# Run the example
asyncio.run(reference_example())
```

## API Integration

### Python Client

This example demonstrates how to use the Python client to interact with the WiseFlow API.

```python
from core.api.client import WiseFlowClient

def api_client_example():
    # Initialize the client
    client = WiseFlowClient(
        base_url="http://localhost:8000",
        api_key="your-api-key"
    )
    
    # Check API health
    health = client.health_check()
    print(f"API health: {health}")
    
    # Process content
    result = client.process_content(
        content="This is an example content to process.",
        focus_point="Extract information about example content",
        explanation="Looking for examples of content processing"
    )
    
    print(f"Processing result: {result}")
    
    # Batch process
    items = [
        {
            "content": "This is the first item to process.",
            "content_type": "text/plain",
            "metadata": {"title": "Item 1"}
        },
        {
            "content": "This is the second item to process.",
            "content_type": "text/plain",
            "metadata": {"title": "Item 2"}
        }
    ]
    
    results = client.batch_process(
        items=items,
        focus_point="Extract information about example items",
        explanation="Looking for examples of batch processing"
    )
    
    print(f"Batch processing results: {results}")

# Run the example
api_client_example()
```

### Asynchronous Python Client

This example demonstrates how to use the asynchronous Python client to interact with the WiseFlow API.

```python
from core.api.client import AsyncWiseFlowClient
import asyncio

async def async_api_client_example():
    # Initialize the client
    client = AsyncWiseFlowClient(
        base_url="http://localhost:8000",
        api_key="your-api-key"
    )
    
    # Check API health
    health = await client.health_check()
    print(f"API health: {health}")
    
    # Process content
    result = await client.process_content(
        content="This is an example content to process.",
        focus_point="Extract information about example content",
        explanation="Looking for examples of content processing"
    )
    
    print(f"Processing result: {result}")
    
    # Batch process
    items = [
        {
            "content": "This is the first item to process.",
            "content_type": "text/plain",
            "metadata": {"title": "Item 1"}
        },
        {
            "content": "This is the second item to process.",
            "content_type": "text/plain",
            "metadata": {"title": "Item 2"}
        }
    ]
    
    results = await client.batch_process(
        items=items,
        focus_point="Extract information about example items",
        explanation="Looking for examples of batch processing"
    )
    
    print(f"Batch processing results: {results}")

# Run the example
asyncio.run(async_api_client_example())
```

### Webhook Integration

This example demonstrates how to integrate with WiseFlow using webhooks.

```python
from core.api.client import WiseFlowClient
from flask import Flask, request, jsonify
import hmac
import hashlib
import base64
import json
import threading

app = Flask(__name__)

# Webhook secret
WEBHOOK_SECRET = "your-webhook-secret"

# Verify webhook signature
def verify_signature(payload, signature):
    payload_str = json.dumps(payload, sort_keys=True)
    hmac_obj = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    )
    expected_signature = base64.b64encode(hmac_obj.digest()).decode('utf-8')
    return hmac.compare_digest(signature, expected_signature)

# Webhook endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    # Get the signature from the header
    signature = request.headers.get('X-Webhook-Signature')
    
    # Get the payload
    payload = request.json
    
    # Verify the signature
    if not verify_signature(payload, signature):
        return jsonify({"error": "Invalid signature"}), 401
    
    # Process the webhook
    event = payload.get('event')
    data = payload.get('data')
    
    print(f"Received webhook: {event}")
    print(f"Data: {data}")
    
    # Process different event types
    if event == 'content.processed':
        # Handle content processed event
        pass
    elif event == 'content.batch_processed':
        # Handle batch processed event
        pass
    elif event == 'focus_point.processed':
        # Handle focus point processed event
        pass
    elif event == 'insight.generated':
        # Handle insight generated event
        pass
    
    return jsonify({"status": "success"}), 200

# Register webhook with WiseFlow
def register_webhook():
    # Initialize the client
    client = WiseFlowClient(
        base_url="http://localhost:8000",
        api_key="your-api-key"
    )
    
    # Register the webhook
    result = client.register_webhook(
        endpoint="https://your-webhook-endpoint.com/webhook",
        events=["content.processed", "content.batch_processed", "focus_point.processed", "insight.generated"],
        headers={"Custom-Header": "Value"},
        secret=WEBHOOK_SECRET,
        description="Example webhook"
    )
    
    print(f"Webhook registration result: {result}")

# Run the webhook server
if __name__ == '__main__':
    # Register the webhook in a separate thread
    threading.Thread(target=register_webhook).start()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000)
```

## Plugin Development

### Custom Connector

This example demonstrates how to create a custom connector plugin.

```python
from core.connectors import ConnectorBase, DataItem
from typing import List, Dict, Any, Optional
import aiohttp
import logging

logger = logging.getLogger(__name__)

class CustomConnector(ConnectorBase):
    """
    Custom connector for collecting data from a specific API.
    
    This connector demonstrates how to create a custom connector
    that collects data from a specific API.
    """
    
    name = "custom_connector"
    description = "Custom connector for specific API"
    source_type = "api"
    
    def initialize(self) -> bool:
        """
        Initialize the connector.
        
        Returns:
            True if initialization is successful, False otherwise
        """
        logger.info("Initializing custom connector")
        return True
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """
        Collect data from the API.
        
        Args:
            params: Parameters for data collection
                - api_url: URL of the API to collect data from
                - api_key: API key for authentication
                
        Returns:
            A list of DataItem objects containing the collected data
        """
        if not params:
            logger.warning("No parameters provided for custom connector")
            return []
        
        api_url = params.get("api_url")
        api_key = params.get("api_key")
        
        if not api_url:
            logger.warning("No API URL provided for custom connector")
            return []
        
        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Create a DataItem for each item in the response
                        data_items = []
                        for item in data.get("items", []):
                            data_item = DataItem(
                                content=item.get("content", ""),
                                content_type="application/json",
                                url=api_url,
                                metadata={
                                    "title": item.get("title", ""),
                                    "id": item.get("id", ""),
                                    "timestamp": item.get("timestamp", "")
                                }
                            )
                            data_items.append(data_item)
                        
                        logger.info(f"Collected {len(data_items)} items from API")
                        return data_items
                    else:
                        logger.warning(f"Failed to collect data from API: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error collecting data from API: {e}")
            return []
    
    async def collect_with_retry(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """
        Collect data from the API with retry logic.
        
        Args:
            params: Parameters for data collection
                
        Returns:
            A list of DataItem objects containing the collected data
        """
        # Maximum number of retries
        max_retries = 3
        
        for retry in range(max_retries):
            try:
                return await self.collect(params)
            except Exception as e:
                logger.warning(f"Error collecting data from API (retry {retry+1}/{max_retries}): {e}")
                
                if retry < max_retries - 1:
                    # Wait before retrying
                    await asyncio.sleep(2 ** retry)  # Exponential backoff
        
        logger.error(f"Failed to collect data from API after {max_retries} retries")
        return []

# Register the connector with the plugin manager
from core.plugins import PluginManager
plugin_manager = PluginManager()
plugin_manager.register_plugin(CustomConnector)
```

### Custom Processor

This example demonstrates how to create a custom processor plugin.

```python
from core.plugins.processors import ProcessorBase, ProcessedData
from core.connectors import DataItem
from typing import Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)

class CustomProcessor(ProcessorBase):
    """
    Custom processor for processing JSON data.
    
    This processor demonstrates how to create a custom processor
    that processes JSON data.
    """
    
    name = "custom_processor"
    description = "Custom processor for JSON data"
    content_types = ["application/json"]
    
    def process(self, data_item: DataItem, params: Dict[str, Any]) -> Optional[ProcessedData]:
        """
        Process a JSON data item.
        
        Args:
            data_item: The data item to process
            params: Processing parameters
                - focus_point: The focus point for information extraction
                - explanation: Additional context for the focus point
                - fields: List of fields to extract from the JSON data
                
        Returns:
            A ProcessedData object containing the extracted information
        """
        if not data_item.content:
            logger.warning("Empty content in data item")
            return None
        
        focus_point = params.get("focus_point", "")
        explanation = params.get("explanation", "")
        fields = params.get("fields", [])
        
        if not focus_point:
            logger.warning("No focus point provided for custom processor")
            return None
        
        try:
            # Parse the JSON content
            if isinstance(data_item.content, str):
                content = json.loads(data_item.content)
            else:
                content = data_item.content
            
            # Extract the specified fields
            extracted_data = {}
            for field in fields:
                if field in content:
                    extracted_data[field] = content[field]
            
            # Create processed data
            processed_content = [{
                "content": json.dumps(extracted_data),
                "metadata": {
                    "focus_point": focus_point,
                    "explanation": explanation,
                    "fields": fields
                }
            }]
            
            logger.info(f"Processed JSON data with {len(extracted_data)} fields")
            
            return ProcessedData(
                processed_content=processed_content,
                metadata={
                    "focus_point": focus_point,
                    "explanation": explanation,
                    "url": data_item.url,
                    "content_type": data_item.content_type
                }
            )
        except Exception as e:
            logger.error(f"Error processing JSON data: {e}")
            return None

# Register the processor with the plugin manager
from core.plugins import PluginManager
plugin_manager = PluginManager()
plugin_manager.register_plugin(CustomProcessor)
```

### Custom Analyzer

This example demonstrates how to create a custom analyzer plugin.

```python
from core.plugins.analyzers import AnalyzerBase, AnalysisResult
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class CustomAnalyzer(AnalyzerBase):
    """
    Custom analyzer for sentiment analysis.
    
    This analyzer demonstrates how to create a custom analyzer
    that performs sentiment analysis on processed content.
    """
    
    name = "sentiment_analyzer"
    description = "Analyzer for sentiment analysis"
    analysis_type = "sentiment"
    
    def analyze(self, data: List[Dict[str, Any]], params: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Analyze processed content to determine sentiment.
        
        Args:
            data: List of processed content items
            params: Analysis parameters
                - threshold: Minimum confidence score for sentiment (default: 0.7)
                
        Returns:
            An AnalysisResult object containing the sentiment analysis
        """
        if not data:
            logger.warning("No data provided for sentiment analyzer")
            return AnalysisResult(results=[], metadata={})
        
        threshold = params.get("threshold", 0.7) if params else 0.7
        
        try:
            # Perform sentiment analysis
            sentiments = []
            
            for item in data:
                content = item.get("content", "")
                if not content:
                    continue
                
                # Simple sentiment analysis (for demonstration)
                positive_words = ["good", "great", "excellent", "positive", "happy", "joy"]
                negative_words = ["bad", "terrible", "negative", "sad", "unhappy", "disappointed"]
                
                positive_count = sum(1 for word in positive_words if word in content.lower())
                negative_count = sum(1 for word in negative_words if word in content.lower())
                
                total_count = positive_count + negative_count
                if total_count == 0:
                    sentiment = "neutral"
                    score = 0.5
                else:
                    positive_ratio = positive_count / total_count
                    if positive_ratio > 0.6:
                        sentiment = "positive"
                        score = 0.5 + positive_ratio / 2
                    elif positive_ratio < 0.4:
                        sentiment = "negative"
                        score = 0.5 - (1 - positive_ratio) / 2
                    else:
                        sentiment = "neutral"
                        score = 0.5
                
                if score >= threshold:
                    sentiments.append({
                        "content": content[:100] + "..." if len(content) > 100 else content,
                        "sentiment": sentiment,
                        "score": score,
                        "source": item.get("url", "")
                    })
            
            logger.info(f"Analyzed sentiment for {len(sentiments)} items")
            
            return AnalysisResult(
                results=sentiments,
                metadata={
                    "threshold": threshold,
                    "total_items": len(data),
                    "analyzed_items": len(sentiments)
                }
            )
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return AnalysisResult(results=[], metadata={"error": str(e)})

# Register the analyzer with the plugin manager
from core.plugins import PluginManager
plugin_manager = PluginManager()
plugin_manager.register_plugin(CustomAnalyzer)
```

## Advanced Use Cases

### Knowledge Graph Construction

This example demonstrates how to build and query a knowledge graph.

```python
from core.knowledge import KnowledgeGraphBuilder
import asyncio

async def knowledge_graph_example():
    # Initialize the knowledge graph builder
    kg_builder = KnowledgeGraphBuilder(name="Example Knowledge Graph")
    
    # Add entities to the knowledge graph
    kg_builder.add_entity(
        entity_id="entity1",
        name="John Doe",
        entity_type="person",
        properties={
            "age": 30,
            "occupation": "Software Engineer"
        }
    )
    
    kg_builder.add_entity(
        entity_id="entity2",
        name="Acme Corp",
        entity_type="organization",
        properties={
            "industry": "Technology",
            "founded": 2010
        }
    )
    
    kg_builder.add_entity(
        entity_id="entity3",
        name="Project X",
        entity_type="project",
        properties={
            "status": "In Progress",
            "deadline": "2023-12-31"
        }
    )
    
    # Add relationships to the knowledge graph
    kg_builder.add_relationship(
        source_id="entity1",
        target_id="entity2",
        relationship_type="works_for",
        properties={
            "start_date": "2020-01-01",
            "position": "Senior Developer"
        }
    )
    
    kg_builder.add_relationship(
        source_id="entity1",
        target_id="entity3",
        relationship_type="works_on",
        properties={
            "role": "Lead Developer",
            "hours_per_week": 20
        }
    )
    
    kg_builder.add_relationship(
        source_id="entity2",
        target_id="entity3",
        relationship_type="owns",
        properties={
            "investment": 1000000
        }
    )
    
    # Query the knowledge graph
    # Get all entities of type "person"
    persons = kg_builder.get_entities_by_type("person")
    print(f"Persons: {persons}")
    
    # Get all relationships of type "works_for"
    works_for = kg_builder.get_relationships_by_type("works_for")
    print(f"Works for relationships: {works_for}")
    
    # Get all relationships for entity1
    entity1_relationships = kg_builder.get_relationships_for_entity("entity1")
    print(f"Entity1 relationships: {entity1_relationships}")
    
    # Get all entities connected to entity2
    entity2_connections = kg_builder.get_connected_entities("entity2")
    print(f"Entity2 connections: {entity2_connections}")
    
    # Export the knowledge graph
    kg_json = kg_builder.export_to_json()
    print(f"Knowledge graph JSON: {kg_json}")

# Run the example
asyncio.run(knowledge_graph_example())
```

### Multimodal Analysis

This example demonstrates how to perform multimodal analysis with images.

```python
from core.general_process import process_item_with_images
import asyncio

async def multimodal_analysis_example():
    # Define the item and images
    item_id = "item1"
    content = "This is an example content with images."
    image_urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg"
    ]
    focus_point = "Extract information from content and images"
    
    # Process the item with images
    multimodal_result = await process_item_with_images(
        item_id=item_id,
        content=content,
        image_urls=image_urls,
        focus_point=focus_point
    )
    
    print(f"Multimodal analysis result: {multimodal_result}")

# Run the example
asyncio.run(multimodal_analysis_example())
```

### Cross-Source Analysis

This example demonstrates how to perform cross-source analysis.

```python
from core.analysis.entity_linking import link_entities
from core.analysis.trend_analysis import analyze_trends
import asyncio

async def cross_source_analysis_example():
    # Define the data from different sources
    data = [
        {
            "content": "Acme Corp announced a new product today.",
            "source": "news",
            "timestamp": "2023-01-01T12:00:00Z"
        },
        {
            "content": "Acme Corp stock price increased by 10%.",
            "source": "financial",
            "timestamp": "2023-01-01T14:00:00Z"
        },
        {
            "content": "Acme Corp CEO John Doe gave a presentation about the new product.",
            "source": "blog",
            "timestamp": "2023-01-01T16:00:00Z"
        },
        {
            "content": "Acme Corp's new product has received positive reviews.",
            "source": "social",
            "timestamp": "2023-01-02T10:00:00Z"
        },
        {
            "content": "Acme Corp announced plans to expand production of the new product.",
            "source": "news",
            "timestamp": "2023-01-03T09:00:00Z"
        }
    ]
    
    # Link entities across sources
    entities = await link_entities(data)
    print(f"Linked entities: {entities}")
    
    # Analyze trends across sources
    trends = await analyze_trends(data)
    print(f"Trends: {trends}")

# Run the example
asyncio.run(cross_source_analysis_example())
```

These examples demonstrate the various capabilities of WiseFlow and how to use them in different scenarios. You can adapt these examples to your specific use cases and requirements.

