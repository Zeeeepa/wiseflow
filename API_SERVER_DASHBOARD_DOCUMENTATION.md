# WiseFlow API Server and Dashboard Documentation

## Overview

This document provides an overview of the improvements made to the WiseFlow API server and dashboard functionality. The changes focus on fixing runtime errors, improving error handling, enhancing security, and standardizing responses.

## Key Improvements

### 1. Fixed Import Structure

- Resolved circular import issues in `dashboard/__init__.py` by moving imports inside functions
- Fixed incorrect relative import in `dashboard/main.py`
- Ensured proper initialization of required classes and components

### 2. Improved Error Handling

- Implemented standardized error response format across all endpoints
- Added proper exception handling with detailed error messages
- Created error response models for consistent error reporting
- Added validation for request parameters

### 3. Enhanced Security

- Restricted CORS configuration to only allow specific origins
- Improved API key authentication with better validation
- Added rate limiting to prevent abuse
- Implemented proper file upload validation and sanitization

### 4. Standardized Request/Response Format

- Created consistent response models (SuccessResponse, ErrorResponse)
- Implemented request validation using Pydantic models
- Added validators for request parameters to ensure data integrity

### 5. Added Missing Functionality

- Implemented the missing `message_manager` function in `backend.py`
- Fixed background task handling to ensure proper execution
- Added proper template directory handling in `routes.py`

### 6. Improved Logging

- Enhanced logging throughout the application
- Added detailed error logging with stack traces
- Implemented consistent log formatting

## API Endpoints

### API Server

- `GET /`: Root endpoint
- `GET /health`: Health check endpoint
- `POST /api/v1/process`: Process content using specialized prompting strategies
- `POST /api/v1/batch`: Process multiple content items concurrently
- `GET /api/v1/webhooks`: List all registered webhooks
- `POST /api/v1/webhooks`: Register a new webhook
- `GET /api/v1/webhooks/{webhook_id}`: Get a webhook by ID
- `PUT /api/v1/webhooks/{webhook_id}`: Update an existing webhook
- `DELETE /api/v1/webhooks/{webhook_id}`: Delete a webhook
- `POST /api/v1/webhooks/trigger`: Trigger webhooks for a specific event
- `POST /api/v1/integration/extract`: Extract information from content
- `POST /api/v1/integration/analyze`: Analyze content using multi-step reasoning
- `POST /api/v1/integration/contextual`: Process content with contextual understanding

### Dashboard

- `GET /dashboard/`: Dashboard home page
- `GET /dashboard/search`: Search dashboard page
- `GET /dashboard/monitor`: Resource monitor dashboard
- `GET /dashboard/data-mining`: Data mining dashboard page
- `GET /dashboard/database`: Database management interface
- `GET /dashboard/plugins`: Information about available plugins
- `GET /dashboard/templates`: Templates management page
- `GET /dashboard/visualization`: Data visualization page
- `GET /dashboard/settings`: Settings page

### Search API

- `POST /search/api/search/github`: Search GitHub
- `POST /search/api/search/arxiv`: Search Arxiv
- `POST /search/api/search/web`: Search the web
- `POST /search/api/search/youtube`: Search YouTube
- `GET /search/api/search/listings`: Get all active search listings
- `POST /search/api/search/toggle/{search_id}`: Toggle the status of a search listing

### Data Mining API

- `POST /data-mining/api/data-mining/tasks`: Create a new data mining task
- `GET /data-mining/api/data-mining/tasks`: Get all data mining tasks
- `POST /data-mining/api/data-mining/templates`: Save a data mining template
- `GET /data-mining/api/data-mining/templates`: Get all data mining templates
- `POST /data-mining/api/data-mining/preview`: Generate a preview of a data mining task
- `GET /data-mining/api/data-mining/tasks/{task_id}`: Get a data mining task by ID
- `PUT /data-mining/api/data-mining/tasks/{task_id}`: Update a data mining task
- `DELETE /data-mining/api/data-mining/tasks/{task_id}`: Delete a data mining task
- `POST /data-mining/api/data-mining/tasks/{task_id}/toggle`: Toggle the status of a data mining task
- `POST /data-mining/api/data-mining/tasks/{task_id}/run`: Run a data mining task
- `GET /data-mining/api/data-mining/tasks/{task_id}/results`: Get the results of a data mining task
- `POST /data-mining/api/data-mining/tasks/{task_id}/analyze`: Analyze the results of a data mining task
- `POST /data-mining/api/data-mining/tasks/{task_id}/interconnect`: Create an interconnection between two data mining tasks
- `GET /data-mining/api/data-mining/interconnections`: Get all task interconnections
- `DELETE /data-mining/api/data-mining/interconnections/{interconnection_id}`: Delete a task interconnection

## Configuration

### Environment Variables

- `WISEFLOW_API_KEY`: API key for authentication
- `ALLOWED_ORIGINS`: Comma-separated list of allowed origins for CORS
- `RATE_LIMIT_ENABLED`: Whether rate limiting is enabled (default: true)
- `RATE_LIMIT_REQUESTS`: Maximum number of requests per window (default: 100)
- `RATE_LIMIT_WINDOW`: Rate limiting window in seconds (default: 3600)
- `API_HOST`: Host for the API server (default: 0.0.0.0)
- `API_PORT`: Port for the API server (default: 8000)
- `API_RELOAD`: Whether to enable auto-reload (default: false)
- `DEBUG`: Whether to enable debug mode (default: false)
- `PROJECT_DIR`: Project directory for the backend service

## Best Practices

1. **Error Handling**: Always use try-except blocks and return standardized error responses
2. **Validation**: Validate all request parameters using Pydantic models
3. **Security**: Use proper authentication and authorization mechanisms
4. **Rate Limiting**: Implement rate limiting to prevent abuse
5. **Logging**: Log all errors and important events
6. **Documentation**: Keep documentation up-to-date with code changes
7. **Testing**: Write tests for all endpoints and functionality

