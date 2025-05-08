# WiseFlow API Reference

This document provides a comprehensive reference for the WiseFlow API, including all endpoints, request and response formats, and authentication requirements.

## Table of Contents

- [Authentication](#authentication)
- [Base URL](#base-url)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [API Endpoints](#api-endpoints)
  - [Health Check](#health-check)
  - [Content Processing](#content-processing)
  - [Batch Processing](#batch-processing)
  - [Integration Endpoints](#integration-endpoints)
  - [Webhook Management](#webhook-management)
  - [Focus Point Management](#focus-point-management)
  - [Insight Management](#insight-management)
- [Webhook Events](#webhook-events)
- [Client Libraries](#client-libraries)

## Authentication

All API requests require authentication using an API key. You can set your API key in the environment variable `WISEFLOW_API_KEY`.

Include the API key in the `X-API-Key` header of your requests:

```
X-API-Key: your-api-key
```

## Base URL

The base URL for the API is:

```
http://your-wiseflow-instance:8000
```

Replace `your-wiseflow-instance` with the hostname or IP address of your WiseFlow instance.

## Response Format

All API responses are in JSON format. Successful responses have the following structure:

```json
{
  "data": {
    // Response data
  },
  "timestamp": "2023-01-01T12:00:00Z"
}
```

## Error Handling

Error responses have the following structure:

```json
{
  "error": {
    "code": "error_code",
    "message": "Error message",
    "details": {
      // Additional error details
    }
  },
  "timestamp": "2023-01-01T12:00:00Z"
}
```

Common error codes:

- `400`: Bad Request - The request was malformed or missing required parameters
- `401`: Unauthorized - Invalid or missing API key
- `404`: Not Found - The requested resource was not found
- `429`: Too Many Requests - Rate limit exceeded
- `500`: Internal Server Error - An error occurred on the server

## Rate Limiting

The API has rate limiting to prevent abuse. The rate limits are:

- 60 requests per minute per API key
- 1000 requests per day per API key

Rate limit headers are included in all responses:

- `X-RateLimit-Limit`: The maximum number of requests allowed in the current time window
- `X-RateLimit-Remaining`: The number of requests remaining in the current time window
- `X-RateLimit-Reset`: The time when the current rate limit window resets (Unix timestamp)

## API Endpoints

### Health Check

#### GET /health

Check the health status of the API.

**Response:**

```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2023-01-01T12:00:00Z"
}
```

### Content Processing

#### POST /api/v1/process

Process content using specialized prompting strategies.

**Request Body:**

```json
{
  "content": "The content to process",
  "focus_point": "The focus point for extraction",
  "explanation": "Additional explanation or context",
  "content_type": "text/plain",
  "use_multi_step_reasoning": false,
  "references": "Optional reference materials for contextual understanding",
  "metadata": {}
}
```

**Parameters:**

- `content` (string, required): The content to process
- `focus_point` (string, required): The focus point for extraction
- `explanation` (string, optional): Additional explanation or context
- `content_type` (string, optional): The content type (default: "text/plain")
- `use_multi_step_reasoning` (boolean, optional): Whether to use multi-step reasoning (default: false)
- `references` (string, optional): Reference materials for contextual understanding
- `metadata` (object, optional): Additional metadata

**Response:**

```json
{
  "summary": "Extracted or processed information",
  "metadata": {},
  "timestamp": "2023-01-01T12:00:00Z"
}
```

### Batch Processing

#### POST /api/v1/batch-process

Process multiple items concurrently.

**Request Body:**

```json
{
  "items": [
    {
      "content": "The content to process",
      "content_type": "text/plain",
      "metadata": {}
    }
  ],
  "focus_point": "The focus point for extraction",
  "explanation": "Additional explanation or context",
  "use_multi_step_reasoning": false,
  "max_concurrency": 5
}
```

**Parameters:**

- `items` (array, required): Array of items to process
  - `content` (string, required): The content to process
  - `content_type` (string, optional): The content type (default: "text/plain")
  - `metadata` (object, optional): Additional metadata
- `focus_point` (string, required): The focus point for extraction
- `explanation` (string, optional): Additional explanation or context
- `use_multi_step_reasoning` (boolean, optional): Whether to use multi-step reasoning (default: false)
- `max_concurrency` (integer, optional): Maximum number of concurrent processing tasks (default: 5)

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

#### POST /api/v1/integration/extract

Extract information from content.

**Request Body:**

```json
{
  "content": "The content to process",
  "focus_point": "The focus point for extraction",
  "explanation": "Additional explanation or context",
  "content_type": "text/plain",
  "references": "Optional reference materials for contextual understanding",
  "metadata": {}
}
```

**Parameters:**

- `content` (string, required): The content to process
- `focus_point` (string, required): The focus point for extraction
- `explanation` (string, optional): Additional explanation or context
- `content_type` (string, optional): The content type (default: "text/plain")
- `references` (string, optional): Reference materials for contextual understanding
- `metadata` (object, optional): Additional metadata

**Response:**

```json
{
  "extracted_information": "Extracted information",
  "metadata": {},
  "timestamp": "2023-01-01T12:00:00Z"
}
```

#### POST /api/v1/integration/analyze

Analyze content using multi-step reasoning.

**Request Body:**

```json
{
  "content": "The content to process",
  "focus_point": "The focus point for extraction",
  "explanation": "Additional explanation or context",
  "content_type": "text/plain",
  "references": "Optional reference materials for contextual understanding",
  "metadata": {}
}
```

**Parameters:**

- `content` (string, required): The content to process
- `focus_point` (string, required): The focus point for extraction
- `explanation` (string, optional): Additional explanation or context
- `content_type` (string, optional): The content type (default: "text/plain")
- `references` (string, optional): Reference materials for contextual understanding
- `metadata` (object, optional): Additional metadata

**Response:**

```json
{
  "analysis": "Analysis result",
  "reasoning_steps": [],
  "metadata": {},
  "timestamp": "2023-01-01T12:00:00Z"
}
```

#### POST /api/v1/integration/contextual

Process content with contextual understanding.

**Request Body:**

```json
{
  "content": "The content to process",
  "focus_point": "The focus point for extraction",
  "explanation": "Additional explanation or context",
  "content_type": "text/plain",
  "references": "Reference materials for contextual understanding",
  "metadata": {}
}
```

**Parameters:**

- `content` (string, required): The content to process
- `focus_point` (string, required): The focus point for extraction
- `explanation` (string, optional): Additional explanation or context
- `content_type` (string, optional): The content type (default: "text/plain")
- `references` (string, required): Reference materials for contextual understanding
- `metadata` (object, optional): Additional metadata

**Response:**

```json
{
  "contextual_understanding": "Contextual understanding result",
  "metadata": {},
  "timestamp": "2023-01-01T12:00:00Z"
}
```

### Webhook Management

#### GET /api/v1/webhooks

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

#### POST /api/v1/webhooks

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

**Parameters:**

- `endpoint` (string, required): The webhook endpoint URL
- `events` (array, required): Array of event types to subscribe to
- `headers` (object, optional): Custom headers to include in webhook requests
- `secret` (string, optional): Secret for signing webhook payloads
- `description` (string, optional): Description of the webhook

**Response:**

```json
{
  "webhook_id": "webhook_1",
  "message": "Webhook registered successfully",
  "timestamp": "2023-01-01T12:00:00Z"
}
```

#### GET /api/v1/webhooks/{webhook_id}

Get a webhook by ID.

**Parameters:**

- `webhook_id` (string, required): ID of the webhook to retrieve

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

#### PUT /api/v1/webhooks/{webhook_id}

Update an existing webhook.

**Parameters:**

- `webhook_id` (string, required): ID of the webhook to update

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

#### DELETE /api/v1/webhooks/{webhook_id}

Delete a webhook.

**Parameters:**

- `webhook_id` (string, required): ID of the webhook to delete

**Response:**

```json
{
  "webhook_id": "webhook_1",
  "message": "Webhook deleted successfully",
  "timestamp": "2023-01-01T12:00:00Z"
}
```

#### POST /api/v1/webhooks/trigger

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

**Parameters:**

- `event` (string, required): Event type to trigger
- `data` (object, required): Event data
- `async_mode` (boolean, optional): Whether to trigger webhooks asynchronously (default: true)

**Response:**

```json
{
  "event": "content.processed",
  "message": "Webhooks triggered successfully",
  "responses": [],
  "timestamp": "2023-01-01T12:00:00Z"
}
```

### Focus Point Management

#### GET /api/v1/focus-points

List all focus points.

**Query Parameters:**

- `limit` (integer, optional): Maximum number of focus points to return (default: 10)
- `offset` (integer, optional): Offset for pagination (default: 0)
- `active` (boolean, optional): Filter by active status

**Response:**

```json
{
  "focus_points": [
    {
      "id": "focus_point_1",
      "focuspoint": "Example focus point",
      "explanation": "Example explanation",
      "activated": true,
      "search_engine": true,
      "sites": [
        {
          "url": "https://example.com",
          "type": "web"
        }
      ],
      "created_at": "2023-01-01T12:00:00Z",
      "updated_at": "2023-01-01T12:30:00Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

#### POST /api/v1/focus-points

Create a new focus point.

**Request Body:**

```json
{
  "focuspoint": "Example focus point",
  "explanation": "Example explanation",
  "activated": true,
  "search_engine": true,
  "sites": [
    {
      "url": "https://example.com",
      "type": "web"
    }
  ],
  "references": [
    {
      "title": "Example reference",
      "content": "Example reference content",
      "source": "https://example.com/reference",
      "type": "text"
    }
  ]
}
```

**Parameters:**

- `focuspoint` (string, required): The focus point description
- `explanation` (string, optional): Additional explanation or context
- `activated` (boolean, optional): Whether the focus point is active (default: true)
- `search_engine` (boolean, optional): Whether to use search engine (default: false)
- `sites` (array, optional): Array of sites to crawl
  - `url` (string, required): Site URL
  - `type` (string, optional): Site type (default: "web")
- `references` (array, optional): Array of reference materials
  - `title` (string, required): Reference title
  - `content` (string, required): Reference content
  - `source` (string, optional): Reference source
  - `type` (string, optional): Reference type (default: "text")

**Response:**

```json
{
  "focus_point_id": "focus_point_1",
  "message": "Focus point created successfully",
  "timestamp": "2023-01-01T12:00:00Z"
}
```

#### GET /api/v1/focus-points/{focus_point_id}

Get a focus point by ID.

**Parameters:**

- `focus_point_id` (string, required): ID of the focus point to retrieve

**Response:**

```json
{
  "focus_point": {
    "id": "focus_point_1",
    "focuspoint": "Example focus point",
    "explanation": "Example explanation",
    "activated": true,
    "search_engine": true,
    "sites": [
      {
        "url": "https://example.com",
        "type": "web"
      }
    ],
    "references": [
      {
        "id": "reference_1",
        "title": "Example reference",
        "content": "Example reference content",
        "source": "https://example.com/reference",
        "type": "text"
      }
    ],
    "created_at": "2023-01-01T12:00:00Z",
    "updated_at": "2023-01-01T12:30:00Z"
  }
}
```

#### PUT /api/v1/focus-points/{focus_point_id}

Update an existing focus point.

**Parameters:**

- `focus_point_id` (string, required): ID of the focus point to update

**Request Body:**

```json
{
  "focuspoint": "Updated focus point",
  "explanation": "Updated explanation",
  "activated": true,
  "search_engine": true,
  "sites": [
    {
      "url": "https://example.com",
      "type": "web"
    }
  ],
  "references": [
    {
      "title": "Updated reference",
      "content": "Updated reference content",
      "source": "https://example.com/reference",
      "type": "text"
    }
  ]
}
```

**Response:**

```json
{
  "focus_point_id": "focus_point_1",
  "message": "Focus point updated successfully",
  "timestamp": "2023-01-01T12:00:00Z"
}
```

#### DELETE /api/v1/focus-points/{focus_point_id}

Delete a focus point.

**Parameters:**

- `focus_point_id` (string, required): ID of the focus point to delete

**Response:**

```json
{
  "focus_point_id": "focus_point_1",
  "message": "Focus point deleted successfully",
  "timestamp": "2023-01-01T12:00:00Z"
}
```

#### POST /api/v1/focus-points/{focus_point_id}/process

Process a focus point.

**Parameters:**

- `focus_point_id` (string, required): ID of the focus point to process

**Response:**

```json
{
  "focus_point_id": "focus_point_1",
  "message": "Focus point processing started",
  "task_id": "task_1",
  "timestamp": "2023-01-01T12:00:00Z"
}
```

### Insight Management

#### GET /api/v1/insights

List all insights.

**Query Parameters:**

- `limit` (integer, optional): Maximum number of insights to return (default: 10)
- `offset` (integer, optional): Offset for pagination (default: 0)
- `focus_point_id` (string, optional): Filter by focus point ID

**Response:**

```json
{
  "insights": [
    {
      "id": "insight_1",
      "focus_id": "focus_point_1",
      "timestamp": "2023-01-01T12:00:00Z",
      "insights": [
        {
          "type": "trend",
          "content": "Insight content",
          "confidence": 0.9,
          "sources": [
            "info_id_1",
            "info_id_2"
          ]
        }
      ],
      "metadata": {
        "focus_point": "Example focus point",
        "time_period_days": 7
      }
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

#### POST /api/v1/insights/generate

Generate insights for a focus point.

**Request Body:**

```json
{
  "focus_point_id": "focus_point_1",
  "time_period_days": 7
}
```

**Parameters:**

- `focus_point_id` (string, required): ID of the focus point to generate insights for
- `time_period_days` (integer, optional): Number of days to consider for insight generation (default: 7)

**Response:**

```json
{
  "insight_id": "insight_1",
  "message": "Insight generation started",
  "task_id": "task_1",
  "timestamp": "2023-01-01T12:00:00Z"
}
```

#### GET /api/v1/insights/{insight_id}

Get an insight by ID.

**Parameters:**

- `insight_id` (string, required): ID of the insight to retrieve

**Response:**

```json
{
  "insight": {
    "id": "insight_1",
    "focus_id": "focus_point_1",
    "timestamp": "2023-01-01T12:00:00Z",
    "insights": [
      {
        "type": "trend",
        "content": "Insight content",
        "confidence": 0.9,
        "sources": [
          "info_id_1",
          "info_id_2"
        ]
      }
    ],
    "metadata": {
      "focus_point": "Example focus point",
      "time_period_days": 7
    }
  }
}
```

## Webhook Events

WiseFlow can send webhook notifications to your systems when certain events occur. This allows you to build integrations that react to events in real-time.

### Available Events

The following events are available for webhook subscriptions:

- `content.processed`: Triggered when content is processed
- `content.batch_processed`: Triggered when a batch of content is processed
- `integration.extract`: Triggered when information is extracted
- `integration.analyze`: Triggered when content is analyzed
- `integration.contextual`: Triggered when contextual understanding is performed
- `focus_point.processed`: Triggered when a focus point is processed
- `insight.generated`: Triggered when insights are generated

### Webhook Payload

Webhook payloads are sent as JSON objects with the following structure:

```json
{
  "event": "content.processed",
  "data": {
    "focus_point": "Example focus point",
    "content_type": "text/plain",
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

For more information on using the WiseFlow API, see the [API Integration Guide](api_integration.md).

