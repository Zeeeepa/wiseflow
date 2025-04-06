# Phase 2: Expansion - UI Mockups

This document provides detailed UI mockup descriptions for the Expansion phase of the Wiseflow upgrade plan.

## YouTube Content Explorer

The YouTube Content Explorer provides a specialized interface for discovering, analyzing, and extracting insights from YouTube videos and channels.

**Key Features:**
- Channel and video search with advanced filters
- Video transcription and content analysis
- Thumbnail and frame analysis
- Comment sentiment analysis
- Engagement metrics visualization
- Topic and trend identification

**UI Elements:**
- Search interface with filters for channel, date, duration, etc.
- Video player with integrated transcript
- Channel profile with analytics
- Comment analysis dashboard
- Visual timeline of key moments
- Related content recommendations

**Mockup Description:**
The YouTube Content Explorer features a video-centric design with a prominent search bar at the top. Search results are displayed in a grid layout with video thumbnails, titles, channel names, and key metrics (views, likes, comments). Filters on the left allow refining results by upload date, duration, channel, category, etc. Clicking on a video opens a detailed view with the video player at the top and tabs below for different analyses: Transcript (showing the full text with timestamps and key phrase highlighting), Comments (displaying a sentiment analysis dashboard and top comments), Visual Analysis (showing key frames with object detection and scene analysis), and Metrics (visualizing engagement over time and compared to similar videos). The channel view provides analytics on posting frequency, audience engagement, and topic evolution over time.

## Code Search Interface

The Code Search Interface provides powerful tools for searching, analyzing, and understanding code across repositories.

**Key Features:**
- Semantic code search across multiple repositories
- Language-specific parsing and understanding
- Code similarity and pattern detection
- Function and class relationship mapping
- Code quality and complexity metrics
- Security vulnerability scanning

**UI Elements:**
- Advanced search with language and pattern filters
- Code viewer with syntax highlighting and navigation
- Function and class browser
- Dependency graph visualization
- Code quality dashboard
- Similar code finder

**Mockup Description:**
The Code Search Interface features a dual-pane layout similar to modern code editors. The left pane provides search capabilities with support for regular expressions, semantic queries, and code patterns. Search results are displayed in a list with code snippets and repository information. The right pane shows the selected code with syntax highlighting, line numbers, and navigation tools. Above the code viewer, tabs provide access to different analysis tools: Structure (showing a tree view of functions, classes, and their relationships), Quality (displaying metrics like complexity, test coverage, and potential issues), Dependencies (visualizing import relationships and external dependencies), and Similar Code (identifying duplicate or similar code patterns across repositories). A bottom panel can be expanded to show terminal output, search history, or additional context.

## Entity Explorer

The Entity Explorer provides tools for discovering, analyzing, and linking entities across different data sources.

**Key Features:**
- Entity extraction and classification
- Entity resolution and disambiguation
- Relationship mapping and visualization
- Timeline construction
- Cross-source entity linking
- Entity profile generation

**UI Elements:**
- Entity search and filter interface
- Entity profile cards with source attribution
- Relationship graph visualization
- Timeline view of entity mentions
- Source comparison view
- Entity merging and splitting tools

**Mockup Description:**
The Entity Explorer features a search-first interface with a prominent search bar and entity type filters (person, organization, location, concept, etc.). Search results are displayed as entity cards with key attributes, source counts, and confidence scores. Clicking on an entity opens a detailed profile view with tabs for different perspectives: Overview (showing key attributes and a summary), Sources (listing all mentions across data sources with context), Relationships (visualizing connections to other entities in an interactive graph), Timeline (displaying mentions and events chronologically), and Variants (showing different names or identifiers used for the entity across sources). The interface includes tools for manually merging duplicate entities or splitting incorrectly combined ones. A comparison view allows examining how the same entity is represented across different sources.

## Knowledge Graph Visualization

The Knowledge Graph Visualization provides an interactive interface for exploring and querying the knowledge graph constructed from extracted information.

**Key Features:**
- Interactive graph visualization
- Entity and relationship filtering
- Path finding between entities
- Subgraph extraction and exploration
- Knowledge graph querying
- Visual knowledge graph construction and editing

**UI Elements:**
- Interactive graph canvas with zoom and pan controls
- Entity and relationship type filters
- Search and query interface
- Detail panel for selected entities and relationships
- History and bookmarking tools
- Export and sharing options

**Mockup Description:**
The Knowledge Graph Visualization features a large central canvas displaying entities as nodes and relationships as edges in an interactive graph. A control panel on the left provides filters for entity types (color-coded), relationship types, data sources, and time periods. A search bar at the top allows finding specific entities or running graph queries in a simplified query language. Selecting a node or edge displays its details in a panel on the right, including attributes, source information, and confidence scores. The interface includes tools for expanding the graph around selected nodes, finding paths between entities, and extracting subgraphs based on criteria. Users can save views as bookmarks, export visualizations in various formats, and share links to specific graph states. An edit mode allows authorized users to manually add, modify, or remove entities and relationships with full provenance tracking.