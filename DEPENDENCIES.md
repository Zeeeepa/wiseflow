# WiseFlow Dependencies Documentation

This document provides an overview of the dependencies used in the WiseFlow project, explaining their purpose and usage within the codebase.

## Dependency Management Structure

WiseFlow uses a simplified dependency management approach:

- `requirements.txt`: Contains all core dependencies required for basic functionality
- `requirements-optional.txt`: Optional dependencies for extended features
- `requirements-dev.txt`: Dependencies needed for development and testing

Module-specific requirements:
- `weixin_mp/requirements.txt`: Dependencies specific to the WeChat Mini Program module
- `core/requirements.txt`: Dependencies specific to the core module

## Installation

The recommended way to install dependencies is using the provided installation script:

```bash
# Basic installation (core dependencies only)
python install.py

# Install with optional dependencies
python install.py --optional

# Install with development dependencies
python install.py --dev

# Install all dependencies (core, optional, and dev)
python install.py --all

# Upgrade existing packages to the latest version
python install.py --upgrade
```

The installation script performs the following tasks:
1. Checks Python version compatibility
2. Updates pip to the latest version
3. Installs the required dependencies
4. Sets up the environment (.env file)
5. Checks for additional system requirements
6. Installs Playwright browsers if needed

## Core Dependencies

### HTTP and Networking
- **requests**: HTTP client for making API calls and web requests
- **aiohttp**: Asynchronous HTTP client/server for high-performance web requests
- **httpx**: Modern HTTP client with async support
- **websockets**: WebSocket client and server library for real-time communication

### Web Scraping and Parsing
- **beautifulsoup4**: HTML/XML parsing library for web scraping
- **html2text**: Converts HTML to plain text
- **lxml**: Fast XML and HTML parser
- **cssselect**: CSS selector support for lxml
- **fake-useragent**: Provides various user-agent strings for web scraping
- **playwright**: Browser automation for dynamic content scraping
- **tf-playwright-stealth**: Stealth plugin for Playwright to avoid detection

### Data Processing and Analysis
- **numpy**: Numerical computing library for array operations
- **pandas**: Data manipulation and analysis library
- **matplotlib**: Data visualization library
- **scipy**: Scientific computing library
- **statsmodels**: Statistical models for data analysis
- **networkx**: Network analysis and graph operations
- **scikit-learn**: Machine learning library
- **seaborn**: Statistical data visualization

### Natural Language Processing
- **nltk**: Natural Language Toolkit for text processing
- **langdetect**: Language detection library
- **snowballstemmer**: Stemming algorithms for text processing

### Document Processing
- **PyPDF2**: PDF manipulation library
- **pdf2image**: Converts PDF to images
- **pillow**: Python Imaging Library for image processing

### API and Web Framework
- **fastapi**: Modern, fast web framework for building APIs
- **uvicorn**: ASGI server for FastAPI
- **pydantic**: Data validation and settings management

### Database
- **aiosqlite**: Asynchronous SQLite database interface
- **pocketbase**: Client for PocketBase backend

### Utilities
- **python-dotenv**: Environment variable management
- **asyncio**: Asynchronous I/O, event loop, and coroutines
- **psutil**: Process and system utilities
- **loguru**: Logging library with better formatting
- **tqdm**: Progress bar library
- **rich**: Rich text and formatting in the terminal
- **colorama**: Terminal color support
- **aiofiles**: Asynchronous file operations
- **xxhash**: Fast hash algorithm implementation
- **packaging**: Utilities for package version parsing

### LLM and AI
- **openai**: OpenAI API client for accessing GPT models
- **litellm** (optional): Multi-provider LLM interface
- **langchain** (optional): Framework for LLM applications
- **langgraph** (optional): Graph-based LLM workflows

## Optional Dependencies

### Document Export
- **reportlab**: PDF generation library
- **weasyprint**: HTML to PDF conversion

### External APIs
- **googleapiclient**: Google API client library
- **feedparser**: RSS/Atom feed parser

## Development Dependencies

### Testing
- **pytest**: Testing framework
- **pytest-asyncio**: Async support for pytest
- **pytest-cov**: Code coverage for pytest
- **pytest-mock**: Mocking support for pytest

### Code Quality
- **black**: Code formatter
- **isort**: Import sorter
- **flake8**: Linter
- **mypy**: Static type checker

### Documentation
- **sphinx**: Documentation generator
- **sphinx-rtd-theme**: Read the Docs theme for Sphinx

### Development Tools
- **pre-commit**: Git hooks manager
- **pip-tools**: Dependency management tools

## Dependency Upgrade Guide

When upgrading dependencies, follow these guidelines:

1. **Test thoroughly**: Always test after upgrading dependencies, especially major versions
2. **Check compatibility**: Ensure interdependent packages are compatible
3. **Update gradually**: Update one dependency at a time when possible
4. **Follow semantic versioning**:
   - Major version changes (2.0.0 → 3.0.0): May contain breaking changes
   - Minor version changes (2.1.0 → 2.2.0): New features, no breaking changes
   - Patch version changes (2.1.1 → 2.1.2): Bug fixes only

### Recommended Upgrade Process

1. Create a new virtual environment
2. Install the updated dependencies
3. Run the test suite
4. Check for deprecation warnings
5. Update code to address any breaking changes
6. Document any significant changes in the upgrade

### Handling Dependency Conflicts

If you encounter dependency conflicts:

1. Identify the conflicting packages
2. Check compatibility matrices for the packages
3. Try to find a version that satisfies all requirements
4. If necessary, consider alternative packages with similar functionality
5. Update the requirements files with the resolved versions
