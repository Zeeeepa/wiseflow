#!/usr/bin/env python3
"""
Migration script for Wiseflow restructuring.

This script helps migrate from the old project structure to the new structure.
It copies files from the old structure to the new structure, updating imports as needed.
"""

import os
import sys
import shutil
import re
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("migration.log")
    ]
)
logger = logging.getLogger(__name__)

# Define migration mappings
FILE_MAPPINGS = {
    # Resource monitor
    "core/resource_monitor.py": "wiseflow/system/resource_monitor.py",
    "dashboard/resource_monitor.py": "wiseflow/system/resource_monitor.py",
    
    # Task management
    "core/task_manager.py": "wiseflow/system/task_manager.py",
    "core/task/__init__.py": "wiseflow/system/task_manager.py",
    "core/task/config.py": "wiseflow/system/task_manager.py",
    "core/task/monitor.py": "wiseflow/system/task_manager.py",
    "core/thread_pool_manager.py": "wiseflow/system/thread_pool.py",
    
    # API
    "api_server.py": "wiseflow/api/server.py",
    "core/api/client.py": "wiseflow/api/client.py",
    
    # Analysis
    "core/analysis/__init__.py": "wiseflow/core/analysis/entities.py",
    "core/knowledge/graph.py": "wiseflow/core/analysis/knowledge_graph.py",
    "core/analysis/entity_extraction.py": "wiseflow/core/analysis/entities.py",
    "core/analysis/entity_linking.py": "wiseflow/core/analysis/knowledge_graph.py",
    "core/analysis/pattern_recognition.py": "wiseflow/core/analysis/patterns.py",
    "core/analysis/trend_analysis.py": "wiseflow/core/analysis/trends.py",
    "core/analysis/data_mining.py": "wiseflow/core/analysis/mining.py",
    
    # Connectors
    "core/connectors/__init__.py": "wiseflow/core/connectors/base.py",
    "core/connectors/web/__init__.py": "wiseflow/core/connectors/web.py",
    "core/connectors/github/__init__.py": "wiseflow/core/connectors/github.py",
    "core/connectors/academic/__init__.py": "wiseflow/core/connectors/academic.py",
    "core/connectors/youtube/__init__.py": "wiseflow/core/connectors/youtube.py",
    "core/connectors/code_search/__init__.py": "wiseflow/core/connectors/code_search.py",
    
    # Extraction
    "core/crawl4ai/async_webcrawler.py": "wiseflow/core/extraction/crawler.py",
    "core/crawl4ai/content_scraping_strategy.py": "wiseflow/core/extraction/scraper.py",
    "core/crawl4ai/processors/__init__.py": "wiseflow/core/extraction/processor.py",
    
    # LLM
    "core/llms/__init__.py": "wiseflow/core/llm/base.py",
    "core/llms/openai_wrapper.py": "wiseflow/core/llm/openai.py",
    "core/llms/litellm_wrapper.py": "wiseflow/core/llm/base.py",
    "core/llms/advanced/specialized_prompting.py": "wiseflow/core/llm/specialized.py",
    
    # Plugins
    "core/plugins/__init__.py": "wiseflow/core/plugins/base.py",
    "core/plugins/loader.py": "wiseflow/core/plugins/loader.py",
    "core/plugins/utils.py": "wiseflow/core/plugins/utils.py",
    
    # Utils
    "core/utils/general_utils.py": "wiseflow/core/utils/general.py",
    "core/utils/export_infos.py": "wiseflow/core/utils/export.py",
    "core/utils/pb_api.py": "wiseflow/core/utils/io.py",
    
    # Dashboard
    "dashboard/__init__.py": "wiseflow/dashboard/__init__.py",
    "dashboard/main.py": "wiseflow/dashboard/main.py",
    "dashboard/visualization/__init__.py": "wiseflow/dashboard/visualization/__init__.py",
}

# Define import mappings
IMPORT_MAPPINGS = {
    "from core.resource_monitor import": "from wiseflow.system.resource_monitor import",
    "from core.task_manager import": "from wiseflow.system.task_manager import",
    "from core.thread_pool_manager import": "from wiseflow.system.thread_pool import",
    "from core.task import": "from wiseflow.system.task_manager import",
    "from core.analysis import": "from wiseflow.core.analysis.entities import",
    "from core.knowledge.graph import": "from wiseflow.core.analysis.knowledge_graph import",
    "from core.analysis.entity_extraction import": "from wiseflow.core.analysis.entities import",
    "from core.analysis.entity_linking import": "from wiseflow.core.analysis.knowledge_graph import",
    "from core.analysis.pattern_recognition import": "from wiseflow.core.analysis.patterns import",
    "from core.analysis.trend_analysis import": "from wiseflow.core.analysis.trends import",
    "from core.analysis.data_mining import": "from wiseflow.core.analysis.mining import",
    "from core.connectors import": "from wiseflow.core.connectors.base import",
    "from core.connectors.web import": "from wiseflow.core.connectors.web import",
    "from core.connectors.github import": "from wiseflow.core.connectors.github import",
    "from core.connectors.academic import": "from wiseflow.core.connectors.academic import",
    "from core.connectors.youtube import": "from wiseflow.core.connectors.youtube import",
    "from core.connectors.code_search import": "from wiseflow.core.connectors.code_search import",
    "from core.crawl4ai.async_webcrawler import": "from wiseflow.core.extraction.crawler import",
    "from core.crawl4ai.content_scraping_strategy import": "from wiseflow.core.extraction.scraper import",
    "from core.crawl4ai.processors import": "from wiseflow.core.extraction.processor import",
    "from core.llms import": "from wiseflow.core.llm.base import",
    "from core.llms.openai_wrapper import": "from wiseflow.core.llm.openai import",
    "from core.llms.litellm_wrapper import": "from wiseflow.core.llm.base import",
    "from core.llms.advanced.specialized_prompting import": "from wiseflow.core.llm.specialized import",
    "from core.plugins import": "from wiseflow.core.plugins.base import",
    "from core.plugins.loader import": "from wiseflow.core.plugins.loader import",
    "from core.plugins.utils import": "from wiseflow.core.plugins.utils import",
    "from core.utils.general_utils import": "from wiseflow.core.utils.general import",
    "from core.utils.export_infos import": "from wiseflow.core.utils.export import",
    "from core.utils.pb_api import": "from wiseflow.core.utils.io import",
    "from dashboard import": "from wiseflow.dashboard import",
    "from dashboard.main import": "from wiseflow.dashboard.main import",
    "from dashboard.visualization import": "from wiseflow.dashboard.visualization import",
    "import core.": "import wiseflow.core.",
    "import dashboard.": "import wiseflow.dashboard.",
}

def update_imports(content: str) -> str:
    """
    Update imports in the file content.
    
    Args:
        content: File content
        
    Returns:
        Updated file content
    """
    updated_content = content
    
    for old_import, new_import in IMPORT_MAPPINGS.items():
        updated_content = updated_content.replace(old_import, new_import)
    
    return updated_content

def migrate_file(src_path: str, dest_path: str) -> bool:
    """
    Migrate a file from the old structure to the new structure.
    
    Args:
        src_path: Source file path
        dest_path: Destination file path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create destination directory if it doesn't exist
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        # Read source file
        with open(src_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update imports
        updated_content = update_imports(content)
        
        # Write to destination file
        with open(dest_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        logger.info(f"Migrated {src_path} to {dest_path}")
        return True
    except Exception as e:
        logger.error(f"Error migrating {src_path} to {dest_path}: {e}")
        return False

def migrate_project():
    """Migrate the project from the old structure to the new structure."""
    logger.info("Starting migration...")
    
    # Create new directory structure
    for dest_path in set(FILE_MAPPINGS.values()):
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    # Migrate files
    success_count = 0
    failure_count = 0
    
    for src_path, dest_path in FILE_MAPPINGS.items():
        if os.path.exists(src_path):
            if migrate_file(src_path, dest_path):
                success_count += 1
            else:
                failure_count += 1
        else:
            logger.warning(f"Source file {src_path} does not exist")
    
    logger.info(f"Migration completed: {success_count} files migrated successfully, {failure_count} failures")

if __name__ == "__main__":
    migrate_project()

