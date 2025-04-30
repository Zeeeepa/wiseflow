# Wiseflow Dashboard

The Wiseflow Dashboard provides a web-based interface for visualizing and analyzing data mined from various sources using the Wiseflow plugin system.

## Features

- **Data Mining Visualization**: Visualize knowledge graphs, trends, and entity relationships extracted from text data.
- **Plugin Integration**: Seamlessly integrates with the Wiseflow plugin system, including connectors, processors, and analyzers.
- **Interactive UI**: User-friendly interface for analyzing and visualizing data.
- **Resource Monitoring**: Monitor system resources and task execution.

## Architecture

The dashboard is built on top of the Wiseflow core plugin system and consists of the following components:

### Dashboard Plugin Integration

The dashboard integrates with the core plugin system through the `DashboardPluginManager` class, which provides access to connectors, processors, and analyzers.

### Visualization Components

- **Knowledge Graph Visualization**: Visualizes entity relationships as interactive graphs.
- **Trend Visualization**: Visualizes trends and patterns in time series data.
- **Entity Visualization**: Visualizes entities and their attributes.

### Web Interface

The dashboard provides a web interface built with FastAPI and includes the following routes:

- `/dashboard`: Main dashboard interface
- `/dashboard/plugins`: Plugin management interface
- `/dashboard/monitor`: Resource monitoring interface

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

## API Endpoints

The dashboard provides the following API endpoints:

- `/analyze`: Analyze text using the specified analyzer
- `/visualize/knowledge-graph`: Create a knowledge graph visualization from text
- `/visualize/trend`: Create a trend visualization from text
- `/plugins/connectors`: Get a list of available connectors
- `/plugins/processors`: Get a list of available processors
- `/plugins/analyzers`: Get a list of available analyzers
- `/plugins/connect`: Connect to a data source and fetch data

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

## Dependencies

- FastAPI: Web framework for building APIs
- Jinja2: Template engine for rendering HTML
- Matplotlib: Visualization library for generating plots
- NetworkX: Graph library for knowledge graph visualization
- NumPy: Numerical computing library
- Pandas: Data analysis library

