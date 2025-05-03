# WiseFlow: LLM-Powered Information Extraction and Analysis

**[中文](README.md) | English | [日本語](README_JP.md) | [한국어](README_KR.md)**

🚀 **Use LLMs to dig out what you care about from massive amounts of information and a variety of sources daily!**

We don't lack information, but rather the ability to filter noise from vast amounts of data, allowing valuable information to surface.

🌱 See how WiseFlow helps you save time, filter irrelevant information, and organize your focus points! 🌱

## 🔍 Overview

WiseFlow is an LLM-powered system designed to extract, analyze, and organize information from various sources based on user-defined focus points. It helps users filter through the noise of the internet to find the specific information they care about.

## 🏗️ Architecture

WiseFlow consists of several interconnected modules:

1. **Core Module**: The main processing engine that handles data collection, analysis, and storage.
2. **API Server**: A FastAPI server that provides RESTful endpoints for integration with other systems.
3. **Dashboard**: A web interface for managing focus points, viewing extracted information, and configuring the system.
4. **Connectors**: Modules for connecting to various data sources (web, academic, GitHub, YouTube, etc.).
5. **Plugins**: Extensible components for custom data processing and analysis.

## 🧩 Key Components

### Core Components

- **Crawlers**: Web crawling and data collection from various sources
- **Analyzers**: Text and multimodal content analysis
- **Knowledge Graph**: Entity extraction, relationship mapping, and knowledge representation
- **LLM Integration**: Advanced prompting strategies and specialized processing
- **Task Management**: Concurrent task execution and resource monitoring

### API Server

The API server provides endpoints for:
- Content processing and analysis
- Batch processing of multiple items
- Webhook integration for event notifications
- Integration with external systems

### Dashboard

The dashboard offers:
- Focus point management
- Data visualization
- Search functionality
- Notification system
- Plugin management

## 🔄 Data Flow

1. **Data Collection**: Information is collected from configured sources (websites, RSS feeds, etc.)
2. **Processing**: Content is processed using specialized prompting strategies
3. **Analysis**: Entities, relationships, and insights are extracted
4. **Storage**: Processed information is stored in the database
5. **Retrieval**: Users can access and visualize the extracted information

## 🛠️ Installation and Usage

### Prerequisites

- Python 3.10+
- PocketBase (for database)
- Access to an LLM service (OpenAI, SiliconFlow, etc.)

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/TeamWiseFlow/wiseflow.git
   ```

2. Set up PocketBase:
   ```bash
   chmod +x install_pocketbase
   ./install_pocketbase
   ```

3. Configure environment variables in `core/.env`:
   ```
   LLM_API_KEY=Your_API_KEY
   LLM_API_BASE="https://api.siliconflow.cn/v1"
   PRIMARY_MODEL="deepseek-ai/DeepSeek-R1-Distill-Qwen-14B"
   SECONDARY_MODEL="Qwen/Qwen2.5-14B-Instruct"
   VL_MODEL="deepseek-ai/deepseek-vl2"
   PROJECT_DIR="work_dir"
   PB_API_AUTH="test@example.com|1234567890"
   ```

4. Install dependencies:
   ```bash
   cd wiseflow/core
   pip install -r requirements.txt
   python -m playwright install --with-deps chromium
   ```

5. Run the application:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

### Docker Deployment

For Docker deployment:

1. Copy the environment file:
   ```bash
   cp env_docker .env
   ```

2. Edit the `.env` file with your configuration

3. Start the services:
   ```bash
   docker compose up -d
   ```

## 🔌 Integration

WiseFlow can be integrated with other systems in several ways:

1. **API Integration**: Use the RESTful API endpoints provided by the API server
2. **Webhook Integration**: Configure webhooks to receive notifications on events
3. **Direct Database Access**: Access the PocketBase database directly using SDKs
4. **Plugin Development**: Create custom plugins for specialized processing

## 🧪 Development

### Code Structure

```
wiseflow/
├── api_server.py         # FastAPI server for API endpoints
├── core/                 # Core functionality
│   ├── agents/           # Agent-based processing
│   ├── analysis/         # Data analysis modules
│   ├── connectors/       # Data source connectors
│   ├── crawl4ai/         # Web crawling functionality
│   ├── export/           # Data export utilities
│   ├── knowledge/        # Knowledge graph implementation
│   ├── llms/             # LLM integration
│   ├── plugins/          # Plugin system
│   ├── references/       # Reference management
│   ├── scrapers/         # Web scraping utilities
│   ├── task/             # Task management
│   └── utils/            # Utility functions
├── dashboard/            # Web dashboard
│   ├── plugins/          # Dashboard plugins
│   ├── visualization/    # Data visualization
│   └── main.py           # Dashboard entry point
└── pb/                   # PocketBase database
```

### Adding New Features

1. **New Connectors**: Add new data source connectors in `core/connectors/`
2. **New Analyzers**: Implement new analysis modules in `core/analysis/`
3. **New Plugins**: Create custom plugins in `core/plugins/`
4. **New Visualizations**: Add new visualization components in `dashboard/visualization/`

## 📄 License

This project is licensed under the [Apache 2.0 License](LICENSE).

## 📬 Contact

For any questions or suggestions, please open an [issue](https://github.com/TeamWiseFlow/wiseflow/issues).

## 🤝 Acknowledgements

This project is based on the following excellent open-source projects:

- [crawl4ai](https://github.com/unclecode/crawl4ai) - Open-source LLM Friendly Web Crawler & Scraper
- [pocketbase](https://github.com/pocketbase/pocketbase) - Open Source realtime backend in 1 file
- [python-pocketbase](https://github.com/vaphes/pocketbase) - PocketBase client SDK for Python
- [feedparser](https://github.com/kurtmckee/feedparser) - Parse feeds in Python

The development of this project was inspired by [GNE](https://github.com/GeneralNewsExtractor/GeneralNewsExtractor), [AutoCrawler](https://github.com/kingname/AutoCrawler), and [SeeAct](https://github.com/OSU-NLP-Group/SeeAct).

## Citation

If you reference or cite this project in your work, please include the following information:

```
Author: WiseFlow Team
https://github.com/TeamWiseFlow/wiseflow
Licensed under Apache 2.0
```

