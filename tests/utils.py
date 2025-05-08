"""
Utility functions for testing.
"""

import os
import json
import tempfile
from typing import Dict, List, Any, Optional, Union

def create_temp_file(content: str, suffix: str = ".txt") -> str:
    """
    Create a temporary file with the given content.
    
    Args:
        content: The content to write to the file
        suffix: The file suffix (default: .txt)
        
    Returns:
        The path to the temporary file
    """
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, 'w') as f:
        f.write(content)
    return path

def create_temp_json_file(data: Union[Dict, List]) -> str:
    """
    Create a temporary JSON file with the given data.
    
    Args:
        data: The data to write to the file
        
    Returns:
        The path to the temporary file
    """
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f)
    return path

def load_test_data(filename: str) -> Any:
    """
    Load test data from the test_data directory.
    
    Args:
        filename: The name of the file to load
        
    Returns:
        The loaded data
    """
    test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
    filepath = os.path.join(test_data_dir, filename)
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Test data file not found: {filepath}")
    
    if filepath.endswith(".json"):
        with open(filepath, 'r') as f:
            return json.load(f)
    else:
        with open(filepath, 'r') as f:
            return f.read()

def compare_json_objects(obj1: Dict, obj2: Dict, ignore_keys: Optional[List[str]] = None) -> bool:
    """
    Compare two JSON objects for equality, optionally ignoring certain keys.
    
    Args:
        obj1: The first object
        obj2: The second object
        ignore_keys: Keys to ignore in the comparison
        
    Returns:
        True if the objects are equal, False otherwise
    """
    ignore_keys = ignore_keys or []
    
    if not isinstance(obj1, dict) or not isinstance(obj2, dict):
        return obj1 == obj2
    
    keys1 = set(obj1.keys()) - set(ignore_keys)
    keys2 = set(obj2.keys()) - set(ignore_keys)
    
    if keys1 != keys2:
        return False
    
    for key in keys1:
        if isinstance(obj1[key], dict) and isinstance(obj2[key], dict):
            if not compare_json_objects(obj1[key], obj2[key], ignore_keys):
                return False
        elif isinstance(obj1[key], list) and isinstance(obj2[key], list):
            if len(obj1[key]) != len(obj2[key]):
                return False
            for item1, item2 in zip(obj1[key], obj2[key]):
                if isinstance(item1, dict) and isinstance(item2, dict):
                    if not compare_json_objects(item1, item2, ignore_keys):
                        return False
                elif item1 != item2:
                    return False
        elif obj1[key] != obj2[key]:
            return False
    
    return True

def async_test(coro):
    """
    Decorator for running async test functions.
    
    Args:
        coro: The coroutine function to run
        
    Returns:
        A wrapper function that runs the coroutine
    """
    import asyncio
    
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro(*args, **kwargs))
    
    return wrapper

