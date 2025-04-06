# Wiseflow: Intelligent Continuous Data Mining System

Wiseflow is an AI-powered information extraction tool that uses LLMs to mine relevant information from various sources based on user-defined focus points. It employs a "wide search" approach for broad information collection rather than "deep search" for specific questions.

## Features

- **Multi-source Data Mining**: Collect data from web, GitHub repositories, and more
- **Focus Point Processing**: Extract relevant information based on user-defined focus points
- **Concurrent Processing**: Process multiple data sources simultaneously
- **Reference Support**: Add files, websites, and documents as references for focus points
- **Auto-shutdown**: Automatically shut down tasks when they are complete
- **Plugin Architecture**: Easily extend with new data sources and processors

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Zeeeepa/wiseflow.git
   cd wiseflow
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp core/.env.example core/.env
   ```
   Edit the `.env` file to set your API keys and other configuration options.

4. Set up PocketBase:
   - Download and install PocketBase from [pocketbase.io](https://pocketbase.io/)
   - Start PocketBase and create an admin account
   - Run the schema update script to set up the database:
     ```bash
     python -m core.utils.schema_update
     ```

## Usage

### Starting the Data Mining Process

```bash
python -m core.run_task_new
```

### Adding Focus Points

1. Open the PocketBase admin interface
2. Go to the `focus_points` collection
3. Create a new focus point with:
   - `focuspoint`: The main topic or question to focus on
   - `explanation`: Additional context or explanation
   - `activated`: Set to `true` to enable processing
   - `auto_shutdown`: Set to `true` to automatically shut down when complete
   - `concurrency`: Number of concurrent tasks (default: 1)

### Adding Data Sources

1. Open the PocketBase admin interface
2. Go to the `sites` collection
3. Create a new site with:
   - `url`: The URL of the website or GitHub repository
   - `type`: Select `web` for websites or `github` for GitHub repositories

### Adding References

References can be added programmatically using the `ReferenceManager`:

```python
from core.references import ReferenceManager

# Initialize the reference manager
reference_manager = ReferenceManager()

# Add a file reference
reference_manager.add_file_reference(focus_id="your_focus_id", file_path="/path/to/file.txt")

# Add a web reference
reference_manager.add_web_reference(focus_id="your_focus_id", url="https://example.com")

# Add a text reference
reference_manager.add_text_reference(focus_id="your_focus_id", content="Your reference text", name="reference_name")
```

## Architecture

Wiseflow uses a plugin-based architecture with the following components:

- **Connectors**: Collect data from various sources
  - `WebConnector`: Collects data from websites
  - `GitHubConnector`: Collects data from GitHub repositories

- **Processors**: Process collected data
  - `FocusPointProcessor`: Extracts information based on focus points

- **Task Management**: Manages concurrent data mining tasks
  - `AsyncTaskManager`: Manages asynchronous tasks with concurrency control

- **Reference Management**: Manages reference materials for focus points
  - `ReferenceManager`: Handles file, web, and text references

## License

This project is licensed under the MIT License - see the LICENSE file for details.