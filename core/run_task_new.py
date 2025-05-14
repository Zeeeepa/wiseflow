#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enhanced task runner for Wiseflow.

This module provides an enhanced task runner with concurrency and plugin support.
"""

from pathlib import Path
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

import logging
logging.getLogger("httpx").setLevel(logging.WARNING)

import asyncio
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from core.utils.general_utils import get_logger
from core.utils.pb_api import PbTalker
from core.task import AsyncTaskManager, Task, create_task_id
from core.plugins import PluginManager
from core.plugins.connectors import ConnectorBase, DataItem
from core.plugins.processors import ProcessorBase, ProcessedData

# Configure logging
wiseflow_logger = get_logger('wiseflow')

# Initialize PocketBase client
pb = PbTalker(wiseflow_logger)

# Configure the maximum number of concurrent tasks
MAX_CONCURRENT_TASKS = int(os.environ.get("MAX_CONCURRENT_TASKS", "4"))

# Initialize the task manager
task_manager = AsyncTaskManager(max_workers=MAX_CONCURRENT_TASKS)

# Initialize the plugin manager
plugin_manager = PluginManager(plugins_dir="core")
