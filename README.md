# Wiseflow

Wiseflow is an LLM-based information extraction and analysis tool that helps you dig out what you care about from massive amounts of information and a variety of sources daily.

## Features

- **Information Extraction**: Extract relevant information from various sources based on your focus points.
- **Advanced Analysis**: Analyze extracted information using LLMs to generate insights.
- **API Integration**: Integrate with other systems using the REST API.
- **Dashboard**: Visualize and manage your information and insights using the dashboard.
- **Extensible Architecture**: Extend the application with custom connectors, processors, and analyzers.
- **Multi-step Reasoning**: Perform complex reasoning on extracted information.
- **Cross-source Analysis**: Analyze information across multiple sources to identify patterns and connections.
- **Knowledge Graph Construction**: Build and maintain knowledge graphs from extracted information.
- **Reference Support**: Provide contextual understanding with reference materials.

## Installation

### Prerequisites

- Python 3.9 or higher
- Node.js 14 or higher (for the dashboard)
- PocketBase (for the database)

### Basic Installation

```bash
# Clone the repository
git clone https://github.com/Zeeeepa/wiseflow.git
cd wiseflow

# Install dependencies
pip install -r requirements.txt
```

### Complete Installation

```bash
# Install PocketBase (database)
# For Linux/macOS
chmod +x install_pocketbase.sh
./install_pocketbase.sh

# For Windows
powershell -ExecutionPolicy Bypass -File install_pocketbase.ps1

# Install all dependencies (including optional ones)
pip install -r requirements.txt -r requirements-optional.txt -r requirements-dev.txt
```

## Configuration

Wiseflow can be configured using environment variables or a configuration file. Create a `.env` file in the root directory with the following variables:

```
# API configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false
WISEFLOW_API_KEY=your-api-key

# LLM configuration
LLM_PROVIDER=litellm
PRIMARY_MODEL=gpt-3.5-turbo
SECONDARY_MODEL=gpt-3.5-turbo
LLM_API_KEY=your-llm-api-key
LLM_API_BASE=https://api.openai.com/v1

# PocketBase configuration
PB_API_BASE=http://127.0.0.1:8090
PB_API_AUTH=admin@example.com|your-password
```

See the [Configuration Guide](docs/configuration.md) for more details.

## Usage

### Starting the API Server

```bash
python api_server.py
```

### Starting the Dashboard

```bash
python dashboard/main.py
```

### Using the API

```python
import requests

# Set up the API client
api_url = "http://localhost:8000"
api_key = "your-api-key"
headers = {
    "X-API-Key": api_key,
    "Content-Type": "application/json"
}

# Process content
response = requests.post(
    f"{api_url}/api/v1/process",
    headers=headers,
    json={
        "content": "Your content here",
        "focus_point": "What you want to extract",
        "content_type": "text/plain"
    }
)

print(response.json())
```

See the [API Documentation](docs/api_reference.md) for more details.

## Development

### Setting Up the Development Environment

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest
```

### Project Structure

* `api_server.py`: The main API server
* `core/`: Core modules and components
* `dashboard/`: Dashboard application
* `docs/`: Documentation
* `tests/`: Tests

See the [Development Guide](docs/development.md) for more details.

## Contributing

Contributions are welcome! Please see the [Contributing Guide](docs/contributing.md) for more details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

