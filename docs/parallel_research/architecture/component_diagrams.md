# Component Diagrams

This page provides component diagrams for the parallel research architecture in WiseFlow. These diagrams illustrate the structure and relationships between the major components of the system.

## High-Level Component Diagram

The following diagram shows the high-level components of the parallel research architecture:

```mermaid
graph TD
    User[User] --> Dashboard[Dashboard UI]
    Dashboard --> ResearchAPI[Research API]
    ResearchAPI --> ResearchConnector[Research Connector]
    ResearchConnector --> LinearGraph[Linear Graph]
    ResearchConnector --> GraphBasedGraph[Graph-based Graph]
    ResearchConnector --> MultiAgentGraph[Multi-agent Graph]
    LinearGraph --> SearchAPI[Search API Integration]
    GraphBasedGraph --> SearchAPI
    MultiAgentGraph --> SearchAPI
    LinearGraph --> ThreadPool[Thread Pool Manager]
    GraphBasedGraph --> ThreadPool
    MultiAgentGraph --> ThreadPool
    LinearGraph --> TaskManager[Task Manager]
    GraphBasedGraph --> TaskManager
    MultiAgentGraph --> TaskManager
    SearchAPI --> ExternalAPIs[External Search APIs]
    ThreadPool --> SystemResources[System Resources]
    TaskManager --> SystemResources
```

## Research Connector Component Diagram

The following diagram shows the components of the Research Connector:

```mermaid
graph TD
    ResearchConnector[Research Connector] --> Configuration[Configuration]
    ResearchConnector --> ResearchGraphFactory[Research Graph Factory]
    ResearchConnector --> StateManager[State Manager]
    ResearchGraphFactory --> LinearGraph[Linear Graph]
    ResearchGraphFactory --> GraphBasedGraph[Graph-based Graph]
    ResearchGraphFactory --> MultiAgentGraph[Multi-agent Graph]
    Configuration --> SearchAPIConfig[Search API Configuration]
    Configuration --> ResearchModeConfig[Research Mode Configuration]
    Configuration --> ParallelWorkersConfig[Parallel Workers Configuration]
    StateManager --> ReportState[Report State]
    StateManager --> Sections[Sections]
    StateManager --> Queries[Queries]
    StateManager --> SearchResults[Search Results]
```

## Linear Graph Component Diagram

The following diagram shows the components of the Linear Graph:

```mermaid
graph TD
    LinearGraph[Linear Graph] --> GenerateReportPlan[Generate Report Plan]
    LinearGraph --> WriteSections[Write Sections]
    GenerateReportPlan --> PlannerModel[Planner LLM Model]
    GenerateReportPlan --> SearchAPI[Search API]
    WriteSections --> WriterModel[Writer LLM Model]
    WriteSections --> SearchAPI
    PlannerModel --> ModelProvider[Model Provider]
    WriterModel --> ModelProvider
```

## Graph-based Graph Component Diagram

The following diagram shows the components of the Graph-based Graph:

```mermaid
graph TD
    GraphBasedGraph[Graph-based Graph] --> InitializeResearch[Initialize Research]
    GraphBasedGraph --> GenerateQueries[Generate Queries]
    GraphBasedGraph --> ExecuteSearches[Execute Searches]
    GraphBasedGraph --> SynthesizeKnowledge[Synthesize Knowledge]
    GraphBasedGraph --> UpdateReport[Update Report]
    GraphBasedGraph --> ReflectOnResearch[Reflect on Research]
    GraphBasedGraph --> FinalizeReport[Finalize Report]
    InitializeResearch --> PlannerModel[Planner LLM Model]
    GenerateQueries --> PlannerModel
    ExecuteSearches --> SearchAPI[Search API]
    SynthesizeKnowledge --> WriterModel[Writer LLM Model]
    UpdateReport --> WriterModel
    ReflectOnResearch --> PlannerModel
    FinalizeReport --> WriterModel
    PlannerModel --> ModelProvider[Model Provider]
    WriterModel --> ModelProvider
```

## Multi-agent Graph Component Diagram

The following diagram shows the components of the Multi-agent Graph:

```mermaid
graph TD
    MultiAgentGraph[Multi-agent Graph] --> SupervisorPlanning[Supervisor Planning]
    MultiAgentGraph --> ResearcherInvestigation[Researcher Investigation]
    MultiAgentGraph --> IntegrationFinalization[Integration Finalization]
    SupervisorPlanning --> SupervisorModel[Supervisor LLM Model]
    ResearcherInvestigation --> ResearcherModel[Researcher LLM Model]
    ResearcherInvestigation --> SearchAPI[Search API]
    IntegrationFinalization --> SupervisorModel
    SupervisorModel --> ModelProvider[Model Provider]
    ResearcherModel --> ModelProvider
```

## Thread Pool Manager Component Diagram

The following diagram shows the components of the Thread Pool Manager:

```mermaid
graph TD
    ThreadPoolManager[Thread Pool Manager] --> Executor[Thread Pool Executor]
    ThreadPoolManager --> TaskRegistry[Task Registry]
    ThreadPoolManager --> FutureRegistry[Future Registry]
    ThreadPoolManager --> EventPublisher[Event Publisher]
    Executor --> WorkerThreads[Worker Threads]
    TaskRegistry --> TaskStore[Task Store]
    FutureRegistry --> FutureStore[Future Store]
    EventPublisher --> EventSystem[Event System]
```

## Task Manager Component Diagram

The following diagram shows the components of the Task Manager:

```mermaid
graph TD
    TaskManager[Task Manager] --> TaskRegistry[Task Registry]
    TaskManager --> Scheduler[Task Scheduler]
    TaskManager --> Executor[Task Executor]
    TaskManager --> DependencyManager[Dependency Manager]
    TaskManager --> RetryManager[Retry Manager]
    TaskManager --> EventPublisher[Event Publisher]
    TaskRegistry --> TaskStore[Task Store]
    Scheduler --> SchedulingAlgorithm[Scheduling Algorithm]
    Executor --> AsyncioTasks[Asyncio Tasks]
    DependencyManager --> DependencyGraph[Dependency Graph]
    RetryManager --> RetryPolicy[Retry Policy]
    EventPublisher --> EventSystem[Event System]
```

## Search API Integration Component Diagram

The following diagram shows the components of the Search API Integration:

```mermaid
graph TD
    SearchAPIIntegration[Search API Integration] --> APISelector[API Selector]
    SearchAPIIntegration --> APIAdapters[API Adapters]
    SearchAPIIntegration --> ResultProcessor[Result Processor]
    APISelector --> ConfigurationManager[Configuration Manager]
    APIAdapters --> TavilyAdapter[Tavily Adapter]
    APIAdapters --> PerplexityAdapter[Perplexity Adapter]
    APIAdapters --> ExaAdapter[Exa Adapter]
    APIAdapters --> ArXivAdapter[ArXiv Adapter]
    APIAdapters --> PubMedAdapter[PubMed Adapter]
    APIAdapters --> OtherAdapters[Other Adapters]
    ResultProcessor --> ResultNormalizer[Result Normalizer]
    ResultProcessor --> ResultFilter[Result Filter]
```

## Dashboard UI Component Diagram

The following diagram shows the components of the Dashboard UI:

```mermaid
graph TD
    DashboardUI[Dashboard UI] --> ResearchConfigPanel[Research Config Panel]
    DashboardUI --> TaskMonitorPanel[Task Monitor Panel]
    DashboardUI --> ResultsPanel[Results Panel]
    DashboardUI --> TemplatesPanel[Templates Panel]
    ResearchConfigPanel --> SourceSelector[Source Selector]
    ResearchConfigPanel --> ModeSelector[Mode Selector]
    ResearchConfigPanel --> ParallelWorkersConfig[Parallel Workers Config]
    ResearchConfigPanel --> SearchAPIConfig[Search API Config]
    TaskMonitorPanel --> TaskList[Task List]
    TaskMonitorPanel --> TaskDetails[Task Details]
    TaskMonitorPanel --> ResourceMonitor[Resource Monitor]
    ResultsPanel --> ResultViewer[Result Viewer]
    ResultsPanel --> Visualizations[Visualizations]
    ResultsPanel --> ExportOptions[Export Options]
    TemplatesPanel --> TemplateList[Template List]
    TemplatesPanel --> TemplateSaver[Template Saver]
    TemplatesPanel --> TemplateLoader[Template Loader]
```

## Component Interactions

The following diagram shows the interactions between major components during a research task:

```mermaid
graph TD
    User[User] -->|1. Configure Research| Dashboard[Dashboard UI]
    Dashboard -->|2. Submit Research Task| ResearchAPI[Research API]
    ResearchAPI -->|3. Create Research Task| TaskManager[Task Manager]
    TaskManager -->|4. Schedule Task| Scheduler[Task Scheduler]
    Scheduler -->|5. Execute Task| ResearchConnector[Research Connector]
    ResearchConnector -->|6. Select Graph| ResearchGraphFactory[Research Graph Factory]
    ResearchGraphFactory -->|7. Create Graph| ResearchGraph[Research Graph]
    ResearchGraph -->|8. Execute Graph| GraphExecutor[Graph Executor]
    GraphExecutor -->|9. Execute Node| ThreadPool[Thread Pool Manager]
    ThreadPool -->|10. Execute Search| SearchAPI[Search API Integration]
    SearchAPI -->|11. Query API| ExternalAPI[External Search API]
    ExternalAPI -->|12. Return Results| SearchAPI
    SearchAPI -->|13. Process Results| GraphExecutor
    GraphExecutor -->|14. Update State| ResearchGraph
    ResearchGraph -->|15. Return Results| ResearchConnector
    ResearchConnector -->|16. Complete Task| TaskManager
    TaskManager -->|17. Notify Completion| Dashboard
    Dashboard -->|18. Display Results| User
```

## Component Responsibilities

### Research Connector

- Provides the main API for research
- Manages research configuration
- Selects and executes the appropriate research graph
- Handles research state management

### Research Graphs

- Define the workflow for different research modes
- Manage the execution of research nodes
- Handle state transitions between nodes
- Implement the research logic for each mode

### Thread Pool Manager

- Manages a pool of worker threads
- Executes CPU-bound tasks concurrently
- Tracks task status and results
- Publishes events for task lifecycle

### Task Manager

- Manages asynchronous tasks
- Handles task scheduling and prioritization
- Manages task dependencies
- Implements retry logic and timeout handling

### Search API Integration

- Provides a unified interface to multiple search APIs
- Handles API authentication and rate limiting
- Normalizes search results from different APIs
- Implements fallback mechanisms for API failures

### Dashboard UI

- Provides a user interface for configuring research
- Displays task status and progress
- Visualizes research results
- Manages research templates and presets

## See Also

- [Architecture Overview](./architecture_overview.md)
- [Data Flow Diagrams](./data_flow_diagrams.md)
- [Sequence Diagrams](./sequence_diagrams.md)
- [Architecture Decisions](./architecture_decisions.md)

