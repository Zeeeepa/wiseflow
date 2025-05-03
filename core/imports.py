"""
Centralized imports module for WiseFlow.

This module provides a central location for importing common modules and classes
to avoid circular dependencies and improve code organization.
"""

import os
import json
import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple, Set, Callable

# Configure logging
def get_logger(name, project_dir=None):
    """Get a logger with the specified name."""
    from core.utils.general_utils import get_logger as utils_get_logger
    return utils_get_logger(name, project_dir)

# Initialize environment variables
def load_environment():
    """Load environment variables from .env file."""
    from pathlib import Path
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)

# Common constants
PROJECT_DIR = os.environ.get("PROJECT_DIR", "")
if PROJECT_DIR:
    os.makedirs(PROJECT_DIR, exist_ok=True)

# PocketBase API client
def get_pb_client(logger=None):
    """Get a PocketBase API client."""
    from core.utils.pb_api import PbTalker
    return PbTalker(logger)

# LLM models
def get_llm_client(model=None):
    """Get an LLM client."""
    if not model:
        model = os.environ.get("PRIMARY_MODEL", "")
        if not model:
            raise ValueError("PRIMARY_MODEL not set, please set it in environment variables or edit core/.env")
    
    from core.llms.litellm_wrapper import litellm_llm, litellm_llm_async
    return {
        "sync": litellm_llm,
        "async": litellm_llm_async,
        "model": model
    }

# Plugin system
def get_plugin_manager(plugins_dir="core/plugins", config_file="core/plugins/config.json"):
    """Get the plugin manager."""
    from core.plugins.loader import get_plugin_manager as loader_get_plugin_manager
    return loader_get_plugin_manager(plugins_dir, config_file)

# Knowledge graph
def get_knowledge_graph_builder():
    """Get the knowledge graph builder."""
    from core.knowledge.graph import knowledge_graph_builder
    return knowledge_graph_builder

# Entity classes
def get_entity_classes():
    """Get entity and relationship classes."""
    from core.analysis import Entity, Relationship, KnowledgeGraph
    return {
        "Entity": Entity,
        "Relationship": Relationship,
        "KnowledgeGraph": KnowledgeGraph
    }

# Data item class
def get_data_item_class():
    """Get the DataItem class."""
    from core.connectors import DataItem
    return DataItem

# Connector base class
def get_connector_base():
    """Get the ConnectorBase class."""
    from core.connectors import ConnectorBase
    return ConnectorBase

# Plugin base classes
def get_plugin_base_classes():
    """Get plugin base classes."""
    from core.plugins.base import BasePlugin, ConnectorPlugin, ProcessorPlugin, AnalyzerPlugin
    return {
        "BasePlugin": BasePlugin,
        "ConnectorPlugin": ConnectorPlugin,
        "ProcessorPlugin": ProcessorPlugin,
        "AnalyzerPlugin": AnalyzerPlugin
    }

# Specialized prompting
def get_specialized_prompt_processor():
    """Get the specialized prompt processor."""
    from core.llms.advanced.specialized_prompting import SpecializedPromptProcessor
    return SpecializedPromptProcessor

