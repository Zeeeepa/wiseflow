# Parallel Research Architecture

This section provides comprehensive documentation about the architecture of the parallel research capabilities in WiseFlow. It includes component diagrams, data flow diagrams, sequence diagrams, and architecture decisions.

## Table of Contents

1. [Architecture Overview](./architecture_overview.md)
2. [Component Diagrams](./component_diagrams.md)
3. [Data Flow Diagrams](./data_flow_diagrams.md)
4. [Sequence Diagrams](./sequence_diagrams.md)
5. [Architecture Decisions](./architecture_decisions.md)

## Introduction

WiseFlow's parallel research architecture is designed to enable efficient and scalable information extraction and analysis from various sources using Large Language Models (LLMs). The architecture supports multiple research modes, parallel processing, and extensibility through plugins.

## Key Components

The parallel research architecture consists of several key components:

### Research Connector

The Research Connector is the main entry point for the research API. It provides methods for performing research on topics and continuing research based on previous results. The connector supports multiple research modes and search APIs.

### Research Graphs

Research Graphs define the workflow for different research modes:

1. **Linear Graph**: A simple sequential research process.
2. **Graph-based Graph**: An iterative research approach with reflection and refinement.
3. **Multi-agent Graph**: A collaborative research approach using specialized agents.

### Thread Pool Manager

The Thread Pool Manager provides functionality for executing CPU-bound tasks concurrently using a thread pool. It is used by the research system to execute tasks in parallel.

### Task Manager

The Task Manager provides functionality for managing and executing asynchronous tasks with support for dependencies, priorities, retries, and timeouts. It is used by the research system to manage complex task workflows.

### Search API Integrations

The Search API Integrations provide access to various search APIs for gathering information. The system supports multiple search APIs including Tavily, Perplexity, Exa, ArXiv, PubMed, and more.

### Dashboard UI

The Dashboard UI provides a user-friendly interface for configuring, executing, and monitoring parallel research tasks. It includes components for configuring research parameters, monitoring tasks, and visualizing results.

## Architecture Principles

The parallel research architecture is guided by several principles:

1. **Modularity**: The system is composed of modular components that can be developed, tested, and deployed independently.

2. **Extensibility**: The architecture supports extension through plugins and custom components.

3. **Scalability**: The system can scale to handle large-scale research tasks through parallel processing.

4. **Resilience**: The architecture includes error handling, retries, and recovery mechanisms to ensure resilience.

5. **Observability**: The system provides monitoring, logging, and visualization capabilities for observing research tasks.

## Architecture Diagrams

For detailed architecture diagrams, see the following pages:

- [Component Diagrams](./component_diagrams.md)
- [Data Flow Diagrams](./data_flow_diagrams.md)
- [Sequence Diagrams](./sequence_diagrams.md)

## Architecture Decisions

For information about key architecture decisions, see the [Architecture Decisions](./architecture_decisions.md) page.

## See Also

- [API Documentation](../api/README.md)
- [Developer Guide](../developer_guide/README.md)
- [Administrator Guide](../admin_guide/README.md)

