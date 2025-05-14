# Parallel Research API

This document describes the API endpoints for managing parallel research flows in WiseFlow.

## Overview

The Parallel Research API allows you to:

1. Start multiple research flows in parallel
2. Continue research based on previous results
3. Monitor the status of research flows
4. Cancel running research flows

## Authentication

All API endpoints require authentication using an API key. The API key should be provided in the `X-API-Key` header.

```
X-API-Key: your-api-key
```

## Endpoints

### Start Parallel Research

Start multiple research flows in parallel.

**URL**: `/api/v1/research/parallel`

**Method**: `POST`

**Request Body**:

```json
{
  "topics": ["Topic 1", "Topic 2", "Topic 3"],
  "config": {
    "search_api": "tavily",
    "research_mode": "linear",
    "max_search_depth": 3,
    "number_of_queries": 4,
    "report_structure": "Custom report structure (optional)",
    "visualization_enabled": false
  },
  "metadata": {
    "user_id": "123",
    "source": "api"
  }
}
```

**Parameters**:

- `topics` (required): List of research topics to process in parallel
- `config` (optional): Research configuration
  - `search_api`: Search API to use (tavily, perplexity, exa, arxiv, pubmed, linkup, duckduckgo, googlesearch)
  - `research_mode`: Research mode to use (linear, graph, multi_agent)
  - `max_search_depth`: Maximum search depth
  - `number_of_queries`: Number of queries per iteration
  - `report_structure`: Custom report structure (optional)
  - `visualization_enabled`: Whether to enable visualization
- `metadata` (optional): Additional metadata

**Response**:

```json
{
  "flow_ids": ["flow-id-1", "flow-id-2", "flow-id-3"],
  "status": "success",
  "message": "Started 3 parallel research flows",
  "timestamp": "2023-01-01T12:00:00.000Z"
}
```

### Start Continuous Research

Start a continuous research flow based on previous results.

**URL**: `/api/v1/research/parallel/continuous`

**Method**: `POST`

**Request Body**:

```json
{
  "previous_flow_id": "flow-id-1",
  "new_topic": "Follow-up question or new topic",
  "config": {
    "search_api": "tavily",
    "research_mode": "linear",
    "max_search_depth": 3,
    "number_of_queries": 4,
    "report_structure": "Custom report structure (optional)",
    "visualization_enabled": false
  },
  "metadata": {
    "user_id": "123",
    "source": "api"
  }
}
```

**Parameters**:

- `previous_flow_id` (required): ID of the previous research flow
- `new_topic` (required): New topic or follow-up question
- `config` (optional): Research configuration (same as above)
- `metadata` (optional): Additional metadata

**Response**:

```json
{
  "flow_ids": ["flow-id-4"],
  "status": "success",
  "message": "Continuous research flow started",
  "timestamp": "2023-01-01T12:00:00.000Z"
}
```

### Get All Research Flows

Get the status of all research flows.

**URL**: `/api/v1/research/parallel/status`

**Method**: `GET`

**Query Parameters**:

- `status` (optional): Filter by status (pending, running, completed, failed, cancelled)
  - Can be specified multiple times to filter by multiple statuses
  - Example: `/api/v1/research/parallel/status?status=running&status=pending`

**Response**:

```json
{
  "flows": [
    {
      "flow_id": "flow-id-1",
      "topic": "Topic 1",
      "status": "completed",
      "created_at": "2023-01-01T12:00:00.000Z",
      "started_at": "2023-01-01T12:00:01.000Z",
      "completed_at": "2023-01-01T12:05:00.000Z",
      "progress": 1.0,
      "error": null,
      "metadata": {
        "user_id": "123",
        "source": "api"
      },
      "config": {
        "search_api": "tavily",
        "research_mode": "linear",
        "max_search_depth": 3,
        "number_of_queries": 4
      }
    },
    {
      "flow_id": "flow-id-2",
      "topic": "Topic 2",
      "status": "running",
      "created_at": "2023-01-01T12:00:00.000Z",
      "started_at": "2023-01-01T12:00:01.000Z",
      "completed_at": null,
      "progress": 0.5,
      "error": null,
      "metadata": {
        "user_id": "123",
        "source": "api"
      },
      "config": {
        "search_api": "tavily",
        "research_mode": "linear",
        "max_search_depth": 3,
        "number_of_queries": 4
      }
    }
  ],
  "count": 2,
  "timestamp": "2023-01-01T12:10:00.000Z"
}
```

### Get Research Flow

Get the status of a specific research flow.

**URL**: `/api/v1/research/parallel/{flow_id}`

**Method**: `GET`

**Path Parameters**:

- `flow_id` (required): ID of the research flow

**Response**:

```json
{
  "flow": {
    "flow_id": "flow-id-1",
    "topic": "Topic 1",
    "status": "completed",
    "created_at": "2023-01-01T12:00:00.000Z",
    "started_at": "2023-01-01T12:00:01.000Z",
    "completed_at": "2023-01-01T12:05:00.000Z",
    "progress": 1.0,
    "error": null,
    "metadata": {
      "user_id": "123",
      "source": "api"
    },
    "config": {
      "search_api": "tavily",
      "research_mode": "linear",
      "max_search_depth": 3,
      "number_of_queries": 4
    }
  },
  "result": {
    "topic": "Topic 1",
    "sections": [
      {
        "title": "Introduction",
        "content": "...",
        "subsections": []
      },
      {
        "title": "Main Body",
        "content": "...",
        "subsections": [
          {
            "title": "Subtopic 1",
            "content": "..."
          },
          {
            "title": "Subtopic 2",
            "content": "..."
          }
        ]
      },
      {
        "title": "Conclusion",
        "content": "...",
        "subsections": []
      }
    ],
    "metadata": {
      "search_api": "tavily",
      "research_mode": "linear",
      "search_depth": 3,
      "queries_per_iteration": 4
    }
  }
}
```

### Cancel Research Flow

Cancel a specific research flow.

**URL**: `/api/v1/research/parallel/{flow_id}/cancel`

**Method**: `POST`

**Path Parameters**:

- `flow_id` (required): ID of the research flow to cancel

**Response**:

```json
{
  "flow_id": "flow-id-2",
  "status": "success",
  "message": "Research flow cancelled",
  "timestamp": "2023-01-01T12:15:00.000Z"
}
```

## Error Responses

### 401 Unauthorized

```json
{
  "detail": "Invalid API key"
}
```

### 404 Not Found

```json
{
  "detail": "Flow not found: flow-id"
}
```

### 429 Too Many Requests

```json
{
  "detail": "Maximum number of concurrent flows reached"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Error message"
}
```

## Status Codes

- `pending`: The flow has been created but not started yet
- `running`: The flow is currently running
- `completed`: The flow has completed successfully
- `failed`: The flow has failed
- `cancelled`: The flow has been cancelled

## Progress Tracking

The `progress` field in the flow status indicates the progress of the research flow as a value between 0.0 and 1.0:

- 0.0: Not started
- 0.2: Started generating report plan
- 0.4: Completed generating report plan
- 0.5: Started writing sections
- 0.9: Completed writing sections
- 1.0: Completed

