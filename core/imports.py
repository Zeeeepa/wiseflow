#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Centralized imports module for Wiseflow.

This module provides a single place to import all commonly used components,
helping to avoid circular imports and standardize import patterns across the codebase.
"""

# Standard library imports
import os
import sys
import json
import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable, Tuple, Set
from datetime import datetime
from pathlib import Path
from enum import Enum, auto
import re
import uuid
import traceback
from collections import Counter, defaultdict

# Third-party imports
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from loguru import logger

# Core configuration
from core.config import config

# Utility modules
from core.utils.general_utils import (
    get_logger,
    normalize_url,
    url_pattern,
    extract_and_convert_dates,
    is_chinese,
    isURL
)
from core.utils.error_handling import (
    handle_exceptions,
    WiseflowError,
    log_error,
    save_error_to_file
)
from core.utils.pb_api import PbTalker

# LLM modules
from core.llms.openai_wrapper import openai_llm
from core.llms.litellm_wrapper import LiteLLMWrapper

# Agent modules
from core.agents.get_info import (
    pre_process,
    extract_info_from_img,
    get_author_and_publish_date,
    get_more_related_urls,
    get_info
)
from core.agents.insights import (
    generate_trend_analysis,
    generate_entity_analysis,
    generate_insight_summary,
    generate_insights_for_focus,
    get_insights_for_focus
)

# Analysis modules
from core.analysis.entity_extraction import extract_entities
from core.analysis.entity_linking import (
    link_entities,
    merge_entities,
    get_entity_by_id,
    get_entities_by_name,
    update_entity_link,
    visualize_entity_network
)
from core.analysis.multimodal_analysis import process_item_with_images
from core.analysis.multimodal_knowledge_integration import integrate_multimodal_analysis_with_knowledge_graph

# Knowledge graph
from core.knowledge.graph import (
    KnowledgeGraphBuilder,
    build_knowledge_graph,
    enrich_knowledge_graph,
    query_knowledge_graph,
    infer_relationships,
    visualize_knowledge_graph,
    validate_knowledge_graph,
    export_knowledge_graph
)

# Connector modules
from core.connectors import (
    ConnectorBase,
    DataItem,
    WebConnector,
    RSSConnector,
    GitHubConnector,
    YouTubeConnector,
    AcademicConnector,
    initialize_all_connectors
)

# Plugin system
from core.plugins import (
    PluginBase,
    PluginManager,
    load_plugin,
    register_plugin
)

# Reference management
from core.references import (
    ReferenceManager,
    Reference,
    add_reference,
    get_reference,
    search_references
)

# Task management
from core.task_manager import (
    TaskManager,
    TaskDependencyError
)
from core.thread_pool_manager import (
    ThreadPoolManager,
    TaskPriority,
    TaskStatus
)

# Event system
from core.event_system import (
    EventBus,
    Event,
    EventType,
    subscribe,
    unsubscribe,
    publish,
    publish_sync,
    get_history,
    clear_history
)

# Resource monitoring
from core.resource_monitor import ResourceMonitor

# Web crawler
from core.crawl4ai import (
    AsyncWebCrawler,
    CacheMode,
    BrowserConfig,
    CrawlerRunConfig
)

# Initialize project directory
project_dir = config.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)

# Initialize global logger
wiseflow_logger = get_logger('wiseflow', project_dir)

