"""
PocketBase API client for the dashboard.

This module provides a wrapper for the PocketBase API client.
"""

import os
import sys
from pocketbase import PocketBase
from pocketbase.client import FileUpload
from typing import BinaryIO, Optional, List, Dict

# Add the parent directory to the path to allow importing from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.utils.pb_api import PbTalker  # Import the original PbTalker

# Re-export the PbTalker class
__all__ = ['PbTalker']

