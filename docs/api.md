# API Documentation

This document describes the API endpoints provided by Wiseflow.

## Authentication

All API requests require an API key, which should be provided in the `X-API-Key` header.

```
X-API-Key: your-api-key
```

You can configure your API key in the `.env` file:

```
WISEFLOW_API_KEY=your-api-key
```

## Endpoints

### Health Check

```
GET /health
```

Check if the API server is running.

#### Response

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2023-01-01T00:00:00.000Z"
}
```

### Process Content

```
POST /api/v1/process
```

Process content using specialized prompting strategies.

#### Request

```json
{
  "content": "Your content here",
  "focus_point": "What you want to extract",
  "explanation": "Additional context",
  "content_type": "text/plain",
  "use_multi_step_reasoning": false,
  "references": null,
  "metadata": {}
}
```

**Parameters:**

- `content` (string, required): The content to process
- `focus_point` (string, required): What you want to extract from the content
- `explanation` (string, optional): Additional context for the extraction
- `content_type` (string, optional): The type of content. Possible values:
  - `text/plain` (default)
  - `text/html`
  - `text/markdown`
  - `text/code`
  - `text/academic`
  - `text/video`
  - `text/social`
- `use_multi_step_reasoning` (boolean, optional): Whether to use multi-step reasoning
- `references` (array, optional): Reference materials for contextual understanding
- `metadata` (object, optional): Additional metadata

#### Response

```json
{
  "summary": "Extracted information",
  "metadata": {
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "max_tokens": 1000,
    "prompt_template": "text_extraction",
    "content_type": "text/plain",
    "task": "extraction",
    "timestamp": "2023-01-01T00:00:00.000Z"
  }
}
```

### Batch Process

```
POST /api/v1/batch
```

Process multiple items concurrently.

#### Request

```json
{
  "items": [
    {
      "content": "Your content here",
      "content_type": "text/plain",
      "metadata": {}
    }
  ],
  "focus_point": "What you want to extract",
  "explanation": "Additional context",
  "use_multi_step_reasoning": false,
  "max_concurrency": 5
}
```

**Parameters:**

- `items` (array, required): Array of items to process
  - `content` (string, required): The content to process
  - `content_type` (string, optional): The type of content
  - `metadata` (object, optional): Additional metadata
- `focus_point` (string, required): What you want to extract from the content
- `explanation` (string, optional): Additional context for the extraction
- `use_multi_step_reasoning` (boolean, optional): Whether to use multi-step reasoning
- `max_concurrency` (integer, optional): Maximum number of concurrent processing tasks

#### Response

```json
[
  {
    "summary": "Extracted information",
    "metadata": {
      "model": "gpt-3.5-turbo",
      "temperature": 0.7,
      "max_tokens": 1000,
      "prompt_template": "text_extraction",
      "content_type": "text/plain",
      "task": "extraction",
      "timestamp": "2023-01-01T00:00:00.000Z"
    }
  }
]
```

### Register Webhook

```
POST /api/v1/webhooks
```

Register a webhook for receiving notifications.

#### Request

```json
{
  "url": "https://example.com/webhook",
  "events": ["process.completed", "batch.completed"],
  "secret": "your-webhook-secret"
}
```

**Parameters:**

- `url` (string, required): The URL to send webhook notifications to
- `events` (array, required): Array of events to subscribe to
- `secret` (string, optional): Secret for signing webhook payloads

#### Response

```json
{
  "id": "webhook-id",
  "url": "https://example.com/webhook",
  "events": ["process.completed", "batch.completed"],
  "created_at": "2023-01-01T00:00:00.000Z"
}
```

### List Webhooks

```
GET /api/v1/webhooks
```

List all registered webhooks.

#### Response

```json
[
  {
    "id": "webhook-id",
    "url": "https://example.com/webhook",
    "events": ["process.completed", "batch.completed"],
    "created_at": "2023-01-01T00:00:00.000Z"
  }
]
```

### Delete Webhook

```
DELETE /api/v1/webhooks/{webhook_id}
```

Delete a registered webhook.

#### Response

```json
{
  "success": true,
  "message": "Webhook deleted"
}
```

## Error Handling

The API uses standard HTTP status codes to indicate the success or failure of a request:

- `200 OK`: The request was successful
- `400 Bad Request`: The request was invalid
- `401 Unauthorized`: The API key is missing or invalid
- `404 Not Found`: The requested resource was not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: An error occurred on the server

Error responses have the following format:

```json
{
  "error": {
    "code": "error_code",
    "message": "Error message",
    "details": {}
  }
}
```

## Rate Limiting

The API has rate limiting to prevent abuse. The rate limits are:

- 60 requests per minute for `/api/v1/process`
- 10 requests per minute for `/api/v1/batch`

Rate limit headers are included in the response:

- `X-RateLimit-Limit`: The maximum number of requests allowed per minute
- `X-RateLimit-Remaining`: The number of requests remaining in the current minute
- `X-RateLimit-Reset`: The time at which the rate limit will reset (Unix timestamp)

## Examples

### Processing Text Content

```python
import requests

api_url = "http://localhost:8000"
api_key = "your-api-key"
headers = {
    "X-API-Key": api_key,
    "Content-Type": "application/json"
}

response = requests.post(
    f"{api_url}/api/v1/process",
    headers=headers,
    json={
        "content": "The quick brown fox jumps over the lazy dog.",
        "focus_point": "Identify the animals mentioned in the text.",
        "content_type": "text/plain"
    }
)

print(response.json())
```

### Processing Multiple Items

```python
import requests

api_url = "http://localhost:8000"
api_key = "your-api-key"
headers = {
    "X-API-Key": api_key,
    "Content-Type": "application/json"
}

response = requests.post(
    f"{api_url}/api/v1/batch",
    headers=headers,
    json={
        "items": [
            {
                "content": "The quick brown fox jumps over the lazy dog.",
                "content_type": "text/plain"
            },
            {
                "content": "The early bird catches the worm.",
                "content_type": "text/plain"
            }
        ],
        "focus_point": "Identify the animals mentioned in the text.",
        "max_concurrency": 2
    }
)

print(response.json())
```

### Registering a Webhook

```python
import requests

api_url = "http://localhost:8000"
api_key = "your-api-key"
headers = {
    "X-API-Key": api_key,
    "Content-Type": "application/json"
}

response = requests.post(
    f"{api_url}/api/v1/webhooks",
    headers=headers,
    json={
        "url": "https://example.com/webhook",
        "events": ["process.completed", "batch.completed"],
        "secret": "your-webhook-secret"
    }
)

print(response.json())
```

