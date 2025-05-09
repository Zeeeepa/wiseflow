# WiseFlow API Server

This document provides instructions for setting up and running the WiseFlow API server.

## Overview

The WiseFlow API server provides a RESTful API for integrating WiseFlow with other systems. It enables content processing, webhook management, and other functionality.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Zeeeepa/wiseflow.git
   cd wiseflow
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file to set your configuration:
   - Set `LLM_API_KEY` to your OpenAI API key
   - Set `PB_API_AUTH` to your PocketBase authentication credentials
   - Configure other settings as needed

## Running the API Server

1. Start the API server:
   ```bash
   python api_server.py
   ```

2. The server will be available at `http://0.0.0.0:8000` by default (or the host/port specified in your `.env` file)

## API Endpoints

### Public Endpoints

- `GET /`: Root endpoint, returns basic information about the API
- `GET /health`: Health check endpoint

### Protected Endpoints (require API key)

All protected endpoints require an `X-API-Key` header with the API key specified in the `WISEFLOW_API_KEY` environment variable.

#### Content Processing

- `POST /api/v1/process`: Process content using specialized prompting strategies
- `POST /api/v1/batch`: Process multiple items concurrently

#### Webhook Management

- `GET /api/v1/webhooks`: List all registered webhooks
- `POST /api/v1/webhooks`: Register a new webhook
- `GET /api/v1/webhooks/{webhook_id}`: Get a webhook by ID
- `PUT /api/v1/webhooks/{webhook_id}`: Update an existing webhook
- `DELETE /api/v1/webhooks/{webhook_id}`: Delete a webhook
- `POST /api/v1/webhooks/trigger`: Trigger webhooks for a specific event

#### Integration Endpoints

- `POST /api/v1/integration/extract`: Extract information from content
- `POST /api/v1/integration/analyze`: Analyze content using multi-step reasoning
- `POST /api/v1/integration/contextual`: Process content with contextual understanding

## Testing

1. Run the test script to verify the API server is working correctly:
   ```bash
   python test_api_server.py
   ```

## Troubleshooting

If you encounter issues:

1. Check the logs for error messages
2. Verify your environment variables are set correctly
3. Ensure all dependencies are installed
4. Check that the PocketBase server is running (if using PocketBase)

## Security Considerations

- The API server uses API key authentication for protected endpoints
- Set a strong, unique API key in production
- Consider using HTTPS in production environments
- Limit access to the API server to trusted networks

