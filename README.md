# WiseFlow

WiseFlow is a powerful Python framework that uses LLMs to extract valuable information from massive amounts of data across various sources. It helps you focus on what matters most by intelligently processing and analyzing content.

## 🚀 Version 2.0 - Major Upgrade

We're excited to announce WiseFlow 2.0, a major upgrade that brings significant improvements in performance, security, and functionality.

### What's New in 2.0

- **Enhanced Performance**: Improved concurrency, caching, and resource management
- **Better Security**: Added JWT authentication, API key management, and input validation
- **Modern API**: Upgraded to FastAPI with improved error handling and documentation
- **Expanded LLM Support**: Better integration with multiple LLM providers via LiteLLM
- **Improved Metrics**: Comprehensive metrics collection and monitoring
- **Enhanced Caching**: More efficient caching system with Redis support
- **Better Error Handling**: Robust error handling and recovery strategies
- **Comprehensive Documentation**: Improved documentation with MkDocs

### Upgrading from 1.x

If you're upgrading from WiseFlow 1.x, please follow these steps:

1. **Update Dependencies**: Run `pip install -r requirements.txt` to update all dependencies
2. **Configuration Changes**: Review the new configuration options in `core/config.py`
3. **API Changes**: Update your API clients to work with the new FastAPI endpoints
4. **Database Migration**: Run `python scripts/migrate_schema.py` to update your database schema
5. **Review Documentation**: Check the updated documentation for new features and changes

For a detailed migration guide, see [UPGRADING.md](UPGRADING.md).

## 📋 Features

- **Information Extraction**: Extract specific information from various content types
- **Multi-Source Research**: Conduct research across multiple sources simultaneously
- **Entity Analysis**: Identify and analyze entities in your content
- **Knowledge Graph**: Build and visualize knowledge graphs from your data
- **Parallel Processing**: Process multiple tasks concurrently for faster results
- **Customizable Plugins**: Extend functionality with custom plugins
- **Web Dashboard**: Monitor and manage your tasks through a web interface
- **API Integration**: Integrate with other systems through a comprehensive API

## 🛠️ Installation

### Prerequisites

- Python 3.9+
- Redis (optional, for distributed caching)
- PocketBase (for data storage)

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/wiseflow.git
   cd wiseflow
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Run the application:
   ```bash
   python wiseflow.py
   ```

## 🚀 Quick Start

### Basic Usage

```python
from wiseflow import WiseFlow

# Initialize WiseFlow
wf = WiseFlow()

# Process content
result = await wf.process_content(
    content="Your content here",
    focus_point="What you want to extract",
    content_type="text"
)

print(result)
```

### Research Example

```python
from wiseflow import WiseFlow

# Initialize WiseFlow
wf = WiseFlow()

# Start a research task
research_id = await wf.start_research(
    topic="Artificial Intelligence trends in 2025",
    max_depth=3
)

# Get research results
result = await wf.get_research_result(research_id)

print(result)
```

## 📚 Documentation

For detailed documentation, visit [https://wiseflow.readthedocs.io/](https://wiseflow.readthedocs.io/)

## 🧩 Plugins

WiseFlow supports plugins to extend its functionality. See [PLUGINS.md](PLUGINS.md) for more information.

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support, please open an issue on GitHub or contact us at support@wiseflow.ai.

