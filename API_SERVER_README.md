# WiseFlow API Server and Dashboard

## Overview

WiseFlow API Server and Dashboard provide a powerful interface for LLM-based information extraction and analysis. This README provides instructions on how to set up and run the API server and dashboard.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Zeeeepa/wiseflow.git
   cd wiseflow
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file in the root directory with the following environment variables:

```
# API Server Configuration
WISEFLOW_API_KEY=your_api_key_here
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false
DEBUG=false

# LLM Configuration
PRIMARY_MODEL=gpt-3.5-turbo

# Project Configuration
PROJECT_DIR=/path/to/project/directory
```

## Running the API Server

To run the API server:

```bash
python api_server.py
```

The API server will be available at `http://localhost:8000`.

## Running the Dashboard

To run the dashboard:

```bash
uvicorn dashboard.main:app --host 0.0.0.0 --port 8001
```

The dashboard will be available at `http://localhost:8001`.

## API Documentation

Once the API server is running, you can access the API documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Dashboard Documentation

The dashboard provides the following main pages:

- Home: `http://localhost:8001/dashboard/`
- Search: `http://localhost:8001/dashboard/search`
- Monitor: `http://localhost:8001/dashboard/monitor`
- Data Mining: `http://localhost:8001/dashboard/data-mining`
- Database Management: `http://localhost:8001/dashboard/database`
- Plugins: `http://localhost:8001/dashboard/plugins`
- Templates: `http://localhost:8001/dashboard/templates`
- Visualization: `http://localhost:8001/dashboard/visualization`
- Settings: `http://localhost:8001/dashboard/settings`

## Security Considerations

1. **API Key**: Always use a strong, unique API key in production.
2. **CORS**: Restrict allowed origins to only the domains that need access.
3. **Rate Limiting**: Enable rate limiting to prevent abuse.
4. **Environment Variables**: Never commit sensitive environment variables to version control.

## Troubleshooting

If you encounter any issues:

1. Check the logs for error messages.
2. Ensure all required environment variables are set.
3. Verify that all dependencies are installed correctly.
4. Make sure the required ports are not in use by other applications.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

