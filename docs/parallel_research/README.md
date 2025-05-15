# Parallel Research Documentation

This documentation provides comprehensive information about the parallel research capabilities in WiseFlow. It covers API documentation, user guides, architecture diagrams, and developer documentation to ensure proper usage and maintainability.

## Overview

WiseFlow's parallel research capabilities allow users to extract information from various sources using Large Language Models (LLMs) in a concurrent and efficient manner. The system supports multiple research modes and parallel processing to handle large-scale information extraction and analysis tasks.

## Documentation Structure

This documentation is organized into the following sections:

### [API Documentation](./api/README.md)
- API reference for the research connector
- Endpoint specifications
- Request/response formats
- Authentication and authorization

### [User Guide](./user_guide/README.md)
- Dashboard UI usage
- Configuration options
- Research modes explanation
- Best practices for parallel research

### [Architecture](./architecture/README.md)
- Component diagrams
- Data flow diagrams
- Sequence diagrams
- Architecture decisions

### [Developer Guide](./developer_guide/README.md)
- Extension points
- Plugin development
- Integration with other systems
- Testing and debugging

### [Administrator Guide](./admin_guide/README.md)
- Installation and configuration
- Performance tuning
- Monitoring and logging
- Troubleshooting

## Key Concepts

### Research Modes

WiseFlow supports three research modes:

1. **Linear Mode**: A simple sequential research process that follows a straightforward path from query to results.

2. **Graph-based Mode**: An iterative research approach with reflection and refinement, allowing for deeper exploration of topics.

3. **Multi-agent Mode**: A collaborative research approach using specialized agents that work in parallel on different aspects of the research topic.

### Parallel Processing

WiseFlow implements parallel processing through:

1. **Thread Pool Management**: Efficient allocation and management of threads for concurrent task execution.

2. **Task Management**: Scheduling, prioritization, and dependency management for research tasks.

3. **Configurable Parallelism**: User-configurable parallel workers for different data sources.

## Getting Started

To get started with parallel research in WiseFlow, see the [Quick Start Guide](./user_guide/quick_start.md).

## Contributing to Documentation

We welcome contributions to improve this documentation. Please see the [Contributing Guide](./CONTRIBUTING.md) for more information.

