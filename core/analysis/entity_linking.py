"""
Entity linking module for Wiseflow.

This module provides functionality to link entities across different data sources.
"""

import logging
import json
import uuid
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

import networkx as nx
import matplotlib.pyplot as plt
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from core.utils.general_utils import get_logger

logger = logging.getLogger(__name__)
