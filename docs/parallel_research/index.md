# Parallel Research Documentation

Welcome to the comprehensive documentation for WiseFlow's parallel research capabilities. This documentation provides detailed information for users, developers, and system administrators.

## Overview

WiseFlow's parallel research capabilities allow you to run multiple research tasks simultaneously, significantly improving throughput and efficiency. The system is designed to be scalable, reliable, and easy to use, with both a user-friendly dashboard interface and a powerful API.

## Documentation Sections

### [User Guide](user_guide.md)

The User Guide provides information for end users of the parallel research capabilities. It covers:

- Getting started with parallel research
- Using the dashboard interface
- Using the API
- Common use cases
- Research configuration options
- Visualizing research results
- Troubleshooting common issues

### [Developer Guide](developer_guide.md)

The Developer Guide provides information for developers who want to understand, use, or extend the parallel research capabilities. It covers:

- Architecture overview
- Core components
- API reference
- Integration examples
- Extending the system
- Event system integration
- Performance considerations
- Testing and debugging

### [System Guide](system_guide.md)

The System Guide provides information for system administrators who need to deploy, configure, and maintain the parallel research capabilities. It covers:

- System requirements
- Deployment guides
- Configuration options
- Monitoring and maintenance
- Troubleshooting
- Security considerations
- Upgrade guide
- Support and resources

## Quick Start

To get started with parallel research:

1. **Through the Dashboard**:
   - Open your browser and go to `http://your-wiseflow-server:8000/dashboard`
   - Click on the "Research" tab in the navigation menu
   - Click the "New Research" button
   - Enter your research topic and configure settings
   - Click "Start Research"

2. **Through the API**:
   ```python
   import requests
   import json

   # API endpoint
   url = "http://your-wiseflow-server:8000/api/v1/research"

   # API key authentication
   headers = {
       "Content-Type": "application/json",
       "X-API-Key": "your-api-key"
   }

   # Research request
   data = {
       "topic": "Artificial Intelligence Ethics",
       "use_multi_agent": True,
       "priority": "HIGH",
       "tags": ["ai", "ethics", "research"],
       "config": {
           "search_api": "exa",
           "number_of_queries": 5,
           "max_search_depth": 3,
           "include_academic_papers": True
       }
   }

   # Send request
   response = requests.post(url, headers=headers, data=json.dumps(data))
   result = response.json()

   # Get research ID
   research_id = result["research_id"]
   ```

## Additional Resources

- [API Reference](../api_reference.md): Detailed API documentation
- [Troubleshooting Guide](../troubleshooting.md): Solutions to common issues
- [GitHub Repository](https://github.com/Zeeeepa/wiseflow): Source code and issue tracker

