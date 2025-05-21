#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Directory utilities for WiseFlow.

This module provides utilities for working with directories, including
creating directories, cleaning up temporary directories, and handling
file paths in a cross-platform way.
"""

import os
import shutil
import tempfile
import logging
import platform
from typing import List, Optional, Tuple
from pathlib import Path
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def ensure_directory(path: str) -> str:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        Absolute path to the directory
    """
    abs_path = os.path.abspath(path)
    os.makedirs(abs_path, exist_ok=True)
    return abs_path

def ensure_directory_for_file(file_path: str) -> str:
    """
    Ensure the directory for a file exists, creating it if necessary.
    
    Args:
        file_path: File path
        
    Returns:
        Absolute path to the directory
    """
    directory = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(directory, exist_ok=True)
    return directory

def create_temp_directory(base_dir: Optional[str] = None, prefix: str = "wiseflow_") -> str:
    """
    Create a temporary directory.
    
    Args:
        base_dir: Base directory for the temporary directory
        prefix: Prefix for the temporary directory name
        
    Returns:
        Path to the temporary directory
    """
    if base_dir:
        os.makedirs(base_dir, exist_ok=True)
        return tempfile.mkdtemp(dir=base_dir, prefix=prefix)
    return tempfile.mkdtemp(prefix=prefix)

def create_temp_file(base_dir: Optional[str] = None, prefix: str = "wiseflow_", suffix: str = "") -> str:
    """
    Create a temporary file.
    
    Args:
        base_dir: Base directory for the temporary file
        prefix: Prefix for the temporary file name
        suffix: Suffix for the temporary file name
        
    Returns:
        Path to the temporary file
    """
    if base_dir:
        os.makedirs(base_dir, exist_ok=True)
        fd, path = tempfile.mkstemp(dir=base_dir, prefix=prefix, suffix=suffix)
    else:
        fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
    
    os.close(fd)
    return path

def clean_temp_directory(directory: str, max_age_days: int = 7) -> int:
    """
    Clean up old files in a temporary directory.
    
    Args:
        directory: Directory to clean
        max_age_days: Maximum age of files in days
        
    Returns:
        Number of files removed
    """
    if not os.path.exists(directory):
        return 0
        
    cutoff_time = time.time() - (max_age_days * 86400)
    count = 0
    
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.getctime(item_path) < cutoff_time:
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to remove old temp file/directory {item_path}: {e}")
                
    return count

def get_platform_specific_path(path: str) -> str:
    """
    Convert a path to a platform-specific path.
    
    Args:
        path: Path to convert
        
    Returns:
        Platform-specific path
    """
    # Convert to Path object to handle platform-specific path separators
    return str(Path(path))

def get_absolute_path(path: str) -> str:
    """
    Get the absolute path for a path.
    
    Args:
        path: Path to convert
        
    Returns:
        Absolute path
    """
    # Expand user directory if path starts with ~
    if path.startswith("~"):
        path = os.path.expanduser(path)
        
    return os.path.abspath(path)

def get_relative_path(path: str, base_path: str) -> str:
    """
    Get the relative path for a path.
    
    Args:
        path: Path to convert
        base_path: Base path to make the path relative to
        
    Returns:
        Relative path
    """
    return os.path.relpath(path, base_path)

def list_files(directory: str, pattern: Optional[str] = None, recursive: bool = False) -> List[str]:
    """
    List files in a directory.
    
    Args:
        directory: Directory to list files in
        pattern: Optional glob pattern to filter files by
        recursive: Whether to list files recursively
        
    Returns:
        List of file paths
    """
    import glob
    
    if not os.path.exists(directory):
        return []
        
    if pattern:
        if recursive:
            return glob.glob(os.path.join(directory, "**", pattern), recursive=True)
        return glob.glob(os.path.join(directory, pattern))
        
    result = []
    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                result.append(os.path.join(root, file))
    else:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path):
                result.append(item_path)
                
    return result

def get_file_size(file_path: str) -> int:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Size of the file in bytes
    """
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return 0
        
    return os.path.getsize(file_path)

def get_file_modification_time(file_path: str) -> float:
    """
    Get the modification time of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Modification time of the file as a timestamp
    """
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return 0
        
    return os.path.getmtime(file_path)

def get_directory_size(directory: str) -> int:
    """
    Get the total size of a directory in bytes.
    
    Args:
        directory: Path to the directory
        
    Returns:
        Total size of the directory in bytes
    """
    if not os.path.exists(directory) or not os.path.isdir(directory):
        return 0
        
    total_size = 0
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if os.path.isfile(file_path):
                total_size += os.path.getsize(file_path)
                
    return total_size

def copy_directory(src: str, dst: str, overwrite: bool = False) -> bool:
    """
    Copy a directory.
    
    Args:
        src: Source directory
        dst: Destination directory
        overwrite: Whether to overwrite existing files
        
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(src) or not os.path.isdir(src):
        logger.error(f"Source directory does not exist: {src}")
        return False
        
    if os.path.exists(dst) and not overwrite:
        logger.error(f"Destination directory already exists: {dst}")
        return False
        
    try:
        if os.path.exists(dst) and overwrite:
            shutil.rmtree(dst)
            
        shutil.copytree(src, dst)
        return True
    except Exception as e:
        logger.error(f"Error copying directory {src} to {dst}: {e}")
        return False

def move_directory(src: str, dst: str, overwrite: bool = False) -> bool:
    """
    Move a directory.
    
    Args:
        src: Source directory
        dst: Destination directory
        overwrite: Whether to overwrite existing files
        
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(src) or not os.path.isdir(src):
        logger.error(f"Source directory does not exist: {src}")
        return False
        
    if os.path.exists(dst) and not overwrite:
        logger.error(f"Destination directory already exists: {dst}")
        return False
        
    try:
        if os.path.exists(dst) and overwrite:
            shutil.rmtree(dst)
            
        shutil.move(src, dst)
        return True
    except Exception as e:
        logger.error(f"Error moving directory {src} to {dst}: {e}")
        return False

def remove_directory(directory: str, ignore_errors: bool = False) -> bool:
    """
    Remove a directory.
    
    Args:
        directory: Directory to remove
        ignore_errors: Whether to ignore errors
        
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(directory) or not os.path.isdir(directory):
        return True
        
    try:
        shutil.rmtree(directory, ignore_errors=ignore_errors)
        return True
    except Exception as e:
        if not ignore_errors:
            logger.error(f"Error removing directory {directory}: {e}")
        return False

def get_system_temp_dir() -> str:
    """
    Get the system temporary directory.
    
    Returns:
        Path to the system temporary directory
    """
    return tempfile.gettempdir()

def is_path_writable(path: str) -> bool:
    """
    Check if a path is writable.
    
    Args:
        path: Path to check
        
    Returns:
        True if the path is writable, False otherwise
    """
    if os.path.exists(path):
        return os.access(path, os.W_OK)
        
    # Check if parent directory is writable
    parent_dir = os.path.dirname(path)
    if not parent_dir:
        parent_dir = '.'
    return os.access(parent_dir, os.W_OK)

def get_free_space(path: str) -> int:
    """
    Get the free space in bytes for a path.
    
    Args:
        path: Path to check
        
    Returns:
        Free space in bytes
    """
    if not os.path.exists(path):
        path = os.path.dirname(path)
        if not path:
            path = '.'
            
    if platform.system() == 'Windows':
        import ctypes
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value
    else:
        st = os.statvfs(path)
        return st.f_bavail * st.f_frsize

