# Wiseflow Dashboard

The Wiseflow Dashboard provides a web-based interface for visualizing and analyzing data mined from various sources using the Wiseflow plugin system.

## Features

- **Data Mining Visualization**: Visualize knowledge graphs, trends, and entity relationships extracted from text data.
- **Plugin Integration**: Seamlessly integrates with the Wiseflow plugin system, including connectors, processors, and analyzers.
- **Interactive UI**: User-friendly interface for analyzing and visualizing data.
- **Resource Monitoring**: Monitor system resources and task execution.
- **Parallel Research Management**: Create, monitor, and visualize parallel research tasks.

## Architecture

The dashboard is built on top of the Wiseflow core plugin system and consists of the following components:

### Dashboard Plugin Integration

The dashboard integrates with the core plugin system through the `DashboardPluginManager` class, which provides access to connectors, processors, and analyzers.

### Visualization Components

- **Knowledge Graph Visualization**: Visualizes entity relationships as interactive graphs.
- **Trend Visualization**: Visualizes trends and patterns in time series data.
- **Entity Visualization**: Visualizes entities and their attributes.

### Research Management

The dashboard provides a research management interface through the `research_api.py` module, which allows users to:

- Create new research tasks
- Monitor research progress
- View research results
- Visualize research findings
- Cancel research tasks

### Web Interface

The dashboard provides a web interface built with FastAPI and includes the following routes:

- `/dashboard`: Main dashboard interface
- `/dashboard/plugins`: Plugin management interface
- `/dashboard/monitor`: Resource monitoring interface
- `/dashboard/research`: Research management interface
- `/dashboard/research/{research_id}`: Research details interface
- `/dashboard/research/{research_id}/visualize`: Research visualization interface

## Usage

### Starting the Dashboard

The dashboard is integrated with the Wiseflow backend server and starts automatically when the server is started.

```bash
python -m core.app
```

### Accessing the Dashboard

Once the server is running, you can access the dashboard at:

```
http://localhost:8000/dashboard
```

### Using the Dashboard

1. **Text Analysis**: Enter text in the input field and select the analysis type (entity or trend).
2. **Visualization**: Click the "Visualize Results" button to generate visualizations.
3. **Plugin Management**: Navigate to the Plugins page to view and configure available plugins.
4. **Resource Monitoring**: Navigate to the Monitor page to view system resource usage.
5. **Research Management**: Navigate to the Research page to create and monitor research tasks.

### Creating a Research Task

1. Navigate to the Research page
2. Click the "New Research" button
3. Enter your research topic
4. Configure research settings (optional)
5. Toggle "Use Multi-Agent Approach" if desired
6. Set priority level
7. Add tags for organization (optional)
8. Click "Start Research"

### Monitoring Research Progress

1. Navigate to the Research page
2. View all active research tasks in the "Active Research" section
3. Track progress indicators for each task
4. View estimated completion times

### Viewing Research Results

1. Navigate to the Research page
2. Click on a completed research task to view results
3. Navigate through different sections of the research report
4. Use the visualization tools to explore relationships and trends

## API Endpoints

The dashboard provides the following API endpoints:

- `/analyze`: Analyze text using the specified analyzer
- `/visualize/knowledge-graph`: Create a knowledge graph visualization from text
- `/visualize/trend`: Create a trend visualization from text
- `/plugins/connectors`: Get a list of available connectors
- `/plugins/processors`: Get a list of available processors
- `/plugins/analyzers`: Get a list of available analyzers
- `/plugins/connect`: Connect to a data source and fetch data
- `/research`: Create a new research task or get all research tasks
- `/research/active`: Get all active research tasks
- `/research/metrics`: Get research metrics
- `/research/{research_id}`: Get a research task
- `/research/{research_id}/result`: Get the result of a research task
- `/research/{research_id}/cancel`: Cancel a research task
- `/research/{research_id}/visualize`: Create a visualization for a research result

## Development

### Adding New Visualizations

To add a new visualization type:

1. Create a new visualization module in the `dashboard/visualization` directory.
2. Implement the visualization logic in the module.
3. Update the `dashboard/visualization/__init__.py` file to include the new visualization type.
4. Add the necessary UI components to the dashboard templates.

### Adding New Plugin Integrations

To add integration with a new plugin type:

1. Update the `dashboard/plugins/__init__.py` file to include the new plugin type.
2. Implement the necessary methods in the `DashboardPluginManager` class.
3. Update the UI components to support the new plugin type.

### Adding New Research Features

To add new research features:

1. Update the `dashboard/research_api.py` file to include the new features.
2. Implement the necessary methods in the `research_api.py` module.
3. Update the UI components to support the new features.
4. Add the necessary API endpoints to the `dashboard/routes.py` file.

## Dependencies

- FastAPI: Web framework for building APIs
- Jinja2: Template engine for rendering HTML
- Matplotlib: Visualization library for generating plots
- NetworkX: Graph library for knowledge graph visualization
- NumPy: Numerical computing library
- Pandas: Data analysis library
