#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migration script for Wiseflow restructuring.

This script helps users migrate from the old structure to the new structure.
"""

import os
import shutil
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("migration")

def create_directory(path):
    """Create a directory if it doesn't exist."""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {path}: {e}")
        return False

def copy_file(src, dst):
    """Copy a file from source to destination."""
    try:
        shutil.copy2(src, dst)
        logger.info(f"Copied {src} to {dst}")
        return True
    except Exception as e:
        logger.error(f"Error copying {src} to {dst}: {e}")
        return False

def migrate_files():
    """Migrate files from the old structure to the new structure."""
    # Define the migration mappings
    migrations = [
        # Resource monitoring
        ("core/resource_monitor.py", "wiseflow/resource_monitoring/resource_monitor.py"),
        ("dashboard/resource_monitor.py", "wiseflow/resource_monitoring/dashboard_resource_monitor.py"),
        
        # Task management
        ("core/task_manager.py", "wiseflow/task_management/task_manager.py"),
        ("core/thread_pool_manager.py", "wiseflow/task_management/thread_pool_manager.py"),
        ("core/run_task.py", "wiseflow/task_management/run_task.py"),
        ("core/run_task_new.py", "wiseflow/task_management/run_task_new.py"),
        ("core/task/__init__.py", "wiseflow/task_management/legacy_task.py"),
        ("core/task/config.py", "wiseflow/task_management/task_config.py"),
        ("core/task/monitor.py", "wiseflow/task_management/task_monitor.py"),
        
        # Connectors
        ("core/connectors/web/__init__.py", "wiseflow/connectors/web/__init__.py"),
        ("core/connectors/github/__init__.py", "wiseflow/connectors/github/__init__.py"),
        ("core/connectors/academic/__init__.py", "wiseflow/connectors/academic/__init__.py"),
        ("core/connectors/youtube/__init__.py", "wiseflow/connectors/youtube/__init__.py"),
        ("core/connectors/code_search/__init__.py", "wiseflow/connectors/code_search/__init__.py"),
        
        # Analysis
        ("core/analysis/entity_extraction.py", "wiseflow/analysis/entity_extraction/entity_extraction.py"),
        ("core/analysis/entity_linking.py", "wiseflow/analysis/entity_linking/entity_linking.py"),
        ("core/analysis/trend_analysis.py", "wiseflow/analysis/trend_analysis/trend_analysis.py"),
        ("core/knowledge/graph.py", "wiseflow/analysis/knowledge_graph/graph.py"),
        
        # Plugins
        ("core/plugins/analyzers/entity_analyzer.py", "wiseflow/plugins/analyzers/entity_analyzer.py"),
        ("core/plugins/analyzers/trend_analyzer.py", "wiseflow/plugins/analyzers/trend_analyzer.py"),
        ("core/plugins/processors/text/text_processor.py", "wiseflow/plugins/processors/text_processor.py"),
        ("core/plugins/loader.py", "wiseflow/plugins/loader.py"),
        ("core/plugins/utils.py", "wiseflow/plugins/utils.py"),
        
        # API
        ("api_server.py", "wiseflow/api/api_server.py"),
        ("core/api/client.py", "wiseflow/api/client.py"),
        
        # Utils
        ("core/utils/general_utils.py", "wiseflow/utils/general_utils.py"),
        ("core/utils/pb_api.py", "wiseflow/utils/pb_api.py"),
        ("core/utils/exa_search.py", "wiseflow/utils/exa_search.py"),
        ("core/utils/zhipu_search.py", "wiseflow/utils/zhipu_search.py"),
        
        # Config
        ("core/crawl4ai/config.py", "wiseflow/config/crawl4ai_config.py"),
    ]
    
    # Create the new directories
    for _, dst in migrations:
        dst_dir = os.path.dirname(dst)
        if not create_directory(dst_dir):
            logger.error(f"Failed to create directory {dst_dir}")
            return False
    
    # Copy the files
    for src, dst in migrations:
        if os.path.exists(src):
            if not copy_file(src, dst):
                logger.error(f"Failed to copy {src} to {dst}")
                return False
        else:
            logger.warning(f"Source file {src} does not exist, skipping")
    
    return True

def create_init_files():
    """Create __init__.py files in all directories."""
    for root, dirs, _ in os.walk("wiseflow"):
        for dir_name in dirs:
            init_file = os.path.join(root, dir_name, "__init__.py")
            if not os.path.exists(init_file):
                try:
                    with open(init_file, "w") as f:
                        f.write("# This file is part of the Wiseflow package.\n")
                    logger.info(f"Created {init_file}")
                except Exception as e:
                    logger.error(f"Error creating {init_file}: {e}")

def create_main_init():
    """Create the main __init__.py file."""
    init_content = """#!/usr/bin/env python
# -*- coding: utf-8 -*-
\"\"\"
Wiseflow - AI-powered information extraction tool.

This package provides tools for extracting relevant information from various sources
based on user-defined focus points.
\"\"\"

__version__ = "0.1.0"
__author__ = "Wiseflow Team"
__email__ = "info@wiseflow.example.com"
__license__ = "MIT"

# Import commonly used modules
from wiseflow.task_management.run_task import process_focus_task, generate_insights
from wiseflow.resource_monitoring.resource_monitor import ResourceMonitor
from wiseflow.task_management.task_manager import TaskManager
from wiseflow.task_management.thread_pool_manager import ThreadPoolManager, TaskPriority, TaskStatus
from wiseflow.utils.general_utils import get_logger
from wiseflow.utils.pb_api import PbTalker

# Initialize logger
logger = get_logger("wiseflow")
"""
    
    try:
        with open("wiseflow/__init__.py", "w") as f:
            f.write(init_content)
        logger.info("Created wiseflow/__init__.py")
        return True
    except Exception as e:
        logger.error(f"Error creating wiseflow/__init__.py: {e}")
        return False

def create_setup_py():
    """Create setup.py file."""
    setup_content = """#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name="wiseflow",
    version="0.1.0",
    description="AI-powered information extraction tool",
    author="Wiseflow Team",
    author_email="info@wiseflow.example.com",
    url="https://github.com/Zeeeepa/wiseflow",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0,<3.0.0",
        "python-dotenv>=0.15.0,<1.0.0",
        "asyncio>=3.4.3,<4.0.0",
        "psutil>=5.8.0,<6.0.0",
        "pocketbase>=0.8.0,<1.0.0",
        "beautifulsoup4>=4.9.3,<5.0.0",
        "html2text>=2020.1.16,<2023.0.0",
        "httpx>=0.16.1,<1.0.0",
        "aiohttp>=3.7.3,<4.0.0",
        "nltk>=3.6.2,<4.0.0",
        "chardet>=4.0.0,<5.0.0",
        "PyPDF2>=2.0.0,<3.0.0",
        "python-docx>=0.8.11,<1.0.0",
        "numpy>=1.19.5,<2.0.0",
        "pandas>=1.2.0,<2.0.0",
        "tqdm>=4.56.0,<5.0.0",
        "concurrent-futures-extra>=1.0.0,<2.0.0",
        "structlog>=21.1.0,<22.0.0",
        "rich>=10.0.0,<11.0.0",
        "fastapi>=0.68.0,<1.0.0",
        "uvicorn>=0.15.0,<1.0.0",
        "feedparser>=6.0.0,<7.0.0",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
)
"""
    
    try:
        with open("setup.py", "w") as f:
            f.write(setup_content)
        logger.info("Created setup.py")
        return True
    except Exception as e:
        logger.error(f"Error creating setup.py: {e}")
        return False

def create_readme():
    """Create README.md file."""
    readme_content = """# Wiseflow

AI-powered information extraction tool that uses large language models to mine relevant information from various sources based on user-defined focus points.

## Overview

Wiseflow is designed as a "wide search" system that collects broad information from various sources, as opposed to "deep search" systems that focus on answering specific questions. The key features include:

1. **Web Crawling**: Uses Crawl4ai to extract content from websites
2. **LLM-based Information Extraction**: Processes content using large language models to extract relevant information
3. **Focus Points**: User-defined topics of interest that guide information extraction
4. **PocketBase Database**: Stores extracted information and configuration
5. **Scheduling System**: Periodically crawls sources based on configured frequencies
6. **Plugin Architecture**: Supports extensibility through plugins for different data sources and processors

## New Directory Structure

The project has been restructured for better organization and maintainability:

```
wiseflow/
├── task_management/     # Task scheduling and execution
├── resource_monitoring/ # System resource monitoring
├── connectors/          # Data source connectors
│   ├── web/
│   ├── github/
│   ├── academic/
│   ├── youtube/
│   └── code_search/
├── analysis/            # Data analysis components
│   ├── entity_extraction/
│   ├── entity_linking/
│   ├── trend_analysis/
│   └── knowledge_graph/
├── plugins/             # Plugin system
│   ├── processors/
│   └── analyzers/
├── api/                 # API server and client
├── utils/               # Utility functions
└── config/              # Configuration
```

## Installation

```bash
pip install -e .
```

## Usage

```python
from wiseflow.task_management.run_task import process_focus_task
from wiseflow.utils.pb_api import PbTalker

# Initialize PocketBase client
pb = PbTalker()

# Get focus points
focus_points = pb.read('focus_points', filter='activated=True')
sites = pb.read('sites')

# Process a focus point
for focus in focus_points:
    focus_sites = [s for s in sites if s['id'] in focus.get('sites', [])]
    process_focus_task(focus, focus_sites)
```

## Docker Deployment

```bash
docker-compose up -d
```

## License

MIT
"""
    
    try:
        with open("README.md", "w") as f:
            f.write(readme_content)
        logger.info("Created README.md")
        return True
    except Exception as e:
        logger.error(f"Error creating README.md: {e}")
        return False

def main():
    """Main entry point."""
    logger.info("Starting migration to new structure...")
    
    # Check if the wiseflow directory already exists
    if os.path.exists("wiseflow"):
        logger.warning("The wiseflow directory already exists.")
        response = input("Do you want to continue and potentially overwrite files? (y/n): ")
        if response.lower() != "y":
            logger.info("Migration aborted.")
            return
    
    # Create the wiseflow directory
    if not create_directory("wiseflow"):
        logger.error("Failed to create the wiseflow directory.")
        return
    
    # Migrate files
    if not migrate_files():
        logger.error("Migration failed.")
        return
    
    # Create __init__.py files
    create_init_files()
    
    # Create main __init__.py
    if not create_main_init():
        logger.error("Failed to create main __init__.py.")
        return
    
    # Create setup.py
    if not create_setup_py():
        logger.error("Failed to create setup.py.")
        return
    
    # Create README.md
    if not create_readme():
        logger.error("Failed to create README.md.")
        return
    
    logger.info("Migration completed successfully.")
    logger.info("You can now install the package with: pip install -e .")

if __name__ == "__main__":
    main()

