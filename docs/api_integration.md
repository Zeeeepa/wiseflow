# WiseFlow API and Integration Guide

This guide provides information on how to integrate with WiseFlow using its API and webhook functionality.

## Table of Contents

- [API Overview](#api-overview)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
- [Webhook Integration](#webhook-integration)
- [Client Libraries](#client-libraries)
- [Examples](#examples)

## API Overview

WiseFlow provides a RESTful API that allows you to integrate with its content processing and analysis capabilities. The API is built using FastAPI and follows standard REST conventions.

### Base URL

The base URL for the API is:

```
http://your-wiseflow-instance:8000
```

Replace `your-wiseflow-instance` with the hostname or IP address of your WiseFlow instance.

## Authentication

All API requests require authentication using an API key. You can set your API key in the environment variable `WISEFLOW_API_KEY`.

Include the API key in the `X-API-Key` header of your requests:

```
X-API-Key: your-api-key
```

## API Endpoints

### Health Check

```
GET /health
```

Returns the health status of the API.

### Content Processing

#### Process Content

```
POST /api/v1/process
```

Process content using specialized prompting strategies.

**Request Body:**

```json
{
  "content": "The content to process",
  "focus_point": "The focus point for extraction",
  "explanation": "Additional explanation or context",
  "content_type": "text",
  "use_multi_step_reasoning": false,
  "references": "Optional reference materials for contextual understanding",
  "metadata": {}
}
```

**Response:**

```json
{
  "summary": "Extracted or processed information",
  "metadata": {},
  "timestamp": "2023-01-01T12:00:00Z"
}
```

#### Batch Process

```
POST /api/v1/batch-process
```

Process multiple items concurrently.

**Request Body:**

```json
{
  "items": [
    {
      "content": "The content to process",
      "content_type": "text",
      "metadata": {}
    }
  ],
  "focus_point": "The focus point for extraction",
  "explanation": "Additional explanation or context",
  "use_multi_step_reasoning": false,
  "max_concurrency": 5
}
```

**Response:**

```json
[
  {
    "summary": "Extracted or processed information",
    "metadata": {},
    "timestamp": "2023-01-01T12:00:00Z"
  }
]
```

### Integration Endpoints

#### Extract Information

```
POST /api/v1/integration/extract
```

Extract information from content.

**Request Body:**

```json
{
  "content": "The content to process",
  "focus_point": "The focus point for extraction",
  "explanation": "Additional explanation or context",
  "content_type": "text",
  "references": "Optional reference materials for contextual understanding",
  "metadata": {}
}
```

**Response:**

```json
{
  "extracted_information": "Extracted information",
  "metadata": {},
  "timestamp": "2023-01-01T12:00:00Z"
}
```

#### Analyze Content

```
POST /api/v1/integration/analyze
```

Analyze content using multi-step reasoning.

**Request Body:**

```json
{
  "content": "The content to process",
  "focus_point": "The focus point for extraction",
  "explanation": "Additional explanation or context",
  "content_type": "text",
  "references": "Optional reference materials for contextual understanding",
  "metadata": {}
}
```

**Response:**

```json
{
  "analysis": "Analysis result",
  "reasoning_steps": [],
  "metadata": {},
  "timestamp": "2023-01-01T12:00:00Z"
}
```

#### Contextual Understanding

```
POST /api/v1/integration/contextual
```

Process content with contextual understanding.

**Request Body:**

```json
{
  "content": "The content to process",
  "focus_point": "The focus point for extraction",
  "explanation": "Additional explanation or context",
  "content_type": "text",
  "references": "Reference materials for contextual understanding",
  "metadata": {}
}
```

**Response:**

```json
{
  "contextual_understanding": "Contextual understanding result",
  "metadata": {},
  "timestamp": "2023-01-01T12:00:00Z"
}
```

### Webhook Management

#### List Webhooks

```
GET /api/v1/webhooks
```

List all registered webhooks.

**Response:**

```json
[
  {
    "id": "webhook_1",
    "endpoint": "https://example.com/webhook",
    "events": ["content.processed"],
    "description": "Example webhook",
    "created_at": "2023-01-01T12:00:00Z",
    "last_triggered": "2023-01-01T12:30:00Z",
    "success_count": 10,
    "failure_count": 0
  }
]
```

#### Register Webhook

```
POST /api/v1/webhooks
```

Register a new webhook.

**Request Body:**

```json
{
  "endpoint": "https://example.com/webhook",
  "events": ["content.processed", "content.batch_processed"],
  "headers": {
    "Custom-Header": "Value"
  },
  "secret": "webhook-secret",
  "description": "Example webhook"
}
```

**Response:**

```json
{
  "webhook_id": "webhook_1",
  "message": "Webhook registered successfully",
  "timestamp": "2023-01-01T12:00:00Z"
}
```

#### Get Webhook

```
GET /api/v1/webhooks/{webhook_id}
```

Get a webhook by ID.

**Response:**

```json
{
  "webhook_id": "webhook_1",
  "webhook": {
    "endpoint": "https://example.com/webhook",
    "events": ["content.processed"],
    "headers": {
      "Custom-Header": "Value"
    },
    "description": "Example webhook",
    "created_at": "2023-01-01T12:00:00Z",
    "last_triggered": "2023-01-01T12:30:00Z",
    "success_count": 10,
    "failure_count": 0
  }
}
```

#### Update Webhook

```
PUT /api/v1/webhooks/{webhook_id}
```

Update an existing webhook.

**Request Body:**

```json
{
  "endpoint": "https://example.com/webhook-updated",
  "events": ["content.processed", "content.batch_processed"],
  "headers": {
    "Custom-Header": "Updated-Value"
  },
  "secret": "updated-webhook-secret",
  "description": "Updated example webhook"
}
```

**Response:**

```json
{
  "webhook_id": "webhook_1",
  "message": "Webhook updated successfully",
  "timestamp": "2023-01-01T12:00:00Z"
}
```

#### Delete Webhook

```
DELETE /api/v1/webhooks/{webhook_id}
```

Delete a webhook.

**Response:**

```json
{
  "webhook_id": "webhook_1",
  "message": "Webhook deleted successfully",
  "timestamp": "2023-01-01T12:00:00Z"
}
```

#### Trigger Webhook

```
POST /api/v1/webhooks/trigger
```

Trigger webhooks for a specific event.

**Request Body:**

```json
{
  "event": "content.processed",
  "data": {
    "content_id": "example-123",
    "focus_point": "Example focus point",
    "timestamp": "2023-01-01T12:00:00Z"
  },
  "async_mode": true
}
```

**Response:**

```json
{
  "event": "content.processed",
  "message": "Webhooks triggered successfully",
  "responses": [],
  "timestamp": "2023-01-01T12:00:00Z"
}
```

## Webhook Integration

WiseFlow can send webhook notifications to your systems when certain events occur. This allows you to build integrations that react to events in real-time.

### Webhook Events

The following events are available for webhook subscriptions:

- `content.processed`: Triggered when content is processed
- `content.batch_processed`: Triggered when a batch of content is processed
- `integration.extract`: Triggered when information is extracted
- `integration.analyze`: Triggered when content is analyzed
- `integration.contextual`: Triggered when contextual understanding is performed

### Webhook Payload

Webhook payloads are sent as JSON objects with the following structure:

```json
{
  "event": "content.processed",
  "data": {
    "focus_point": "Example focus point",
    "content_type": "text",
    "result_summary": "Processed result summary",
    "timestamp": "2023-01-01T12:00:00Z"
  },
  "timestamp": "2023-01-01T12:00:00Z",
  "webhook_id": "webhook_1"
}
```

### Webhook Security

Webhooks can be secured using a secret key. When a secret is provided, WiseFlow will sign the webhook payload using HMAC-SHA256 and include the signature in the `X-Webhook-Signature` header.

To verify the signature:

1. Get the signature from the `X-Webhook-Signature` header
2. Compute the HMAC-SHA256 of the request body using your secret key
3. Compare the computed signature with the one in the header

Example in Python:

```python
import hmac
import hashlib
import base64
import json

def verify_signature(payload, signature, secret):
    payload_str = json.dumps(payload, sort_keys=True)
    hmac_obj = hmac.new(
        secret.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    )
    expected_signature = base64.b64encode(hmac_obj.digest()).decode('utf-8')
    return hmac.compare_digest(signature, expected_signature)
```

## Client Libraries

WiseFlow provides client libraries to simplify integration:

### Python Client

```python
from core.api.client import WiseFlowClient

# Initialize the client
client = WiseFlowClient(
    base_url="http://your-wiseflow-instance:8000",
    api_key="your-api-key"
)

# Process content
result = client.process_content(
    content="Your content here",
    focus_point="Your focus point",
    explanation="Additional context"
)

print(result)
```

### Asynchronous Python Client

```python
import asyncio
from core.api.client import AsyncWiseFlowClient

async def main():
    # Initialize the client
    client = AsyncWiseFlowClient(
        base_url="http://your-wiseflow-instance:8000",
        api_key="your-api-key"
    )
    
    # Process content
    result = await client.process_content(
        content="Your content here",
        focus_point="Your focus point",
        explanation="Additional context"
    )
    
    print(result)

asyncio.run(main())
```

## Examples

See the [API Integration Example](../examples/api_integration_example.py) for a complete example of how to use the WiseFlow API and webhook functionality.
