# Current WiseFlow Architecture

## System Overview Diagram

```
+---------------------+     +---------------------+     +---------------------+
|                     |     |                     |     |                     |
|  External Sources   |     |   User Interface    |     |  External Services  |
|                     |     |                     |     |                     |
+----------+----------+     +----------+----------+     +----------+----------+
           |                           |                           |
           v                           v                           v
+----------+---------------------------+---------------------------+----------+
|                                                                             |
|                                 WiseFlow                                    |
|                                                                             |
|  +---------------+  +---------------+  +---------------+  +---------------+ |
|  |               |  |               |  |               |  |               | |
|  |  Dashboard    |  |  Core Module  |  |  API Server   |  |  Task Manager | |
|  |               |  |               |  |               |  |               | |
|  +-------+-------+  +-------+-------+  +-------+-------+  +-------+-------+ |
|          |                  |                  |                  |          |
|          v                  v                  v                  v          |
|  +-------+------------------+------------------+------------------+-------+ |
|  |                                                                        | |
|  |                           Shared Components                            | |
|  |                                                                        | |
|  |  +---------------+  +---------------+  +---------------+               | |
|  |  |               |  |               |  |               |               | |
|  |  | Event System  |  | Plugin System |  | Configuration |               | |
|  |  |               |  |               |  |               |               | |
|  |  +---------------+  +---------------+  +---------------+               | |
|  |                                                                        | |
|  +------------------------------------------------------------------------+ |
|                                                                             |
+-----------------------------+---------------------------------------------+-+
                              |                                             |
                              v                                             v
                    +---------+---------+                         +---------+---------+
                    |                   |                         |                   |
                    |    PocketBase     |                         |   File Storage    |
                    |                   |                         |                   |
                    +-------------------+                         +-------------------+
```

## Component Relationships

### Core Module

The Core Module is the central component of the WiseFlow system, responsible for processing and analyzing information from various sources.

**Key Responsibilities:**
- Information extraction from various sources
- Analysis using LLMs
- Knowledge graph construction
- Entity extraction and linking

**Dependencies:**
- Depends on Plugin System for extensibility
- Depends on Event System for communication
- Depends on Configuration for settings
- Depends on Task Manager for concurrent processing

**Issues:**
- Too many responsibilities
- Tight coupling with other components
- Mixed business logic and infrastructure concerns

### Dashboard

The Dashboard provides a web-based user interface for interacting with the WiseFlow system.

**Key Responsibilities:**
- Search interface
- Visualization of analysis results
- Configuration management
- Task monitoring

**Dependencies:**
- Depends on Core Module for data processing
- Depends on API Server for data access
- Depends on Configuration for settings

**Issues:**
- Mixed UI and data processing concerns
- Direct dependency on Core Module
- Inconsistent error handling

### API Server

The API Server provides REST API endpoints for external integration with the WiseFlow system.

**Key Responsibilities:**
- REST API endpoints
- Authentication and authorization
- Request validation
- Response formatting

**Dependencies:**
- Depends on Core Module for data processing
- Depends on Configuration for settings
- Depends on Event System for notifications

**Issues:**
- Tight coupling with Core Module
- Limited error handling
- Inconsistent API design

### Task Manager

The Task Manager handles concurrent processing of tasks in the WiseFlow system.

**Key Responsibilities:**
- Task scheduling and execution
- Dependency management
- Resource monitoring and optimization

**Dependencies:**
- Depends on Configuration for settings
- Depends on Event System for notifications

**Issues:**
- Mixed scheduling and execution concerns
- Limited error recovery
- Potential race conditions

### Event System

The Event System facilitates communication between components in the WiseFlow system.

**Key Responsibilities:**
- Event publication and subscription
- Asynchronous communication
- Decoupling of components

**Dependencies:**
- Depends on Configuration for settings

**Issues:**
- Inconsistent usage across components
- Limited error handling
- No clear event contracts

### Plugin System

The Plugin System enables extensibility of the WiseFlow system through custom plugins.

**Key Responsibilities:**
- Plugin loading and management
- Plugin lifecycle management
- Plugin isolation

**Dependencies:**
- Depends on Configuration for settings
- Depends on Event System for notifications

**Issues:**
- Tight coupling with Core Module
- Limited plugin isolation
- Inconsistent plugin interfaces

### Configuration

The Configuration component handles settings and environment variables for the WiseFlow system.

**Key Responsibilities:**
- Environment-based configuration
- Validation of configuration values
- Secure storage of sensitive information

**Dependencies:**
- No major dependencies

**Issues:**
- Complex configuration system
- Limited validation
- Configuration spread across multiple files

## Data Flow

1. **Information Collection**:
   - External sources → Core Module → PocketBase
   - User input → Dashboard → Core Module → PocketBase

2. **Information Processing**:
   - PocketBase → Core Module → External Services → Core Module → PocketBase

3. **Information Presentation**:
   - PocketBase → Core Module → Dashboard → User Interface

4. **Task Execution**:
   - User Interface → Dashboard → API Server → Task Manager → Core Module

5. **Event Propagation**:
   - Component A → Event System → Component B

## Current Architecture Issues

1. **Tight Coupling**:
   - Components directly import each other
   - Shared mutable state
   - Implicit dependencies

2. **Mixed Responsibilities**:
   - Components handle multiple concerns
   - No clear boundaries between components
   - Business logic mixed with infrastructure

3. **Inconsistent Patterns**:
   - Inconsistent error handling
   - Varied state management approaches
   - Mixed synchronous and asynchronous operations

4. **Limited Extensibility**:
   - Plugin system tightly coupled with core
   - Hard-coded dependencies
   - Implicit contracts between components

5. **Complex Configuration**:
   - Configuration spread across multiple files
   - Limited validation
   - No clear configuration management strategy

